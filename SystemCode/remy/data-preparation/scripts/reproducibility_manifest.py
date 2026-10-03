"""Build the reproducibility manifest for the data-preparation project."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
from collections.abc import Iterable, Mapping, Sequence
from pathlib import Path
from typing import Any

REQUIRED_SOURCES = ("FoodData Central", "recipe dataset", "FairPrice listings")
REQUIRED_MARTS = (
    "node_recipe",
    "node_food_concept",
    "node_food",
    "node_component",
    "edge_requires",
    "edge_fulfills",
    "edge_has_component",
    "graph_quality_manifest",
)
MART_ORDER_KEYS: dict[str, tuple[str, ...]] = {
    "node_recipe": ("recipe_id",),
    "node_food_concept": ("canonical_key",),
    "node_food": ("fdc_id",),
    "node_component": ("component_id",),
    "edge_requires": ("recipe_id", "occurrence_id"),
    "edge_fulfills": ("candidate_key",),
    "edge_has_component": ("id",),
    "graph_quality_manifest": ("entity_type", "entity"),
}
MANIFEST_SCHEMA_VERSION = 1
CONTRACT_VERSION = 1
MART_CONTENT_COLUMNS: dict[str, tuple[str, ...]] = {
    "node_recipe": (
        "recipe_id",
        "title",
        "instructions",
        "image_name",
        "source",
        "source_license",
    ),
    "node_food_concept": (
        "canonical_key",
        "name",
        "status",
        "candidate_count",
        "price_reference_count",
        "cost_ready_count",
        "normalization_version",
    ),
    "node_food": (
        "fdc_id",
        "food_key",
        "description",
        "data_type",
        "brand_name",
        "brand_owner",
        "ingredients",
        "serving_size",
        "serving_size_unit",
        "household_serving_fulltext",
        "package_weight",
        "energy_kcal",
        "protein_g",
        "fat_g",
        "saturated_fat_g",
        "carbohydrate_g",
        "fiber_g",
        "sugars_g",
        "sodium_mg",
        "cholesterol_mg",
        "nutrition_source",
        "nutrition_basis",
        "nutrition_version",
        "nutrition_status",
        "source",
    ),
    "node_component": ("component_id", "name", "source"),
    "edge_requires": (
        "recipe_id",
        "occurrence_id",
        "position",
        "raw_text",
        "cleaned_text",
        "normalized_name",
        "quantity",
        "unit",
        "quantity_status",
        "required_state",
        "choice_group",
        "optional",
        "preparation",
        "source",
    ),
    "edge_fulfills": (
        "candidate_key",
        "food_key",
        "canonical_key",
        "kind",
        "approval_status",
        "mapping_version",
        "price_ref",
        "price_match_status",
        "price_basis",
        "reference_price_minor",
        "currency",
        "currency_source",
        "package_mass_g",
        "package_volume_ml",
        "package_count",
        "cost_basis_compatible",
        "retailer",
        "listing_name",
        "listing_key",
        "source_snapshot_id",
        "price_status",
        "observed_at",
        "freshness_status",
        "halal_status",
        "halal_evidence_kind",
        "halal_evidence_ref",
        "halal_policy_version",
        "halal_valid_until",
        "halal_freshness_status",
        "selection_priority",
        "nutrition_rank",
        "may_allergic",
        "potential_allergens",
        "allergen_evidence_kinds",
        "allergen_screening_status",
        "allergen_policy_version",
        "may_non_vegetarian",
        "vegetarian_concerns",
        "vegetarian_status",
        "vegetarian_evidence_kind",
        "vegetarian_policy_version",
        "source",
    ),
    "edge_has_component": (
        "id",
        "food_key",
        "component_id",
        "pct_weight",
        "is_refuse",
        "gram_weight",
        "data_points",
        "min_year_acquired",
        "source",
    ),
    "graph_quality_manifest": (
        "entity_type",
        "entity",
        "row_count",
        "allocation",
        "within_allocation",
        "strict_planning_ready",
        "capability_reason",
    ),
}

from typing import TypedDict


class SourceEntry(TypedDict):
    source_identity: str
    snapshot_id: str
    content_checksum: str
    observation_timestamp: str
    paths: list[str]


class MartEntry(TypedDict):
    row_count: int
    content_checksum: str
    content_columns: list[str]
    contract_version: int


class Manifest(TypedDict):
    schema_version: int
    contract_version: int
    sources: list[SourceEntry]
    marts: dict[str, MartEntry]


def _canonical(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, (dt.datetime, dt.date, dt.time)):
        return value.isoformat()
    if isinstance(value, (bytes, bytearray, memoryview)):
        return bytes(value).hex()
    if isinstance(value, Mapping):
        return {
            str(k): _canonical(v)
            for k, v in sorted(value.items(), key=lambda item: str(item[0]))
        }
    if isinstance(value, (list, tuple, set)):
        return [_canonical(item) for item in value]
    if hasattr(value, "as_tuple"):
        return str(value)
    return value


def compute_file_group_checksum(
        paths: Iterable[Path], chunk_size: int = 1024 * 1024,
) -> str:
    digest = hashlib.sha256()
    for path in sorted(
            (Path(path).resolve() for path in paths), key=lambda item: item.as_posix()
    ):
        if not path.is_file() or not os.access(path, os.R_OK):
            raise ValueError(f"source snapshot is missing or unreadable: {path}")
        size = path.stat().st_size
        if size == 0:
            raise ValueError(f"source snapshot is empty: {path}")
        name = path.name.encode("utf-8")
        digest.update(len(name).to_bytes(8, "big"))
        digest.update(name)
        digest.update(size.to_bytes(8, "big"))
        with path.open("rb") as handle:
            while chunk := handle.read(chunk_size):
                digest.update(chunk)
    return digest.hexdigest()

def compute_rows_checksum(
        rows: Iterable[Mapping[str, Any]], columns: Sequence[str], order_by: Sequence[str]
) -> str:
    canonical_rows = [
        {column: _canonical(row.get(column)) for column in columns} for row in rows
    ]
    canonical_rows.sort(
        key=lambda row: json.dumps(
            [row.get(key) for key in order_by], sort_keys=True, separators=(",", ":")
        )
    )
    digest = hashlib.sha256()
    for row in canonical_rows:
        encoded = json.dumps(row, separators=(",", ":"), ensure_ascii=False).encode(
            "utf-8"
        )
        digest.update(len(encoded).to_bytes(8, "big"))
        digest.update(encoded)
    return digest.hexdigest()


def _read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"cannot read JSON metadata: {path}") from exc
    if not isinstance(value, dict):
        raise TypeError(f"JSON metadata must be an object: {path}")
    return value


def load_source_entries(registry_path: Path) -> list[SourceEntry]:
    registry_path = Path(registry_path).resolve()
    registry = _read_json(registry_path)
    raw_entries = registry.get("sources")
    if not isinstance(raw_entries, list):
        raise TypeError("source registry must contain a sources list")
    found: dict[str, SourceEntry] = {}
    for raw in raw_entries:
        if not isinstance(raw, dict) or not raw.get("source_identity"):
            raise ValueError("every source registry entry needs source_identity")
        identity = str(raw["source_identity"])
        if identity in found:
            raise ValueError(f"duplicate source identity: {identity}")
        paths = raw.get("paths")
        if not isinstance(paths, list) or not paths:
            raise ValueError(f"source has no declared paths: {identity}")
        resolved_paths = [
            Path(path) if Path(path).is_absolute() else registry_path.parent / path
            for path in paths
        ]
        checksum = compute_file_group_checksum(resolved_paths)
        metadata_value = raw.get("metadata_path")
        if not metadata_value:
            raise ValueError(f"source has no capture metadata path: {identity}")
        metadata_path = (
            Path(metadata_value)
            if Path(metadata_value).is_absolute()
            else registry_path.parent / metadata_value
        )
        metadata = _read_json(metadata_path)
        timestamp = (
                metadata.get("observation_timestamp")
                or metadata.get("captured_at")
                or metadata.get("fetched_at")
        )
        if not isinstance(timestamp, str) or not timestamp.strip():
            raise ValueError(
                f"source capture metadata has no observation timestamp: {identity}"
            )
        try:
            dt.datetime.fromisoformat(timestamp)
        except ValueError as exc:
            raise ValueError(
                f"source observation timestamp is invalid: {identity}"
            ) from exc
        snapshot_id = raw.get("snapshot_id")
        if not isinstance(snapshot_id, str) or not snapshot_id.strip():
            raise ValueError(f"source has no snapshot id: {identity}")
        found[identity] = SourceEntry(
            source_identity=identity,
            snapshot_id=snapshot_id,
            paths=[str(path) for path in resolved_paths],
            content_checksum=checksum,
            observation_timestamp=timestamp,
        )
    missing = [item for item in REQUIRED_SOURCES if item not in found]
    extra = sorted(set(found) - set(REQUIRED_SOURCES))
    if missing or extra or len(found) != len(REQUIRED_SOURCES):
        raise ValueError(
            f"source registry must contain exactly three declared sources: missing={missing}, unexpected={extra}"
        )
    return [found[item] for item in REQUIRED_SOURCES]


def compute_mart_entries(database_path: Path) -> dict[str, MartEntry]:
    try:
        from importlib import import_module

        duckdb = import_module("duckdb")
    except ImportError as exc:
        raise ValueError("duckdb is required to compute mart checksums") from exc
    connection = duckdb.connect(str(database_path), read_only=True)
    try:
        entries: dict[str, MartEntry] = {}
        for mart in REQUIRED_MARTS:
            columns = MART_CONTENT_COLUMNS[mart]
            quoted = ", ".join(f'"{column}"' for column in columns)
            try:
                rows = [
                    dict(zip(columns, row))
                    for row in connection.execute(
                        f'select {quoted} from lake.main_mart."{mart}"'
                    ).fetchall()
                ]
            except Exception as exc:
                raise ValueError(f"cannot read required mart: {mart}") from exc
            entries[mart] = MartEntry(
                row_count=len(rows),
                content_checksum=compute_rows_checksum(rows, columns, MART_ORDER_KEYS[mart]),
                content_columns=list(columns),
                contract_version=CONTRACT_VERSION,
            )
        return entries
    finally:
        connection.close()


def build_manifest(
        registry_path: Path, database_path: Path, output_path: Path
) -> Manifest:
    sources = load_source_entries(registry_path)
    marts = compute_mart_entries(database_path)
    manifest: Manifest = {
        "schema_version": MANIFEST_SCHEMA_VERSION,
        "contract_version": CONTRACT_VERSION,
        "sources": sources,
        "marts": marts,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--registry", type=Path, default=Path("reproducibility/source_registry.json")
    )
    parser.add_argument("--database", type=Path, default=Path("target/nonprod.duckdb"))
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("target/nonprod/source_snapshot_manifest.json"),
    )
    args = parser.parse_args()
    try:
        build_manifest(args.registry, args.database, args.output)
    except (OSError, ValueError) as exc:
        parser.error(str(exc))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
