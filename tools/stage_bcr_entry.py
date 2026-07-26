#!/usr/bin/env python3
"""Stage one checked-in module version in a Bazel registry checkout."""

import argparse
import json
import pathlib
import re
import shutil


VERSION_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._+-]*$")


def _read_json(path: pathlib.Path) -> dict:
    return json.loads(path.read_text())


def stage_entry(
    source_registry: pathlib.Path,
    target_registry: pathlib.Path,
    module: str,
    version: str,
) -> pathlib.Path:
    if not VERSION_PATTERN.fullmatch(version):
        raise ValueError(f"invalid module version: {version}")

    source_module = source_registry / "modules" / module
    source_version = source_module / version
    source_metadata_path = source_module / "metadata.json"
    if not source_version.is_dir():
        raise ValueError(f"missing source entry: {source_version}")

    source_metadata = _read_json(source_metadata_path)
    if version not in source_metadata["versions"]:
        raise ValueError(f"{module}@{version} missing from source metadata")

    target_module = target_registry / "modules" / module
    target_version = target_module / version
    target_metadata_path = target_module / "metadata.json"
    target_metadata = (
        _read_json(target_metadata_path) if target_metadata_path.is_file() else {}
    )
    if target_version.exists() or version in target_metadata.get("versions", []):
        raise ValueError(f"{module}@{version} already exists in target registry")

    target_module.mkdir(parents=True, exist_ok=True)
    shutil.copytree(source_version, target_version)

    metadata = dict(source_metadata)
    metadata["versions"] = [*target_metadata.get("versions", []), version]
    metadata["yanked_versions"] = {
        **target_metadata.get("yanked_versions", {}),
        **source_metadata.get("yanked_versions", {}),
    }
    target_metadata_path.write_text(json.dumps(metadata, indent=4) + "\n")
    return target_version


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-registry", type=pathlib.Path, required=True)
    parser.add_argument("--target-registry", type=pathlib.Path, required=True)
    parser.add_argument("--module", required=True)
    parser.add_argument("--version", required=True)
    args = parser.parse_args()

    staged = stage_entry(
        args.source_registry,
        args.target_registry,
        args.module,
        args.version,
    )
    print(f"staged {args.module}@{args.version} at {staged}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
