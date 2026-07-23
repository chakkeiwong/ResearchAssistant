# Release Readiness

## Current Decision

`READY_FOR_LINUX_LOCAL_RELEASE_CANDIDATE_REVIEW`

The repository-controlled Python 3.11 release gate is passing. This status does
not authorize a public release, a tag, or a native-Windows or multi-platform
claim.

## Satisfied Locally

- Source-bound eight-command release gate passes.
- Linux local validation records cover platform, parser smoke, merge rehearsal,
  and synthetic workspace performance.
- Complete CPU-only test inventory passes: `1835 passed, 229 skipped` across
  unit, CLI integration, remaining integration, and script partitions.
- Wheel, sdist, and generated artifact manifest are hash-validated locally.
- Disposable workspace install, demo, privacy, and release-report checks pass.
- Offline defaults, credential-free bounded topic metadata scope, arXiv-first
  source intake, and protected output checks
  remain explicit.
- Seed-paper robustness covers abstract/concept evidence, facet/role balance,
  identity conflicts, provider-gap reporting, venue-registry replay, and
  automatic explicit-seed handoff in six raw-provider fixture cases. The live
  transport smoke remains separately authorized and is not a recall gate.

## Remaining Actions

- Successful GitHub Actions run on the final commit, including Ruff and mypy,
  remains an external CI check.
- Release-owner decision is required only before creating a tag or publishing
  artifacts; it does not block local single-user use.
- A non-sensitive real-corpus performance record is needed only if real-corpus
  performance claims are desired; current evidence is synthetic.

## Publication Boundary

Do not create `v0.1.0`, upload artifacts, or publish a release page until the
release owner approves the scope and final generated manifest. Do not turn
synthetic fixtures or parser smoke into scientific extraction-accuracy claims.

## Scientific And Product Nonclaims

This release does not establish scientific correctness, literature completeness,
forward-citation coverage, publication safety, complete PDF extraction quality,
hosted-service readiness, shared database behavior, SSO/RBAC, or native Windows
support.
