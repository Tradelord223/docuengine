# DocuEngine

DocuEngine is a local-first skeleton for an autonomous long-form documentary editing engine. It is built around a practical hybrid workflow: use rights-cleared real footage as the primary material, use LLM planning for research and edit decisions, and reserve generative video for short inserts or missing shots that pass approval gates.

## What This Implements

- Stable public objects for `ProjectSpec`, `RightsRecord`, `SourceAsset`, `ClipSegment`, `BeatPlan`, `TimelinePlan`, and `ReviewGate`.
- A rights policy that defaults to public-domain, permissive, user-owned, and explicitly permitted assets.
- A hard YouTube safety rule: YouTube assets are blocked unless marked as user-owned, explicitly permitted, or service-authorized.
- Clip scoring and timeline planning that produces an OTIO-shaped JSON timeline.
- QA gates for rights ledger, missing media, citation coverage, timeline integrity, duplicate clip overuse, and unsafe operational detail.
- Render-check helpers for `ffprobe`, `blackdetect`, and `loudnorm` validation.
- A zero-dependency Final Cut Pro XML exporter for handing rough cuts to Final Cut Pro and Logic Pro.
- A Google Drive media-ledger importer that registers cloud-backed footage without copying originals into the repo.
- A metadata clip-index builder that turns registered Drive assets into rough searchable clips and a first timeline without downloading originals.
- A demo CLI that writes project artifacts without requiring paid APIs or heavy video dependencies.

## Quick Start

```bash
python3 -m docuengine demo --out /tmp/docuengine-demo --topic "radar deception in modern warfare"
```

Export a rough-cut timeline for Final Cut Pro:

```bash
python3 -m docuengine export-fcpxml \
  --project /tmp/docuengine-demo/project.json \
  --assets /tmp/docuengine-demo/assets.json \
  --timeline /tmp/docuengine-demo/timeline.json \
  --out /tmp/docuengine-demo/project.fcpxml
```

When exporting Drive-backed media, point `--media-root` at the local Google Drive for desktop mount or proxy folder:

```bash
python3 -m docuengine export-fcpxml \
  --project projects/metallurgical-crucible/project.json \
  --assets projects/metallurgical-crucible/assets.json \
  --timeline projects/metallurgical-crucible/timeline.json \
  --out projects/metallurgical-crucible/metallurgical-crucible.fcpxml \
  --media-root "/Volumes/GoogleDrive/My Drive"
```

Import a Google Drive media ledger CSV:

```bash
python3 -m docuengine ingest-drive-ledger \
  --project-dir projects/metallurgical-crucible \
  --ledger-csv /path/to/media-ledger-export.csv
```

The Drive importer updates `assets.json`, `rights_ledger.json`, `review_gates.json`, and `drive_ledger_ingest_report.json`. The actual footage can remain in Google Drive; DocuEngine stores Drive paths and rights metadata locally.

Build a rough clip index and timeline from registered assets:

```bash
python3 -m docuengine build-clip-index \
  --project-dir projects/metallurgical-crucible
```

This writes `clip_index.json`, refreshes `timeline.json`, and re-runs `review_gates.json`. It uses asset metadata first, so it remains lightweight until you add real scene detection or transcript sidecars.

For precise timing, attach transcript or scene JSON sidecars to asset metadata. See `docs/SIDECAR_INDEXING.md`.

The demo writes:

- `project.json`
- `assets.json`
- `rights_ledger.json`
- `clip_index.json`
- `beat_plan.json`
- `timeline.json`
- `review_gates.json`
- `source_queries.json`

The demo media is a placeholder. Replace it with a real rights-cleared clip before rendering.

## Architecture

The engine is intentionally modular:

- `docuengine.models`: typed project, source, clip, timeline, and review objects.
- `docuengine.policy`: provider/license validation and approval actions.
- `docuengine.sources`: source-provider metadata and query planning.
- `docuengine.ingest`: local asset hashing, media typing, and transcript-to-clip conversion.
- `docuengine.drive_ledger`: Google Drive Sheet CSV ingestion for cloud-backed media assets.
- `docuengine.clip_index`: lightweight metadata-derived clip indexing.
- `docuengine.planner`: clip scoring and OTIO-shaped timeline planning.
- `docuengine.qa`: mandatory review gates before final render.
- `docuengine.render_checks`: command builders and parsers for render QA.
- `docuengine.fcpxml`: minimal Final Cut Pro XML export.
- `docuengine.cli`: local artifact generation.

## Final Cut Pro And Logic Pro

Final Cut Pro and Logic Pro are useful edges because they let DocuEngine stay small. The engine should make edit decisions and export `.fcpxml`; Final Cut Pro handles finishing, and Logic Pro handles audio cleanup/mix work through Final Cut Pro XML interchange.

See `docs/LIGHTWEIGHT_ARCHITECTURE.md` for the recommended workflow.

## Google Drive Media Storage

Large footage should live outside the repo. The recommended setup is Google Drive for desktop in **Stream files** mode, with DocuEngine storing only metadata, rights ledgers, clip indexes, and timelines locally.

See `docs/GOOGLE_DRIVE_MEDIA.md`.

## Source Policy

V1 source providers are:

- DVIDS
- National Archives
- NASA media
- Wikimedia Commons
- Pexels
- Internet Archive
- User-owned uploads

Each asset must keep a rights ledger with source URL, license, attribution, restrictions, allowed usage, and download date.

## Tests

```bash
python3 -m unittest discover
```
