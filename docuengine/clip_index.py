from __future__ import annotations

import json
import re
from pathlib import Path

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
    project_dir: str | Path | None = None,
) -> list[ClipSegment]:
    """Build a lightweight rough clip index from asset metadata without reading media bytes."""
    policy = RightsPolicy()
    base_dir = Path(project_dir) if project_dir else None
    clips: list[ClipSegment] = []
    for asset in assets:
        decision = policy.validate_asset(asset, project)
        if not decision.allowed:
            continue

        sidecar_clips = _clips_from_sidecars(asset, beats, base_dir)
        if sidecar_clips:
            clips.extend(sidecar_clips)
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


def _clips_from_sidecars(
    asset: SourceAsset,
    beats: list[BeatPlan],
    base_dir: Path | None,
) -> list[ClipSegment]:
    transcript_path = _sidecar_path(asset, base_dir, "transcript_path", "sidecar_transcript_path")
    if transcript_path and transcript_path.exists():
        clips = _transcript_clips(asset, beats, transcript_path)
        if clips:
            return clips

    scenes_path = _sidecar_path(asset, base_dir, "scenes_path", "sidecar_scenes_path")
    if scenes_path and scenes_path.exists():
        return _scene_clips(asset, beats, scenes_path)

    return []


def _sidecar_path(asset: SourceAsset, base_dir: Path | None, *keys: str) -> Path | None:
    metadata = asset.metadata or {}
    raw = next((str(metadata[key]) for key in keys if metadata.get(key)), "")
    if not raw:
        return None
    path = Path(raw).expanduser()
    if path.is_absolute() or base_dir is None:
        return path
    return base_dir / path


def _transcript_clips(asset: SourceAsset, beats: list[BeatPlan], path: Path) -> list[ClipSegment]:
    data = json.loads(path.read_text(encoding="utf-8"))
    segments = data.get("segments", data) if isinstance(data, dict) else data
    clips: list[ClipSegment] = []
    for index, segment in enumerate(segments or [], start=1):
        start = _segment_float(segment, "start", "start_seconds")
        end = _segment_float(segment, "end", "end_seconds")
        text = str(segment.get("text") or segment.get("transcript") or "").strip()
        if start is None or end is None or end <= start or not text:
            continue
        clips.append(
            ClipSegment(
                id=f"{asset.id}-transcript-{index}",
                source_asset_id=asset.id,
                start_seconds=start,
                end_seconds=end,
                transcript=text,
                semantic_tags=_semantic_tags(asset, f"{_asset_text(asset)} {text}", beats),
                visual_quality_score=_visual_score(asset),
                audio_quality_score=_audio_score(asset),
                rights_status="approved",
                suggested_use=str(segment.get("suggested_use") or asset.metadata.get("beat_use") or "transcript-derived clip"),
            )
        )
    return clips


def _scene_clips(asset: SourceAsset, beats: list[BeatPlan], path: Path) -> list[ClipSegment]:
    data = json.loads(path.read_text(encoding="utf-8"))
    scenes = data.get("scenes", data) if isinstance(data, dict) else data
    clips: list[ClipSegment] = []
    transcript = _asset_text(asset)
    for index, scene in enumerate(scenes or [], start=1):
        start = _segment_float(scene, "start", "start_seconds")
        end = _segment_float(scene, "end", "end_seconds")
        if start is None or end is None or end <= start:
            continue
        clips.append(
            ClipSegment(
                id=f"{asset.id}-scene-{index}",
                source_asset_id=asset.id,
                start_seconds=start,
                end_seconds=end,
                transcript=f"{transcript} scene {index}",
                semantic_tags=_semantic_tags(asset, transcript, beats),
                visual_quality_score=_visual_score(asset),
                audio_quality_score=_audio_score(asset),
                rights_status="approved",
                suggested_use=str(scene.get("suggested_use") or "metadata-derived scene"),
            )
        )
    return clips


def _segment_float(segment: dict[str, object], *keys: str) -> float | None:
    for key in keys:
        if key in segment:
            try:
                return float(segment[key])
            except (TypeError, ValueError):
                return None
    return None


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
