# The Metallurgical Crucible

First real DocuEngine project package for a 20-minute hybrid documentary.

Important: this is a pre-production package. It has a complete thesis, beat plan, narration draft, source candidates, shot list, generated-insert timeline placeholders, and QA gates. It does not yet include local media clips.

Start with `research_brief.md`, `narration_script.md`, `source_queries.json`, and `review_gates.json`.

Footage storage should use Google Drive for desktop in Stream mode. See `drive_media_manifest.json` for the intended Drive layout and `../../docs/GOOGLE_DRIVE_MEDIA.md` for the workflow.

Drive-side control ledger: https://docs.google.com/spreadsheets/d/<GOOGLE_SHEET_ID>/edit

When footage rows are ready in the ledger, export the Sheet tab as CSV and run:

```bash
python3 -m docuengine ingest-drive-ledger \
  --project-dir projects/metallurgical-crucible \
  --ledger-csv /path/to/media-ledger-export.csv
```
