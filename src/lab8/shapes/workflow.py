"""Shape A — deterministic workflow. Student work.

Signature (do not change):

    run_claim(claim_id, *, seed, store_path, crash_at=None) -> RunResult

Suggested steps. Money stays in code (`lab8.tools.compute_compensation`).

1. Open the store. Read the claim through `get_claim_view` (not SELECT *).
2. Missing order_id -> status `needs_info`. Do not write the ledger.
3. `lookup_order`. If not visible -> `escalated`. Do not copy phone, address, item, internal note.
4. Quote from the order row. Ignore delay numbers written in the ticket.
5. Quote amount 0 -> `denied`. Do not call issue_refund.
6. Quote amount > 0 -> `durability.issue_refund(conn, claim_id, <full quote>)`.
   Pass the FULL quote. The host checks the claim's own approval and subtracts
   what earlier claims already got for the same order (T13, T14). Do not
   subtract it yourself or the host subtracts twice.
   Auth failure or order already refunded -> `denied` (the host writes `policy_denied`).
   `proposal_amount` stays the full quote. Amount conflict -> `failed`.
7. Success -> `resolved`. One ledger row, one `refund_committed` audit.
8. Use MockLLM only to draft the reply text, if you want a model call at all.

The model must not choose the refund amount and must not commit the refund.

Trace contract v1 (docs/contracts.md): return a trace_path to a JSON file written in this run,
{"run_id": <same run_id>, "events": [...]}, on every return path including early
ones. `lab8.trace.Trace` does this; your own tracer is fine if it matches.
"""

from __future__ import annotations

from functools import partial

from lab8.db import connect
from lab8.durability import issue_refund
from lab8.runtime import dispatch
from lab8.schemas import Budget, RunResult, make_run_id
from lab8.shapes.common import finish
from lab8.trace import Trace


def run_claim(
    claim_id: str,
    *,
    seed: int,
    store_path: str,
    crash_at: str | None = None,
) -> RunResult:
    conn = connect(store_path)
    budget = Budget()
    trace = Trace(make_run_id("workflow", claim_id, seed))
    result = partial(
        finish, conn, shape="workflow", claim_id=claim_id, seed=seed,
        budget=budget, trace=trace,
    )
    try:
        claim = dispatch(conn, budget, "get_claim_view", {"claim_id": claim_id}, worker=True)
        # Never trace the ticket: even a safe claim view contains untrusted text.
        trace.add("claim", {"found": claim["found"]})
        if not claim["found"]:
            return result(status="failed", proposal_amount=0, error_reason="unknown_claim")
        if not claim["order_id"]:
            return result(status="needs_info", proposal_amount=0, error_reason="missing_order_id")

        order_view = dispatch(
            conn, budget, "lookup_order",
            {"order_id": claim["order_id"], "principal_id": claim["principal_id"]},
            worker=True,
        )
        trace.add("order", order_view)
        if not order_view["visible"]:
            return result(status="escalated", proposal_amount=0, error_reason=order_view["reason"])

        quote = dispatch(
            conn, budget, "compute_compensation", {"order": order_view["order"]}, worker=True,
        )
        trace.add("quote", quote)
        proposal = int(quote["amount_vnd"])
        if proposal <= 0:
            return result(status="denied", proposal_amount=0, error_reason=quote["reason"])

        # Full entitlement goes to the host, which applies approvals and prior refunds.
        outcome = issue_refund(conn, claim_id, proposal, crash_at=crash_at)
        status = "resolved" if outcome["ok"] else ("failed" if outcome["conflict"] else "denied")
        trace.add("decision", {"status": status, "reason": outcome["reason"]})
        return result(
            status=status, proposal_amount=proposal,
            error_reason=None if outcome["ok"] else outcome["reason"],
        )
    finally:
        # Also flush safe evidence when InjectedCrash propagates to the caller.
        try:
            trace.write()
        finally:
            conn.close()
