from __future__ import annotations

from pathlib import Path
from urllib.parse import quote
from xml.dom import minidom
from xml.etree.ElementTree import Element, SubElement, tostring

from docuengine.models import ProjectSpec, SourceAsset, TimelinePlan


ROLE_MAP = {
    "primary_broll": "video",
    "broll": "video",
    "dialogue": "dialogue",
    "music": "music",
    "effects": "effects",
}


def seconds_to_fcpxml_time(seconds: float, fps: int | float) -> str:
    frames = round(seconds * fps)
    return f"{frames}/{int(fps)}s"


def build_fcpxml_document(
    project: ProjectSpec,
    assets: list[SourceAsset],
    timeline: TimelinePlan,
    version: str = "1.10",
) -> str:
    fps = int(project.output_profile.get("fps", timeline.render_profile.get("fps", 24)))
    width = int(project.output_profile.get("width", timeline.render_profile.get("width", 1920)))
    height = int(project.output_profile.get("height", timeline.render_profile.get("height", 1080)))
    asset_by_id = {asset.id: asset for asset in assets}
    asset_ref_by_id = {asset.id: f"r{index + 2}" for index, asset in enumerate(assets)}

    root = Element("fcpxml", {"version": version})
    resources = SubElement(root, "resources")
    format_id = "r1"
    SubElement(
        resources,
        "format",
        {
            "id": format_id,
            "name": f"FFVideoFormat{height}p{fps}",
            "frameDuration": f"1/{fps}s",
            "width": str(width),
            "height": str(height),
            "colorSpace": "1-1-1 (Rec. 709)",
        },
    )

    for asset in assets:
        SubElement(
            resources,
            "asset",
            {
                "id": asset_ref_by_id[asset.id],
                "name": asset.metadata.get("title", asset.id),
                "src": _file_url(asset.local_path),
                "start": "0s",
                "hasVideo": "1" if asset.media_type == "video" else "0",
                "hasAudio": "1" if asset.media_type in {"video", "audio"} else "0",
                "format": format_id,
            },
        )

    library = SubElement(root, "library")
    event = SubElement(library, "event", {"name": "DocuEngine"})
    project_node = SubElement(event, "project", {"name": project.topic})
    duration = _timeline_duration(timeline)
    sequence = SubElement(
        project_node,
        "sequence",
        {
            "format": format_id,
            "duration": seconds_to_fcpxml_time(duration, fps),
            "tcStart": "0s",
            "tcFormat": "NDF",
        },
    )
    spine = SubElement(sequence, "spine")

    for track in timeline.tracks:
        if track.kind != "video":
            continue
        for clip in track.clips:
            asset = asset_by_id.get(clip.source_asset_id)
            if asset is None:
                continue
            SubElement(
                spine,
                "asset-clip",
                {
                    "name": asset.metadata.get("title", clip.id),
                    "ref": asset_ref_by_id[asset.id],
                    "offset": seconds_to_fcpxml_time(clip.timeline_start_seconds, fps),
                    "start": seconds_to_fcpxml_time(clip.source_start_seconds, fps),
                    "duration": seconds_to_fcpxml_time(
                        clip.timeline_end_seconds - clip.timeline_start_seconds,
                        fps,
                    ),
                    "role": ROLE_MAP.get(clip.role, "video"),
                },
            )

    return _pretty_xml(root)


def _timeline_duration(timeline: TimelinePlan) -> float:
    ends = [
        clip.timeline_end_seconds
        for track in timeline.tracks
        for clip in track.clips
    ]
    return max(ends or [0.0])


def _file_url(path: str) -> str:
    absolute = Path(path).expanduser().absolute()
    return "file://" + quote(str(absolute))


def _pretty_xml(root: Element) -> str:
    compact = tostring(root, encoding="utf-8")
    parsed = minidom.parseString(compact)
    return parsed.toprettyxml(indent="  ")
