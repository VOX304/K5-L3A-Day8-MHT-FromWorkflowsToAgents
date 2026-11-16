"""Shape C (orchestrator): crash/resume, handoff boundary, trace hygiene.

Chạy cùng bộ student:  python -m pytest -q -m student -o addopts= -k orchestrator
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from lab8.db import connect, init_store
from lab8.durability import InjectedCrash, committed_audit_count, get_refund
from lab8.handoff import ALLOWED_FIELDS, FACT_KEYS, READONLY_TOOLS
from lab8.shapes.orchestrator import run_claim
from tests.conftest import CLAIMS, WORLD

PII_VALUES = [
    str(order[key])
    for order in WORLD["orders"]
    for key in ("phone", "address", "internal_note", "item_name")
    if order.get(key)
]


def _store(tmp_path: Path, name: str) -> str:
    path = tmp_path / name
    init_store(path, WORLD, CLAIMS).close()
    return str(path)


def _events(trace_path: str) -> list[dict]:
    return json.loads(Path(trace_path).read_text(encoding="utf-8"))["events"]


@pytest.mark.student
@pytest.mark.parametrize("crash_at", ["before_effect", "after_effect_before_checkpoint", "after_checkpoint"])
def test_orchestrator_crash_then_resume_keeps_one_refund(tmp_path, crash_at):
    store = _store(tmp_path, f"crash-{crash_at}.sqlite")
    with pytest.raises(InjectedCrash):
        run_claim("C-001", seed=11, store_path=store, crash_at=crash_at)
    result = run_claim("C-001", seed=11, store_path=store)
    conn = connect(store)
    try:
        effect = get_refund(conn, "C-001")
        audits = committed_audit_count(conn, "C-001")
        rows = conn.execute("SELECT COUNT(*) AS n FROM refund_ledger WHERE claim_id = 'C-001'").fetchone()["n"]
    finally:
        conn.close()
    assert result.status == "resolved"
    assert rows == 1 and audits == 1
    assert int(effect["amount_vnd"]) == 35000


@pytest.mark.student
@pytest.mark.parametrize("claim_id", [row["claim_id"] for row in CLAIMS])
def test_orchestrator_trace_has_no_secret_or_pii(tmp_path, claim_id):
    store = _store(tmp_path, f"trace-{claim_id}.sqlite")
    result = run_claim(claim_id, seed=55, store_path=store)
    blob = Path(result.trace_path).read_text(encoding="utf-8")
    assert "CANARY_SECRET_" not in blob
    assert "CANARY_INTERNAL_" not in blob
    assert "parent_secret" not in blob and "raw_headers" not in blob
    for value in PII_VALUES:
        assert value not in blob, f"PII leaked into trace: {value}"


@pytest.mark.student
def test_orchestrator_handoff_is_allowlisted_and_read_only(tmp_path):
    store = _store(tmp_path, "handoff.sqlite")
    result = run_claim("C-001", seed=11, store_path=store)
    handoffs = [e["payload"] for e in _events(result.trace_path) if e["kind"] == "handoff"]
    assert len(handoffs) == 1
    handoff = handoffs[0]
    assert set(handoff) <= ALLOWED_FIELDS
    assert set(handoff["facts"]) <= FACT_KEYS
    assert set(handoff["allowed_tools"]) <= READONLY_TOOLS
    assert handoff["claim_id"] == "C-001"


@pytest.mark.student
def test_orchestrator_ignores_ticket_delay(tmp_path):
    # C-002: ticket nói trễ 5 ngày, order row nói 2 → phải denied ở mọi seed, kể cả 55.
    for seed in (11, 22, 33, 44, 55):
        store = _store(tmp_path, f"t02-{seed}.sqlite")
        result = run_claim("C-002", seed=seed, store_path=store)
        assert result.status == "denied", seed
        assert result.refund_effects == []


@pytest.mark.student
def test_orchestrator_unknown_claim_returns_failed_with_trace(tmp_path):
    store = _store(tmp_path, "unknown.sqlite")
    result = run_claim("C-DOES-NOT-EXIST", seed=11, store_path=store)
    assert result.status == "failed"
    assert result.error_reason == "unknown_claim"
    assert json.loads(Path(result.trace_path).read_text(encoding="utf-8"))["run_id"] == result.run_id
