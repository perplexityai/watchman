#!/usr/bin/env python3
"""Validate checked-in BCR overlay entries without network access."""

import base64
import hashlib
import json
import pathlib
import re
import sys


ROOT = pathlib.Path(__file__).resolve().parents[1]
MODULES = ROOT / "bcr" / "modules"
FORBIDDEN_MODULE_CALLS = (
    "archive_override(",
    "git_override(",
    "local_path_override(",
    "multiple_version_override(",
    "register_toolchains(",
    "single_version_override(",
)


def integrity(path: pathlib.Path) -> str:
    digest = hashlib.sha256(path.read_bytes()).digest()
    return "sha256-" + base64.b64encode(digest).decode()


def fail(message: str) -> None:
    raise ValueError(message)


def module_dependencies(module_file: pathlib.Path) -> list[tuple[str, str]]:
    contents = module_file.read_text()
    return re.findall(
        r'bazel_dep\(\s*name\s*=\s*"([^"]+)"\s*,\s*version\s*=\s*"([^"]+)"',
        contents,
    )


def validate_version(module_name: str, version_dir: pathlib.Path) -> None:
    registry_module = version_dir / "MODULE.bazel"
    overlay_module = version_dir / "overlay" / "MODULE.bazel"
    if registry_module.read_bytes() != overlay_module.read_bytes():
        fail(f"{module_name}: registry and overlay MODULE.bazel differ")

    module_contents = registry_module.read_text()
    for call in FORBIDDEN_MODULE_CALLS:
        if call in module_contents:
            fail(f"{module_name}: published MODULE.bazel contains {call}")

    expected_identity = f'name = "{module_name}"'
    if expected_identity not in module_contents:
        fail(f"{module_name}: MODULE.bazel has wrong module name")
    if 'bazel_compatibility = [">=8.0.0"' not in module_contents:
        fail(f"{module_name}: overlays require Bazel compatibility >=8.0.0")

    source = json.loads((version_dir / "source.json").read_text())
    for kind in ("overlay", "patches"):
        base = version_dir / kind
        listed = source.get(kind, {})
        actual_files = (
            {
                path.relative_to(base).as_posix()
                for path in base.rglob("*")
                if path.is_file()
            }
            if base.exists()
            else set()
        )
        if actual_files != set(listed):
            fail(
                f"{module_name}: {kind} inventory differs: "
                f"files={sorted(actual_files)}, metadata={sorted(listed)}"
            )
        for relative_path, expected in listed.items():
            path = base / relative_path
            if not path.is_file():
                fail(f"{module_name}: missing {kind} file {relative_path}")
            actual = integrity(path)
            if actual != expected:
                fail(
                    f"{module_name}: stale integrity for {kind}/{relative_path}: "
                    f"{actual}"
                )


def main() -> int:
    available: dict[str, set[str]] = {}
    dependencies: dict[str, list[tuple[str, str]]] = {}

    for module_dir in sorted(
        path
        for path in MODULES.iterdir()
        if path.is_dir() and (path / "metadata.json").is_file()
    ):
        metadata = json.loads((module_dir / "metadata.json").read_text())
        versions = set(metadata["versions"])
        available[module_dir.name] = versions
        for version in versions:
            version_dir = module_dir / version
            if not version_dir.is_dir():
                fail(f"{module_dir.name}: missing version directory {version}")
            validate_version(module_dir.name, version_dir)
            dependencies[module_dir.name] = module_dependencies(
                version_dir / "MODULE.bazel"
            )

    for module_name, deps in dependencies.items():
        for dependency_name, dependency_version in deps:
            if dependency_name in available and dependency_version not in available[
                dependency_name
            ]:
                fail(
                    f"{module_name}: local dependency {dependency_name}@"
                    f"{dependency_version} is missing"
                )

    print("BCR overlays valid: " + ", ".join(sorted(available)))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(f"error: {error}", file=sys.stderr)
        sys.exit(1)
