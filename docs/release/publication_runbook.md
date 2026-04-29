# Publication Runbook

## Purpose

This runbook defines the steps required before tagging or publishing an
individual local/Git release artifact.

## Build And Verify

```bash
timeout 300 scripts/build_release_artifacts.sh
ra release-artifacts manifest
ra individual-git-release validation-report
ra individual-git-release gate-build
```

## Required Evidence

- clean final release gate;
- artifact manifest with SHA256;
- release notes with matching SHA256;
- version consistency;
- approval from release owner;
- explicit decision for limited pilot, broad individual release, Git-shared
  research release, or no publication.

## Tag Policy

Tags are created only after release-owner approval:

```bash
git tag -a vX.Y.Z -m "Release vX.Y.Z"
git push origin vX.Y.Z
```

Do not create or push tags as part of autonomous validation.

## Artifact Upload

Attach only intended release artifacts and checksum/manifest files. Do not
attach private workspaces, backup archives, logs, local corpora, `.codex`,
`.claude`, credentials, or generated caches.

The current release is not a hosted service, shared database, SSO/RBAC system,
real-time collaboration product, or department platform. Those capabilities are
future extensions and must not be implied by a v0.1 publication.

## Rollback

If a published artifact is found unsafe:

- mark the release page as withdrawn;
- document the blocker;
- publish a fixed artifact under a new version or explicit replacement policy;
- keep the audit trail.
