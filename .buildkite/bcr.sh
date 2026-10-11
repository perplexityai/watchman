#!/usr/bin/env bash
set -euo pipefail
source .buildkite/setup.sh
python3 tests/validate_bcr.py
cd tests/bcr
bazel build \
  --registry="file://$GITHUB_WORKSPACE/bcr" \
  --registry=https://bcr.bazel.build \
  --incompatible_autoload_externally=+@rules_cc \
  @watchman//:watchman

