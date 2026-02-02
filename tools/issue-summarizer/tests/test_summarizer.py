import os
import importlib.util

# Load the test shim directly so tests run regardless of PYTHONPATH
_shim_path = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "issue_summarizer.py")
)
spec = importlib.util.spec_from_file_location("issue_summarizer_shim", _shim_path)
shim = importlib.util.module_from_spec(spec)
spec.loader.exec_module(shim)  # type: ignore
summarizer = shim.summarizer


def test_extract_summary_empty_body() -> None:
    issue = {"title": "Test issue", "body": ""}
    out = summarizer.extract_summary(issue)
    assert "Test issue" in out


def test_extract_action_items_bullets() -> None:
    body = """
- Add unit tests for module
- Create CI job
- Document usage
"""
    issue = {"title": "Tasks", "body": body}
    items = summarizer.extract_action_items(issue)
    assert "Add unit tests for module" in items
    assert "Create CI job" in items
    assert "Document usage" in items


def test_summarize_issue_fallback() -> None:
    issue = {"title": "Fix bug", "body": "TODO: Investigate failure\n- Reproduce locally\n- Add regression test"}
    out = summarizer.summarize_issue(issue)
    assert "Fix bug" in out["summary"]
    assert len(out["action_items"]) >= 2
