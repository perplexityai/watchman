#!/usr/bin/env bash
set -euo pipefail
source .buildkite/setup.sh
install_dependencies
python3 -B .buildkite/artifacts_test.py
python3 -B .github/scripts/test-buildkite-release-gate.py

work_dir=$(mktemp -d)
trap 'rm -rf "$work_dir"' EXIT
if [[ "${BUILDKITE_PULL_REQUEST:-false}" != false ]]; then
  [[ "$BUILDKITE_PULL_REQUEST" =~ ^[1-9][0-9]*$ ]] || exit 1
  curl --fail --silent --show-error --location --retry 3 \
    "https://api.github.com/repos/perplexityai/watchman/pulls/$BUILDKITE_PULL_REQUEST" \
    --output "$work_dir/pr.json"
  python3 - "$work_dir" <<'PY'
import json
import pathlib
import re
import sys
directory = pathlib.Path(sys.argv[1])
pr = json.loads((directory / 'pr.json').read_text())
for key in ('base', 'head'):
    sha = pr[key]['sha']
    if not re.fullmatch(r'[0-9a-f]{40}', sha):
        raise ValueError('Invalid pull request SHA')
    (directory / key).write_text(sha)
(directory / 'title').write_text(pr['title'] + '\n')
PY
  base=$(cat "$work_dir/base")
  head=$(cat "$work_dir/head")
  expected_head=${BUILDKITE_PULL_REQUEST_HEAD_COMMIT:-${BUILDKITE_COMMIT:?}}
  if [[ "$head" != "$expected_head" ]] || ! git merge-base --is-ancestor "$head" HEAD; then
    echo 'Pull request head changed; build its current revision' >&2
    exit 1
  fi
  git fetch --no-tags origin "$base"
  if [[ "$(git rev-parse --is-shallow-repository)" == true ]]; then
    git fetch --unshallow origin
  fi
  export PR_TITLE="$(cat "$work_dir/title")"
else
  git log -1 --format=%B HEAD > "$work_dir/message"
  npx --no-install lefthook run commit-msg "$work_dir/message" --force
fi

[[ "${BUILDKITE_PULL_REQUEST:-false}" != false ]] || exit 0
npx --no-install lefthook run commit-msg "$work_dir/title" --force
git rev-list --reverse "$base..$head" > "$work_dir/commits"
while IFS= read -r commit; do
  git show --no-patch --format=%B "$commit" > "$work_dir/message"
  npx --no-install lefthook run commit-msg "$work_dir/message" --force
done < "$work_dir/commits"
