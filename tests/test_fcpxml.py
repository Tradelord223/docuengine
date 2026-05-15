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

    def test_builds_fcpxml_with_google_drive_proxy_path_and_media_root(self):
        asset = self.asset()
        asset.local_path = "My Drive/DocuEngine/metallurgical-crucible/originals/sr71.mov"
        asset.metadata = {
            "title": "SR-71 Proxy",
            "storage": "google_drive",
            "drive_original_path": "My Drive/DocuEngine/metallurgical-crucible/originals/sr71.mov",
            "drive_proxy_path": "My Drive/DocuEngine/metallurgical-crucible/proxies/sr71-proxy.mp4",
        }

        xml_text = build_fcpxml_document(
            self.project(),
            [asset],
            self.timeline(),
            media_root="/Volumes/GoogleDrive/My Drive",
        )

        root = ElementTree.fromstring(xml_text)
        self.assertEqual(
            root.find("./resources/asset").attrib["src"],
            "file:///Volumes/GoogleDrive/My%20Drive/DocuEngine/metallurgical-crucible/proxies/sr71-proxy.mp4",
        )

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

    def test_cli_exports_fcpxml_with_media_root(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            project = self.project()
            asset = self.asset()
            asset.local_path = "My Drive/DocuEngine/metallurgical-crucible/originals/sr71.mov"
            asset.metadata = {
                "title": "SR-71 Proxy",
                "storage": "google_drive",
                "drive_proxy_path": "My Drive/DocuEngine/metallurgical-crucible/proxies/sr71-proxy.mp4",
            }
            output = Path(tmpdir) / "project.fcpxml"
            (Path(tmpdir) / "project.json").write_text(json.dumps(project.__dict__, indent=2), encoding="utf-8")
            (Path(tmpdir) / "assets.json").write_text(json.dumps([self._asset_to_dict(asset)], indent=2), encoding="utf-8")
            (Path(tmpdir) / "timeline.json").write_text(json.dumps(self._timeline_to_dict(self.timeline()), indent=2), encoding="utf-8")

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
                    "--media-root",
                    "/Volumes/GoogleDrive/My Drive",
                ]
            )

            self.assertEqual(code, 0)
            parsed = ElementTree.fromstring(output.read_text())
            self.assertIn("/Volumes/GoogleDrive/My%20Drive/DocuEngine", parsed.find("./resources/asset").attrib["src"])

    def _asset_to_dict(self, asset):
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

    def _timeline_to_dict(self, timeline):
        return {
            "project_topic": timeline.project_topic,
            "target_duration_seconds": timeline.target_duration_seconds,
            "render_profile": timeline.render_profile,
            "tracks": [
                {
                    "name": track.name,
                    "kind": track.kind,
                    "clips": [clip.__dict__ for clip in track.clips],
                }
                for track in timeline.tracks
            ],
            "overlays": [],
            "generated_inserts": [],
            "otio": timeline.otio,
        }


if __name__ == "__main__":
    unittest.main()
