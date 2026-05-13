# Final Cut / Logic Handoff Notes

This project is currently a pre-production package. Final Cut Pro handoff should happen after source footage is downloaded, rights-checked, and clipped.

## Recommended Next Step

1. Search the source queries in `source_queries.json`.
2. Download only rights-cleared media into a local `media/` directory that is not committed to git.
3. Create `SourceAsset` records with rights ledgers.
4. Run clip detection/transcription.
5. Re-run timeline planning.
6. Export `.fcpxml` for Final Cut Pro.
7. Send the project to Logic Pro for dialogue/music/sound finishing after picture lock.

## Why No FCPXML Yet

The current timeline contains generated insert placeholders and no local video assets. Exporting `.fcpxml` now would produce an empty or non-useful timeline. The QA gate correctly blocks final render until media is attached.
