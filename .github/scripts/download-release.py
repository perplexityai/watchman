"""Wait for Buildkite's completed release upload and verify before publishing."""
import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess
import time

repo = "perplexityai/watchman"
tag = os.environ["RELEASE_TAG"]
if os.environ["GITHUB_REPOSITORY"] != repo or not re.fullmatch(r"v[0-9]+\.[0-9]+\.[0-9]+(?:\.bcr\.[1-9][0-9]*)?", tag):
    raise ValueError("Unexpected release repository or tag")
commit = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
if subprocess.check_output(["git", "rev-parse", f"refs/tags/{tag}^{{commit}}"], text=True).strip() != commit:
    raise ValueError("Release tag moved")
subprocess.run(["git", "merge-base", "--is-ancestor", commit, "origin/main"], check=True)
root = Path("release")
root.mkdir()
# GitHub CLI downloads public assets without forwarding tokens to storage hosts.
for attempt in range(270):
    result = subprocess.run(["gh", "release", "download", tag, "--pattern", "buildkite-release.json", "--dir", str(root), "--clobber"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if result.returncode == 0:
        break
    time.sleep(20)
else:
    raise TimeoutError("Buildkite release artifacts missing after 90 minutes")
spec = importlib.util.spec_from_file_location("artifacts", ".buildkite/artifacts.py")
artifacts = importlib.util.module_from_spec(spec)
spec.loader.exec_module(artifacts)
manifest = json.loads((root / "buildkite-release.json").read_text())
expected = {"commit": commit, "pipeline": "watchman"}
for key, value in expected.items():
    if manifest.get(key) != value:
        raise ValueError(f"Release artifact {key} mismatch")
build_url = manifest.get("build", "")
if not re.fullmatch(r"https://buildkite\.com/perplexity/watchman/builds/[1-9][0-9]*", build_url):
    raise ValueError("Unexpected producer build URL")
if set(manifest["files"]) != artifacts.FILES:
    raise ValueError("Unexpected release artifacts")
for name in sorted(artifacts.FILES):
    subprocess.run(["gh", "release", "download", tag, "--pattern", "buildkite-" + name, "--dir", str(root)], check=True)
    (root / ("buildkite-" + name)).rename(root / name)
artifacts.verify(root, expected)
print(f"Verified {commit}: {build_url}")
