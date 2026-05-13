# Google Drive Media Storage

Yes, DocuEngine can use Google Drive as the footage library without bloating this repo or keeping every original on the Mac.

## Recommended Setup

Use **Google Drive for desktop** in **Stream files** mode.

- Stream files: files appear in Finder, but originals stay in Drive until opened or explicitly made offline.
- Mirror files: Drive keeps everything on local disk. Do not use this for a large footage library.

Google's Drive for desktop support docs describe this stream/mirror distinction: https://support.google.com/drive/answer/13401938

## Folder Layout

Recommended Drive layout:

```text
Google Drive/
  My Drive/
    DocuEngine/
      metallurgical-crucible/
        originals/
        proxies/
        exports/
```

Recommended repo layout:

```text
projects/
  metallurgical-crucible/
    drive_media_manifest.json
    assets.json
    rights_ledger.json
    clip_index.json
    timeline.json
```

The repo stores metadata and edit decisions. Google Drive stores actual footage.

## How Editing Works Without Bloating The Mac

1. Store full-resolution footage in `originals/` on Google Drive.
2. Keep Drive for desktop in Stream mode.
3. Generate or store small proxy clips in `proxies/`.
4. Build rough cuts in Final Cut Pro from proxies where possible.
5. Only stage selected originals locally for final conform/export.
6. Delete temporary local staging files after final render.

Important: when Final Cut Pro opens streamed Drive media, Google Drive may cache that media locally while it is active. This is still much lighter than mirroring the entire footage library, but it is not zero local disk use.

## Why Proxies Matter

Final Cut Pro works best with real file paths. A Drive-streamed file path can work, but opening large originals may trigger downloads and cache growth. Proxies keep the active edit light:

- Low-resolution proxy for rough cut
- Original Drive file preserved for final conform
- `.fcpxml` points to whichever media set is active

## DocuEngine Policy

- Do not commit video/audio media to git.
- Keep only manifests, rights records, transcripts, clip indexes, and timelines in the repo.
- Treat Drive original paths as source-of-truth references.
- Treat local paths as temporary cache/staging unless explicitly marked otherwise.

## Register Drive Footage From The Ledger

After adding rows to the Drive media ledger, export the Sheet tab as CSV and run:

```bash
python3 -m docuengine ingest-drive-ledger \
  --project-dir projects/metallurgical-crucible \
  --ledger-csv /path/to/media-ledger-export.csv
```

Rows are ingested only when `Status` is `ready`, `approved`, `ingest`, `ingest_ready`, or `selected`. Rows still marked `needed`, `pending`, or blank are skipped and recorded in `drive_ledger_ingest_report.json`.

Expected ledger columns:

- `Asset ID`
- `Status`
- `Provider`
- `Source URL`
- `Drive Original Path`
- `Drive Proxy Path`
- `Rights Status`
- `Attribution`
- `Beat/Use`
- `Notes`

Cloud-backed assets pass the missing-media gate when they include a Drive original path, Drive proxy path, Drive file ID, or `My Drive/` path. Final Cut Pro may still download/cache selected media when opening an edit.
