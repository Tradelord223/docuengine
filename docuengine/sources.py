from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SourceProvider:
    id: str
    name: str
    base_url: str
    rights_note: str
    api_note: str


PROVIDERS = {
    "nara": SourceProvider(
        id="nara",
        name="National Archives Catalog",
        base_url="https://catalog.archives.gov",
        rights_note="Most records are public domain, but each item still needs restrictions review.",
        api_note="Use Catalog API search and retain catalog identifiers.",
    ),
    "dvids": SourceProvider(
        id="dvids",
        name="DVIDS",
        base_url="https://www.dvidshub.net",
        rights_note="Generally public domain unless another copyright status is indicated.",
        api_note="Use DVIDS search/API metadata and keep unit/source attribution.",
    ),
    "nasa": SourceProvider(
        id="nasa",
        name="NASA Media",
        base_url="https://images.nasa.gov",
        rights_note="NASA imagery is broadly reusable, but logos and endorsement implications are restricted.",
        api_note="Use NASA image/video library metadata and avoid logo/endorsement claims.",
    ),
    "wikimedia_commons": SourceProvider(
        id="wikimedia_commons",
        name="Wikimedia Commons",
        base_url="https://commons.wikimedia.org",
        rights_note="License varies per file; attribution and share-alike obligations must be preserved.",
        api_note="Extract license metadata through MediaWiki APIs.",
    ),
    "pexels": SourceProvider(
        id="pexels",
        name="Pexels",
        base_url="https://www.pexels.com",
        rights_note="Free use under Pexels license; do not resell unaltered assets.",
        api_note="Use Pexels API with source and contributor attribution where possible.",
    ),
    "internet_archive": SourceProvider(
        id="internet_archive",
        name="Internet Archive",
        base_url="https://archive.org",
        rights_note="License/public-domain status varies by item and uploader; verify before use.",
        api_note="Use metadata endpoints and store item identifier plus license fields.",
    ),
    "user_upload": SourceProvider(
        id="user_upload",
        name="User-Owned Upload",
        base_url="local",
        rights_note="User must attest ownership or permission before final rendering.",
        api_note="No external API; hash and store local path.",
    ),
}


def get_provider(provider_id: str) -> SourceProvider:
    try:
        return PROVIDERS[provider_id]
    except KeyError as exc:
        raise ValueError(f"Unknown source provider: {provider_id}") from exc


def build_search_queries(topic: str, preset: str) -> dict[str, list[str]]:
    base = topic.strip()
    return {
        "dvids": [base, f"{base} b-roll", f"{base} exercise footage"],
        "nara": [base, f"{base} archival film", f"{base} declassified"],
        "nasa": [f"{base} satellite", f"{base} mission control"],
        "wikimedia_commons": [base, f"{base} map", f"{base} diagram"],
        "pexels": [f"{base} abstract", "control room", "radar screen"],
        "internet_archive": [base, f"{base} newsreel", f"{base} public domain film"],
        "preset": [preset.replace("_", " ")],
    }

