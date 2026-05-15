# Durable Goal

Build DocuEngine into a lightweight, local-first autonomous documentary editing engine for high-quality long-form hybrid documentaries.

## End State

DocuEngine should ingest rights-cleared real footage, build a source ledger, create semantically useful clip indexes, plan documentary timelines, export professional interchange files, and run mandatory quality gates before final render or publishing.

## Hard Constraints

- Keep the core dependency-free or near dependency-free.
- Use Final Cut Pro and Logic Pro as professional finishing tools through `.fcpxml`/Final Cut Pro XML interchange instead of rebuilding their capabilities.
- Prefer public-domain, permissive, user-owned, or explicitly licensed footage.
- Block unauthorized YouTube download workflows.
- Keep approval gates for spend, rights-risky assets, final render, and publishing.
- Do not include operational weapon, evasion, or targeting instructions in generated warfare/military content.

## Success Criteria

- Core tests pass with `python3 -m unittest discover`.
- The CLI can generate a demo project artifact set.
- The CLI can export `.fcpxml` from project artifacts.
- The CLI can ingest a Google Drive media ledger without storing large originals in git.
- The CLI can build a rough metadata clip index and upgrade it with transcript/scene sidecars when available.
- The project can produce a usable rough-cut timeline from rights-approved assets and cited beats.
- Every source asset carries a rights record.
- Review gates report legal, factual, render, timeline, duplication, and safety risks.
- Final Cut Pro handoff artifacts are generated without requiring paid video APIs.
- The repo remains private until explicitly approved otherwise.

## Current Production Gap Queue

1. Sidecar indexing for transcripts, scene detection, and manual time ranges.
2. Stronger FCPXML handoff with media role metadata and proxy/original path handling.
3. Render readiness checks that summarize what blocks final export.
4. Project-level command that runs the whole local pipeline in order.
5. First real Metallurgical Crucible asset pass from the Drive ledger once rows are marked ready with source URLs, rights status, and Drive paths.
