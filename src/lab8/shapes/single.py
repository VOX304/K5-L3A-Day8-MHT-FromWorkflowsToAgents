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

import sqlite3
from typing import Any

from lab8 import durability, mock_llm
from lab8.runtime import run_react
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
    budget = Budget()
    trace = Trace(make_run_id("single", claim_id, seed))
    proposal_amount = 0

    conn = sqlite3.connect(store_path)
    conn.row_factory = sqlite3.Row

    def done(status: str, reason: str | None = None) -> RunResult:
        trace.add(
            "final",
            {
                "status": status,
                "proposal_amount": proposal_amount,
                "error_reason": reason,
            },
        )
        return finish(
            conn,
            shape="single",
            claim_id=claim_id,
            seed=seed,
            status=status,
            proposal_amount=proposal_amount,
            budget=budget,
            trace=trace,
            error_reason=reason,
        )

    # Trạng thái tích lũy qua các bước ReAct (vì run_react chỉ giữ last_tool/last_result trong seen)
    state: dict[str, Any] = {
        "claim": None,
        "order": None,
        "quote": None,
        "history": None,
    }

    def decide(seen: dict[str, Any]) -> dict[str, Any]:
        last_tool = seen.get("last_tool")
        last_result = seen.get("last_result") or {}

        # Cập nhật state từ kết quả tool vừa chạy ở bước trước (không log PII/secret vào trace)
        if last_tool == "get_claim_view":
            state["claim"] = last_result
            trace.add("observation", {"tool": last_tool, "found": bool(last_result.get("found"))})
        elif last_tool == "lookup_order":
            state["order"] = last_result
            trace.add("observation", {"tool": last_tool, "visible": bool(last_result.get("visible"))})
        elif last_tool == "compute_compensation":
            state["quote"] = last_result
            trace.add(
                "observation",
                {
                    "tool": last_tool,
                    "amount_vnd": int(last_result.get("amount_vnd", 0)),
                    "reason": last_result.get("reason"),
                },
            )
        elif last_tool == "lookup_refund_history":
            state["history"] = last_result
            trace.add(
                "observation",
                {
                    "tool": last_tool,
                    "refund_count": last_result.get("refund_count", 0),
                    "refunded_vnd": last_result.get("refunded_vnd", 0),
                },
            )

        # Bước 1: Chưa có thông tin claim -> gọi get_claim_view
        if state["claim"] is None:
            mock_llm.complete(
                budget,
                seed=seed,
                purpose="plan",
                prompt=f"claim_id={claim_id} step=get_claim_view",
            )
            trace.add("agent_step", {"action": "tool", "tool": "get_claim_view"})
            return {"tool": "get_claim_view", "args": {"claim_id": claim_id}}

        claim = state["claim"]
        if not claim.get("found"):
            mock_llm.complete(budget, seed=seed, purpose="decide", prompt="unknown_claim")
            return {"final": {"status": "failed", "error_reason": "unknown_claim"}}

        order_id = claim.get("order_id")
        if not order_id:
            mock_llm.complete(budget, seed=seed, purpose="decide", prompt="missing_order")
            return {"final": {"status": "needs_info", "error_reason": "missing_order"}}

        principal_id = claim["principal_id"]

        # Bước 2: Đã có claim -> đọc ticket để ghi nhận model usage nhưng KHÔNG tin số liệu trong ticket,
        # bắt buộc gọi lookup_order để lấy dữ liệu đơn hàng thực tế.
        if state["order"] is None:
            ticket_text = str(claim.get("ticket") or "")
            mock_llm.complete(budget, seed=seed, purpose="parse", prompt=ticket_text)
            trace.add("agent_step", {"action": "tool", "tool": "lookup_order"})
            return {
                "tool": "lookup_order",
                "args": {"order_id": order_id, "principal_id": principal_id},
            }

        order_result = state["order"]
        if not order_result.get("visible"):
            mock_llm.complete(budget, seed=seed, purpose="decide", prompt="order_not_visible")
            return {
                "final": {
                    "status": "escalated",
                    "error_reason": order_result.get("reason", "order_not_visible"),
                }
            }

        # Bước 3: Tính mức bồi thường dựa trên dữ liệu order row thực tế
        if state["quote"] is None:
            mock_llm.complete(
                budget,
                seed=seed,
                purpose="plan",
                prompt=f"order_id={order_id} step=compute_compensation",
            )
            trace.add("agent_step", {"action": "tool", "tool": "compute_compensation"})
            return {
                "tool": "compute_compensation",
                "args": {"order": order_result["order"]},
            }

        quote = state["quote"]
        amount_vnd = int(quote.get("amount_vnd", 0))
        if amount_vnd <= 0:
            mock_llm.complete(budget, seed=seed, purpose="decide", prompt="zero_entitlement")
            return {
                "final": {
                    "status": "denied",
                    "amount_vnd": 0,
                    "error_reason": "zero_entitlement",
                }
            }

        # Bước 4: Kiểm tra lịch sử hoàn tiền trước đó của đơn hàng (per-order cap awareness)
        if state["history"] is None:
            mock_llm.complete(
                budget,
                seed=seed,
                purpose="plan",
                prompt=f"order_id={order_id} step=lookup_refund_history",
            )
            trace.add("agent_step", {"action": "tool", "tool": "lookup_refund_history"})
            return {
                "tool": "lookup_refund_history",
                "args": {"order_id": order_id, "principal_id": principal_id},
            }

        # Bước 5: Đủ bằng chứng -> trả về full quote (không tự trừ lịch sử hoàn tiền) để host thực thi
        mock_llm.complete(
            budget,
            seed=seed,
            purpose="decide",
            prompt=f"approve order_id={order_id} quote={amount_vnd}",
        )
        return {
            "final": {
                "status": "approve",
                "amount_vnd": amount_vnd,
                "reason": quote.get("reason"),
            }
        }

    try:
        outcome = run_react(
            conn,
            budget,
            observation={"claim_id": claim_id},
            decide=decide,
            max_steps=8,
            worker=True,  # Ép runtime chặn mọi tool không nằm trong READONLY_TOOLS
        )

        final = outcome.get("final") or {}
        if outcome.get("stopped") != "final":
            return done("failed", final.get("error_reason", "step_cap"))

        decision_status = final.get("status")
        if decision_status != "approve":
            return done(
                str(decision_status or "failed"),
                final.get("error_reason"),
            )

        # Host validation: lấy full quote và thực thi ghi duy nhất qua durability.issue_refund
        proposal_amount = int(final.get("amount_vnd", 0))
        trace.add(
            "quote",
            {
                "amount_vnd": proposal_amount,
                "reason": final.get("reason"),
            },
        )
        if proposal_amount <= 0:
            proposal_amount = 0
            return done("denied", "zero_entitlement")

        # Ghi trace xuống file trước khi gọi issue_refund để đảm bảo trace hợp lệ nếu xảy ra crash_at (CP3)
        trace.add("host_call", {"action": "issue_refund", "amount_vnd": proposal_amount})
        trace.write()

        result = durability.issue_refund(
            conn, claim_id, proposal_amount, crash_at=crash_at
        )
        trace.add(
            "host_result",
            {
                "ok": bool(result.get("ok")),
                "reason": result.get("reason"),
                "conflict": bool(result.get("conflict")),
            },
        )

        if result.get("conflict"):
            return done("failed", "amount_conflict")
        if result.get("ok"):
            return done("resolved")
        return done("denied", result.get("reason", "policy_denied"))
    finally:
        conn.close()