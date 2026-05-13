from __future__ import annotations

import csv
import hashlib
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from docuengine.ingest import infer_media_type
from docuengine.models import RightsRecord, SourceAsset


READY_STATUSES = {"ready", "approved", "ingest", "ingest_ready", "selected"}

LICENSE_ALIASES = {
    "approved": "explicit_permission",
    "explicit permission": "explicit_permission",
    "explicit_permission": "explicit_permission",
    "owned": "owned",
    "user owned": "owned",
    "user_owned": "owned",
    "public domain": "public_domain",
    "public_domain": "public_domain",
    "pd": "public_domain",
    "us government work": "us_government_work",
    "us_government_work": "us_government_work",
    "u.s. government work": "us_government_work",
    "cc0": "cc0",
    "cc-by": "cc-by",
    "cc by": "cc-by",
    "cc-by-sa": "cc-by-sa",
    "pexels": "pexels",
}

PROVIDER_ALIASES = {
    "dvids": "dvids",
    "defense visual information distribution service": "dvids",
    "nara": "nara",
    "national archives": "nara",
    "national archives and records administration": "nara",
    "nasa": "nasa",
    "wikimedia": "wikimedia_commons",
    "wikimedia commons": "wikimedia_commons",
    "commons": "wikimedia_commons",
    "pexels": "pexels",
    "internet archive": "internet_archive",
    "archive.org": "internet_archive",
    "user upload": "user_upload",
    "user_upload": "user_upload",
}


@dataclass
class DriveLedgerIngestResult:
    assets: list[SourceAsset]
    skipped_rows: list[dict[str, str]]


def ingest_drive_ledger_csv(path: str | Path) -> DriveLedgerIngestResult:
    """Convert a Google Drive media ledger CSV export into DocuEngine assets."""
    ledger_path = Path(path)
    assets: list[SourceAsset] = []
    skipped_rows: list[dict[str, str]] = []

    with ledger_path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        for row_number, row in enumerate(reader, start=2):
            normalized = _normalize_row(row)
            status = _value(normalized, "status").lower().strip()
            if status not in READY_STATUSES:
                skipped_rows.append({"row": str(row_number), "reason": "status_not_ready"})
                continue

            source_url = _value(normalized, "source url", "source_url", "url")
            drive_original = _value(normalized, "drive original path", "original path", "drive_original_path")
            drive_proxy = _value(normalized, "drive proxy path", "proxy path", "drive_proxy_path")
            rights_status = _value(normalized, "rights status", "license", "license id", "license_id")
            provider = _normalize_provider(_value(normalized, "provider", "source provider"))
            license_id = _normalize_license(rights_status)

            if not source_url:
                skipped_rows.append({"row": str(row_number), "reason": "missing_source_url"})
                continue
            if not drive_original and not drive_proxy:
                skipped_rows.append({"row": str(row_number), "reason": "missing_drive_path"})
                continue
            if not license_id:
                skipped_rows.append({"row": str(row_number), "reason": "unapproved_rights_status"})
                continue
            if not provider:
                skipped_rows.append({"row": str(row_number), "reason": "missing_provider"})
                continue

            asset_id = _asset_id(_value(normalized, "asset id", "asset_id"), source_url, row_number)
            media_path = drive_proxy or drive_original
            rights = RightsRecord(
                source_url=source_url,
                license_id=license_id,
                attribution=_value(normalized, "attribution", "credit"),
                downloaded_at=_value(normalized, "download date", "downloaded at", "downloaded_at")
                or datetime.now(UTC).date().isoformat(),
                restrictions=_split_list(_value(normalized, "restrictions")),
                allowed_usage=["commercial", "transform", "editorial"],
            )
            assets.append(
                SourceAsset(
                    id=asset_id,
                    local_path=media_path,
                    source_url=source_url,
                    media_type=_infer_drive_media_type(media_path),
                    provider=provider,
                    metadata={
                        "storage": "google_drive",
                        "drive_original_path": drive_original,
                        "drive_proxy_path": drive_proxy,
                        "ledger_status": status,
                        "rights_status": rights_status,
                        "beat_use": _value(normalized, "beat/use", "beat use", "use"),
                        "notes": _value(normalized, "notes"),
                        "source_row": row_number,
                    },
                    checksum=_drive_checksum(source_url, drive_original, drive_proxy),
                    rights=rights,
                )
            )

    return DriveLedgerIngestResult(assets=assets, skipped_rows=skipped_rows)


def _normalize_row(row: dict[str, str | None]) -> dict[str, str]:
    return {key.strip().lower(): (value or "").strip() for key, value in row.items() if key}


def _value(row: dict[str, str], *keys: str) -> str:
    for key in keys:
        value = row.get(key.lower())
        if value:
            return value
    return ""


def _asset_id(raw: str, source_url: str, row_number: int) -> str:
    candidate = raw or Path(source_url.rstrip("/")).name or f"drive-ledger-row-{row_number}"
    slug = re.sub(r"[^a-z0-9]+", "-", candidate.lower()).strip("-")
    return slug or f"drive-ledger-row-{row_number}"


def _normalize_provider(value: str) -> str:
    key = value.lower().strip()
    if not key:
        return ""
    return PROVIDER_ALIASES.get(key, re.sub(r"[^a-z0-9]+", "_", key).strip("_"))


def _normalize_license(value: str) -> str:
    key = value.lower().strip()
    if not key or key in {"pending", "needed", "unknown", "unreviewed"}:
        return ""
    return LICENSE_ALIASES.get(key, key.replace(" ", "_"))


def _infer_drive_media_type(path: str) -> str:
    media_type = infer_media_type(path)
    return "video" if media_type == "unknown" else media_type


def _drive_checksum(source_url: str, drive_original: str, drive_proxy: str) -> str:
    payload = "|".join([source_url, drive_original, drive_proxy]).encode("utf-8")
    return "drive-sha256:" + hashlib.sha256(payload).hexdigest()


def _split_list(value: str) -> list[str]:
    if not value:
        return []
    return [item.strip() for item in re.split(r"[,;]", value) if item.strip()]
