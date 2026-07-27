# watchman

Hand-maintained Bazel overlay for Watchman.

The published module uses the consumer's C++ toolchain. Hermetic LLVM
toolchains and cross-platform release packaging belong to this repository's
development harness, not the BCR module.

This revision supports Bazel 7 and 8. Inherited BCR dependencies still contain
native C++ rules removed in Bazel 9.

EdenCommon and fb303 are private repositories created from pinned upstream
snapshots. Their BUILD files live under `overlay/bazel/third_party`; consumers
do not depend on separate BCR modules.

Update `overlay/BUILD.bazel`, the upstream URL, source integrity, and version
configuration in `patches/watchman-bazel.patch` together for each Watchman
release.
