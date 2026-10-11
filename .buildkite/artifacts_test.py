"""Reject artifacts from another build, another commit, or modified outputs."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
import artifacts

class ArtifactTest(unittest.TestCase):
    def setUp(self):
        self.work = tempfile.TemporaryDirectory()
        self.addCleanup(self.work.cleanup)
        self.root = Path(self.work.name)
        self.expected = {"commit": "a" * 40, "build_id": "build", "pipeline": "overlay"}
        for name in artifacts.FILES:
            (self.root / name).write_bytes(b"binary")
        self.manifest = {**self.expected, "files": {n: artifacts.digest(self.root / n) for n in artifacts.FILES}}
        self.write_manifest()

    def write_manifest(self):
        (self.root / "buildkite-release.json").write_text(json.dumps(self.manifest))

    def test_valid(self):
        artifacts.verify(self.root, self.expected)

    def test_wrong_identity(self):
        for key in self.expected:
            with self.subTest(key=key):
                expected = {**self.expected, key: "other"}
                with self.assertRaises(ValueError):
                    artifacts.verify(self.root, expected)

    def test_modified_binary(self):
        (self.root / next(iter(artifacts.FILES))).write_bytes(b"poisoned")
        with self.assertRaises(ValueError):
            artifacts.verify(self.root, self.expected)

    def test_extra_file(self):
        (self.root / "unexpected").write_text("extra")
        with self.assertRaises(ValueError):
            artifacts.verify(self.root, self.expected)

    def test_missing_file(self):
        (self.root / next(iter(artifacts.FILES))).unlink()
        with self.assertRaises(ValueError):
            artifacts.verify(self.root, self.expected)

    def test_traversal(self):
        self.manifest["files"]["../outside"] = "0" * 64
        self.write_manifest()
        with self.assertRaises(ValueError):
            artifacts.verify(self.root, self.expected)

    def test_symlink(self):
        name = next(iter(artifacts.FILES))
        target = self.root / name
        target.unlink()
        target.symlink_to("/etc/passwd")
        with self.assertRaises(ValueError):
            artifacts.verify(self.root, self.expected)

    def test_manifest_symlink(self):
        marker = self.root / "buildkite-release.json"
        outside = self.root.parent / (self.root.name + "-manifest")
        outside.write_text(marker.read_text())
        self.addCleanup(outside.unlink)
        marker.unlink()
        marker.symlink_to(outside)
        with self.assertRaises(ValueError):
            artifacts.verify(self.root, self.expected)

if __name__ == "__main__":
    unittest.main()
