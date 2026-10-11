#!/usr/bin/env bash
set -euo pipefail
source .buildkite/setup.sh
python3 tests/validate_bcr.py
bazel build -c opt //:dist
mkdir -p release
for triple in x86_64-linux-gnu aarch64-linux-gnu aarch64-apple-darwin x86_64-windows-gnu; do
  mapfile -t outputs < <(bazel cquery -c opt --output=files "//:watchman-$triple")
  [[ ${#outputs[@]} -eq 1 ]]
  name="watchman-$triple"
  [[ "$triple" != x86_64-windows-gnu ]] || name+=.exe
  install -m755 "${outputs[0]}" "release/$name"
done
python3 .buildkite/artifacts.py pack release
