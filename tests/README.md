# Research Assistant Test Structure

## Layout

- `tests/unit/` — deterministic logic tests, no live network required
- `tests/integration/` — multi-component tests, ideally using local fixtures
- `tests/fixtures/` — saved JSON/XML/TXT examples from real observed cases
- `tests/scripts/` — manual or live validation scripts

## Purpose of each layer

### Unit tests
Use for:
- title normalization
- merge decisions
- schema behavior
- provenance rules
- summary field precedence

### Integration tests
Use for:
- end-to-end metadata merge from multiple fixture sources
- paper record generation
- link workflow with temporary stores

### Fixtures
Fixtures should capture real failure cases we observed in development.
Every important manual failure should become a fixture when possible.

### Scripts
Scripts are for human-in-the-loop validation and live environment checks.
They are not substitutes for deterministic regression tests.

## Current key regression cases

1. NeuTra false-positive Crossref should be quarantined, not merged.
2. DLHMC arXiv-driven ingest should prefer arXiv authors over bad OpenAlex authors.
3. Weak OpenAlex match for local PDF/query should produce low confidence and manual-review notes.

## Future additions

- fixture-based tests for local PDF title extraction
- end-to-end link creation tests
- claim-audit evidence extraction tests once the audit logic improves
- optional live API smoke tests gated behind an environment flag
