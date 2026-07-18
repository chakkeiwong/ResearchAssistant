# M20B4 Final Subplan Review Verdict - Round 5

Date: `2026-07-16`
Reviewer: fresh Codex read-only fallback
Verdict: `REVISE`

Reviewed identities:

- M20B4 subplan SHA-256
  `7c975aa9647170dcb2aadaf4099cd746c473019c514bad0f11bfb76a066932b5`;
- closeout utility SHA-256
  `dad93fcebd68a524b42bc74760bd7e763924ec285b31c8bb701ea156ae3f1242`;
- closeout tests SHA-256
  `597ad861557405e5d31579c969a6d127639861a89dfb34b946bd1282e9e9f513`;
- review bundle SHA-256
  `90093aecf738c35996439b437582fc356818c28521af18bf2edbded61dd42103`;
- unchanged packet SHA-256
  `c3e250b05e2d11ac7c0281aeaa00b467a3b9e7eb90ee1da68d729dfdbfad77ce`.

Claude export remained unavailable after the earlier policy rejection before
invocation and was not routed around. This fallback review granted no live,
credential, provider, cost, source, M21, retry/rerun, push, release, or claim
authority.

## Finding

`supervisor_lifecycle_error` accepts producer-impossible TERM-bearing and
two-KILL histories. The producer assigns that classification only when its
initial `communicate` raises before any TERM action. Its finalizer can then
record at most one cleanup KILL; failed reap changes the classification to
`cleanup_reap_indeterminate`. Therefore only no signal or one KILL is reachable
while the classification remains `supervisor_lifecycle_error`. The current
closeout and tests accept impossible histories, allowing a corrupt manifest to
produce affirmative closed-supervisor process evidence.

The completed-inventory/privacy repair otherwise fails closed. All exact
identities matched, and the credential-free combined matrix passed `100/100`.

## Disposition

The fifth material round did not converge. Do not launch M20B4 or add another
repair/review round without human direction. The exact proposed repair is
limited to giving `supervisor_lifecycle_error` the signal set `{(), (KILL,)}`
and correcting focused positive/adversarial tests. The frozen packet, installed
runtime, worker, supervisor, routes, caps, command, roots, and provider behavior
must remain unchanged.

VERDICT: REVISE
