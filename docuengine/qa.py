from __future__ import annotations

from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

from docuengine.models import BeatPlan, ProjectSpec, ReviewGate, SourceAsset, TimelinePlan
from docuengine.policy import RightsPolicy


def run_quality_gates(
    project: ProjectSpec,
    assets: list[SourceAsset],
    timeline: TimelinePlan,
    beats: list[BeatPlan],
) -> list[ReviewGate]:
    now = datetime.now(UTC).isoformat()
    policy = RightsPolicy()
    gates: list[ReviewGate] = []

    gates.append(
        ReviewGate(
            gate_type="source_assets",
            risk="production",
            decision="blocked" if not assets else "passed",
            approver="system",
            timestamp=now,
            notes=["No source assets attached; final render is blocked until rights-cleared media is ingested"]
            if not assets
            else [f"{len(assets)} source asset(s) attached"],
        )
    )

    rights_notes: list[str] = []
    for asset in assets:
        decision = policy.validate_asset(asset, project)
        if not decision.allowed:
            rights_notes.extend(decision.reasons)
    gates.append(
        ReviewGate(
            gate_type="rights_ledger",
            risk="legal",
            decision="blocked" if rights_notes else "passed",
            approver="system",
            timestamp=now,
            notes=rights_notes or ["All source assets have approved rights records"],
        )
    )

    missing = [
        f"{asset.id}: {asset.local_path}"
        for asset in assets
        if asset.local_path and not _is_cloud_backed(asset) and not Path(asset.local_path).exists()
    ]
    cloud_backed = [asset.id for asset in assets if _is_cloud_backed(asset)]
    missing_notes = missing or ["All referenced local media paths exist"]
    if cloud_backed and not missing:
        missing_notes = [f"{len(cloud_backed)} cloud-backed media asset(s) registered; local existence not required"]
    gates.append(
        ReviewGate(
            gate_type="missing_media",
            risk="render",
            decision="blocked" if missing else "passed",
            approver="system",
            timestamp=now,
            notes=missing_notes,
        )
    )

    uncited = [beat.id for beat in beats if beat.claim.strip() and not beat.citations]
    gates.append(
        ReviewGate(
            gate_type="citation_coverage",
            risk="factual",
            decision="blocked" if uncited else "passed",
            approver="system",
            timestamp=now,
            notes=[f"Uncited claims in beats: {', '.join(uncited)}"] if uncited else ["All beats with claims include citations"],
        )
    )

    asset_ids = {asset.id for asset in assets}
    missing_assets = [
        clip.source_asset_id
        for track in timeline.tracks
        for clip in track.clips
        if clip.source_asset_id not in asset_ids
    ]
    gates.append(
        ReviewGate(
            gate_type="timeline_integrity",
            risk="edit",
            decision="blocked" if missing_assets else "passed",
            approver="system",
            timestamp=now,
            notes=[f"Timeline references missing assets: {', '.join(sorted(set(missing_assets)))}"]
            if missing_assets
            else ["Timeline references resolvable source assets"],
        )
    )

    clip_counts = Counter(
        clip.source_clip_id for track in timeline.tracks for clip in track.clips
    )
    overused = [clip_id for clip_id, count in clip_counts.items() if count > 3]
    gates.append(
        ReviewGate(
            gate_type="duplicate_clip_overuse",
            risk="quality",
            decision="blocked" if overused else "passed",
            approver="system",
            timestamp=now,
            notes=[f"Overused source clips: {', '.join(overused)}"] if overused else ["No clip is overused"],
        )
    )

    unsafe = _unsafe_operational_detail(beats)
    gates.append(
        ReviewGate(
            gate_type="unsafe_operational_detail",
            risk="safety",
            decision="blocked" if unsafe else "passed",
            approver="system",
            timestamp=now,
            notes=unsafe or ["No operational weapon, evasion, or targeting instructions detected"],
        )
    )

    return gates


def _unsafe_operational_detail(beats: list[BeatPlan]) -> list[str]:
    blocked_phrases = [
        "step-by-step targeting",
        "evade detection",
        "build an explosive",
        "weaponize",
        "targeting coordinates",
        "operational attack plan",
    ]
    findings: list[str] = []
    for beat in beats:
        haystack = f"{beat.claim} {beat.narration}".lower()
        for phrase in blocked_phrases:
            if phrase in haystack:
                findings.append(f"{beat.id}: contains '{phrase}'")
    return findings


def _is_cloud_backed(asset: SourceAsset) -> bool:
    metadata = asset.metadata or {}
    return metadata.get("storage") == "google_drive" and bool(
        metadata.get("drive_original_path")
        or metadata.get("drive_proxy_path")
        or metadata.get("drive_file_id")
        or asset.local_path.startswith("gdrive://")
        or asset.local_path.startswith("My Drive/")
    )
