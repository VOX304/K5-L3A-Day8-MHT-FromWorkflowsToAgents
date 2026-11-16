"""The experimental plan must preserve money decisions and crash safety."""

import pytest

from bonus.orchestrator_no_history import run_claim as run_variant
from lab8.db import init_store
from lab8.durability import InjectedCrash
from lab8.shapes.orchestrator import run_claim as run_baseline
from lab8.tools import tool_cost
from tests.conftest import CLAIMS, WORLD


@pytest.mark.parametrize("claim_id", ["C-001", "C-002", "C-004", "C-005", "C-013", "C-014"])
def test_omitting_history_read_preserves_financial_result(tmp_path, claim_id):
    results = []
    for label, run in (("baseline", run_baseline), ("variant", run_variant)):
        store = tmp_path / f"{label}.sqlite"
        init_store(store, WORLD, CLAIMS).close()
        results.append(run(claim_id, seed=55, store_path=str(store)))
    baseline, variant = results
    assert variant.shape == "orchestrator_no_history"
    assert variant.run_id != baseline.run_id
    assert variant.trace_path != baseline.trace_path
    assert (variant.status, variant.proposal_amount, variant.refund_effects, variant.committed_audit_count) == (
        baseline.status, baseline.proposal_amount, baseline.refund_effects, baseline.committed_audit_count,
    )
    assert variant.error_reason == baseline.error_reason
    assert variant.model_calls == baseline.model_calls
    assert (variant.input_tokens, variant.output_tokens) == (baseline.input_tokens, baseline.output_tokens)
    saved_reads = 0 if claim_id == "C-004" else 1
    assert baseline.tool_calls - variant.tool_calls == saved_reads
    assert baseline.cost_estimate - variant.cost_estimate == pytest.approx(saved_reads * tool_cost())


@pytest.mark.parametrize("point", ["before_effect", "after_effect_before_checkpoint", "after_checkpoint"])
def test_experimental_plan_keeps_host_crash_safety(public_db, point):
    with pytest.raises(InjectedCrash):
        run_variant("C-001", seed=11, store_path=str(public_db), crash_at=point)
    result = run_variant("C-001", seed=11, store_path=str(public_db))
    assert result.status == "resolved"
    assert len(result.refund_effects) == 1
    assert result.refund_effects[0]["amount_vnd"] == 35000
    assert result.committed_audit_count == 1
