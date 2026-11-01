"""Version traceability, including generated-artifact-only commits."""
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

import version


class VersionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="pcb-version-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.change_root = patch.object(version, "ROOT", self.root)
        self.change_root.start()
        self.addCleanup(self.change_root.stop)
        self.git("init", "-q")
        self.source = self.root / "circuit.json"
        self.source.write_text('{"rail": 3.3}\n')

    def git(self, *args):
        return subprocess.check_output(["git", "-C", str(self.root),
                                        "-c", "user.name=Version fixture",
                                        "-c", "user.email=fixture@example.invalid", *args], text=True).strip()

    def commit_source(self):
        self.git("add", "circuit.json")
        self.git("commit", "-qm", "Synthetic circuit fixture")
        return self.git("rev-parse", "HEAD")

    def test_uncommitted_sources_use_real_source_digest(self):
        initial = version.identify([self.source])
        self.assertIsNone(initial["git_commit"])
        self.assertTrue(initial["design_sources_dirty"])
        self.assertIn("src-" + initial["source_sha256"][:12], initial["silkscreen_identifier"])
        self.source.write_text('{"rail": 12}\n')
        self.assertNotEqual(initial["source_sha256"], version.identify([self.source])["source_sha256"])

    def test_source_commit_and_dirty_changes_are_distinguished(self):
        commit = self.commit_source()
        clean = version.identify([self.source])
        self.assertEqual(clean["git_commit"], commit)
        self.assertFalse(clean["design_sources_dirty"])
        self.source.write_text('{"rail": 12}\n')
        dirty = version.identify([self.source])
        self.assertEqual(dirty["git_commit"], commit)
        self.assertTrue(dirty["design_sources_dirty"])
        self.assertTrue(dirty["silkscreen_identifier"].endswith("-dirty"))
        self.assertNotEqual(clean["source_sha256"], dirty["source_sha256"])

    def test_artifact_commit_does_not_create_recursive_silkscreen_change(self):
        commit = self.commit_source()
        before = version.identify([self.source])
        (self.root / "board.generated.json").write_text(json.dumps(before))
        self.git("add", "board.generated.json")
        self.git("commit", "-qm", "Synthetic generated artifact fixture")
        self.assertNotEqual(self.git("rev-parse", "HEAD"), commit)
        self.assertEqual(version.identify([self.source]), before)

    def test_untracked_design_source_marks_existing_commit_dirty(self):
        self.commit_source()
        extra = self.root / "footprint.kicad_mod"
        extra.write_text("synthetic footprint input\n")
        record = version.identify([extra, self.source])
        self.assertTrue(record["design_sources_dirty"])
        self.assertEqual(record, version.identify([self.source, extra]))


if __name__ == "__main__":
    unittest.main(verbosity=2)
