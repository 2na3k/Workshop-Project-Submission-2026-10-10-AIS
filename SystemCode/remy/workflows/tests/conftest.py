from dataclasses import dataclass

import pytest


@dataclass
class FakeLLM:
    response: object
    calls: int = 0
    provider: str = "fake"
    model: str = "fake-model"

    def invoke(self, prompt: str) -> object:
        self.calls += 1
        return self.response


@pytest.fixture
def fake_llm():
    return FakeLLM(
        {
            "horizon_days": 3,
            "meals_per_day": 2,
            "allergies": [{"code": "peanut", "severity": "severe"}],
            "dietary": [{"code": "vegan"}],
            "nutrient_tolerance_pct": 0,
            "unapplied": [],
        }
    )
