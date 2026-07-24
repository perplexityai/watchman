# watchman

Hand-maintained Bazel overlay for Watchman.

The published module uses the consumer's C++ toolchain. Hermetic LLVM
toolchains and cross-platform release packaging belong to this repository's
development harness, not the BCR module.

This revision supports Bazel 7 and 8. Inherited BCR dependencies still contain
native C++ rules removed in Bazel 9.

Update `overlay/BUILD.bazel`, the upstream URL, source integrity, and version
configuration in `patches/watchman-bazel.patch` together for each Watchman
release.
