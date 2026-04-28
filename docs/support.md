# Support

This support process is for private individual installs. Share diagnostics, not research data.

## Before Asking For Help

Run these commands from a fresh terminal:

```bash
ra version
ra doctor --matrix
ra platform-status
ra privacy status
ra --root /tmp/research-assistant-support-demo demo setup
ra --root /tmp/research-assistant-support-demo demo run
ra --root /tmp/research-assistant-support-demo release-report
```

For install problems, also run:

```bash
python --version
python -m pip --version
```

For parser problems, add:

```bash
ra parser-tool-matrix
ra parser-benchmark-smoke
```

For backup or restore problems, add:

```bash
ra backup inspect --path /path/to/backup.tar.gz
ra --root /tmp/research-assistant-restore-check backup restore --path /path/to/backup.tar.gz
```

For Git-sharing problems, add:

```bash
ra repository-hygiene check --strict
ra workspace merge --source /path/to/other/repo --target /path/to/my/repo
ra workspace rebuild-derived
ra individual-git-release validation-report
ra individual-git-release gate-build
```

## Safe To Share

- command names and exit status;
- `ra version` output;
- `ra platform-status` output;
- `ra doctor --matrix` output after removing private paths if needed;
- `ra release-report` output from a demo or empty workspace;
- `ra backup inspect` status, manifest file count, and issue codes.

## Do Not Share

- private PDFs, TeX source, datasets, notes, or screenshots of paper content;
- `local_research/` contents;
- backup archives;
- `.research-assistant/config.json` if it contains private paths or future provider settings;
- `.codex`, `.claude`, shell history, tokens, credentials, provider keys, or browser cookies;
- colleague feedback that includes private paper titles unless the author explicitly approves sharing them.

## Bug Report Shape

Include:

- operating system and whether this is Linux, WSL, macOS, or native Windows;
- Python version;
- install mode, such as wheel, source checkout, or editable checkout;
- exact command that failed;
- expected result;
- actual status, issue code, or traceback summary;
- whether the demo workflow works in `/tmp/research-assistant-support-demo`;
- whether the issue involves install, parser tools, workspace validation, backup/restore, or performance.
- whether the issue involves Git sharing, repository hygiene, merge/import, validation evidence, or release gating.

Keep examples synthetic whenever possible. If a real paper triggers a failure, report the command shape and issue code first, then arrange a private review path before sharing any content.

## Current Support Boundary

Supported in this release:

- one user, one local workspace;
- offline demo, config, workspace validation, backup, restore, privacy, parser diagnostics, and release-report workflows;
- Linux/WSL-style POSIX shell release scripts on the validated machine.

Not supported in this release:

- shared departmental server deployment;
- shared database, SSO/RBAC, or multi-user collaboration;
- live LLM/provider workflows by default;
- native Windows shell-script workflow;
- parser accuracy certification for arbitrary PDFs.
