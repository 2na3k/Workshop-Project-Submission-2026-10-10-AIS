import json
from pathlib import Path


def test_plan_updated_example_has_explanation():
    api_doc = Path(__file__).resolve().parents[4] / "remy/api/docs/API_doc.md"
    document = api_doc.read_text(encoding="utf-8")
    section = document.split("## 3. POST `/api/v1/chat`", 1)[1].split("## 4.", 1)[0]
    lines = section.splitlines()
    event_index = next(
        index for index, line in enumerate(lines) if line.strip() == "event: plan_updated"
    )
    data_line = next(line.strip() for line in lines[event_index + 1:] if line.strip().startswith("data:"))
    payload = json.loads(data_line.removeprefix("data:").strip())

    assert "delta" in payload
    assert "explanation" in payload
    assert "recipe" in payload["explanation"]
    assert "constraints" in payload["explanation"]
