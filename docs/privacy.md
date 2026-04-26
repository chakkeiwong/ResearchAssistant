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
