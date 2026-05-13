# Final Cut / Logic Handoff Notes

This project is currently a pre-production package. Final Cut Pro handoff should happen after source footage is downloaded, rights-checked, and clipped.

## Recommended Next Step

1. Search the source queries in `source_queries.json`.
2. Add only rights-cleared media to the Google Drive project folders, preferably with low-resolution proxies.
3. Mark ready rows in the Drive media ledger and export the ledger tab as CSV.
4. Run `python3 -m docuengine ingest-drive-ledger --project-dir projects/metallurgical-crucible --ledger-csv /path/to/media-ledger-export.csv`.
5. Run clip detection/transcription.
6. Re-run timeline planning.
7. Export `.fcpxml` for Final Cut Pro.
8. Send the project to Logic Pro for dialogue/music/sound finishing after picture lock.

## Why No FCPXML Yet

The current timeline contains generated insert placeholders and no local video assets. Exporting `.fcpxml` now would produce an empty or non-useful timeline. The QA gate correctly blocks final render until media is attached.
