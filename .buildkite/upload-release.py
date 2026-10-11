import json
import os
from pathlib import Path
import time
import urllib.error
import urllib.parse
import urllib.request

repo = "perplexityai/watchman"
tag = os.environ["BUILDKITE_TAG"]
headers = {"Authorization": f"Bearer {os.environ['GH_TOKEN']}",
           "Accept": "application/vnd.github+json", "User-Agent": "watchman-buildkite-release"}

def request(url, method="GET", data=None, content_type="application/json"):
    req = urllib.request.Request(url, method=method, data=data,
                                 headers={**headers, "Content-Type": content_type})
    with urllib.request.urlopen(req, timeout=120) as response:
        body = response.read()
        return json.loads(body) if body else None

# Release Please can create the tag before the release exists.
for attempt in range(60):
    try:
        release = request(f"https://api.github.com/repos/{repo}/releases/tags/{tag}")
        break
    except urllib.error.HTTPError as error:
        if error.code != 404 or attempt == 59:
            raise
        time.sleep(10)
upload_url = release["upload_url"].split("{")[0]
if urllib.parse.urlparse(upload_url).hostname != "uploads.github.com":
    raise SystemExit("Unexpected GitHub release upload endpoint")
existing = {asset["name"]: asset["id"] for asset in release["assets"]}
# Remove the old completion marker before replacing any staged asset.
marker = existing.pop("buildkite-release.json", None)
if marker is not None:
    request(f"https://api.github.com/repos/{repo}/releases/assets/{marker}", "DELETE")
paths = sorted(Path("release").iterdir())
# Completion manifest goes last; readers never consume partial uploads.
paths.sort(key=lambda path: path.name == "buildkite-release.json")
for path in paths:
    name = path.name if path.name == "buildkite-release.json" else f"buildkite-{path.name}"
    if name in existing:
        request(f"https://api.github.com/repos/{repo}/releases/assets/{existing[name]}", "DELETE")
    request(f"{upload_url}?{urllib.parse.urlencode({'name': name})}", "POST",
            path.read_bytes(), "application/octet-stream")
    print(f"Uploaded {name}")
