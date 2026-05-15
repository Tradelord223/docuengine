import json
import tempfile
import unittest
from pathlib import Path
from xml.etree import ElementTree

from docuengine.cli import main
from docuengine.models import BeatPlan, Citation, ProjectSpec, RightsRecord, SourceAsset


class PipelineFixture:
    def project(self) -> ProjectSpec:
        return ProjectSpec(
            topic="metallurgical crucible",
            target_duration_seconds=1200,
            thesis="Wartime material experiments shaped modern alloys.",
            audience="documentary viewers",
            mood="forensic and cinematic",
            pacing="measured with high-intensity archival sequences",
            preset="military_history",
            allowed_providers=["nasa", "dvids", "nara", "wikimedia_commons", "user_upload"],
        )

    def beat(self) -> BeatPlan:
        return BeatPlan(
            id="beat-sr71",
            chapter="The Titanium Phantom",
            claim="The SR-71 required titanium manufacturing techniques beyond conventional aluminum aircraft.",
            narration="The Blackbird was a manufacturing problem disguised as an aircraft.",
            required_visuals=["sr-71", "titanium", "runway"],
            emotional_intensity=0.8,
            citations=[
                Citation(
                    title="NASA SR-71 Fact Sheet",
                    url="https://www.nasa.gov/reference/sr-71-blackbird/",
                    publisher="NASA",
                    accessed_at="2026-05-13",
                )
            ],
        )

    def asset(self) -> SourceAsset:
        rights = RightsRecord(
            source_url="https://www.nasa.gov/reference/sr-71-blackbird/",
            license_id="public_domain",
            attribution="NASA",
            downloaded_at="2026-05-13",
            restrictions=[],
            allowed_usage=["commercial", "transform", "editorial"],
        )
        return SourceAsset(
            id="sr-71-nasa-flight",
            local_path="My Drive/DocuEngine/metallurgical-crucible/proxies/sr71-proxy.mp4",
            source_url=rights.source_url,
            media_type="video",
            provider="nasa",
            metadata={
                "storage": "google_drive",
                "drive_original_path": "My Drive/DocuEngine/metallurgical-crucible/originals/sr71.mov",
                "drive_proxy_path": "My Drive/DocuEngine/metallurgical-crucible/proxies/sr71-proxy.mp4",
                "beat_use": "SR-71 titanium runway sequence",
                "notes": "High desert runway b-roll for the Titanium Phantom chapter",
            },
            checksum="drive-sha256:abc",
            rights=rights,
        )

    def asset_to_dict(self, asset: SourceAsset) -> dict:
        return {
            "id": asset.id,
            "local_path": asset.local_path,
            "source_url": asset.source_url,
            "media_type": asset.media_type,
            "provider": asset.provider,
            "metadata": asset.metadata,
            "checksum": asset.checksum,
            "rights": asset.rights.__dict__,
        }

    def beat_to_dict(self, beat: BeatPlan) -> dict:
        return {
            "id": beat.id,
            "chapter": beat.chapter,
            "claim": beat.claim,
            "narration": beat.narration,
            "required_visuals": beat.required_visuals,
            "emotional_intensity": beat.emotional_intensity,
            "citations": [citation.__dict__ for citation in beat.citations],
        }


class RoughCutPipelineTests(unittest.TestCase):
    def test_prepare_rough_cut_writes_index_timeline_gates_report_and_fcpxml(self):
        fixture = PipelineFixture()
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)
            output = project_dir / "rough.fcpxml"
            (project_dir / "project.json").write_text(json.dumps(fixture.project().__dict__, indent=2), encoding="utf-8")
            (project_dir / "assets.json").write_text(
                json.dumps([fixture.asset_to_dict(fixture.asset())], indent=2),
                encoding="utf-8",
            )
            (project_dir / "beat_plan.json").write_text(
                json.dumps([fixture.beat_to_dict(fixture.beat())], indent=2),
                encoding="utf-8",
            )

            code = main(
                [
                    "prepare-rough-cut",
                    "--project-dir",
                    str(project_dir),
                    "--fcpxml-out",
                    str(output),
                    "--media-root",
                    "/Volumes/GoogleDrive/My Drive",
                ]
            )

            self.assertEqual(code, 0)
            self.assertTrue((project_dir / "clip_index.json").exists())
            self.assertTrue((project_dir / "timeline.json").exists())
            self.assertTrue((project_dir / "review_gates.json").exists())
            report = json.loads((project_dir / "rough_cut_report.json").read_text(encoding="utf-8"))
            self.assertEqual(report["status"], "ready_for_final_cut")
            self.assertEqual(report["clip_count"], 1)
            self.assertEqual(report["fcpxml_path"], str(output))
            parsed = ElementTree.fromstring(output.read_text(encoding="utf-8"))
            self.assertEqual(parsed.tag, "fcpxml")

    def test_prepare_rough_cut_blocks_fcpxml_when_no_assets_exist(self):
        fixture = PipelineFixture()
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)
            output = project_dir / "rough.fcpxml"
            (project_dir / "project.json").write_text(json.dumps(fixture.project().__dict__, indent=2), encoding="utf-8")
            (project_dir / "assets.json").write_text("[]\n", encoding="utf-8")
            (project_dir / "beat_plan.json").write_text(
                json.dumps([fixture.beat_to_dict(fixture.beat())], indent=2),
                encoding="utf-8",
            )

            code = main(["prepare-rough-cut", "--project-dir", str(project_dir), "--fcpxml-out", str(output)])

            self.assertEqual(code, 1)
            self.assertFalse(output.exists())
            report = json.loads((project_dir / "rough_cut_report.json").read_text(encoding="utf-8"))
            self.assertEqual(report["status"], "blocked")
            self.assertIn("source_assets", report["blocked_gates"])


if __name__ == "__main__":
    unittest.main()
