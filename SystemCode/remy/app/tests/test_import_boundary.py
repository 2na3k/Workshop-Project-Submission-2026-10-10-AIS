from pathlib import Path


def test_workflow_source_does_not_import_api():
    root = Path(__file__).parents[2] / "workflows" / "src" / "workflows"
    assert not any("from api" in path.read_text() or "import api" in path.read_text() for path in root.rglob("*.py"))
