# fb303

Hand-maintained Bazel overlay for the fb303 snapshot used by Watchman.

The overlay exposes only the C++ counters and service-data targets needed by
EdenCommon and Watchman. Update `overlay/BUILD.bazel` when the pinned upstream
snapshot changes.
