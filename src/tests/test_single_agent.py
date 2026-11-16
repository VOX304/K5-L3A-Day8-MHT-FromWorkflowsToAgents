"""Unit tests for Shape B (Single Agent) — Nguyen Van Tung."""

from __future__ import annotations

import pytest

from lab8.db import init_store
from lab8.shapes.single import run_claim
from tests.conftest import CLAIMS, WORLD


def _store(tmp_path, name: str):
    path = tmp_path / name
    init_store(path, WORLD, CLAIMS).close()
    return path


def test_single_agent_distrusts_ticket_delay(tmp_path):
    """Claim C-002: Customer claims delay of 5 days in ticket, but order DB row is 2 days (zero entitlement).
    Single agent must check order row and deny, not trust ticket text."""
    store = _store(tmp_path, "single-t02.sqlite")
    res = run_claim("C-002", seed=11, store_path=str(store))
    assert res.status == "denied"
    assert res.proposal_amount == 0


def test_single_agent_step_cap_within_limit(tmp_path):
    """Ensure normal successful claim completes well within max_steps=8."""
    store = _store(tmp_path, "single-t01.sqlite")
    res = run_claim("C-001", seed=11, store_path=str(store))
    assert res.status == "resolved"
    assert res.proposal_amount == 35000
    # Steps: get_claim_view (1), lookup_order (2), compute_compensation (3), lookup_refund_history (4) -> finish
    assert res.tool_calls <= 8
    assert res.model_calls > 0


def test_single_agent_missing_order_needs_info(tmp_path):
    """Claim C-004 has missing order_id -> agent should return needs_info."""
    store = _store(tmp_path, "single-t04.sqlite")
    res = run_claim("C-004", seed=11, store_path=str(store))
    assert res.status == "needs_info"
    assert res.error_reason == "missing_order"
