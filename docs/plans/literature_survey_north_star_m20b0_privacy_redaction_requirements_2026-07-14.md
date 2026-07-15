# M20B0 Privacy And Redaction Requirements

Date: `2026-07-14`
Status: `PLANNING_REQUIREMENTS_ONLY`

## Secret Lifecycle

- A real key may enter only through the exact human-approved runtime interface.
- Descriptor validation completes before key lookup.
- Key lookup, injection, and dispatch occur in the narrowest possible process
  scope; the persisted descriptor remains unchanged and credential-free.
- The key value is never returned by a helper, serialized, hashed for evidence,
  or included in a request binding.
- Missing, blank, duplicate, malformed, or wrong-source credential state fails
  before network dispatch.

## Enumerated Persistence And Diagnostic Surfaces

M20B2 must use a unique synthetic canary and inspect all declared outputs after
success, provider error, parser error, timeout, worker kill, and manifest-write
failure paths:

- persisted descriptors and route manifests;
- accepted response bodies and body inventories;
- filenames and directory names;
- process arguments and captured stdout/stderr;
- application logs and exception messages;
- request, result, environment, cost, and campaign manifests;
- JUnit and other test artifacts;
- review packets, result notes, and control documents;
- Git status/diff/object candidates within the exact integration payload; and
- temporary files inside the declared test/output roots.

The pass statement is limited to: no canary occurrence was observed across the
enumerated tested surfaces and failure paths. Untested operating-system,
provider-side, proxy, shell-history, process-inspection, crash-dump, swap, and
hardware surfaces remain residual risk unless separately examined.

## Logging And Error Rules

- Never log a constructed authenticated URL, full query string, request object,
  environment mapping, credential source value, headers, cookies, or exception
  representation that may contain them.
- Logs and manifests may use the pre-credential descriptor digest, route kind,
  redacted credential-presence state, response/body digest, and closed error
  code only.
- Redaction happens before formatting or persistence; post-hoc replacement of
  an already written secret is not an acceptable control.
- Any unexpected exception in the credential/dispatch boundary becomes a
  secret-safe closed error and stops further dispatch.

## Cost And Privacy Coupling

Credential use is forbidden unless the same dispatch is covered by the
human-approved cost/credit budget. A request whose cost semantics cannot be
bounded or reconciled uses a closed unknown-cost status and stops subsequent
dispatch. Cost evidence must contain no account, key, billing, or secret value.
