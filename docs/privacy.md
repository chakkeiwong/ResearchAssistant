# Privacy

The individual release is offline-first.

Default behavior:
- no default workflow sends papers or notes to external providers;
- live LLM/provider use is disabled;
- provider settings in `.research-assistant/config.json` are inert by default;
- generated artifacts are marked as requiring human review.

Check the current state:

```bash
ra privacy status
ra config show
```

Networked discovery commands and future provider-backed features must remain explicit opt-in workflows. Do not use them for private papers unless the relevant policy has been reviewed.

Release hardening checks such as clean install, demo, backup, restore, parser matrix, platform status, and performance smoke are designed to run without sending papers or notes to external providers.

Before sharing a Git repository or importing another workspace, run:

```bash
ra repository-hygiene check
```

The hygiene check blocks obvious private/raw/generated files and validation
records with forbidden private fields. Workspace merge skips rebuildable reports
and refuses private source artifacts rather than copying them.

Use strict mode before release or before sharing a repository:

```bash
ra repository-hygiene check --strict
```

Strict mode also inspects local build/cache/private roots such as `build/`,
`dist/`, `.codex`, `.claude`, `.pytest_cache`, raw paper directories, backup
archives, and common secret-like fields or provider-key markers.

Validation evidence is shareable only when sanitized. Do not record private
paper titles, private file paths, backup archive paths, credentials, provider
keys, tokens, or raw paper content in `individual-git-release
validation-record`.
