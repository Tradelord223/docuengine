import json
import tempfile
import unittest
from pathlib import Path

from docuengine.cli import main
from docuengine.models import (
    BeatPlan,
    Citation,
    ClipSegment,
    ProjectSpec,
    RightsRecord,
    SourceAsset,
)
from docuengine.planner import plan_timeline, score_clip_for_beat
from docuengine.policy import RightsPolicy
from docuengine.qa import run_quality_gates


class DocumentaryEngineTests(unittest.TestCase):
    def rights(self, license_id="public_domain", usage=None):
        return RightsRecord(
            source_url="https://www.dvidshub.net/video/123/example",
            license_id=license_id,
            attribution="DVIDS / Example Unit",
            downloaded_at="2026-05-13",
            restrictions=[],
            allowed_usage=usage or ["commercial", "transform", "editorial"],
        )

    def asset(self, asset_id="asset-1", provider="dvids", rights=None, path="/tmp/source.mp4"):
        return SourceAsset(
            id=asset_id,
            local_path=path,
            source_url="https://www.dvidshub.net/video/123/example",
            media_type="video",
            provider=provider,
            metadata={"title": "field exercise"},
            checksum="sha256:abc",
            rights=rights or self.rights(),
        )

    def beat(self):
        return BeatPlan(
            id="beat-1",
            chapter="Cold Open",
            claim="Modern command systems changed battlefield tempo.",
            narration="Command systems changed battlefield tempo before the public understood why.",
            required_visuals=["command center", "radar", "field exercise"],
            emotional_intensity=0.8,
            citations=[
                Citation(
                    title="DVIDS source",
                    url="https://www.dvidshub.net/video/123/example",
                    publisher="DVIDS",
                    accessed_at="2026-05-13",
                )
            ],
        )

    def project(self, **overrides):
        data = {
            "topic": "networked warfare history",
            "target_duration_seconds": 180,
            "thesis": "Command networks compressed tactical decision loops.",
            "audience": "documentary viewers",
            "mood": "tense archival",
            "pacing": "measured with bursts",
            "preset": "warfare_documentary",
            "budget_cap_usd": 5.0,
            "allowed_providers": ["dvids", "nara", "nasa", "wikimedia_commons", "pexels", "internet_archive", "user_upload"],
            "output_profile": {"width": 1920, "height": 1080, "fps": 24, "format": "mp4"},
        }
        data.update(overrides)
        return ProjectSpec(**data)

    def test_project_spec_rejects_unknown_preset(self):
        with self.assertRaisesRegex(ValueError, "Unsupported preset"):
            self.project(preset="celebrity_clone")

    def test_rights_policy_blocks_unapproved_youtube_downloads(self):
        asset = self.asset(
            provider="youtube",
            rights=self.rights(license_id="unknown", usage=["stream_reference_only"]),
        )
        asset.source_url = "https://www.youtube.com/watch?v=abc123"

        decision = RightsPolicy().validate_asset(asset, self.project())

        self.assertFalse(decision.allowed)
        self.assertIn("YouTube assets require user ownership, explicit permission, or a service-authorized download", decision.reasons)

    def test_rights_policy_allows_public_domain_military_sources(self):
        decision = RightsPolicy().validate_asset(self.asset(), self.project())

        self.assertTrue(decision.allowed)
        self.assertIn("keep_attribution", decision.required_actions)

    def test_clip_scoring_prefers_relevant_legal_fresh_footage(self):
        beat = self.beat()
        relevant = ClipSegment(
            id="clip-1",
            source_asset_id="asset-1",
            start_seconds=12.0,
            end_seconds=22.0,
            transcript="operators coordinate a radar-guided field exercise",
            semantic_tags=["command center", "radar", "field exercise"],
            visual_quality_score=0.9,
            audio_quality_score=0.7,
            rights_status="approved",
            suggested_use="primary b-roll",
        )
        generic = ClipSegment(
            id="clip-2",
            source_asset_id="asset-2",
            start_seconds=0.0,
            end_seconds=10.0,
            transcript="generic skyline",
            semantic_tags=["city", "sunset"],
            visual_quality_score=0.9,
            audio_quality_score=0.8,
            rights_status="approved",
            suggested_use="filler",
        )

        self.assertGreater(score_clip_for_beat(relevant, beat), score_clip_for_beat(generic, beat))

    def test_timeline_planner_creates_editable_otio_shaped_plan(self):
        beat = self.beat()
        clip = ClipSegment(
            id="clip-1",
            source_asset_id="asset-1",
            start_seconds=12.0,
            end_seconds=27.0,
            transcript="operators coordinate a radar-guided field exercise",
            semantic_tags=["command center", "radar", "field exercise"],
            visual_quality_score=0.9,
            audio_quality_score=0.7,
            rights_status="approved",
            suggested_use="primary b-roll",
        )

        timeline = plan_timeline(self.project(), [beat], [clip])

        self.assertEqual(timeline.render_profile["format"], "mp4")
        self.assertEqual(timeline.otio["OTIO_SCHEMA"], "Timeline.1")
        self.assertEqual(timeline.tracks[0].clips[0].source_clip_id, "clip-1")
        self.assertTrue(any(overlay.kind == "source_citation" for overlay in timeline.overlays))

    def test_timeline_planner_bounds_subtitles_to_selected_clip_duration(self):
        beat = self.beat()
        short_clip = ClipSegment(
            id="clip-short",
            source_asset_id="asset-1",
            start_seconds=10.0,
            end_seconds=15.0,
            transcript="short command center clip",
            semantic_tags=["command center", "radar", "field exercise"],
            visual_quality_score=0.9,
            audio_quality_score=0.7,
            rights_status="approved",
            suggested_use="primary b-roll",
        )

        timeline = plan_timeline(self.project(target_duration_seconds=180), [beat], [short_clip])

        self.assertEqual(timeline.tracks[0].clips[0].timeline_end_seconds, 5.0)
        self.assertEqual(timeline.subtitle_track[0]["end_seconds"], 5.0)
        self.assertTrue(all(overlay.end_seconds <= 5.0 for overlay in timeline.overlays))

    def test_quality_gates_block_missing_rights_and_uncited_claims(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            existing = Path(tmpdir) / "source.mp4"
            existing.write_bytes(b"placeholder")
            asset = self.asset(path=str(existing))
            asset.rights = None
            beat = self.beat()
            beat.citations = []
            clip = ClipSegment(
                id="clip-1",
                source_asset_id=asset.id,
                start_seconds=0,
                end_seconds=5,
                transcript="",
                semantic_tags=["radar"],
                visual_quality_score=0.8,
                audio_quality_score=0.7,
                rights_status="approved",
                suggested_use="b-roll",
            )
            timeline = plan_timeline(self.project(), [beat], [clip])

            gates = run_quality_gates(self.project(), [asset], timeline, [beat])

            failed = {gate.gate_type for gate in gates if gate.decision == "blocked"}
            self.assertIn("rights_ledger", failed)
            self.assertIn("citation_coverage", failed)

    def test_quality_gates_block_projects_without_source_assets(self):
        timeline = plan_timeline(self.project(), [self.beat()], [])

        gates = run_quality_gates(self.project(), [], timeline, [self.beat()])

        source_gate = next(gate for gate in gates if gate.gate_type == "source_assets")
        self.assertEqual(source_gate.decision, "blocked")

    def test_demo_cli_writes_project_artifacts(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            code = main(["demo", "--out", tmpdir, "--topic", "radar deception in modern warfare"])

            self.assertEqual(code, 0)
            project = json.loads((Path(tmpdir) / "project.json").read_text())
            timeline = json.loads((Path(tmpdir) / "timeline.json").read_text())
            gates = json.loads((Path(tmpdir) / "review_gates.json").read_text())
            self.assertEqual(project["preset"], "warfare_documentary")
            self.assertEqual(timeline["otio"]["OTIO_SCHEMA"], "Timeline.1")
            self.assertTrue(any(gate["gate_type"] == "rights_ledger" for gate in gates))


if __name__ == "__main__":
    unittest.main()
