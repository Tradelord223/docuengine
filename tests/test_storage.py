import tempfile
import unittest
from pathlib import Path

from docuengine.storage import (
    GoogleDriveLibraryPlan,
    build_google_drive_library_plan,
    classify_media_location,
    make_project_slug,
)


class StoragePlanningTests(unittest.TestCase):
    def test_make_project_slug_is_filesystem_safe(self):
        self.assertEqual(
            make_project_slug("The Metallurgical Crucible: Wartime Material Experiments!"),
            "the-metallurgical-crucible-wartime-material-experiments",
        )

    def test_build_google_drive_library_plan_keeps_originals_out_of_repo(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = Path(tmpdir) / "repo"
            drive = Path(tmpdir) / "Google Drive" / "My Drive"
            plan = build_google_drive_library_plan(
                drive_root=drive,
                project_title="The Metallurgical Crucible",
                repo_root=repo,
            )

            self.assertIsInstance(plan, GoogleDriveLibraryPlan)
            self.assertEqual(plan.mode, "streamed_originals")
            self.assertEqual(plan.originals_dir, drive / "DocuEngine" / "the-metallurgical-crucible" / "originals")
            self.assertEqual(plan.manifest_path, repo / "projects" / "the-metallurgical-crucible" / "drive_media_manifest.json")
            self.assertNotEqual(plan.originals_dir.parts[: len(repo.parts)], repo.parts)

    def test_build_google_drive_library_plan_accepts_existing_project_slug(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            plan = build_google_drive_library_plan(
                drive_root=Path(tmpdir) / "Drive",
                project_title="Long Display Title",
                repo_root=Path(tmpdir) / "repo",
                project_slug="metallurgical-crucible",
            )

            self.assertEqual(plan.project_slug, "metallurgical-crucible")
            self.assertEqual(plan.repo_project_dir, Path(tmpdir) / "repo" / "projects" / "metallurgical-crucible")

    def test_classify_media_location_detects_drive_streamed_files(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            drive = Path(tmpdir) / "Google Drive"
            media = drive / "My Drive" / "DocuEngine" / "clip.mov"

            location = classify_media_location(media, drive)

            self.assertEqual(location["storage"], "google_drive")
            self.assertEqual(location["locality"], "streamed_or_cached")

    def test_classify_media_location_detects_local_files(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            drive = Path(tmpdir) / "Google Drive"
            media = Path(tmpdir) / "repo" / "proxy.mp4"

            location = classify_media_location(media, drive)

            self.assertEqual(location["storage"], "local")
            self.assertEqual(location["locality"], "local_file")


if __name__ == "__main__":
    unittest.main()
