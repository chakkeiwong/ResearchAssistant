# External Validation Protocol

## Purpose

The supported release is a Linux/WSL local tool. This protocol records only
sanitized local Linux metadata and command statuses. It is not a protocol for a
hosted service, shared database, SSO/RBAC deployment, or real-time collaboration
platform.

## Required Validation Types

- `linux_local`
- `linux_parser_tools`

## Record Shape

```json
{
  "schema_version": "individual-external-validation-v1",
  "validation_type": "linux_local",
  "platform": "Linux/WSL2",
  "python_version": "3.11.15",
  "install_method": "wheel",
  "optional_parser_tools": ["pdftotext"],
  "result": "passed",
  "command_summary": ["clean install passed", "demo passed"],
  "blockers": [],
  "warnings": []
}
```

## Do Not Record

- private PDFs, TeX source, datasets, notes, paper titles, or screenshots;
- local workspace contents;
- backup archives;
- provider keys, tokens, credentials, cookies, or shell history;
- unsanitized local paths or usernames.

## Validation Commands

Use disposable workspaces and bounded commands:

```bash
env WHEEL_PATH=/path/to/research_assistant-0.1.0-py3-none-any.whl timeout 240 scripts/run_clean_install_smoke.sh
timeout 180 scripts/run_release_smoke.sh
ra platform-status
ra doctor --matrix
ra parser-tool-matrix
ra parser-benchmark-smoke
ra individual-git-release validation-report
ra individual-git-release gate-build
```

Records should be stored under
`local_research/governance/individual_git_release/validation/` and remain local
unless explicitly sanitized for sharing.
