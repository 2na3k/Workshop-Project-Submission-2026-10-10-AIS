from api.features.plan.service import resolve_recipe_causes


def test_present_evidence_cause_distinct():
    assert resolve_recipe_causes(["present-evidence-excludes"]) == [
        "present-evidence-excludes"
    ]
    assert resolve_recipe_causes(["evidence-absent"]) == ["evidence-absent"]
    assert resolve_recipe_causes(["unmapped"]) == ["unmapped"]


def test_multi_cause_precedence():
    causes = resolve_recipe_causes(
        ["unmapped", "evidence-absent", "present-evidence-excludes", "unmapped"]
    )

    assert causes == [
        "present-evidence-excludes",
        "evidence-absent",
        "unmapped",
    ]
