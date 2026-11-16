"""Shape A — deterministic refund workflow (CP2 + CP3)."""

from __future__ import annotations

import sqlite3

from lab8 import durability
from lab8.schemas import Budget, RunResult, make_run_id
from lab8.shapes.common import finish
from lab8.tools import (
    compute_compensation,
    get_claim_view,
    lookup_order,
    lookup_refund_history,
    tool_cost,
)
from lab8.trace import Trace


def run_claim(
    claim_id: str,
    *,
    seed: int,
    store_path: str,
    crash_at: str | None = None,
) -> RunResult:
    budget = Budget()
    trace = Trace(make_run_id("workflow", claim_id, seed))
    proposal_amount = 0

    conn = sqlite3.connect(store_path)
    conn.row_factory = sqlite3.Row

    def read(fn, *args):
        result = fn(conn, *args)
        budget.add_tool(tool_cost())
        return result

    def done(status: str, reason: str | None = None) -> RunResult:
        trace.add("final", {
            "status": status,
            "proposal_amount": proposal_amount,
            "error_reason": reason,
        })
        return finish(
            conn,
            shape="workflow",
            claim_id=claim_id,
            seed=seed,
            status=status,
            proposal_amount=proposal_amount,
            budget=budget,
            trace=trace,
            error_reason=reason,
        )

    try:
        claim = read(get_claim_view, claim_id)
        if not claim.get("found"):
            return done("failed", "unknown_claim")

        order_id = claim.get("order_id")
        if not order_id:
            return done("needs_info", "missing_order")

        principal_id = claim["principal_id"]
        order_result = read(lookup_order, order_id, principal_id)
        if not order_result.get("visible"):
            return done("escalated", order_result.get("reason", "order_not_visible"))

        # The order row, not the customer's ticket, is authoritative.
        quote = read(compute_compensation, order_result["order"])
        proposal_amount = int(quote["amount_vnd"])
        trace.add("quote", {
            "amount_vnd": proposal_amount,
            "reason": quote.get("reason"),
        })
        if proposal_amount <= 0:
            proposal_amount = 0
            return done("denied", "zero_entitlement")

        # Observe prior refunds; never subtract them from the quote.
        history = read(lookup_refund_history, order_id, principal_id)
        trace.add("refund_history", {
            "refund_count": history.get("refund_count", 0),
            "refunded_vnd": history.get("refunded_vnd", 0),
        })

        # Persist a valid trace before a deliberately injected crash can occur.
        trace.add("host_call", {"action": "issue_refund", "amount_vnd": proposal_amount})
        trace.write()
        result = durability.issue_refund(
            conn, claim_id, proposal_amount, crash_at=crash_at
        )
        trace.add("host_result", {
            "ok": bool(result.get("ok")),
            "reason": result.get("reason"),
            "conflict": bool(result.get("conflict")),
        })

        if result.get("conflict"):
            return done("failed", "amount_conflict")
        if result.get("ok"):
            return done("resolved")
        return done("denied", result.get("reason", "policy_denied"))
    finally:
        conn.close()
