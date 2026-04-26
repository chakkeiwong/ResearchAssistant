# ADR 0002 — Identity And RBAC

## Status

Proposed

## Context

The platform needs owners, reviewers, stewards, approval gates, and audit history. Production identity requires department policy and possibly SSO integration.

## Decision

Implement a local deterministic RBAC contract first: users, roles, permissions, assignments, comments, and append-only events. Treat SSO and production identity as governed integration.

## Alternatives Considered

- No explicit identity model.
- Direct SSO integration immediately.
- Use only git authorship.

## Consequences

Local RBAC enables deterministic tests and workflow design but must not be represented as production identity.

## Required Tests

- Permission allow/deny tests.
- Append-only event tests.
- Approval authorization tests.
- Conflict and version tests.

## Usefulness Verification

Simulate owner, derivation reviewer, experiment reviewer, and steward workflows without manual JSON edits.

## Stop Conditions

Do not claim production authentication or SSO until department identity policy and deployment model are approved.
