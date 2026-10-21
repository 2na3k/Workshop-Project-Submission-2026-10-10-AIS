"""Validate a generated source snapshot manifest against pinned checksums."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from reproducibility_manifest import (
    MANIFEST_SCHEMA_VERSION,
    REQUIRED_MARTS,
    REQUIRED_SOURCES,
)


def check_manifest(manifest_path: Path, expected_path: Path) -> list[str]:
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        expected = json.loads(expected_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return [f"cannot read reproducibility input: {exc}"]
    errors: list[str] = []
    if manifest.get("schema_version") != MANIFEST_SCHEMA_VERSION:
        errors.append(
            f"manifest schema_version {manifest.get('schema_version')!r} is unsupported"
        )
    if expected.get("manifest_schema_version") != manifest.get("schema_version"):
        errors.append(
            "expected checksum manifest_schema_version does not match manifest"
        )
    source_ids = [
        source.get("source_identity")
        for source in manifest.get("sources", [])
        if isinstance(source, dict)
    ]
    for source in REQUIRED_SOURCES:
        if source_ids.count(source) != 1:
            errors.append(f"missing or duplicate source: {source}")
    if len(source_ids) != len(REQUIRED_SOURCES):
        errors.append("manifest must contain exactly the three declared sources")
    marts = manifest.get("marts", {})
    expected_marts = expected.get("marts", {})
    for mart in REQUIRED_MARTS:
        if mart not in marts:
            errors.append(f"missing mart: {mart}")
        if mart not in expected_marts:
            errors.append(f"missing pinned checksum: {mart}")
    for mart, pinned in expected_marts.items():
        actual = marts.get(mart, {}).get("content_checksum")
        expected_checksum = (
            pinned.get("content_checksum") if isinstance(pinned, dict) else pinned
        )
        if actual != expected_checksum:
            errors.append(f"mart checksum diverged: {mart}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--manifest",
        type=Path,
        default=Path("target/nonprod/source_snapshot_manifest.json"),
    )
    parser.add_argument(
        "--expected", type=Path, default=Path("reproducibility/expected_checksums.json")
    )
    args = parser.parse_args()
    errors = check_manifest(args.manifest, args.expected)
    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 1
    print("reproducibility check passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
