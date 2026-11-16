"""R1 ablation: omit one investigator read, keep the same host and model.

Reuse Nguyen Dac Tuan Nghia's orchestrator in an isolated module instance.
Only the investigator plan changes: remove lookup_refund_history. The host
still re-reads history transactionally. A separate shape/run id prevents
the experiment's traces from overwriting the official orchestrator's traces.
This is a research-card experiment, not a claim for bonus points.
"""

from importlib.util import module_from_spec, spec_from_file_location

from lab8.shapes import orchestrator


_spec = spec_from_file_location("bonus._orchestrator_no_history_impl", orchestrator.__file__)
if _spec is None or _spec.loader is None:
    raise ImportError("cannot load the orchestrator for the controlled ablation")
_variant = module_from_spec(_spec)
_spec.loader.exec_module(_variant)
_variant.SHAPE = "orchestrator_no_history"
_variant.INVESTIGATOR_TOOLS = [
    tool for tool in _variant.INVESTIGATOR_TOOLS if tool != "lookup_refund_history"
]
run_claim = _variant.run_claim
