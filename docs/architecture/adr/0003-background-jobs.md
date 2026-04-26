# ADR 0003 — Background Jobs

## Status

Proposed

## Context

Parsing, indexing, benchmark, and experiment workflows can run long. Previous unbounded validation caused stale sessions, so bounded execution is mandatory.

## Decision

Start with a local job queue contract with timeout, cancellation, retries, logs, progress, and crash recovery. Consider Redis/Celery/RQ/Arq only after the local contract is tested.

## Alternatives Considered

- Foreground commands only.
- Direct adoption of a distributed worker framework.
- Cron-only scheduling.

## Consequences

A local queue gives safe behavior in tests and single-user deployments. Distributed execution remains a governed integration decision.

## Required Tests

- Timeout tests.
- Cancellation tests.
- Retry tests.
- Log preservation tests.
- Crash recovery tests.

## Usefulness Verification

Run a batch ingest plus benchmark plus index refresh workflow and verify it can be monitored, timed out, and cancelled.

## Stop Conditions

Do not introduce an unbounded background worker or network service without operations policy approval.
