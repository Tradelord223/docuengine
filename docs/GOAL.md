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
- Every source asset carries a rights record.
- Review gates report legal, factual, render, timeline, duplication, and safety risks.
- The repo remains private until explicitly approved otherwise.

