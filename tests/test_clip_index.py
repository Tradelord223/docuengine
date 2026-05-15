import json
import tempfile
import unittest
from pathlib import Path

from docuengine.clip_index import build_clip_index
from docuengine.cli import main
from docuengine.models import (
    BeatPlan,
    Citation,
    ProjectSpec,
    RightsRecord,
    SourceAsset,
)


class ClipIndexTests(unittest.TestCase):
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

    def asset(self, **overrides) -> SourceAsset:
        rights = RightsRecord(
            source_url="https://www.nasa.gov/reference/sr-71-blackbird/",
            license_id="public_domain",
            attribution="NASA",
            downloaded_at="2026-05-13",
            restrictions=[],
            allowed_usage=["commercial", "transform", "editorial"],
        )
        data = {
            "id": "sr-71-nasa-flight",
            "local_path": "My Drive/DocuEngine/metallurgical-crucible/proxies/sr71-proxy.mp4",
            "source_url": rights.source_url,
            "media_type": "video",
            "provider": "nasa",
            "metadata": {
                "storage": "google_drive",
                "drive_original_path": "My Drive/DocuEngine/metallurgical-crucible/originals/sr71.mov",
                "drive_proxy_path": "My Drive/DocuEngine/metallurgical-crucible/proxies/sr71-proxy.mp4",
                "beat_use": "SR-71 titanium runway sequence",
                "notes": "High desert runway b-roll for the Titanium Phantom chapter",
            },
            "checksum": "drive-sha256:abc",
            "rights": rights,
        }
        data.update(overrides)
        return SourceAsset(**data)

    def test_build_clip_index_creates_searchable_segments_from_drive_assets(self):
        clips = build_clip_index(self.project(), [self.asset()], [self.beat()])

        self.assertEqual(len(clips), 1)
        self.assertEqual(clips[0].source_asset_id, "sr-71-nasa-flight")
        self.assertEqual(clips[0].rights_status, "approved")
        self.assertGreater(clips[0].visual_quality_score, 0.7)
        self.assertIn("sr-71", clips[0].semantic_tags)
        self.assertIn("titanium", clips[0].semantic_tags)
        self.assertIn("runway", clips[0].transcript.lower())

    def test_build_clip_index_skips_assets_that_fail_rights_policy(self):
        blocked_rights = RightsRecord(
            source_url="https://example.com/clip",
            license_id="cc-by-nc",
            attribution="Example",
            downloaded_at="2026-05-13",
            restrictions=[],
            allowed_usage=["transform"],
        )
        blocked = self.asset(provider="wikimedia_commons", rights=blocked_rights)

        clips = build_clip_index(self.project(), [blocked], [self.beat()])

        self.assertEqual(clips, [])

    def test_build_clip_index_cli_writes_clips_timeline_and_gates(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)
            (project_dir / "project.json").write_text(json.dumps(self.project().__dict__, indent=2), encoding="utf-8")
            (project_dir / "assets.json").write_text(
                json.dumps([self._asset_to_dict(self.asset())], indent=2),
                encoding="utf-8",
            )
            (project_dir / "beat_plan.json").write_text(
                json.dumps([self._beat_to_dict(self.beat())], indent=2),
                encoding="utf-8",
            )

            code = main(["build-clip-index", "--project-dir", str(project_dir)])

            self.assertEqual(code, 0)
            clips = json.loads((project_dir / "clip_index.json").read_text(encoding="utf-8"))
            timeline = json.loads((project_dir / "timeline.json").read_text(encoding="utf-8"))
            gates = json.loads((project_dir / "review_gates.json").read_text(encoding="utf-8"))
            self.assertEqual(clips[0]["source_asset_id"], "sr-71-nasa-flight")
            self.assertEqual(timeline["tracks"][0]["clips"][0]["source_asset_id"], "sr-71-nasa-flight")
            self.assertEqual({gate["gate_type"]: gate["decision"] for gate in gates}["timeline_integrity"], "passed")

    def test_build_clip_index_uses_transcript_sidecar_for_timed_segments(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)
            sidecars = project_dir / "sidecars"
            sidecars.mkdir()
            (sidecars / "sr71.transcript.json").write_text(
                json.dumps(
                    {
                        "segments": [
                            {
                                "start": 3.5,
                                "end": 9.0,
                                "text": "The SR-71 used titanium to survive extreme runway-to-Mach heat cycles.",
                            },
                            {
                                "start": 12.0,
                                "end": 18.0,
                                "text": "Cadmium tools and chlorinated water could damage the Blackbird airframe.",
                            },
                        ]
                    },
                    indent=2,
                ),
                encoding="utf-8",
            )
            asset = self.asset(
                metadata={
                    **self.asset().metadata,
                    "transcript_path": "sidecars/sr71.transcript.json",
                }
            )

            clips = build_clip_index(self.project(), [asset], [self.beat()], project_dir=project_dir)

            self.assertEqual([clip.id for clip in clips], ["sr-71-nasa-flight-transcript-1", "sr-71-nasa-flight-transcript-2"])
            self.assertEqual(clips[0].start_seconds, 3.5)
            self.assertEqual(clips[0].end_seconds, 9.0)
            self.assertIn("titanium", clips[0].semantic_tags)
            self.assertIn("chlorinated", clips[1].transcript)

    def test_build_clip_index_uses_scene_sidecar_when_no_transcript_sidecar_exists(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)
            sidecars = project_dir / "sidecars"
            sidecars.mkdir()
            (sidecars / "sr71.scenes.json").write_text(
                json.dumps(
                    {
                        "scenes": [
                            {"start_seconds": 0.0, "end_seconds": 7.25},
                            {"start_seconds": 7.25, "end_seconds": 15.0},
                        ]
                    },
                    indent=2,
                ),
                encoding="utf-8",
            )
            asset = self.asset(
                metadata={
                    **self.asset().metadata,
                    "scenes_path": "sidecars/sr71.scenes.json",
                }
            )

            clips = build_clip_index(self.project(), [asset], [self.beat()], project_dir=project_dir)

            self.assertEqual([clip.id for clip in clips], ["sr-71-nasa-flight-scene-1", "sr-71-nasa-flight-scene-2"])
            self.assertEqual(clips[1].start_seconds, 7.25)
            self.assertEqual(clips[1].end_seconds, 15.0)
            self.assertIn("metadata-derived scene", clips[0].suggested_use)

    def _asset_to_dict(self, asset: SourceAsset) -> dict:
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

    def _beat_to_dict(self, beat: BeatPlan) -> dict:
        return {
            "id": beat.id,
            "chapter": beat.chapter,
            "claim": beat.claim,
            "narration": beat.narration,
            "required_visuals": beat.required_visuals,
            "emotional_intensity": beat.emotional_intensity,
            "citations": [citation.__dict__ for citation in beat.citations],
        }


if __name__ == "__main__":
    unittest.main()
