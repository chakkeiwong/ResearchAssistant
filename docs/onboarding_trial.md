# Onboarding Trial

Use this checklist with a developer or colleague who did not implement the release.

## Trial Metadata

- Date:
- Platform:
- Python version:
- Install mode:
- Optional tools available:
- Time to demo:
- Release blocker: yes/no

## Commands

```bash
python -m pip install research_assistant-0.1.0-py3-none-any.whl
ra --help
ra version
ra --root /tmp/research-assistant-onboarding init
ra --root /tmp/research-assistant-onboarding doctor
ra --root /tmp/research-assistant-onboarding demo setup
ra --root /tmp/research-assistant-onboarding demo run
ra --root /tmp/research-assistant-onboarding release-report
ra --root /tmp/research-assistant-onboarding repository-hygiene check --strict
ra --root /tmp/research-assistant-onboarding individual-git-release validation-record --validation-type colleague_onboarding --result passed --scope real_external --platform "<platform>" --python-version "<python>" --install-method "<wheel or source>" --command-summary "onboarding checklist completed"
ra --root /tmp/research-assistant-onboarding backup create
ra --root /tmp/research-assistant-onboarding backup inspect --path <backup-path>
ra --root /tmp/research-assistant-restore-check backup restore --path <backup-path>
ra --root /tmp/research-assistant-onboarding privacy status
```

Share only the metadata above and non-private command statuses. Do not share private PDFs, source files, notes, `local_research/`, backup archives, credentials, provider keys, or private paper content. See `docs/support.md`.

## Feedback

- Confusing step:
- Unexpected output:
- Missing documentation:
- Optional parser/tool issue:
- Backup/restore concern:
- Suggested fix:
