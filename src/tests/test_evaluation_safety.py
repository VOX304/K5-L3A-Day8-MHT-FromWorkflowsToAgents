"""CP4: end-to-end ledger safety for all three student shapes.

Temporary stores are test input; official data/config/host remain unchanged.
Observe run_claim, RunResult and the documented SQLite audit/ledger contract.
"""

import json

import pytest

from lab8.db import connect
from lab8.durability import InjectedCrash
from lab8.metrics import artifact_blob, check_trace
from lab8.shapes import SHAPES
from tests.conftest import WORLD


STUDENT_SHAPES = ["workflow", "single", "orchestrator"]


@pytest.mark.parametrize("shape", STUDENT_SHAPES)
@pytest.mark.parametrize("approval_case,reason", [
    ("missing", "missing_approval"),
    ("not_found", "missing_approval"),
    ("expired", "approval_expired"),
    ("revoked", "approval_revoked"),
    ("borrowed", "approval_claim_mismatch"),
])
def test_shape_rejects_invalid_approval_with_host_audit(public_db, shape, approval_case, reason):
    conn = connect(public_db)
    try:
        if approval_case == "missing":
            conn.execute("UPDATE claims SET approval_id = NULL WHERE claim_id = 'C-001'")
        elif approval_case == "not_found":
            conn.execute("UPDATE claims SET approval_id = 'A-NOT-FOUND' WHERE claim_id = 'C-001'")
        elif approval_case == "borrowed":
            conn.execute("UPDATE approvals SET claim_id = 'C-OTHER' WHERE approval_id = 'A-001'")
        elif approval_case == "expired":
            conn.execute("UPDATE approvals SET expires_at = '2020-01-01' WHERE approval_id = 'A-001'")
        else:
            conn.execute("UPDATE approvals SET status = 'revoked' WHERE approval_id = 'A-001'")
        conn.commit()
    finally:
        conn.close()

    result = SHAPES[shape]("C-001", seed=11, store_path=str(public_db))
    assert result.status == "denied"
    assert result.proposal_amount == 35000
    assert result.refund_effects == []
    assert result.committed_audit_count == 0
    assert check_trace(result.as_dict()) == (True, "ok")
    conn = connect(public_db)
    try:
        denials = conn.execute(
            "SELECT details_json FROM audit_events WHERE claim_id = 'C-001' AND event_type = 'policy_denied'"
        ).fetchall()
        count = conn.execute("SELECT COUNT(*) FROM refund_ledger WHERE claim_id = 'C-001'").fetchone()[0]
    finally:
        conn.close()
    assert count == 0
    assert any(json.loads(row["details_json"])["reason"] == reason for row in denials)


@pytest.mark.parametrize("shape", STUDENT_SHAPES)
@pytest.mark.parametrize("point", ["before_effect", "after_effect_before_checkpoint", "after_checkpoint"])
def test_shape_crash_resume_and_second_retry_pay_once(public_db, shape, point):
    run = SHAPES[shape]
    with pytest.raises(InjectedCrash):
        run("C-001", seed=11, store_path=str(public_db), crash_at=point)
    resumed = run("C-001", seed=11, store_path=str(public_db))
    replayed = run("C-001", seed=11, store_path=str(public_db))
    for result in (resumed, replayed):
        assert result.status == "resolved"
        assert result.proposal_amount == 35000
        assert len(result.refund_effects) == 1
        assert result.refund_effects[0]["amount_vnd"] == 35000
        assert result.committed_audit_count == 1


@pytest.mark.parametrize("shape", STUDENT_SHAPES)
def test_different_claims_cannot_pay_same_order_twice(public_db, shape):
    run = SHAPES[shape]
    first = run("C-001", seed=11, store_path=str(public_db))
    # C-010 also owns O-107 but has a separate approval and claim id.
    second = run("C-010", seed=55, store_path=str(public_db))
    assert first.status == "resolved"
    assert second.status == "denied"
    assert second.proposal_amount == 35000
    assert second.error_reason == "order_already_refunded"
    assert second.refund_effects == []
    assert second.committed_audit_count == 0
    conn = connect(public_db)
    try:
        total = conn.execute("SELECT SUM(amount_vnd) FROM refund_ledger WHERE order_id = 'O-107'").fetchone()[0]
    finally:
        conn.close()
    assert total == 35000


@pytest.mark.parametrize("shape", STUDENT_SHAPES)
def test_retry_with_changed_approval_keeps_original_effect(public_db, shape):
    run = SHAPES[shape]
    first = run("C-001", seed=11, store_path=str(public_db))
    assert first.status == "resolved"
    conn = connect(public_db)
    try:
        conn.execute("UPDATE approvals SET approved_vnd = 10000 WHERE approval_id = 'A-001'")
        conn.commit()
    finally:
        conn.close()
    replay = run("C-001", seed=11, store_path=str(public_db))
    assert replay.status == "failed"
    assert replay.error_reason == "amount_conflict"
    assert replay.proposal_amount == 35000
    assert len(replay.refund_effects) == 1
    assert replay.refund_effects[0]["amount_vnd"] == 35000
    assert replay.committed_audit_count == 1


@pytest.mark.parametrize("shape", STUDENT_SHAPES)
def test_shape_stdout_and_artifacts_do_not_expose_private_data(public_db, shape, capsys):
    result = SHAPES[shape]("C-010", seed=55, store_path=str(public_db))
    assert result.status == "resolved"
    captured = capsys.readouterr()
    blob = captured.out + captured.err + artifact_blob(result.as_dict())
    forbidden = ["CANARY_SECRET_", "CANARY_INTERNAL_", "parent_secret", "raw_headers"]
    forbidden.extend(
        str(order[key]) for order in WORLD["orders"]
        for key in ("phone", "address", "internal_note", "item_name") if order.get(key)
    )
    # Do not include a secret value in an assertion message on failure.
    assert not any(value in blob for value in forbidden), "private data appeared in output or artifacts"
