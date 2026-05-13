from __future__ import annotations

import json
import re
from typing import Any


def build_ffprobe_command(path: str) -> list[str]:
    return [
        "ffprobe",
        "-v",
        "error",
        "-show_format",
        "-show_streams",
        "-print_format",
        "json",
        path,
    ]


def build_blackdetect_command(path: str, min_duration: float = 0.5, pixel_threshold: float = 0.1) -> list[str]:
    return [
        "ffmpeg",
        "-hide_banner",
        "-i",
        path,
        "-vf",
        f"blackdetect=d={min_duration:g}:pix_th={pixel_threshold:g}",
        "-an",
        "-f",
        "null",
        "-",
    ]


def build_loudnorm_command(
    path: str,
    integrated_lufs: float = -16,
    true_peak_db: float = -1.5,
    loudness_range: float = 11,
) -> list[str]:
    return [
        "ffmpeg",
        "-hide_banner",
        "-i",
        path,
        "-af",
        (
            f"loudnorm=I={integrated_lufs:g}:TP={true_peak_db:g}:"
            f"LRA={loudness_range:g}:print_format=json"
        ),
        "-f",
        "null",
        "-",
    ]


def parse_blackdetect_events(log_text: str) -> list[dict[str, float]]:
    pattern = re.compile(
        r"black_start:(?P<start>-?\d+(?:\.\d+)?)\s+"
        r"black_end:(?P<end>-?\d+(?:\.\d+)?)\s+"
        r"black_duration:(?P<duration>-?\d+(?:\.\d+)?)"
    )
    return [
        {
            "start": float(match.group("start")),
            "end": float(match.group("end")),
            "duration": float(match.group("duration")),
        }
        for match in pattern.finditer(log_text)
    ]


def parse_loudnorm_summary(log_text: str) -> dict[str, Any]:
    start = log_text.find("{")
    end = log_text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError("No loudnorm JSON summary found")
    payload = json.loads(log_text[start : end + 1])
    return {key: _coerce_number(value) for key, value in payload.items()}


def _coerce_number(value: Any) -> Any:
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            return value
    return value
