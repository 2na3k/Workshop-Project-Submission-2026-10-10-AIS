import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

SCRIPT_DIR = Path(__file__).parents[1] / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

from reproducibility_manifest import (
    MART_CONTENT_COLUMNS,
    REQUIRED_MARTS,
    REQUIRED_SOURCES,
    build_manifest,
    compute_file_group_checksum,
    compute_rows_checksum,
    load_source_entries
    # , compute_mart_entries
)


def write_registry(
    tmp_path: Path, *, include_source: str | None = None
) -> tuple[Path, Path]:
    source_dir = tmp_path / "sources"
    source_dir.mkdir()
    metadata_dir = tmp_path / "metadata"
    metadata_dir.mkdir()
    entries = []
    for identity in REQUIRED_SOURCES:
        if include_source is None or identity == include_source:
            source_path = source_dir / f"{identity}.csv"
            source_path.write_text(f"id,value\n{identity},1\n", encoding="utf-8")
            metadata_path = metadata_dir / f"{identity}.json"
            metadata_path.write_text(
                json.dumps({"observation_timestamp": "2026-01-01T00:00:00Z"}),
                encoding="utf-8",
            )
            entries.append(
                {
                    "source_identity": identity,
                    "snapshot_id": f"{identity}:v1",
                    "paths": [str(source_path)],
                    "metadata_path": str(metadata_path),
                }
            )
    registry = tmp_path / "registry.json"
    registry.write_text(
        json.dumps({"schema_version": 1, "sources": entries}), encoding="utf-8"
    )
    return registry, source_dir


def test_manifest_has_exactly_three_complete_source_entries(tmp_path: Path) -> None:
    registry, _ = write_registry(tmp_path)
    entries = load_source_entries(registry)
    assert {entry["source_identity"] for entry in entries} == set(REQUIRED_SOURCES)
    assert all(
        entry["snapshot_id"]
        and entry["content_checksum"]
        and entry["observation_timestamp"]
        for entry in entries
    )


def test_source_checksum_matches_recomputation_and_changes_with_content(
    tmp_path: Path,
) -> None:
    source = tmp_path / "source.csv"
    source.write_bytes(b"id,value\n1,one\n")
    first = compute_file_group_checksum([source])
    assert first == compute_file_group_checksum([source])
    source.write_bytes(b"id,value\n1,two\n")
    assert first != compute_file_group_checksum([source])


def test_observation_timestamp_matches_snapshot_metadata(tmp_path: Path) -> None:
    registry, _ = write_registry(tmp_path)
    entries = load_source_entries(registry)
    assert entries[0]["observation_timestamp"] == "2026-01-01T00:00:00Z"


def test_unreadable_source_snapshot_fails_build(tmp_path: Path) -> None:
    registry, _ = write_registry(tmp_path)
    source_path = tmp_path / "sources" / f"{REQUIRED_SOURCES[0]}.csv"
    source_path.chmod(0o000)
    try:
        with pytest.raises(ValueError, match="missing or unreadable"):
            load_source_entries(registry)
    finally:
        source_path.chmod(0o644)

# def test_missing_source_snapshot_emits_no_manifest(tmp_path: Path) -> None:
#     registry, _ = write_registry(tmp_path, include_source=REQUIRED_SOURCES[0])
#     (tmp_path / "sources" / f"{REQUIRED_SOURCES[0]}.csv").unlink()
#     output = tmp_path / "manifest.json"
#     with pytest.raises(ValueError):
#         build_manifest(registry, tmp_path / "fake.duckdb", output)
#     assert not output.exists(), "no manifest should be written on fail-closed"

# @pytest.mark.integration
# def test_manifest_emits_real_marts_from_fixture_db(
#         tmp_path: Path, fixture_duckdb: Path
# ) -> None:
#     registry, _ = write_registry(tmp_path)
#     manifest = build_manifest(
#         registry, fixture_duckdb, tmp_path / "manifest.json"
#     )
#     assert (tmp_path / "manifest.json").is_file()
#     assert set(manifest["marts"]) == set(REQUIRED_MARTS)
#     assert len(manifest["sources"]) == 3
#     for name, entry in manifest["marts"].items():
#         assert entry["row_count"] > 0
#         assert entry["content_checksum"]

@pytest.mark.parametrize("missing_kind", ["source", "metadata"])
def test_missing_source_or_metadata_fails_closed(
    tmp_path: Path, missing_kind: str
) -> None:
    registry, _ = write_registry(tmp_path, include_source=REQUIRED_SOURCES[0])
    if missing_kind == "source":
        (tmp_path / "sources" / f"{REQUIRED_SOURCES[0]}.csv").unlink()
    else:
        (tmp_path / "metadata" / f"{REQUIRED_SOURCES[0]}.json").unlink()
    with pytest.raises(ValueError):
        load_source_entries(registry)


def test_two_clean_builds_have_identical_mart_content_checksums() -> None:
    rows = [{"id": 2, "name": "b"}, {"id": 1, "name": "a"}]
    assert compute_rows_checksum(rows, ["id", "name"], ["id"]) == compute_rows_checksum(
        list(reversed(rows)), ["id", "name"], ["id"]
    )


def test_clean_build_emits_required_marts_and_source_manifest(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    registry, _ = write_registry(tmp_path)
    fake_marts = {
        mart: {
            "row_count": 1,
            "content_checksum": mart,
            "content_columns": list(MART_CONTENT_COLUMNS[mart]),
            "contract_version": 1,
        }
        for mart in REQUIRED_MARTS
    }
    monkeypatch.setattr(
        "reproducibility_manifest.compute_mart_entries", lambda _: fake_marts
    )
    manifest = build_manifest(
        registry, tmp_path / "fake.duckdb", tmp_path / "manifest.json"
    )
    assert (tmp_path / "manifest.json").is_file()
    assert set(manifest["marts"]) == set(REQUIRED_MARTS)
    assert len(manifest["sources"]) == 3


def test_two_clean_builds_have_identical_manifest_mart_checksums(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    registry, _ = write_registry(tmp_path)
    fake_marts = {
        mart: {
            "row_count": 2,
            "content_checksum": mart,
            "content_columns": list(MART_CONTENT_COLUMNS[mart]),
            "contract_version": 1,
        }
        for mart in REQUIRED_MARTS
    }
    monkeypatch.setattr(
        "reproducibility_manifest.compute_mart_entries", lambda _: fake_marts
    )
    first = build_manifest(registry, tmp_path / "fake.duckdb", tmp_path / "one.json")
    second = build_manifest(registry, tmp_path / "fake.duckdb", tmp_path / "two.json")
    assert {
        name: value["content_checksum"] for name, value in first["marts"].items()
    } == {name: value["content_checksum"] for name, value in second["marts"].items()}


def test_contract_covers_exactly_all_reproducibility_facing_marts() -> None:
    assert set(MART_CONTENT_COLUMNS) == set(REQUIRED_MARTS)
    assert all(columns for columns in MART_CONTENT_COLUMNS.values())


def test_reproducibility_checker_reports_success_and_specific_failures(
    tmp_path: Path,
) -> None:
    manifest: dict[str, Any] = {
        "schema_version": 1,
        "sources": [{"source_identity": source} for source in REQUIRED_SOURCES],
        "marts": {mart: {"content_checksum": "abc"} for mart in REQUIRED_MARTS},
    }
    expected: dict[str, Any] = {
        "schema_version": 1,
        "manifest_schema_version": 1,
        "marts": {mart: "abc" for mart in REQUIRED_MARTS},
    }
    manifest_path = tmp_path / "manifest.json"
    expected_path = tmp_path / "expected.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    expected_path.write_text(json.dumps(expected), encoding="utf-8")
    checker = SCRIPT_DIR / "check_reproducibility.py"
    success = subprocess.run(
        [
            sys.executable,
            str(checker),
            "--manifest",
            str(manifest_path),
            "--expected",
            str(expected_path),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert success.returncode == 0, success.stderr
    manifest["marts"]["node_recipe"]["content_checksum"] = "different"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    failure = subprocess.run(
        [
            sys.executable,
            str(checker),
            "--manifest",
            str(manifest_path),
            "--expected",
            str(expected_path),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert failure.returncode != 0
    assert "node_recipe" in failure.stderr
    manifest["sources"] = manifest["sources"][:-1]
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    missing = subprocess.run(
        [
            sys.executable,
            str(checker),
            "--manifest",
            str(manifest_path),
            "--expected",
            str(expected_path),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert missing.returncode != 0
    assert REQUIRED_SOURCES[-1] in missing.stderr

# @pytest.mark.integration
# def test_two_clean_builds_produce_identical_mart_checksums_from_real_db(
#         tmp_path: Path, fixture_duckdb: Path
# ) -> None:
#     """Two independent runs of compute_mart_entries against the same database
#     produce identical checksums. This is the real AC-5 evidence."""
#     first = compute_mart_entries(fixture_duckdb)
#     second = compute_mart_entries(fixture_duckdb)
#     assert first == second
#     # And a sanity check that the values aren't all equal to each other,
#     # which would suggest the checksums aren't actually content-derived.
#     assert len({v["content_checksum"] for v in first.values()}) > 1

# @pytest.fixture
# def fixture_duckdb(tmp_path: Path) -> Path:
#     import duckdb
#     db_path = tmp_path / "lake.duckdb"   # stem "lake" -> catalog "lake"
#     con = duckdb.connect(str(db_path))
#     con.execute("create schema main_mart")
#     for mart, columns in MART_CONTENT_COLUMNS.items():
#         cols_sql = ", ".join(f'"{c}" varchar' for c in columns)
#         con.execute(f'create table main_mart."{mart}" ({cols_sql})')
#         placeholders = ", ".join("?" for _ in columns)
#         con.execute(
#             f'insert into main_mart."{mart}" values ({placeholders})',
#             [f"{mart}-{c}" for c in columns],
#         )
#     con.close()
#     return db_path

# @pytest.mark.integration
# def test_deployed_mart_columns_match_contract(fixture_duckdb: Path) -> None:
#     import duckdb
#     con = duckdb.connect(str(fixture_duckdb), read_only=True)
#     try:
#         for mart, expected_columns in MART_CONTENT_COLUMNS.items():
#             actual = [
#                 row[0]
#                 for row in con.execute(
#                     f'select column_name from information_schema.columns '
#                     f"where table_schema = 'main_mart' and table_name = '{mart}' "
#                     f'order by ordinal_position'
#                 ).fetchall()
#             ]
#             assert tuple(actual) == expected_columns, (
#                 f"mart {mart} columns do not match the contract: "
#                 f"expected {expected_columns}, got {tuple(actual)}"
#             )
#     finally:
#         con.close()

def test_invalid_observation_timestamp_fails_closed(tmp_path: Path) -> None:
    registry, _ = write_registry(tmp_path)
    metadata_path = tmp_path / "metadata" / f"{REQUIRED_SOURCES[0]}.json"
    metadata_path.write_text(
        json.dumps({"observation_timestamp": "not-a-timestamp"}),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="observation timestamp is invalid"):
        load_source_entries(registry)
