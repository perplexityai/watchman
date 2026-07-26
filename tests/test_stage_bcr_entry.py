import json
import pathlib
import tempfile
import unittest

from tools.stage_bcr_entry import stage_entry


MODULE = "watchman"
VERSION = "2026.07.06.00.bcr.1"


def write_metadata(module_dir: pathlib.Path, versions: list[str], yanked=None) -> None:
    module_dir.mkdir(parents=True, exist_ok=True)
    (module_dir / "metadata.json").write_text(
        json.dumps(
            {
                "homepage": "https://example.com",
                "maintainers": [],
                "repository": ["github:example/watchman"],
                "versions": versions,
                "yanked_versions": yanked or {},
            }
        )
    )


class StageBcrEntryTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        root = pathlib.Path(self.temp_dir.name)
        self.source = root / "source"
        self.target = root / "target"
        source_module = self.source / "modules" / MODULE
        write_metadata(source_module, [VERSION])
        source_version = source_module / VERSION
        source_version.mkdir()
        (source_version / "MODULE.bazel").write_text('module(name = "watchman")\n')

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_stages_version_and_merges_registry_history(self) -> None:
        target_module = self.target / "modules" / MODULE
        write_metadata(target_module, ["2025.01.01.00"], {"2025.01.01.00": "bad"})

        staged = stage_entry(self.source, self.target, MODULE, VERSION)

        self.assertEqual(
            (staged / "MODULE.bazel").read_text(),
            'module(name = "watchman")\n',
        )
        metadata = json.loads((target_module / "metadata.json").read_text())
        self.assertEqual(metadata["versions"], ["2025.01.01.00", VERSION])
        self.assertEqual(metadata["yanked_versions"], {"2025.01.01.00": "bad"})

    def test_rejects_existing_target_version(self) -> None:
        target_module = self.target / "modules" / MODULE
        write_metadata(target_module, [VERSION])

        with self.assertRaisesRegex(ValueError, "already exists"):
            stage_entry(self.source, self.target, MODULE, VERSION)

        self.assertFalse((target_module / VERSION).exists())

    def test_rejects_version_path_traversal(self) -> None:
        with self.assertRaisesRegex(ValueError, "invalid module version"):
            stage_entry(self.source, self.target, MODULE, "../outside")

        self.assertFalse((self.target / "outside").exists())
