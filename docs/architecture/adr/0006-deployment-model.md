# ADR 0006 — Deployment Model

## Status

Proposed

## Context

The platform may eventually need a web UI, API, shared storage, job workers, monitoring, and secure deployment. Deployment choices affect identity, storage, observability, and compliance.

## Decision

Start with local CLI/API contracts and dashboard exports. Add web/server deployment only after storage, identity/RBAC, operations policy, and job orchestration ADRs are accepted.

Local stdio MCP is allowed as an adapter over the same local contracts because
it does not expose a hosted service or shared network endpoint. HTTP MCP,
shared MCP deployment, or server-side MCP operations remain deferred with the
rest of web/server deployment.

## Alternatives Considered

- CLI-only permanently.
- Immediate web app with no backend governance.
- External managed platform first.

## Consequences

This keeps current work deterministic and avoids fake production claims. UI work can begin against stable local contracts before server deployment.

## Required Tests

- API/JSON contract tests.
- UI workflow tests once UI exists.
- Accessibility tests.
- Deployment smoke tests only after server mode exists.

## Usefulness Verification

Reviewers can complete core paper triage and readiness workflows through the UI/API without manual JSON edits.

## Stop Conditions

Do not claim production server readiness without authentication, authorization, monitoring, backup, runbook, and security review.
