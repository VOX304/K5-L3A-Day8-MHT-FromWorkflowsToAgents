"""Shape C — orchestrator plus read-only investigators. Student work.

1. Build a handoff with `lab8.handoff.make_handoff`. Allowed tools are read-only.
   Never put parent_secret, raw headers, or the full claim row into facts.
2. `lab8.runtime.run_readonly_investigators` runs those tools.
3. The orchestrator quotes from the investigator's order view and calls
   `durability.issue_refund`. Investigators have no write registry.
   Pass the full quote; the host subtracts earlier refunds on the same order.
   `lookup_refund_history` is a read-only tool you may hand to an investigator.
4. Trace the sanitized handoff, not the parent context.

An LLM summary of the parent context is not a sanitizer. Use the allowlist.

Trace contract v1 (docs/contracts.md): return a trace_path to a JSON file written in this run,
{"run_id": <same run_id>, "events": [...]}, on every return path including early
ones. `lab8.trace.Trace` does this; your own tracer is fine if it matches.
"""

from __future__ import annotations

from functools import partial

from lab8.db import connect
from lab8.durability import issue_refund
from lab8.handoff import make_handoff
from lab8.mock_llm import complete
from lab8.runtime import dispatch, run_readonly_investigators
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
    trace = Trace(make_run_id("orchestrator", claim_id, seed))
    result = partial(
        finish, conn, shape="orchestrator", claim_id=claim_id, seed=seed,
        budget=budget, trace=trace,
    )
    try:
        claim = dispatch(conn, budget, "get_claim_view", {"claim_id": claim_id}, worker=True)
        trace.add("claim", {"found": claim["found"]})
        if not claim["found"]:
            return result(status="failed", proposal_amount=0, error_reason="unknown_claim")
        if not claim["order_id"]:
            return result(status="needs_info", proposal_amount=0, error_reason="missing_order_id")

        complete(budget, seed=seed, purpose="plan", prompt="investigate owner order and current policy")
        handoff = make_handoff(
            request_id=f"REQ-{claim_id}", claim_id=claim_id,
            task="check_applicable_policy", facts={},
            allowed_tools=["lookup_order", "lookup_policy", "compute_compensation"],
        )
        trace.add("handoff", handoff)
        investigated = run_readonly_investigators(
            conn, budget, handoff, principal_id=claim["principal_id"],
        )
        order_view = investigated["tools"]["lookup_order"]
        trace.add("order", order_view)
        if not order_view["visible"]:
            return result(status="escalated", proposal_amount=0, error_reason=order_view["reason"])

        quote = investigated["tools"]["compute_compensation"]
        trace.add("quote", quote)
        proposal = int(quote["amount_vnd"])
        if proposal <= 0:
            return result(status="denied", proposal_amount=0, error_reason=quote["reason"])

        # Investigators cannot pay; the orchestrator submits the full quote to the host.
        outcome = issue_refund(conn, claim_id, proposal, crash_at=crash_at)
        status = "resolved" if outcome["ok"] else ("failed" if outcome["conflict"] else "denied")
        trace.add("decision", {"status": status, "reason": outcome["reason"]})
        return result(
            status=status, proposal_amount=proposal,
            error_reason=None if outcome["ok"] else outcome["reason"],
        )
    finally:
        try:
            trace.write()
        finally:
            conn.close()
