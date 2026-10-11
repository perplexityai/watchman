#!/usr/bin/env bash
set -euo pipefail
[[ "${BUILDKITE_PULL_REQUEST:-false}" == false ]]
[[ "${BUILDKITE_TAG:-}" =~ ^v[0-9]+\.[0-9]+\.[0-9]+(\.bcr\.[1-9][0-9]*)?$ ]]
[[ "${BUILDKITE_PIPELINE_SLUG:?}" == "watchman" ]]
[[ "${BUILDKITE_REPO:?}" == "https://github.com/perplexityai/watchman.git" ]]
git fetch --no-tags origin main
[[ "$(git rev-parse HEAD)" == "$BUILDKITE_COMMIT" ]]
git merge-base --is-ancestor HEAD origin/main
work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT
buildkite-agent artifact download 'release/*' "$work" --build "${BUILDKITE_BUILD_ID:?}" --step dist-build
python3 .buildkite/artifacts.py verify "$work/release"
response=$(curl --fail --silent --show-error --request POST \
  --header "Authorization: Token $BUILDKITE_AGENT_ACCESS_TOKEN" \
  --header 'Content-Type: application/json' \
  --data '{"repo_url":"https://github.com/perplexityai/watchman.git","workflow":"bazel-opt.yml","permissions":{"contents":"write"}}' \
  "$BUILDKITE_AGENT_ENDPOINT/jobs/$BUILDKITE_JOB_ID/github_workflow_access_token")
printf '%s' "$response" | buildkite-agent redactor add --format json
GH_TOKEN=$(printf '%s' "$response" | python3 -c 'import json,sys; print(json.load(sys.stdin)["token"])')
export GH_TOKEN
unset response
script="$PWD/.buildkite/upload-release.py"
cd "$work"
python3 "$script"
