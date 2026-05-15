# Sidecar Indexing

DocuEngine can build a precise clip index from small JSON sidecars while the original footage stays in Google Drive.

## Asset Metadata

Add one or both fields to a `SourceAsset.metadata` object:

```json
{
  "transcript_path": "sidecars/sr71.transcript.json",
  "scenes_path": "sidecars/sr71.scenes.json"
}
```

Paths are resolved relative to the project directory when using:

```bash
python3 -m docuengine build-clip-index \
  --project-dir projects/metallurgical-crucible
```

Transcript sidecars take priority over scene sidecars. If neither exists, the engine falls back to a single metadata-derived rough clip for the asset.

## Transcript Sidecar

Use this shape for WhisperX-like transcript segments:

```json
{
  "segments": [
    {
      "start": 3.5,
      "end": 9.0,
      "text": "The SR-71 used titanium to survive extreme runway-to-Mach heat cycles."
    }
  ]
}
```

Accepted time keys are `start`/`end` or `start_seconds`/`end_seconds`.

## Scene Sidecar

Use this shape for PySceneDetect-like scene ranges:

```json
{
  "scenes": [
    {
      "start_seconds": 0.0,
      "end_seconds": 7.25
    }
  ]
}
```

The sidecar files are intentionally tiny and safe to commit. Do not commit video/audio originals.
