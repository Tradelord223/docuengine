# Lightweight Architecture

The cheapest durable version of this project is not a full editing application. It is a planning, rights, clipping, timeline, and interchange engine that hands off finishing work to tools that already exist.

## Keep the Core Small

- Use only the Python standard library in the core package.
- Store project state as JSON files that can be inspected, diffed, and regenerated.
- Treat heavyweight tools as optional adapters: FFmpeg, WhisperX, PySceneDetect, Final Cut Pro, Logic Pro, and generative video APIs.
- Prefer command builders and import/export files over direct GUI automation.
- Avoid local model downloads until a project actually needs them.

## Final Cut Pro Edge

Final Cut Pro is useful because the engine can export `.fcpxml` timelines instead of trying to become a full non-linear editor.

Practical workflow:

1. DocuEngine researches, validates rights, scores clips, and builds a timeline.
2. DocuEngine exports `.fcpxml`.
3. Final Cut Pro imports the timeline for magnetic-timeline editing, captions, color, titles, multicam work, and final export.

This keeps the engine lightweight while still taking advantage of a professional editor.

## Logic Pro Edge

Logic Pro is useful for audio finishing because Apple supports Final Cut Pro XML interchange between Final Cut Pro and Logic Pro.

Practical workflow:

1. DocuEngine generates narration, subtitle timing, source citations, and a rough audio plan.
2. Final Cut Pro imports the `.fcpxml` rough cut.
3. Logic Pro receives the project through Final Cut Pro XML for dialogue cleanup, sound design, music, loudness, and stem export.
4. Final Cut Pro receives the mixed audio back for final render.

DocuEngine should not try to replace Logic. It should provide clean roles, timing, and source structure so Logic can do the work it is best at.

## Minimal V1 Toolchain

Required:

- Python 3.11+
- Git

Optional:

- Final Cut Pro for visual finishing through `.fcpxml`
- Logic Pro for audio finishing through Final Cut Pro XML
- FFmpeg/ffprobe for render checks
- WhisperX for transcript timing
- PySceneDetect for shot boundary detection

## What Not To Build Yet

- A custom visual editor
- A custom DAW
- Heavy local model orchestration
- Cloud job infrastructure
- Browser automation for editing apps
- A database before JSON files become painful

