from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass(frozen=True)
class GoogleDriveLibraryPlan:
    mode: str
    project_slug: str
    drive_root: Path
    project_drive_dir: Path
    originals_dir: Path
    proxies_dir: Path
    exports_dir: Path
    repo_project_dir: Path
    manifest_path: Path
    notes: list[str]

    def to_dict(self) -> dict[str, object]:
        payload = asdict(self)
        for key, value in list(payload.items()):
            if isinstance(value, Path):
                payload[key] = str(value)
        return payload


def make_project_slug(title: str, max_length: int = 80) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
    slug = re.sub(r"-+", "-", slug)
    if not slug:
        return "untitled-project"
    return slug[:max_length].strip("-")


def build_google_drive_library_plan(
    drive_root: str | Path,
    project_title: str,
    repo_root: str | Path,
    library_folder: str = "DocuEngine",
    project_slug: str | None = None,
) -> GoogleDriveLibraryPlan:
    drive_root_path = Path(drive_root).expanduser()
    repo_root_path = Path(repo_root).expanduser()
    slug = project_slug or make_project_slug(project_title)
    project_drive_dir = drive_root_path / library_folder / slug
    repo_project_dir = repo_root_path / "projects" / slug

    return GoogleDriveLibraryPlan(
        mode="streamed_originals",
        project_slug=slug,
        drive_root=drive_root_path,
        project_drive_dir=project_drive_dir,
        originals_dir=project_drive_dir / "originals",
        proxies_dir=project_drive_dir / "proxies",
        exports_dir=project_drive_dir / "exports",
        repo_project_dir=repo_project_dir,
        manifest_path=repo_project_dir / "drive_media_manifest.json",
        notes=[
            "Configure Google Drive for desktop to Stream files, not Mirror files.",
            "Store original footage in originals_dir; do not commit media to git.",
            "Use low-resolution proxies for Final Cut Pro rough cuts when possible.",
            "Expect opened Drive files to be cached locally while actively used by editing software.",
        ],
    )


def classify_media_location(path: str | Path, drive_root: str | Path) -> dict[str, str]:
    media_path = Path(path).expanduser()
    drive_root_path = Path(drive_root).expanduser()
    if _is_relative_to(media_path, drive_root_path):
        return {
            "storage": "google_drive",
            "locality": "streamed_or_cached",
            "path": str(media_path),
            "drive_root": str(drive_root_path),
        }
    return {
        "storage": "local",
        "locality": "local_file",
        "path": str(media_path),
        "drive_root": str(drive_root_path),
    }


def _is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except (FileNotFoundError, RuntimeError, ValueError):
        try:
            path.absolute().relative_to(root.absolute())
            return True
        except ValueError:
            return False
