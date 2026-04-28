# Scalability Validation Protocol

## Purpose

Industrial release claims require measured corpus sizes and performance limits.
Synthetic performance is useful, but real or sanitized corpus evidence is
required before broad release.

## Corpus Tiers

- `synthetic_1000`
- `synthetic_10000`
- `sanitized_real_small`
- `sanitized_real_medium`
- `department_large_optional`

## Metrics

- validation time;
- artifact index time;
- search/index time;
- export time;
- backup time;
- restore dry-run time;
- backup size;
- warnings and blockers.

## Privacy

Do not commit or share private corpus contents, titles, file paths, backup
archives, or logs. Record only aggregate metrics.

## Acceptance

Industrial release notes must state the largest measured corpus tier and any
known limitations. If only synthetic evidence exists, say so.
