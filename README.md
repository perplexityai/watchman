# Watchman Bazel overlay

Hand-maintained Bazel Central Registry overlay for
[Watchman](https://github.com/facebook/watchman).

The intended consumer API is:

```starlark
bazel_dep(
    name = "watchman",
    version = "2026.07.06.00.bcr.1",
)
```

```sh
bazel build @watchman//:watchman
```

## BCR modules

The ready-to-submit `watchman` registry entry lives under
[`bcr/modules/watchman`](bcr/modules/watchman). It points at the upstream
Watchman archive, layers Bazel files onto the extracted tree, then applies
source patches.

EdenCommon and fb303 remain private implementation repositories created by the
Watchman module. Their BUILD files and source patches ship inside the Watchman
overlay; consumers need only one `bazel_dep`.

The published modules use the consumer's C++ toolchain. They do not register
the development harness's LLVM toolchain or apply root-only module overrides.
Initial overlays support Bazel 7 and 8. Several inherited BCR dependencies
still use native C++ rules removed in Bazel 9; the development harness patches
those dependencies until fixed BCR revisions exist.

BCR presubmit covers Linux x64, Linux arm64, and macOS arm64. Windows remains
available through the hermetic MinGW development target below.

## Development builds

This repository remains a hermetic build and release harness. It uses
[`hermetic-llvm`](https://github.com/hermeticbuild/hermetic-llvm) to build:

- Linux x64 (`x86_64-linux-gnu`)
- Linux arm64 (`aarch64-linux-gnu`)
- Darwin arm64 (`aarch64-apple-darwin`)
- Windows x64 (`x86_64-windows-gnu`)

```sh
bazel build //:watchman-x86_64-linux-gnu
bazel build //:watchman-aarch64-linux-gnu
bazel build //:watchman-aarch64-apple-darwin
bazel build //:watchman-x86_64-windows-gnu
```

Build every distribution binary:

```sh
bazel build //:dist
```

Run a smoke test on its matching host:

```sh
tests/watchman_smoke_test.sh /path/to/watchman
```

```powershell
tests/watchman_smoke_test.ps1 -Watchman C:\path\to\watchman.exe
```

Install development hooks once after cloning:

```sh
npm ci
```

Commit messages and pull request titles use Conventional Commits.

## License

Copyright 2026 Perplexity AI.

Licensed under the [Apache License 2.0](LICENSE).
