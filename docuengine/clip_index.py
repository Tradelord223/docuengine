from __future__ import annotations

import re

from docuengine.models import BeatPlan, ClipSegment, ProjectSpec, SourceAsset
from docuengine.policy import RightsPolicy


DEFAULT_DURATIONS = {
    "video": 18.0,
    "image": 8.0,
    "audio": 18.0,
    "document": 10.0,
}


def build_clip_index(
    project: ProjectSpec,
    assets: list[SourceAsset],
    beats: list[BeatPlan],
) -> list[ClipSegment]:
    """Build a lightweight rough clip index from asset metadata without reading media bytes."""
    policy = RightsPolicy()
    clips: list[ClipSegment] = []
    for asset in assets:
        decision = policy.validate_asset(asset, project)
        if not decision.allowed:
            continue

        transcript = _asset_text(asset)
        tags = _semantic_tags(asset, transcript, beats)
        duration = _duration(asset)
        clips.append(
            ClipSegment(
                id=f"{asset.id}-rough-1",
                source_asset_id=asset.id,
                start_seconds=0.0,
                end_seconds=duration,
                transcript=transcript,
                semantic_tags=tags,
                visual_quality_score=_visual_score(asset),
                audio_quality_score=_audio_score(asset),
                rights_status="approved",
                suggested_use=str(asset.metadata.get("beat_use") or "metadata-derived b-roll"),
            )
        )
    return clips


def _asset_text(asset: SourceAsset) -> str:
    metadata = asset.metadata or {}
    parts = [
        asset.id,
        asset.provider,
        asset.media_type,
        asset.source_url,
        str(metadata.get("title", "")),
        str(metadata.get("beat_use", "")),
        str(metadata.get("notes", "")),
        str(metadata.get("drive_original_path", "")),
        str(metadata.get("drive_proxy_path", "")),
    ]
    if asset.rights:
        parts.extend([asset.rights.attribution, asset.rights.license_id])
    return " ".join(part for part in parts if part).strip()


def _semantic_tags(asset: SourceAsset, transcript: str, beats: list[BeatPlan]) -> list[str]:
    tokens = set(_tokens(transcript))
    for beat in beats:
        for visual in beat.required_visuals:
            visual_text = visual.lower().strip()
            if visual_text and visual_text in transcript.lower():
                tokens.add(visual_text)
    return sorted(tokens)[:30]


def _tokens(text: str) -> list[str]:
    normalized = text.lower().replace("_", "-")
    return [
        token.strip("-")
        for token in re.findall(r"[a-z0-9][a-z0-9-]{2,}", normalized)
        if token.strip("-") and token not in {"https", "http", "www", "com", "drive", "docuengine"}
    ]


def _duration(asset: SourceAsset) -> float:
    raw = (asset.metadata or {}).get("duration_seconds")
    if raw is not None:
        try:
            return max(3.0, min(float(raw), 30.0))
        except (TypeError, ValueError):
            pass
    return DEFAULT_DURATIONS.get(asset.media_type, 12.0)


def _visual_score(asset: SourceAsset) -> float:
    if asset.media_type in {"video", "image"}:
        return 0.76 if (asset.metadata or {}).get("storage") == "google_drive" else 0.72
    return 0.45


def _audio_score(asset: SourceAsset) -> float:
    if asset.media_type in {"video", "audio"}:
        return 0.62
    return 0.35
