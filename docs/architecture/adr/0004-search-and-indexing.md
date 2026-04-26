# ADR 0004 — Search And Indexing

## Status

Proposed

## Context

Industrial research workflows need search across papers, sections, equations, theorems, assumptions, experiments, code links, comments, and citations.

## Decision

Use SQLite FTS for the first local full-text index. Keep semantic/vector search behind a disabled governance gate until provider, privacy, and evaluation policy exists.

## Alternatives Considered

- No dedicated search index.
- External search service immediately.
- Vector search first.

## Consequences

SQLite FTS is deterministic and local. It does not provide frontier semantic search by itself, but it establishes indexing contracts and tests.

## Required Tests

- Golden query tests.
- Ranking regression tests.
- Stale-index tests.
- Graph consistency tests.

## Usefulness Verification

Answer curated research tasks and track top-10 precision.

## Stop Conditions

Do not send text to embedding or external search providers without LLM/provider governance approval.
