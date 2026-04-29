# External Validation Record Template

Use this template only for sanitized evidence from a real target environment.
Do not include private papers, private paths, screenshots of research content,
workspace archives, backup archives, credentials, tokens, cookies, or shell
history.

## Metadata

- Date:
- Validation type:
  - `colleague_onboarding`
  - `macos`
  - `minimal_parser_tools`
  - other:
- Scope:
  - `real_external`
  - `external_machine`
- Platform:
- Python version:
- Install method:
- Optional parser tools available:

## Commands

- Clean install smoke:
- Release smoke:
- Parser diagnostics:
- Demo workflow:
- Gate/report command:

## Result

- Result:
  - `passed`
  - `warnings`
  - `blocked`
- Sanitized command summary:
- Warnings:
- Blockers:

## Privacy Review

- Confirm no private papers included:
- Confirm no private paths/usernames included:
- Confirm no credentials/tokens included:
- Confirm no backup archives included:

## Recording Command

```bash
ra --root <validation-root> individual-git-release validation-record \
  --validation-type <type> \
  --result <passed|warnings|blocked> \
  --scope <real_external|external_machine> \
  --platform "<platform>" \
  --python-version "<python>" \
  --install-method "<wheel or source>" \
  --command-summary "<sanitized command summary>" \
  --evidence-note "<sanitized note>"
```
