import csv
import json
import tempfile
import unittest
from pathlib import Path

from docuengine.cli import main
from docuengine.drive_ledger import ingest_drive_ledger_csv
from docuengine.models import (
    BeatPlan,
    Citation,
    ProjectSpec,
    SourceAsset,
    TimelinePlan,
)
from docuengine.qa import run_quality_gates


class DriveLedgerIngestionTests(unittest.TestCase):
    def write_csv(self, path: Path, rows: list[dict[str, str]]) -> None:
        headers = [
            "Asset ID",
            "Status",
            "Provider",
            "Source URL",
            "Drive Original Path",
            "Drive Proxy Path",
            "Rights Status",
            "Attribution",
            "Beat/Use",
            "Notes",
        ]
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=headers)
            writer.writeheader()
            writer.writerows(rows)

    def project(self, **overrides) -> ProjectSpec:
        data = {
            "topic": "metallurgical crucible",
            "target_duration_seconds": 1200,
            "thesis": "Wartime material experiments shaped modern alloys.",
            "audience": "documentary viewers",
            "mood": "forensic and cinematic",
            "pacing": "measured with high-intensity archival sequences",
            "preset": "military_history",
            "allowed_providers": ["nasa", "dvids", "nara", "wikimedia_commons", "user_upload"],
        }
        data.update(overrides)
        return ProjectSpec(**data)

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

    def timeline(self) -> TimelinePlan:
        return TimelinePlan(
            project_topic="metallurgical crucible",
            target_duration_seconds=1200,
            render_profile={"width": 1920, "height": 1080, "fps": 24, "format": "mp4"},
            tracks=[],
            overlays=[],
            generated_inserts=[],
            otio={"OTIO_SCHEMA": "Timeline.1", "tracks": []},
        )

    def test_ingest_drive_ledger_csv_creates_assets_and_skips_unready_rows(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            ledger = Path(tmpdir) / "ledger.csv"
            self.write_csv(
                ledger,
                [
                    {
                        "Asset ID": "SR-71 NASA Flight",
                        "Status": "ready",
                        "Provider": "NASA",
                        "Source URL": "https://www.nasa.gov/reference/sr-71-blackbird/",
                        "Drive Original Path": "My Drive/DocuEngine/metallurgical-crucible/originals/sr71.mov",
                        "Drive Proxy Path": "My Drive/DocuEngine/metallurgical-crucible/proxies/sr71-proxy.mp4",
                        "Rights Status": "public domain",
                        "Attribution": "NASA",
                        "Beat/Use": "Titanium Phantom b-roll",
                        "Notes": "Use for SR-71 runway sequence",
                    },
                    {
                        "Asset ID": "Wanted Jumo Footage",
                        "Status": "needed",
                        "Provider": "Internet Archive",
                        "Source URL": "",
                        "Drive Original Path": "",
                        "Drive Proxy Path": "",
                        "Rights Status": "pending",
                        "Attribution": "",
                        "Beat/Use": "The Fire of the Turbine",
                        "Notes": "Not sourced yet",
                    },
                ],
            )

            result = ingest_drive_ledger_csv(ledger)

            self.assertEqual(len(result.assets), 1)
            self.assertEqual(result.assets[0].id, "sr-71-nasa-flight")
            self.assertEqual(result.assets[0].provider, "nasa")
            self.assertEqual(result.assets[0].media_type, "video")
            self.assertEqual(result.assets[0].rights.license_id, "public_domain")
            self.assertEqual(result.assets[0].metadata["storage"], "google_drive")
            self.assertEqual(result.assets[0].metadata["drive_proxy_path"], "My Drive/DocuEngine/metallurgical-crucible/proxies/sr71-proxy.mp4")
            self.assertEqual(result.skipped_rows[0]["reason"], "status_not_ready")

    def test_quality_gates_allow_google_drive_backed_media_without_local_file(self):
        result = ingest_drive_ledger_csv(
            self._single_ready_ledger(
                {
                    "Asset ID": "SR-71 NASA Flight",
                    "Status": "ready",
                    "Provider": "NASA",
                    "Source URL": "https://www.nasa.gov/reference/sr-71-blackbird/",
                    "Drive Original Path": "My Drive/DocuEngine/metallurgical-crucible/originals/sr71.mov",
                    "Rights Status": "public_domain",
                    "Attribution": "NASA",
                }
            )
        )

        gates = run_quality_gates(self.project(), result.assets, self.timeline(), [self.beat()])

        gate_map = {gate.gate_type: gate for gate in gates}
        self.assertEqual(gate_map["source_assets"].decision, "passed")
        self.assertEqual(gate_map["rights_ledger"].decision, "passed")
        self.assertEqual(gate_map["missing_media"].decision, "passed")

    def test_ingest_drive_ledger_normalizes_composite_public_source_provider(self):
        result = ingest_drive_ledger_csv(
            self._single_ready_ledger(
                {
                    "Asset ID": "SR-71 composite source",
                    "Status": "ready",
                    "Provider": "Smithsonian / NASA / USAF / NARA / DVIDS",
                    "Source URL": "https://airandspace.si.edu/collection-objects/lockheed-sr-71-blackbird",
                    "Drive Original Path": "My Drive/DocuEngine/metallurgical-crucible/originals/sr71-smithsonian.mov",
                    "Rights Status": "public_domain",
                    "Attribution": "Smithsonian National Air and Space Museum",
                }
            )
        )

        self.assertEqual(result.assets[0].provider, "smithsonian")
        gates = run_quality_gates(
            self.project(allowed_providers=["smithsonian", "nasa", "dvids", "nara", "wikimedia_commons", "user_upload"]),
            result.assets,
            self.timeline(),
            [self.beat()],
        )
        self.assertEqual({gate.gate_type: gate.decision for gate in gates}["rights_ledger"], "passed")

    def test_ingest_drive_ledger_cli_updates_project_artifacts_and_review_gates(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir) / "project"
            project_dir.mkdir()
            ledger = Path(tmpdir) / "ledger.csv"
            existing_media = Path(tmpdir) / "existing-user-upload.mov"
            existing_media.write_bytes(b"existing user-owned media placeholder")
            self.write_csv(
                ledger,
                [
                    {
                        "Asset ID": "SR-71 NASA Flight",
                        "Status": "ready",
                        "Provider": "NASA",
                        "Source URL": "https://www.nasa.gov/reference/sr-71-blackbird/",
                        "Drive Original Path": "My Drive/DocuEngine/metallurgical-crucible/originals/sr71.mov",
                        "Drive Proxy Path": "My Drive/DocuEngine/metallurgical-crucible/proxies/sr71-proxy.mp4",
                        "Rights Status": "public_domain",
                        "Attribution": "NASA",
                        "Beat/Use": "Titanium Phantom b-roll",
                        "Notes": "",
                    }
                ],
            )
            (project_dir / "project.json").write_text(json.dumps(self.project().__dict__, indent=2), encoding="utf-8")
            (project_dir / "beat_plan.json").write_text(
                json.dumps(
                    [
                        {
                            "id": self.beat().id,
                            "chapter": self.beat().chapter,
                            "claim": self.beat().claim,
                            "narration": self.beat().narration,
                            "required_visuals": self.beat().required_visuals,
                            "emotional_intensity": self.beat().emotional_intensity,
                            "citations": [citation.__dict__ for citation in self.beat().citations],
                        }
                    ],
                    indent=2,
                ),
                encoding="utf-8",
            )
            (project_dir / "timeline.json").write_text(
                json.dumps(
                    {
                        "project_topic": "metallurgical crucible",
                        "target_duration_seconds": 1200,
                        "render_profile": {"width": 1920, "height": 1080, "fps": 24, "format": "mp4"},
                        "tracks": [],
                        "overlays": [],
                        "generated_inserts": [],
                        "otio": {"OTIO_SCHEMA": "Timeline.1", "tracks": []},
                    },
                    indent=2,
                ),
                encoding="utf-8",
            )
            (project_dir / "assets.json").write_text(
                json.dumps(
                    [
                        {
                            "id": "existing-user-upload",
                            "local_path": str(existing_media),
                            "source_url": existing_media.as_uri(),
                            "media_type": "video",
                            "provider": "user_upload",
                            "metadata": {"title": "Existing user-owned clip"},
                            "checksum": "sha256:existing",
                            "rights": {
                                "source_url": existing_media.as_uri(),
                                "license_id": "owned",
                                "attribution": "User supplied",
                                "downloaded_at": "2026-05-13",
                                "restrictions": [],
                                "allowed_usage": ["commercial", "transform", "editorial"],
                            },
                        }
                    ],
                    indent=2,
                ),
                encoding="utf-8",
            )

            code = main(["ingest-drive-ledger", "--project-dir", str(project_dir), "--ledger-csv", str(ledger)])

            self.assertEqual(code, 0)
            assets = json.loads((project_dir / "assets.json").read_text(encoding="utf-8"))
            rights = json.loads((project_dir / "rights_ledger.json").read_text(encoding="utf-8"))
            gates = json.loads((project_dir / "review_gates.json").read_text(encoding="utf-8"))
            self.assertEqual([asset["id"] for asset in assets], ["existing-user-upload", "sr-71-nasa-flight"])
            self.assertEqual({record["license_id"] for record in rights}, {"owned", "public_domain"})
            self.assertEqual({gate["gate_type"]: gate["decision"] for gate in gates}["missing_media"], "passed")

    def _single_ready_ledger(self, row: dict[str, str]) -> Path:
        tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(tmpdir.cleanup)
        path = Path(tmpdir.name) / "ledger.csv"
        defaults = {
            "Drive Proxy Path": "",
            "Beat/Use": "",
            "Notes": "",
        }
        defaults.update(row)
        self.write_csv(path, [defaults])
        return path


if __name__ == "__main__":
    unittest.main()
