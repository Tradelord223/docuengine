from __future__ import annotations

from docuengine.models import (
    BeatPlan,
    ClipSegment,
    GeneratedInsert,
    Overlay,
    ProjectSpec,
    TimelineClip,
    TimelinePlan,
    TimelineTrack,
)


def score_clip_for_beat(
    clip: ClipSegment,
    beat: BeatPlan,
    used_asset_ids: set[str] | None = None,
) -> float:
    used_asset_ids = used_asset_ids or set()
    tags = {tag.lower() for tag in clip.semantic_tags}
    transcript = clip.transcript.lower()
    required = [item.lower() for item in beat.required_visuals]

    direct_matches = sum(1 for item in required if item in tags or item in transcript)
    relevance = direct_matches / max(len(required), 1)
    approved_bonus = 1.0 if clip.rights_status == "approved" else 0.0
    novelty_penalty = 0.18 if clip.source_asset_id in used_asset_ids else 0.0
    suggested_bonus = 0.08 if "primary" in clip.suggested_use.lower() or "b-roll" in clip.suggested_use.lower() else 0.0

    return round(
        (0.48 * relevance)
        + (0.18 * clip.visual_quality_score)
        + (0.10 * clip.audio_quality_score)
        + (0.16 * approved_bonus)
        + suggested_bonus
        - novelty_penalty,
        4,
    )


def plan_timeline(
    project: ProjectSpec,
    beats: list[BeatPlan],
    clips: list[ClipSegment],
) -> TimelinePlan:
    picture_track = TimelineTrack(name="Picture", kind="video")
    overlays: list[Overlay] = []
    generated_inserts: list[GeneratedInsert] = []
    subtitle_track: list[dict[str, object]] = []

    cursor = 0.0
    used_asset_ids: set[str] = set()
    beat_duration = project.target_duration_seconds / max(len(beats), 1)

    for beat in beats:
        selected = _select_clip(beat, clips, used_asset_ids)
        target_length = max(5.0, min(beat_duration, 22.0))
        planned_length = target_length

        if selected is None:
            generated_inserts.append(
                GeneratedInsert(
                    id=f"gen-{beat.id}",
                    reason=f"No approved source clip matched beat {beat.id}",
                    prompt=_generation_prompt(project, beat),
                    approved_provider=None,
                    estimated_cost_usd=0.0,
                )
            )
            overlays.append(
                Overlay(
                    id=f"placeholder-{beat.id}",
                    kind="chapter_card",
                    text=beat.chapter,
                    start_seconds=cursor,
                    end_seconds=cursor + min(target_length, 8.0),
                    metadata={"requires_visual": True},
                )
            )
        else:
            length = min(target_length, selected.duration_seconds)
            planned_length = length
            timeline_clip = TimelineClip(
                id=f"tl-{beat.id}-{selected.id}",
                source_clip_id=selected.id,
                source_asset_id=selected.source_asset_id,
                timeline_start_seconds=cursor,
                timeline_end_seconds=cursor + length,
                source_start_seconds=selected.start_seconds,
                source_end_seconds=selected.start_seconds + length,
                role="primary_broll",
                rationale=f"Matched {beat.chapter}: {', '.join(beat.required_visuals)}",
            )
            picture_track.clips.append(timeline_clip)
            used_asset_ids.add(selected.source_asset_id)

        overlays.append(
            Overlay(
                id=f"chapter-{beat.id}",
                kind="lower_third",
                text=beat.chapter,
                start_seconds=cursor,
                end_seconds=cursor + min(planned_length, 6.0),
                metadata={"emotional_intensity": beat.emotional_intensity},
            )
        )

        for index, citation in enumerate(beat.citations):
            overlays.append(
                Overlay(
                    id=f"citation-{beat.id}-{index}",
                    kind="source_citation",
                    text=f"{citation.publisher}: {citation.title}",
                    start_seconds=max(cursor, cursor + planned_length - 5.0),
                    end_seconds=cursor + planned_length,
                    metadata={"url": citation.url, "accessed_at": citation.accessed_at},
                )
            )

        subtitle_track.append(
            {
                "beat_id": beat.id,
                "start_seconds": cursor,
                "end_seconds": cursor + planned_length,
                "text": beat.narration,
            }
        )
        cursor += planned_length

    tracks = [picture_track]
    otio = _build_otio(project, tracks)
    return TimelinePlan(
        project_topic=project.topic,
        target_duration_seconds=project.target_duration_seconds,
        render_profile=dict(project.output_profile),
        tracks=tracks,
        overlays=overlays,
        generated_inserts=generated_inserts,
        otio=otio,
        music_bed={"strategy": "licensed_or_original_only", "duck_under_narration_db": -10},
        subtitle_track=subtitle_track,
    )


def _select_clip(
    beat: BeatPlan,
    clips: list[ClipSegment],
    used_asset_ids: set[str],
) -> ClipSegment | None:
    approved = [clip for clip in clips if clip.rights_status == "approved"]
    if not approved:
        return None
    ranked = sorted(
        approved,
        key=lambda clip: score_clip_for_beat(clip, beat, used_asset_ids),
        reverse=True,
    )
    best = ranked[0]
    if score_clip_for_beat(best, beat, used_asset_ids) < 0.25:
        return None
    return best


def _generation_prompt(project: ProjectSpec, beat: BeatPlan) -> str:
    visual_list = ", ".join(beat.required_visuals)
    return (
        f"Create a short abstract documentary insert for '{project.topic}'. "
        f"Tone: {project.mood}. Beat: {beat.chapter}. Visual needs: {visual_list}. "
        "Avoid depicting real living people unless explicit consent is documented."
    )


def _build_otio(project: ProjectSpec, tracks: list[TimelineTrack]) -> dict[str, object]:
    return {
        "OTIO_SCHEMA": "Timeline.1",
        "name": project.topic,
        "metadata": {
            "preset": project.preset,
            "target_duration_seconds": project.target_duration_seconds,
            "render_profile": dict(project.output_profile),
        },
        "tracks": [
            {
                "OTIO_SCHEMA": "Stack.1",
                "name": track.name,
                "kind": track.kind,
                "children": [
                    {
                        "OTIO_SCHEMA": "Clip.2",
                        "name": clip.id,
                        "metadata": {
                            "source_clip_id": clip.source_clip_id,
                            "source_asset_id": clip.source_asset_id,
                            "role": clip.role,
                            "rationale": clip.rationale,
                        },
                        "source_range": {
                            "start_time": clip.source_start_seconds,
                            "duration": clip.source_end_seconds - clip.source_start_seconds,
                        },
                        "timeline_range": {
                            "start_time": clip.timeline_start_seconds,
                            "duration": clip.timeline_end_seconds - clip.timeline_start_seconds,
                        },
                    }
                    for clip in track.clips
                ],
            }
            for track in tracks
        ],
    }
