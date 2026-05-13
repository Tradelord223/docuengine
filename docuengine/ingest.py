from __future__ import annotations

import hashlib
from pathlib import Path

from docuengine.models import ClipSegment, RightsRecord, SourceAsset


VIDEO_EXTENSIONS = {".mp4", ".mov", ".mkv", ".webm", ".avi"}
AUDIO_EXTENSIONS = {".wav", ".mp3", ".m4a", ".aac", ".flac"}
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".tif", ".tiff"}
TEXT_EXTENSIONS = {".txt", ".srt", ".vtt", ".json", ".md", ".pdf"}


def compute_sha256(path: str | Path) -> str:
    target = Path(path)
    digest = hashlib.sha256()
    with target.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return f"sha256:{digest.hexdigest()}"


def infer_media_type(path: str | Path) -> str:
    suffix = Path(path).suffix.lower()
    if suffix in VIDEO_EXTENSIONS:
        return "video"
    if suffix in AUDIO_EXTENSIONS:
        return "audio"
    if suffix in IMAGE_EXTENSIONS:
        return "image"
    if suffix in TEXT_EXTENSIONS:
        return "document"
    return "unknown"


def create_user_asset(
    path: str | Path,
    asset_id: str,
    source_url: str,
    rights: RightsRecord,
    metadata: dict[str, object] | None = None,
) -> SourceAsset:
    target = Path(path)
    if not target.exists():
        raise FileNotFoundError(target)
    return SourceAsset(
        id=asset_id,
        local_path=str(target),
        source_url=source_url,
        media_type=infer_media_type(target),
        provider="user_upload",
        metadata=metadata or {"filename": target.name},
        checksum=compute_sha256(target),
        rights=rights,
    )


def transcript_segments_to_clips(
    source_asset_id: str,
    segments: list[dict[str, object]],
    rights_status: str = "approved",
) -> list[ClipSegment]:
    clips: list[ClipSegment] = []
    for index, segment in enumerate(segments):
        text = str(segment.get("text", ""))
        tags = [word.strip(".,:;!?").lower() for word in text.split() if len(word) > 4]
        clips.append(
            ClipSegment(
                id=f"{source_asset_id}-seg-{index + 1}",
                source_asset_id=source_asset_id,
                start_seconds=float(segment["start"]),
                end_seconds=float(segment["end"]),
                transcript=text,
                semantic_tags=sorted(set(tags))[:12],
                visual_quality_score=float(segment.get("visual_quality_score", 0.65)),
                audio_quality_score=float(segment.get("audio_quality_score", 0.65)),
                rights_status=rights_status,
                suggested_use=str(segment.get("suggested_use", "transcript-derived clip")),
            )
        )
    return clips

