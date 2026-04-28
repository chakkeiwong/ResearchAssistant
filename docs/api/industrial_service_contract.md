# Industrial Service Contract

## Purpose

This document defines the local service/API contract required before UI,
orchestration, or shared services are implemented.

## Contract Families

- papers;
- artifacts;
- reviews;
- assignments;
- comments;
- derivations;
- experiments;
- traceability;
- parser benchmarks;
- search;
- readiness;
- governance and policies.

## Error Taxonomy

- `blocked`
- `warnings`
- `conflict`
- `unauthorized`
- `not_found`
- `validation_error`

## Trust Boundary

Every response that includes generated or machine-derived content must carry
review status and provenance. Proposal fields must not mutate accepted audit
facts without an explicit human approval workflow.
