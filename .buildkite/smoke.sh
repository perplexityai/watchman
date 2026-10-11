#!/usr/bin/env bash
set -euo pipefail
work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT
buildkite-agent artifact download 'release/*' "$work" --build "${BUILDKITE_BUILD_ID:?}" --step dist-build
python3 .buildkite/artifacts.py verify "$work/release"
case "$(uname -s)-$(uname -m)" in
  Linux-x86_64) triple=x86_64-linux-gnu ;;
  Darwin-arm64) triple=aarch64-apple-darwin ;;
  *) echo 'Unexpected smoke agent' >&2; exit 1 ;;
esac
binary="$work/release/watchman-$triple"
chmod +x "$binary"
bash tests/watchman_smoke_test.sh "$binary"
