from backend.agents.state import initial_state
from backend.api.routes import _result


def test_result_reports_failed_state_as_failed():
    state = initial_state("arxiv:1706.03762", "https://github.com/tensorflow/tensor2tensor", "audit_1")
    state["current_node"] = "failed"
    state["errors"].append("boom")

    result = _result(state)

    assert result.status == "failed"
    assert result.errors == ["boom"]

