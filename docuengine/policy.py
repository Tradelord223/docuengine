from __future__ import annotations

from dataclasses import dataclass, field

from docuengine.models import ProjectSpec, SourceAsset


PERMISSIVE_LICENSES = {
    "public_domain",
    "cc0",
    "cc-by",
    "cc-by-sa",
    "pexels",
    "us_government_work",
    "owned",
    "explicit_permission",
}

NON_COMMERCIAL_MARKERS = {"nc", "noncommercial", "non-commercial"}
NO_DERIVATIVE_MARKERS = {"nd", "no_derivatives", "no-derivatives"}
YOUTUBE_ALLOWED_USAGE = {"user_owned", "explicit_permission", "service_authorized_download"}


@dataclass
class SourceDecision:
    allowed: bool
    reasons: list[str] = field(default_factory=list)
    required_actions: list[str] = field(default_factory=list)
    normalized_license: str = "unknown"


class RightsPolicy:
    """Rights and provider policy for documentary-safe source ingestion."""

    def validate_asset(self, asset: SourceAsset, project: ProjectSpec) -> SourceDecision:
        reasons: list[str] = []
        required_actions = ["preserve_source_url"]

        provider = asset.provider.lower().strip()
        source_url = asset.source_url.lower()
        is_youtube = provider == "youtube" or "youtube.com/" in source_url or "youtu.be/" in source_url

        if is_youtube:
            rights_usage = set(asset.rights.allowed_usage if asset.rights else [])
            if not rights_usage.intersection(YOUTUBE_ALLOWED_USAGE):
                reasons.append(
                    "YouTube assets require user ownership, explicit permission, or a service-authorized download"
                )

        if provider not in set(project.allowed_providers) and not is_youtube:
            reasons.append(f"Provider is not allowed for this project: {asset.provider}")

        if asset.rights is None:
            reasons.append(f"Missing rights ledger for asset: {asset.id}")
            return SourceDecision(
                allowed=False,
                reasons=reasons,
                required_actions=required_actions,
                normalized_license="missing",
            )

        license_id = asset.rights.license_id.lower().strip()
        restrictions = {item.lower().strip() for item in asset.rights.restrictions}
        allowed_usage = {item.lower().strip() for item in asset.rights.allowed_usage}

        if asset.rights.attribution.strip():
            required_actions.append("keep_attribution")

        if provider in {"dvids", "nasa", "nara"}:
            required_actions.append("no_government_endorsement")

        if license_id not in PERMISSIVE_LICENSES and not license_id.startswith("cc-by"):
            reasons.append(f"License is not in the approved V1 allowlist: {asset.rights.license_id}")

        if _contains_marker(license_id, NON_COMMERCIAL_MARKERS) or restrictions.intersection(NON_COMMERCIAL_MARKERS):
            reasons.append("Non-commercial licenses are not allowed for documentary exports")

        if _contains_marker(license_id, NO_DERIVATIVE_MARKERS) or restrictions.intersection(NO_DERIVATIVE_MARKERS):
            reasons.append("No-derivatives licenses cannot be transformed into an edited documentary")

        if "transform" not in allowed_usage:
            reasons.append("Rights record must explicitly allow transformative editing")

        if "commercial" not in allowed_usage:
            reasons.append("Rights record must explicitly allow commercial/editorial distribution")

        return SourceDecision(
            allowed=not reasons,
            reasons=reasons,
            required_actions=sorted(set(required_actions)),
            normalized_license=license_id,
        )


def _contains_marker(value: str, markers: set[str]) -> bool:
    parts = {part for chunk in value.replace("_", "-").split("-") for part in [chunk]}
    return bool(parts.intersection(markers) or any(marker in value for marker in markers))

