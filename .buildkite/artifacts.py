"""Bind distribution artifacts to one producer build and checked-out commit."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

FILES = set(json.loads((Path(__file__).parent / "assets.json").read_text()))

def identity():
    return {"commit": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
            "build_id": os.environ["BUILDKITE_BUILD_ID"],
            "pipeline": os.environ["BUILDKITE_PIPELINE_SLUG"]}

def digest(path):
    with path.open("rb") as stream:
        checksum = hashlib.sha256()
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            checksum.update(chunk)
        return checksum.hexdigest()

def verify(root, expected=None):
    marker = root / "buildkite-release.json"
    if marker.is_symlink():
        raise ValueError("Unsafe artifact manifest")
    manifest = json.loads(marker.read_text())
    for key, value in (expected or identity()).items():
        if manifest.get(key) != value:
            raise ValueError(f"Artifact {key} mismatch")
    if set(manifest["files"]) != FILES or {p.name for p in root.iterdir()} != FILES | {marker.name}:
        raise ValueError("Unexpected artifact set")
    for name in FILES:
        path = root / name
        if path.is_symlink() or not path.is_file() or digest(path) != manifest["files"][name]:
            raise ValueError(f"Artifact checksum mismatch: {name}")
    return manifest

if __name__ == "__main__":
    root = Path(sys.argv[2])
    if sys.argv[1] == "pack":
        if {p.name for p in root.iterdir()} != FILES:
            raise ValueError("Unexpected producer outputs")
        manifest = {**identity(), "build": os.environ["BUILDKITE_BUILD_URL"],
                    "files": {name: digest(root / name) for name in sorted(FILES)}}
        (root / "buildkite-release.json").write_text(json.dumps(manifest, indent=2) + "\n")
    elif sys.argv[1] == "verify":
        verify(root)
    else:
        raise ValueError("Expected pack or verify")
