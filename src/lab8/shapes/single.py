"""Shape B — one ReAct agent. Student work.

Use `lab8.runtime.run_react` with max_steps=8. `decide` may pick a read tool.
It must not call `issue_refund`. After the loop, the host validates the quote
and is the only writer.

A decide() that trusts ticket text over the order row will fail hidden claims
where the customer overstates the delay or cites a superseded clause.

Per-order cap: an order may already have been refunded by an earlier claim.
The read tool `lookup_refund_history` shows how much. The host still enforces
the cap, so pass the full quote to `durability.issue_refund`, not a net amount.

Caps: stop at 8 steps. Count model calls in the Budget so cost stays comparable.

Trace contract v1 (docs/contracts.md): return a trace_path to a JSON file written in this run,
{"run_id": <same run_id>, "events": [...]}, on every return path including early
ones. `lab8.trace.Trace` does this; your own tracer is fine if it matches.
"""

from __future__ import annotations

from functools import partial
from typing import Any

from lab8.db import connect
from lab8.durability import issue_refund
from lab8.mock_llm import complete
from lab8.runtime import dispatch, run_react
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
    trace = Trace(make_run_id("single", claim_id, seed))
    result = partial(
        finish, conn, shape="single", claim_id=claim_id, seed=seed,
        budget=budget, trace=trace,
    )
    try:
        claim = dispatch(conn, budget, "get_claim_view", {"claim_id": claim_id}, worker=True)
        trace.add("claim", {"found": claim["found"]})
        if not claim["found"]:
            return result(status="failed", proposal_amount=0, error_reason="unknown_claim")
        if not claim["order_id"]:
            return result(status="needs_info", proposal_amount=0, error_reason="missing_order_id")

        def decide(observation: dict[str, Any]) -> dict[str, Any]:
            last_tool = observation.get("last_tool")
            # MockLLM returns seeded text, not executable tool calls. This bounded
            # adapter maps observation states to read actions; money stays in code.
            complete(budget, seed=seed, purpose="plan", prompt=f"last_tool={last_tool}")
            if last_tool is None:
                return {
                    "tool": "lookup_order",
                    "args": {"order_id": claim["order_id"], "principal_id": claim["principal_id"]},
                }
            observed = observation["last_result"]
            trace.add("observation", {"tool": last_tool, "result": observed})
            if last_tool == "lookup_order":
                if not observed["visible"]:
                    return {"final": {"status": "escalated", "error_reason": observed["reason"]}}
                return {"tool": "compute_compensation", "args": {"order": observed["order"]}}
            return {"final": {"quote": observed}}

        loop = run_react(
            conn, budget, observation={"claim": claim}, decide=decide,
            max_steps=8, worker=True,
        )
        final = loop["final"]
        if "quote" not in final:
            return result(
                status=final["status"], proposal_amount=0,
                error_reason=final.get("error_reason"),
            )
        quote = final["quote"]
        proposal = int(quote["amount_vnd"])
        if proposal <= 0:
            return result(status="denied", proposal_amount=0, error_reason=quote["reason"])

        # The loop has no write tool. Only the host commits, after the loop ends.
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
