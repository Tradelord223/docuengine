from __future__ import annotations

import argparse
import json
from pathlib import Path

from docuengine.clip_index import build_clip_index
from docuengine.drive_ledger import ingest_drive_ledger_csv
from docuengine.fcpxml import build_fcpxml_document
from docuengine.models import (
    BeatPlan,
    Citation,
    GeneratedInsert,
    ClipSegment,
    Overlay,
    ProjectSpec,
    RightsRecord,
    SourceAsset,
    TimelineClip,
    TimelinePlan,
    TimelineTrack,
    to_dict,
)
from docuengine.planner import plan_timeline
from docuengine.qa import run_quality_gates
from docuengine.sources import build_search_queries


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="docuengine")
    subparsers = parser.add_subparsers(dest="command", required=True)

    demo = subparsers.add_parser("demo", help="Write a self-contained demo documentary plan")
    demo.add_argument("--out", required=True, help="Output directory for project artifacts")
    demo.add_argument("--topic", default="networked warfare history", help="Documentary topic")
    demo.add_argument("--duration", type=int, default=180, help="Target duration in seconds")

    fcpxml = subparsers.add_parser("export-fcpxml", help="Export project artifacts as Final Cut Pro XML")
    fcpxml.add_argument("--project", required=True, help="Path to project.json")
    fcpxml.add_argument("--assets", required=True, help="Path to assets.json")
    fcpxml.add_argument("--timeline", required=True, help="Path to timeline.json")
    fcpxml.add_argument("--out", required=True, help="Path to write .fcpxml")
    fcpxml.add_argument("--media-root", help="Optional local media root for Drive/proxy-relative paths")

    drive_ledger = subparsers.add_parser(
        "ingest-drive-ledger",
        help="Import a Google Drive media ledger CSV into project assets and rights records",
    )
    drive_ledger.add_argument("--project-dir", required=True, help="Project artifact directory")
    drive_ledger.add_argument("--ledger-csv", required=True, help="CSV export of the Google Drive media ledger")

    clip_index = subparsers.add_parser(
        "build-clip-index",
        help="Build rough clip_index.json and timeline.json from registered source assets",
    )
    clip_index.add_argument("--project-dir", required=True, help="Project artifact directory")

    args = parser.parse_args(argv)
    if args.command == "demo":
        return _write_demo(Path(args.out), args.topic, args.duration)
    if args.command == "export-fcpxml":
        return _export_fcpxml(
            Path(args.project),
            Path(args.assets),
            Path(args.timeline),
            Path(args.out),
            Path(args.media_root) if args.media_root else None,
        )
    if args.command == "ingest-drive-ledger":
        return _ingest_drive_ledger(Path(args.project_dir), Path(args.ledger_csv))
    if args.command == "build-clip-index":
        return _build_clip_index(Path(args.project_dir))
    return 2


def _write_demo(out_dir: Path, topic: str, duration: int) -> int:
    out_dir.mkdir(parents=True, exist_ok=True)
    asset_dir = out_dir / "assets"
    asset_dir.mkdir(exist_ok=True)
    placeholder = asset_dir / "dvids_field_exercise.mp4"
    if not placeholder.exists():
        placeholder.write_bytes(b"docuengine placeholder media for planning tests\n")

    project = ProjectSpec(
        topic=topic,
        target_duration_seconds=duration,
        thesis="Command networks compressed tactical decision loops and changed public understanding of warfare.",
        audience="curious documentary viewers",
        mood="tense archival",
        pacing="measured with bursts",
        preset="warfare_documentary",
        budget_cap_usd=5.0,
    )

    rights = RightsRecord(
        source_url="https://www.dvidshub.net/video/123/example",
        license_id="public_domain",
        attribution="DVIDS / Example Unit",
        downloaded_at="2026-05-13",
        restrictions=[],
        allowed_usage=["commercial", "transform", "editorial"],
    )
    asset = SourceAsset(
        id="asset-dvids-field-exercise",
        local_path=str(placeholder),
        source_url=rights.source_url,
        media_type="video",
        provider="dvids",
        metadata={"title": "Field exercise planning footage", "placeholder": True},
        checksum="sha256:placeholder",
        rights=rights,
    )
    clip = ClipSegment(
        id="clip-command-center",
        source_asset_id=asset.id,
        start_seconds=0.0,
        end_seconds=20.0,
        transcript="operators coordinate a radar-guided field exercise from a command center",
        semantic_tags=["command center", "radar", "field exercise", "operators"],
        visual_quality_score=0.86,
        audio_quality_score=0.72,
        rights_status="approved",
        suggested_use="primary b-roll",
    )
    beat = BeatPlan(
        id="beat-cold-open",
        chapter="Cold Open",
        claim="Command networks changed the tempo of modern warfare.",
        narration="Before the public saw the battlefield, command networks were already changing its tempo.",
        required_visuals=["command center", "radar", "field exercise"],
        emotional_intensity=0.8,
        citations=[
            Citation(
                title="Example DVIDS archival source",
                url=asset.source_url,
                publisher="DVIDS",
                accessed_at="2026-05-13",
            )
        ],
    )

    timeline = plan_timeline(project, [beat], [clip])
    gates = run_quality_gates(project, [asset], timeline, [beat])

    artifacts = {
        "project.json": to_dict(project),
        "assets.json": to_dict([asset]),
        "clip_index.json": to_dict([clip]),
        "beat_plan.json": to_dict([beat]),
        "timeline.json": to_dict(timeline),
        "review_gates.json": to_dict(gates),
        "rights_ledger.json": to_dict([asset.rights]),
        "source_queries.json": build_search_queries(topic, project.preset),
    }
    for filename, payload in artifacts.items():
        (out_dir / filename).write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    (out_dir / "README.md").write_text(_demo_readme(project), encoding="utf-8")
    return 0


def _demo_readme(project: ProjectSpec) -> str:
    return (
        f"# {project.topic}\n\n"
        "This directory contains a DocuEngine planning demo: project spec, rights ledger, "
        "clip index, beat plan, OTIO-shaped timeline JSON, and review gates.\n\n"
        "The placeholder media file is not a real source clip; replace it with a rights-cleared "
        "asset before rendering.\n"
    )


def _export_fcpxml(
    project_path: Path,
    assets_path: Path,
    timeline_path: Path,
    out_path: Path,
    media_root: Path | None = None,
) -> int:
    project = _project_from_dict(_read_json(project_path))
    assets = [_asset_from_dict(item) for item in _read_json(assets_path)]
    timeline = _timeline_from_dict(_read_json(timeline_path))

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(build_fcpxml_document(project, assets, timeline, media_root=media_root), encoding="utf-8")
    return 0


def _ingest_drive_ledger(project_dir: Path, ledger_csv: Path) -> int:
    project = _project_from_dict(_read_json(project_dir / "project.json"))
    beats = [_beat_from_dict(item) for item in _read_json(project_dir / "beat_plan.json")]
    timeline = _timeline_from_dict(_read_json(project_dir / "timeline.json"))
    existing_assets = _read_assets_if_present(project_dir / "assets.json")
    result = ingest_drive_ledger_csv(ledger_csv)
    assets = _merge_assets(existing_assets, result.assets)
    gates = run_quality_gates(project, assets, timeline, beats)

    artifacts = {
        "assets.json": to_dict(assets),
        "rights_ledger.json": to_dict([asset.rights for asset in assets if asset.rights]),
        "review_gates.json": to_dict(gates),
        "drive_ledger_ingest_report.json": {
            "ledger_csv": str(ledger_csv),
            "asset_count": len(result.assets),
            "skipped_rows": result.skipped_rows,
        },
    }
    for filename, payload in artifacts.items():
        (project_dir / filename).write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return 0


def _build_clip_index(project_dir: Path) -> int:
    project = _project_from_dict(_read_json(project_dir / "project.json"))
    assets = _read_assets_if_present(project_dir / "assets.json")
    beats = [_beat_from_dict(item) for item in _read_json(project_dir / "beat_plan.json")]
    clips = build_clip_index(project, assets, beats, project_dir=project_dir)
    timeline = plan_timeline(project, beats, clips)
    gates = run_quality_gates(project, assets, timeline, beats)

    artifacts = {
        "clip_index.json": to_dict(clips),
        "timeline.json": to_dict(timeline),
        "review_gates.json": to_dict(gates),
    }
    for filename, payload in artifacts.items():
        (project_dir / filename).write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return 0


def _read_assets_if_present(path: Path) -> list[SourceAsset]:
    if not path.exists():
        return []
    return [_asset_from_dict(item) for item in _read_json(path)]


def _merge_assets(existing: list[SourceAsset], incoming: list[SourceAsset]) -> list[SourceAsset]:
    merged = {asset.id: asset for asset in existing}
    for asset in incoming:
        merged[asset.id] = asset
    return list(merged.values())


def _read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _project_from_dict(data: dict) -> ProjectSpec:
    return ProjectSpec(**data)


def _rights_from_dict(data: dict | None) -> RightsRecord | None:
    return RightsRecord(**data) if data else None


def _asset_from_dict(data: dict) -> SourceAsset:
    payload = dict(data)
    payload["rights"] = _rights_from_dict(payload.get("rights"))
    return SourceAsset(**payload)


def _citation_from_dict(data: dict) -> Citation:
    return Citation(**data)


def _beat_from_dict(data: dict) -> BeatPlan:
    payload = dict(data)
    payload["citations"] = [_citation_from_dict(item) for item in payload.get("citations", [])]
    return BeatPlan(**payload)


def _timeline_clip_from_dict(data: dict) -> TimelineClip:
    return TimelineClip(**data)


def _track_from_dict(data: dict) -> TimelineTrack:
    payload = dict(data)
    payload["clips"] = [_timeline_clip_from_dict(item) for item in payload.get("clips", [])]
    return TimelineTrack(**payload)


def _overlay_from_dict(data: dict) -> Overlay:
    return Overlay(**data)


def _generated_insert_from_dict(data: dict) -> GeneratedInsert:
    return GeneratedInsert(**data)


def _timeline_from_dict(data: dict) -> TimelinePlan:
    payload = dict(data)
    payload["tracks"] = [_track_from_dict(item) for item in payload.get("tracks", [])]
    payload["overlays"] = [_overlay_from_dict(item) for item in payload.get("overlays", [])]
    payload["generated_inserts"] = [
        _generated_insert_from_dict(item) for item in payload.get("generated_inserts", [])
    ]
    return TimelinePlan(**payload)


if __name__ == "__main__":
    raise SystemExit(main())
