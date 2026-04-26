# ADR 0005 — LLM Provider Policy

## Status

Proposed

## Context

LLMs may help with synthesis, derivation assistance, citation classification, and review triage, but they introduce privacy, hallucination, cost, audit, and provider-risk concerns.

## Decision

Keep live model calls disabled by default. Require provider allowlist, prompt registry, data classification, eval pass, budget policy, and audit logging before any live call.

## Alternatives Considered

- Enable live LLM calls immediately.
- Ban LLM use entirely.
- Allow ad hoc local prompts outside platform governance.

## Consequences

Governed LLM use is slower to enable but safer and auditable.

## Required Tests

- Blocked-by-default tests.
- Provider allowlist tests.
- Prompt registry tests.
- Privacy/data-classification tests.
- Eval regression tests.
- Audit-log redaction tests.

## Usefulness Verification

Run mocked synthesis and derivation-assistance workflows and confirm evidence references, limitations, eval status, and human-review status.

## Stop Conditions

Do not call live providers without approved policy records and passing eval gates.
