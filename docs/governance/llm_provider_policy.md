# LLM Provider Policy

## Default

Live provider calls are disabled by default. Industrial release must not enable
providers until policy owners approve provider, data class, prompt registry,
audit logging, and budget controls.

## Required Before Live Calls

- approved provider allowlist;
- secret-reference design outside plain workspace JSON;
- data classification check;
- approved prompt template and version;
- cost budget;
- audit log record;
- redaction policy;
- human review of generated output.

## Deterministic Tests

Tests must use dry-run or mocked provider records. No deterministic test may
require network or live credentials.
