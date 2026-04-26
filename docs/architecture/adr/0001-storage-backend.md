# ADR 0001 — Storage Backend

## Status

Proposed

## Context

The current platform stores research artifacts as local JSON. That is excellent for transparency and offline work, but it is not sufficient for transactional multi-user workflows, migrations, indexing, backups, and concurrent writes.

## Decision

Keep local JSON compatibility and introduce a repository abstraction. The first governed storage backend should be SQLite because it is local-first, deterministic in tests, transactional, and does not require a server dependency. A later service database can be considered after the SQLite repository proves the contract.

## Alternatives Considered

- Continue local JSON only.
- Move directly to PostgreSQL.
- Use a document database.

## Consequences

SQLite adds migrations, schema tables, backup/restore, query performance, and transactional writes while keeping deployment lightweight. It does not solve distributed multi-user deployment by itself.

## Required Tests

- Repository contract tests over JSON and SQLite backends.
- Migration and rollback tests.
- Corrupt-record recovery tests.
- Concurrent write conflict tests.
- Backup/restore round-trip tests.

## Usefulness Verification

Load a synthetic corpus of at least 1,000 papers/artifacts and measure query latency and migration reliability.

## Stop Conditions

Do not remove JSON compatibility. Do not run destructive migrations without backup/restore and validation reports.
