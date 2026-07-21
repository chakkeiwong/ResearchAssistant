# M19 Terminal Result And M20 Plan Review Verdict Round 1

Date: `2026-07-14`
Reviewer: fresh Codex read-only fallback
Provenance: Claude review gate was policy-rejected before invocation; no
workaround or retry was attempted.
Verdict: `REVISE`

## Material Findings

1. M20 proposed content-derived selected identity/frontier authority without
   retaining the accepted provider body bytes needed for independent parser
   replay. Synthetic fixtures and normalized artifacts cannot carry that
   evidence burden.
2. M20 did not freeze a complete pre-run outcome automaton for version family,
   provider conflicts/outages, malformed/partial responses, cap precedence,
   or multiple raw rows collapsing to one identity.
3. M20 did not define deterministic backward/forward target truncation or
   explicit dispositions for targets and provider remainder beyond cap.

## Repair Applied

- Require capped, per-request, hash-bound accepted public-metadata body files
  and exact offline parser/normalization replay. Headers, credentials,
  exception text, proxy data, and transport diagnostics remain excluded.
- Freeze a canonical JSON outcome automaton into the future approval packet,
  with exact candidate validity, strong-alias/conflict/version rules,
  provider/request precedence, cap precedence, and closed outcomes.
- Use lexical normalized target-ID selection for the first ten targets and
  record duplicates, malformed IDs, every `omitted_by_cap` ID, and one
  `unobserved_provider_remainder` when provider count/cursor metadata proves
  unseen rows.

Focused checks and a fresh rereview are required.

`VERDICT: REVISE`
