# Final Cut / Logic Handoff Notes

This project is currently a pre-production package. Final Cut Pro handoff should happen after source footage is downloaded, rights-checked, and clipped.

## Recommended Next Step

1. Search the source queries in `source_queries.json`.
2. Add only rights-cleared media to the Google Drive project folders, preferably with low-resolution proxies.
3. Mark ready rows in the Drive media ledger and export the ledger tab as CSV.
4. Run `python3 -m docuengine ingest-drive-ledger --project-dir projects/metallurgical-crucible --ledger-csv /path/to/media-ledger-export.csv`.
5. Run `python3 -m docuengine build-clip-index --project-dir projects/metallurgical-crucible` to create a lightweight rough clip index and first timeline from asset metadata.
6. Add real scene detection/transcription sidecars for higher precision.
7. Run `python3 -m docuengine prepare-rough-cut --project-dir projects/metallurgical-crucible --fcpxml-out projects/metallurgical-crucible/metallurgical-crucible.fcpxml --media-root "/Volumes/GoogleDrive/My Drive"` to refresh the rough cut and export `.fcpxml` only when gates pass.
8. Send the project to Logic Pro for dialogue/music/sound finishing after picture lock.

## Why No FCPXML Yet

The current timeline contains generated insert placeholders and no local video assets. Exporting `.fcpxml` now would produce an empty or non-useful timeline. The QA gate correctly blocks final render until media is attached.
