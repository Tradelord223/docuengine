import json
import tempfile
import unittest
from pathlib import Path
from xml.etree import ElementTree

from docuengine.cli import main
from docuengine.fcpxml import build_fcpxml_document, seconds_to_fcpxml_time
from docuengine.models import (
    ClipSegment,
    ProjectSpec,
    RightsRecord,
    SourceAsset,
    TimelineClip,
    TimelinePlan,
    TimelineTrack,
)


class FcpXmlExportTests(unittest.TestCase):
    def project(self):
        return ProjectSpec(
            topic="radar deception",
            target_duration_seconds=60,
            thesis="Electronic deception changed battlefield sensing.",
            audience="documentary viewers",
            mood="archival",
            pacing="tight",
            preset="warfare_documentary",
        )

    def asset(self):
        return SourceAsset(
            id="asset-1",
            local_path="/tmp/source clip.mp4",
            source_url="https://www.dvidshub.net/video/123/example",
            media_type="video",
            provider="dvids",
            metadata={"title": "Source Clip"},
            checksum="sha256:abc",
            rights=RightsRecord(
                source_url="https://www.dvidshub.net/video/123/example",
                license_id="public_domain",
                attribution="DVIDS / Example Unit",
                downloaded_at="2026-05-13",
                restrictions=[],
                allowed_usage=["commercial", "transform", "editorial"],
            ),
        )

    def timeline(self):
        return TimelinePlan(
            project_topic="radar deception",
            target_duration_seconds=60,
            render_profile={"width": 1920, "height": 1080, "fps": 24, "format": "mp4"},
            tracks=[
                TimelineTrack(
                    name="Picture",
                    kind="video",
                    clips=[
                        TimelineClip(
                            id="tl-1",
                            source_clip_id="clip-1",
                            source_asset_id="asset-1",
                            timeline_start_seconds=0,
                            timeline_end_seconds=5,
                            source_start_seconds=10,
                            source_end_seconds=15,
                            role="primary_broll",
                            rationale="matches radar beat",
                        )
                    ],
                )
            ],
            overlays=[],
            generated_inserts=[],
            otio={"OTIO_SCHEMA": "Timeline.1"},
        )

    def test_seconds_to_fcpxml_time_uses_frame_accurate_rational_seconds(self):
        self.assertEqual(seconds_to_fcpxml_time(2.5, fps=24), "60/24s")

    def test_builds_minimal_importable_fcpxml_shape(self):
        xml_text = build_fcpxml_document(self.project(), [self.asset()], self.timeline())

        root = ElementTree.fromstring(xml_text)
        self.assertEqual(root.tag, "fcpxml")
        self.assertEqual(root.attrib["version"], "1.10")
        self.assertEqual(root.find("./resources/asset").attrib["src"], "file:///tmp/source%20clip.mp4")
        self.assertEqual(root.find("./library/event/project/sequence/spine/asset-clip").attrib["role"], "video")

    def test_cli_exports_fcpxml_from_demo_artifacts(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            self.assertEqual(main(["demo", "--out", tmpdir, "--topic", "radar deception"]), 0)
            output = Path(tmpdir) / "project.fcpxml"

            code = main(
                [
                    "export-fcpxml",
                    "--project",
                    str(Path(tmpdir) / "project.json"),
                    "--assets",
                    str(Path(tmpdir) / "assets.json"),
                    "--timeline",
                    str(Path(tmpdir) / "timeline.json"),
                    "--out",
                    str(output),
                ]
            )

            self.assertEqual(code, 0)
            parsed = ElementTree.fromstring(output.read_text())
            self.assertEqual(parsed.tag, "fcpxml")


if __name__ == "__main__":
    unittest.main()
