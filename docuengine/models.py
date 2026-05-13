from __future__ import annotations

from dataclasses import asdict, dataclass, field, is_dataclass
from typing import Any


SUPPORTED_PRESETS = {
    "military_history",
    "warfare_documentary",
    "mind_control_history",
    "intelligence_networks",
    "geopolitics_explainer",
}

DEFAULT_PROVIDERS = [
    "dvids",
    "nara",
    "nasa",
    "wikimedia_commons",
    "pexels",
    "internet_archive",
    "user_upload",
]

DEFAULT_OUTPUT_PROFILE = {
    "width": 1920,
    "height": 1080,
    "fps": 24,
    "format": "mp4",
}


def _copy_dict(value: dict[str, Any] | None, default: dict[str, Any]) -> dict[str, Any]:
    merged = dict(default)
    if value:
        merged.update(value)
    return merged


@dataclass
class ProjectSpec:
    topic: str
    target_duration_seconds: int
    thesis: str
    audience: str
    mood: str
    pacing: str
    preset: str
    budget_cap_usd: float = 0.0
    allowed_providers: list[str] = field(default_factory=lambda: list(DEFAULT_PROVIDERS))
    output_profile: dict[str, Any] = field(default_factory=lambda: dict(DEFAULT_OUTPUT_PROFILE))
    constraints: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.preset not in SUPPORTED_PRESETS:
            raise ValueError(f"Unsupported preset: {self.preset}")
        if not self.topic.strip():
            raise ValueError("Project topic is required")
        if self.target_duration_seconds <= 0:
            raise ValueError("target_duration_seconds must be positive")
        if self.budget_cap_usd < 0:
            raise ValueError("budget_cap_usd cannot be negative")
        self.output_profile = _copy_dict(self.output_profile, DEFAULT_OUTPUT_PROFILE)
        if self.output_profile["width"] <= 0 or self.output_profile["height"] <= 0:
            raise ValueError("output_profile dimensions must be positive")
        if self.output_profile["fps"] <= 0:
            raise ValueError("output_profile fps must be positive")


@dataclass
class RightsRecord:
    source_url: str
    license_id: str
    attribution: str
    downloaded_at: str
    restrictions: list[str] = field(default_factory=list)
    allowed_usage: list[str] = field(default_factory=list)

    def allows(self, usage: str) -> bool:
        normalized = {item.lower() for item in self.allowed_usage}
        return usage.lower() in normalized


@dataclass
class SourceAsset:
    id: str
    local_path: str
    source_url: str
    media_type: str
    provider: str
    metadata: dict[str, Any]
    checksum: str
    rights: RightsRecord | None


@dataclass
class ClipSegment:
    id: str
    source_asset_id: str
    start_seconds: float
    end_seconds: float
    transcript: str
    semantic_tags: list[str]
    visual_quality_score: float
    audio_quality_score: float
    rights_status: str
    suggested_use: str

    def __post_init__(self) -> None:
        if self.end_seconds <= self.start_seconds:
            raise ValueError("ClipSegment end_seconds must be after start_seconds")
        self.visual_quality_score = _clamp_score(self.visual_quality_score)
        self.audio_quality_score = _clamp_score(self.audio_quality_score)

    @property
    def duration_seconds(self) -> float:
        return self.end_seconds - self.start_seconds


@dataclass
class Citation:
    title: str
    url: str
    publisher: str
    accessed_at: str


@dataclass
class BeatPlan:
    id: str
    chapter: str
    claim: str
    narration: str
    required_visuals: list[str]
    emotional_intensity: float
    citations: list[Citation] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.emotional_intensity = _clamp_score(self.emotional_intensity)


@dataclass
class TimelineClip:
    id: str
    source_clip_id: str
    source_asset_id: str
    timeline_start_seconds: float
    timeline_end_seconds: float
    source_start_seconds: float
    source_end_seconds: float
    role: str
    rationale: str


@dataclass
class TimelineTrack:
    name: str
    kind: str
    clips: list[TimelineClip] = field(default_factory=list)


@dataclass
class Overlay:
    id: str
    kind: str
    text: str
    start_seconds: float
    end_seconds: float
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class GeneratedInsert:
    id: str
    reason: str
    prompt: str
    approved_provider: str | None
    estimated_cost_usd: float
    status: str = "requires_approval"


@dataclass
class TimelinePlan:
    project_topic: str
    target_duration_seconds: int
    render_profile: dict[str, Any]
    tracks: list[TimelineTrack]
    overlays: list[Overlay]
    generated_inserts: list[GeneratedInsert]
    otio: dict[str, Any]
    music_bed: dict[str, Any] = field(default_factory=dict)
    subtitle_track: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class ReviewGate:
    gate_type: str
    risk: str
    decision: str
    approver: str
    timestamp: str
    notes: list[str] = field(default_factory=list)


def _clamp_score(value: float) -> float:
    if value < 0:
        return 0.0
    if value > 1:
        return 1.0
    return float(value)


def to_dict(value: Any) -> Any:
    if is_dataclass(value):
        return asdict(value)
    if isinstance(value, list):
        return [to_dict(item) for item in value]
    if isinstance(value, dict):
        return {key: to_dict(item) for key, item in value.items()}
    return value

