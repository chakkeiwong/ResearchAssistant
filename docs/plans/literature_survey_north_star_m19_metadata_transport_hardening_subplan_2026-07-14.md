# M19 Metadata Transport And Supervisor Hardening Subplan

Date: `2026-07-14`
Status: `LOCAL_IMPLEMENTATION_CHECKS_PASSED_PENDING_IDENTIFIED_COMMIT_AND_FINAL_EVIDENCE_DO_NOT_EXECUTE_LIVE`
Milestone: `M19_bounded_live_metadata_validation`
Subphase: `M19A_transport_supervisor_hardening`

## Phase Objective

Implement and locally validate a closed, no-network metadata transport and
one-shot supervisor for the future M19 OpenAlex/arXiv attempt. The hardening
must make every attempted or denied request visible in a closed ledger and
must distinguish boundary invalidity from ordinary provider unavailability.

M19A is local engineering only. It does not call DNS, OpenAlex, arXiv, a proxy,
or any source/PDF/full-text endpoint. It does not authorize the later M19 live
attempt. It does not establish provider quality, citation recall, claim
support, scientific correctness, or product readiness.

## Entry Conditions Inherited From M18

All entry conditions are satisfied for planning, but implementation remains
blocked until this plan passes material review:

| Authority | Exact value | Status |
| --- | --- | --- |
| M18 code authority | `654e6e1a1213bc03b7693ff1a8aea945a5bf08ac` | Candidate gates passed |
| M18 closeout | `e7f1499e135757c0460c040f3fa317e6bdd56dc9` | Direct docs/evidence-only child |
| M18 payload | `0d225f29575778e606f096fda058cb0386dcd967a82284f5aa37a4c5638bd318` | `1,684/1,684` replay passed |
| M18 closeout replay | `/tmp/ra_m18_closeout_record.json` | Passed, SHA-256 `4de376567d321f3b91956292b2db2bbf3936197b335d5af36be5703971ac0019` |
| M18 terminal review | `docs/reviews/literature_survey_m18_terminal_review_verdict_round3_2026-07-14.md` | Fresh Codex `AGREE` |
| Parent M19 plan | `docs/plans/literature_survey_north_star_m19_bounded_live_metadata_validation_subplan_2026-07-13.md` | Planning only, live forbidden |

The historical M16 Phase 11 plan and three `REVISE` verdicts are design input,
not execution authority. Current repository policy retires its hash-bound
natural-language approval-token ceremony. It does not retire transport,
evidence, compute, write-root, privacy, or live-approval boundaries.

## Threat Model And Proportionality

This is a trusted local academic repository. The relevant risks are accidental
network-scope expansion, implicit proxy/redirect/retry behavior, oversized or
malformed provider responses, incomplete request accounting, partial output,
dirty-worktree drift, and false interpretation of metadata. A hostile
multi-tenant attacker is not the default model.

Ordinary Git commits, exact paths, SHA-256 records, unique output roots,
focused tests, a run manifest, and one material review are sufficient for
local integrity. No approval tokens, inode reservation protocol, custom
cryptographic schema, or review of every procedural artifact is required.

## Research Intent Ledger

| Field | M19A contract |
| --- | --- |
| Main question | Can the exact future four-request metadata attempt be represented and supervised inside closed route, count, byte, time, proxy, redirect, retry, IPC, artifact, and write boundaries? |
| Candidate/mechanism | One internal closed transport primitive, an immutable request-outcome sink, and one parent/worker supervisor with manifest-last output. |
| Expected failure mode | `urllib` follows a redirect/proxy, body reads exceed caps, worker hangs, a request is missing from the ledger, or a boundary defect becomes generic `unavailable`. |
| Promotion criterion | All no-network positive/negative transport and supervisor cases pass and produce exact closed ledgers under the identified hardening commit. |
| Promotion veto | Any real socket/DNS call; implicit redirect/proxy/retry; unbounded read/wait/write; unknown ledger state; outside write; boundary violation represented as provider unavailability. |
| Continuation veto | Wrong M18 authority, overlap with protected user work, invalid test harness, unrepresentable boundary, semantic scope expansion, or five-round material review nonconvergence. |
| Repair trigger | Catching-test failure, schema inconsistency, static network tripwire, write-root escape, worker lifecycle leak, or material `REVISE`. |
| Explanatory only | Test count, runtime, fixture record count, serialized ledger size. |
| Must not be concluded | Live reachability, provider reliability, metadata quality, citation recall, source support, scientific correctness, completeness, product readiness. |

## Evidence Contract

| Field | Contract |
| --- | --- |
| Engineering question | Does the hardening code make the future one-shot metadata boundary executable, closed, testable, and replayable without network access? |
| Baseline | M18 `build.py` public-metadata path, which has host checks and an arXiv body cap but uses default `urlopen`, broad exception-to-`unavailable`, no complete request ledger, and no whole-attempt supervisor. |
| Primary criterion | Exact fake-transport and fake-worker matrices close every request/process/write outcome; no-network regression and affected local suites pass from an identified commit. |
| Hard vetoes | Observed network; wrong parent/hash; missing/duplicate request row; redirect/proxy/retry escape; cap overflow accepted; raw response persisted; partial output promoted; outside write; unbounded wait; protected dirty path changed. |
| Explanatory diagnostics | Fixture rows, wall times, bytes below cap, ledger size, and provider labels. |
| Not concluded | Any live/provider/source/human/scientific/product claim. |
| Preserving artifacts | Plan review, hardening commit, code/test manifest, JUnit/log summaries, run manifest, static audit, decision/red-team result, implementation review, refreshed M19 parent and approval packet. |

## Default And Assumption Audit

| Choice | Provenance | Justification | Failure mode | Early diagnostic | Status |
| --- | --- | --- | --- | --- | --- |
| OpenAlex and arXiv only | M18 CLI and parent M19 | They are the implemented adapters | Hidden third host or inert URL is contacted | Exact fake-opener route matrix | Reviewed baseline |
| Four dispatches | Historical Phase 11 and current collector topology | One seed plus topic query per provider | Loop or retry creates a fifth call | Counter tripwire at dispatch 5 | Hypothesis to freeze |
| `2,000,000` accepted bytes/response | Existing arXiv cap and Phase 11 review | Bounded metadata response | OpenAlex remains unbounded or read-all allocates too much | content-length and streaming cap+1 tests | Reviewed inherited cap |
| `8,000,000` total accepted bytes | Four-request cap | Exact aggregate bound | Per-response passes while aggregate exceeds campaign cap | cumulative counter test | Derived bound |
| `30` seconds/request | M18 constant | Existing compatibility | Sequential calls consume 120 seconds before process cleanup | fake clock plus whole supervisor test | Convenience baseline, bounded |
| `187` seconds whole attempt | Historical Phase 11 | Four sequential 30-second sockets leave 60 seconds for launch/termination and 7 seconds for forced cleanup/bookkeeping | Blocking preflight/IPC/fsync exceeds the same absolute deadline or the bound is too loose | fake clock at every blocking operation and independent watchdog tests | Frozen reviewed default for M19; any revision requires plan rereview before implementation |
| `urllib` custom opener | Current implementation family | Avoids adding dependency | handlers still discover proxies or follow redirects | opener construction and fake handler tests | Required |
| Multiprocessing one-frame IPC | Historical Phase 11 | Parent can enforce whole-attempt termination | truncated/extra frame or child leak | closed frame/EOF/lifecycle matrix | Required hypothesis |

This repair selects `187` seconds as the M19 whole-attempt bound. Material plan
agreement constitutes the required feasibility/proportionality review. The
value is copied into the parent route/cap manifest and future approval packet;
it cannot change after implementation or provider results without a refreshed
plan and approval.

## Exact Edit And Artifact Allowlist

Implementation may edit only:

- `src/research_assistant/survey/build.py`;
- new `scripts/literature_survey_m19_live_metadata_supervisor.py`;
- new `tests/unit/test_literature_survey_m19_transport.py`;
- new `tests/scripts/test_literature_survey_m19_live_metadata_supervisor.py`;
- this subplan and its future result;
- the M19 parent only to insert actual implementation/commit/environment/
  route/cap evidence after hardening passes;
- focused M19 review files under `docs/reviews/`; and
- versioned root `docs/validation/literature_survey_m19_transport_hardening_2026-07-14/`
  under the one canonical grammar defined in **Supervisor Contract**: the five
  named JUnit files, their five named logs, the five matching
  `pytest_tmp/<gate>/**` trees, the exact fake-run tree, and the seven named
  validation manifests/results. No other child is allowed.

Do not edit `src/research_assistant/cli.py`, orchestration, source intake,
frontier/source modules, M18 evidence, protected dirty paths, unrelated tests,
packaging, dependencies, defaults, or documentation outside the named M19
controls. If implementation requires one of those paths, stop and refresh the
plan before touching it.

## Exact Local Transport Contract

The closed internal primitive must:

1. accept only method `GET`, scheme `https`, implicit/explicit port `443`, no
   userinfo, no fragment, and exact host/path/query contracts;
2. permit only:
   - `api.openalex.org`, `/works`, keys `search`, `per-page`, `select`;
   - `export.arxiv.org`, `/api/query`, keys `start`, `max_results`, `sortBy`,
     `sortOrder`, and exactly one of `id_list` or `search_query`;
3. build a no-proxy opener (`ProxyHandler({})`) and a redirect handler that
   rejects `301`, `302`, `303`, `307`, and `308` before following;
4. set the exact `30` second request timeout and perform zero application
   retries;
5. read no more than `2,000,001` bytes, using the extra discarded byte only to
   classify overflow; accept no more than `2,000,000` per response or
   `8,000,000` total;
6. validate final scheme/host/port/path/query equality when a response object
   exists; inert OpenAlex/arXiv identifiers in normalized metadata must never
   be opened;
7. sanitize outcomes to closed class/code enums without raw exception text,
   query values, credentials, headers, or response bodies; and
8. call a private explicit outcome sink exactly once per dispatch. No global
   collector, environment-selected file, implicit hook, or public CLI option.

The primitive must not raise ordinary transport/provider errors; it returns
one validated closed outcome and optional parsed records. Programmer/boundary
invariant failures are `MissionStateError` and cannot be caught by a broad
provider fallback. The existing collector `invoke()` broad catch and
`append_query()` unknown-status-to-`unavailable` normalization must be removed
for this path. The collector validates and sinks the closed request outcome
before projecting it to the existing provider-status schema:

- `available` alone projects provider status `available`;
- timeout, redirect, HTTP, transport, oversized, and malformed-response
  outcomes project the existing provider status `unavailable`; their closed
  non-sensitive reason class/code remains in the separate request ledger and
  is not added to the canonical V2 provider-status schema;
- `blocked_invalid_request`, unknown outcome/status/key/type, sink failure,
  duplicate/missing topology, cap error, and ledger-validation failure raise
  a boundary error and terminate the worker as non-interpretable; and
- no exception raised by outcome validation, sink dispatch, ledger closure, or
  request construction may enter an ordinary `unavailable` branch.

Tests must exercise these rules end-to-end through
`build_survey_evidence_packet()` and `_collect_public_metadata`, not only the
transport primitive.

Exact future query topology remains the Phase 11 four-row order:

1. arXiv seed `arxiv:2201.12220v3`, cap `5`;
2. arXiv topic `Neural Optimal Transport for generative modeling and inference`, cap `10`;
3. OpenAlex seed with the same seed string, cap `5`;
4. OpenAlex topic with the same topic, cap `10`.

Any fifth dispatch is a boundary error. These values are test fixtures and the
proposed future smoke scope; they are not yet live authority.

The future route manifest schema is
`ra-literature-survey-m19-route-manifest-v1`. It has exactly
`schema_version`, `hardening_commit`, `topic`, `seed`, `providers`,
`max_records`, `user_agent`, `routes`, `request_cap`, `byte_caps`,
`timeout_seconds`, `whole_attempt_seconds`, `redirect_cap`, `retry_cap`,
`proxy_policy`, and `forbidden_headers`. `byte_caps` is exactly the object
`{"per_request": 2000000, "total": 8000000}`; `proxy_policy` is exactly
`"disabled_explicit_proxy_handler_and_sanitized_environment"`; and every
route/manifest integer rejects booleans. `routes` is a four-element ordered
array of the exact route rows below.

- `providers` is exactly `['arxiv', 'openalex']`; `max_records` is exactly
  `10`; request cap is `4`; timeout is `30`; whole-attempt is `187`; redirect
  and retry caps are zero.
- `user_agent` is exactly `research-assistant-m19/0.1
  (bounded-metadata-validation)`. `forbidden_headers` is a sorted JSON array of
  strings exactly `['authorization', 'cookie', 'from',
  'proxy-authorization', 'referer', 'x-api-key']`; comparison is
  case-insensitive. The request must not load a client certificate, and no
  email, token, cookie, authorization, referer, API key, proxy credential, or
  other credential is permitted.
- Each of four ordered route rows has exactly `request_index`, `provider`,
  `query_kind`, `method`, `scheme`, `hostname`, `port`, `path`, `query`,
  `headers`, and `request_binding_sha256`.
- `query` is a sorted closed object containing the exact decoded strings from
  the topology: arXiv includes `start='0'`, the appropriate cap,
  `sortBy='relevance'`, `sortOrder='descending'`, and either
  `id_list='2201.12220v3'` or
  `search_query='all:Neural Optimal Transport for generative modeling and inference'`;
  OpenAlex includes the exact seed/topic `search`, cap `5`/`10`, and
  `select='id,display_name,authorships,publication_year,doi,cited_by_count,referenced_works,ids,type,publication_date'`.
- Route-row `headers` means **application-supplied** headers and is a closed
  object exactly `Accept: application/atom+xml` for arXiv or
  `Accept: application/json` for OpenAlex plus the exact `User-Agent` above.
  No other application header is supplied. On Python 3.11, the effective
  origin wire headers are exactly those two plus automatically generated
  `Host: export.arxiv.org` or `Host: api.openalex.org`,
  `Accept-Encoding: identity`, and `Connection: close`, each exactly once.
  Header-name comparison is case-insensitive and values are byte-for-byte
  exact after the standard title-casing performed by `urllib`; no proxy or
  tunnel header is allowed. A fake `HTTPSConnection` catching test records the
  effective wire headers. A different Python/urllib automatic-header behavior
  is an environment veto requiring plan review, not an ignored difference.
- `request_binding_sha256` is the lowercase SHA-256 of canonical JSON over the
  row excluding itself. It binds decoded query values and headers without
  duplicating query values in the runtime ledger.

## Request Ledger Contract

Use schema `ra-literature-survey-m19-request-ledger-v1`. Top-level keys are
exactly `schema_version`, `status`, `scope`, `requests`, `totals`, and
`raw_response_policy`.

`scope` has exactly `hardening_commit`, `route_manifest_sha256`, `topic`,
`seed`, `providers`, `max_records`, `request_cap`,
`accepted_payload_cap_per_request`, `accepted_payload_cap_total`,
`diagnostic_overflow_cap_per_request`, `socket_timeout_seconds`,
`whole_attempt_seconds`, `redirect_cap`, `retry_cap`, and `proxy_policy`.
Strings/arrays/integers equal the frozen route manifest; `route_manifest_sha256`
is lowercase 64-hex and is computed over all canonical
`route_manifest.json` bytes; `accepted_payload_cap_per_request` is `2000000`,
`accepted_payload_cap_total` is `8000000`, and
`diagnostic_overflow_cap_per_request` is `1`; every integer rejects boolean
values.

Each request row has exactly:

`request_index`, `provider`, `query_kind`, `normalized_seed_key`,
`topic_query`, `method`, `scheme`, `requested_hostname`, `requested_port`,
`requested_path`, `query_keys`, `request_binding_sha256`, `final_scheme`,
`final_hostname`, `final_port`, `final_path`, `redirect_count`, `retry_count`,
`configured_timeout_seconds`, `observed_elapsed_seconds`,
`accepted_payload_bytes`, `diagnostic_overflow_bytes`,
`normalized_record_count`, `status`, `sanitized_error_class`,
`sanitized_error_code`, and `raw_response_saved`.

Rows are consecutive `1..N`; provider/query pairs and order equal the route
manifest. `normalized_seed_key` is exactly `arxiv:2201.12220v3` and
`topic_query` is boolean `false` for each seed-resolution row;
`normalized_seed_key` is JSON `null` and `topic_query` is boolean `true` for
each topic-search row. `provider`, `query_kind`, `method`, `scheme`, requested
host/path, and request hash are strings; requested/final ports and all counts
are non-boolean integers; `query_keys` is the sorted unique string array from
the corresponding route; `observed_elapsed_seconds` is a finite nonnegative
JSON number that rejects boolean; and `raw_response_saved` is boolean `false`.
Every route field and request hash equals the corresponding manifest row.

Final URL fields are all JSON `null` for timeout, transport, or request-
validation outcomes because no response object was accepted. They are all
non-null and exactly the approved scheme/host/integer port/path for available,
redirect, HTTP, oversized, and malformed-response outcomes. Partial-null
groups are forbidden. Redirect/retry are integer zero and configured timeout
is integer `30`. `accepted_payload_bytes` is the number retained for parsing,
never exceeds `2,000,000`, and its sum never exceeds `8,000,000`;
`diagnostic_overflow_bytes` is integer zero except exactly one for
`stream_cap_exceeded`; bytes named only by `Content-Length` are not counted as
accepted or diagnostic bytes. `normalized_record_count` is zero unless status
is `available` and never exceeds that route's `5`/`10` cap.

Allowed statuses are `available`, `unavailable_timeout`,
`unavailable_redirect_rejected`, `unavailable_http_error`,
`unavailable_transport_error`, `unavailable_oversized`,
`unavailable_malformed_response`, and `blocked_invalid_request`.

Error classes are exactly `timeout`, `redirect`, `http`, `transport`,
`payload`, `parse`, and `request_validation`. Closed codes are:

- `timeout`: `socket_timeout`;
- `redirect`: `http_301`, `http_302`, `http_303`, `http_307`, `http_308`;
- `http`: `http_400`, `http_401`, `http_403`, `http_404`, `http_429`,
  `http_500`, `http_other`;
- `transport`: `dns_failure`, `tls_failure`, `connection_failure`,
  `other_transport_failure`;
- `payload`: `content_length_cap_exceeded`, `stream_cap_exceeded`;
- `parse`: `malformed_json`, `malformed_xml`; and
- `request_validation`: `invalid_method`, `invalid_scheme`, `invalid_host`,
  `invalid_port`, `invalid_path`, `invalid_query_keys`,
  `request_binding_mismatch`, `userinfo_forbidden`, `fragment_forbidden`,
  `final_url_mismatch`, `dispatch_cap_exceeded`.

Aggregate bytes above `8,000,000` cannot be represented as an ordinary row
outcome: ledger validation fails and top-level status is `invalid_ledger`.

Status/class/code compatibility is exact: `available` uses both error fields
null; `unavailable_timeout` uses `timeout/socket_timeout`;
`unavailable_redirect_rejected` uses `redirect` and the matching listed 30x
code; `unavailable_http_error` uses `http` and one listed HTTP code;
`unavailable_transport_error` uses `transport` and one listed transport code;
`unavailable_oversized` uses `payload` and one listed payload code;
`unavailable_malformed_response` uses `parse/malformed_json` for OpenAlex or
`parse/malformed_xml` for arXiv; and `blocked_invalid_request` uses
`request_validation` and one listed validation code. No other pairing or null
is legal. `blocked_invalid_request` is boundary-invalid and never counts as
provider unavailability.

`totals` has exactly `attempted_request_count`, `available_request_count`,
`unavailable_request_count`, `boundary_invalid_request_count`,
`accepted_payload_bytes`, `diagnostic_overflow_bytes`, `redirect_count`, and
`retry_count`. Every value is a non-boolean nonnegative integer equal to row
sums. Available plus ordinary unavailable plus boundary-invalid equals
attempted; a `complete` ledger requires boundary-invalid zero.
`raw_response_policy` has exactly
`raw_responses_saved: false`, `raw_response_artifact_count: 0`, and
`sanitization: 'closed_codes_no_query_values_headers_or_exception_text'`.

Top-level status is exactly `complete`, `incomplete_worker_terminated`, or
`invalid_ledger`. `complete` requires exactly four valid rows in the frozen
order, attempted count four, boundary-invalid count zero, and no boundary/IPC
veto. `incomplete_worker_terminated` contains only the individually valid,
consecutive prefix of zero to four rows actually present in a valid
`worker_error` envelope; totals are recomputed from that prefix, not trusted
from the worker. `invalid_ledger` contains only the individually valid,
consecutive prefix before the first invalid, missing, duplicate, out-of-order,
or unparseable row; malformed/oversized/noncanonical IPC retains zero rows.
Supervisor-authored totals are exact over the retained prefix. Neither
non-complete status supports boundary validity. A block before creation of the
absent output root creates no ledger. JSON rejects duplicate keys,
NaN/infinity, unknown keys, illegal nulls, booleans as integers, topology
gaps/duplicates, and sum or route-manifest mismatches.

Boundary-invalid states are not ordinary unavailable outcomes. Unknown keys,
wrong types including booleans-as-integers, NaN/infinity, topology gaps or
duplicates, invalid status/class/code combinations, sum mismatches, missing
rows without supervisor termination, cap violations, or final-URL drift make
the ledger invalid and veto live-result promotion.

No raw body is committed. Tests use small sanitized fixtures only.

## Supervisor Contract

The worker envelope schema is
`ra-literature-survey-m19-worker-envelope-v1` with exactly
`schema_version`, `status`, `build_result`, `request_outcomes`, and
`worker_error_code`. `status` is `complete` or `worker_error`.
`request_outcomes` is zero to four exact ledger rows. On `complete`, error code
is null and `build_result` has exactly `schema_version`, `status`, `mode`,
`topic`, `seed_count`, `record_count`, `providers`, `max_records`,
`output_dir`, `artifact_paths`, `workflow_state_path`, `provider_statuses`,
`next_required_actions`, `what_is_not_concluded`, and `reused_existing`. On
`worker_error`, result is null and error code is one of
`boundary_error`, `build_error`, or `serialization_error`; raw exception text
is forbidden.

A complete envelope has exactly four request rows in the frozen route order.
Its result has build schema `ra-survey-build-cli-result-v1`; status is
`metadata_only_packet` or `metadata_resolution_blocked`; mode is
`public-metadata`; topic, seed count `1`, ordered providers, max records `10`,
output directory, and workflow-state path equal the launch scope; record count
is a non-boolean integer `0..10`; `reused_existing` is false; artifact paths
have exactly the 12 `PUBLIC_METADATA_PACKET_FILES` names and their in-root
paths; and both action/nonclaim fields are arrays of nonempty strings. Each of
the four `provider_statuses` has exactly `provider`, `query_kind`,
`normalized_seed_key`, `topic_query`, `query_cap`, `status`, `record_count`,
and `raw_response_saved`. Its route fields and cap equal its request row;
`record_count` equals `normalized_record_count`; raw response is false; and
status is `available` iff the request status is `available`, otherwise
`unavailable`. A boundary-invalid request cannot appear in a complete
envelope. The canonical V2 bundle must replay and its manifest record count
must equal the build-result count. Any disagreement is `invalid_ipc`.

A valid `worker_error` envelope may carry only the individually valid
consecutive request prefix collected before failure. `boundary_error` produces
`invalid_ledger`; `build_error` or `serialization_error` produces
`incomplete_worker_terminated`; all three veto a passing summary even when the
prefix happens to contain four ordinary rows. Invalid framing/envelope JSON
retains zero rows. No worker-supplied totals or top-level ledger status is
accepted; the parent derives both from validated rows and parent state.

The supervisor must:

- run the build in one child process under `CUDA_VISIBLE_DEVICES=-1` and a
  sanitized environment without proxy variables or `PYTHONPATH`;
- use one bounded one-way canonical JSON frame, at most `1,000,000` bytes,
  sent with one `send_bytes()` then sender close/EOF; the parent closes its
  inherited send end before polling, polls at most `min(remaining, 0.25)`,
  performs no unbounded receive, validates the full envelope before writing,
  then requires EOF and rejects extra/truncated/duplicate-key/nonfinite data;
- drain worker stdout/stderr concurrently through parent-owned nonblocking
  pipes without retaining content; any worker output is an unexpected-output
  veto, and more than `65,536` observed bytes on either stream is an immediate
  overflow veto and worker-group `SIGTERM` trigger;
- start the worker in its own session/process group, retain exact PID/PGID,
  send group `SIGTERM` at entry+`180`, group `SIGKILL` at entry+`185`, reap it
  before normal exit, and classify timeout/termination from parent state rather
  than ambiguous return codes;
- write only below a predeclared absent mission-local root, reject symlink or
  nonregular ancestors/targets, and publish the summary last;
- preserve a complete closed request ledger even for provider-unavailable
  rows; partial/invalid IPC or supervisor termination cannot support boundary
  validity; and
- never rerun automatically.

`time.monotonic()` is read as the first instruction in `main()`, before
preflight. Absolute deadlines are entry+`180` for soft worker termination,
entry+`185` for hard kill and end of ordinary work, entry+`186.5` for final
watchdog `SIGTERM`, and entry+`187` for final watchdog `SIGKILL`. Preflight,
worker startup, worker `send_bytes`, pipe poll/receive/EOF, subprocess status,
stream capture, fsync, inventory, atomic publication, join, and bookkeeping all
use the same remaining absolute budget; a step that cannot be given a native
timeout is bounded by the watchdog and cannot yield a passing summary after
entry+`185`.

Before the first potentially blocking preflight operation, the supervisor
starts a minimal independent watchdog process and records its PID. The
watchdog calls `setsid()` so it cannot signal itself. A fixed shared structure
contains only supervisor PID, nullable worker PID/PGID, the four frozen
deadlines, and a normal-finish event. At entry+`186.5` it sends `SIGTERM` to a
live worker group and then the supervisor PID; at entry+`187` it sends
`SIGKILL` to either still-live target, treating `ESRCH` as already exited. It
does no filesystem or network work. The supervisor sets normal-finish only
after the worker is reaped and all passing artifacts are durably published,
then joins the watchdog with the remaining budget. If the supervisor blocks in
preflight, startup, receive/EOF, fsync, inventory, publication, or cleanup, the
watchdog therefore enforces process exit by `187` seconds. Fake-clock/process
tests freeze all four instants, a worker blocked in `send_bytes`, a parent
blocked in each named operation, watchdog normal cleanup, group cleanup, and
the absolute cutoff.

The hardening supervisor writes only an exact absent output root with:

- `logs/stdout.json`, `logs/stderr.log`, `logs/command_exit.json`;
- `route_manifest.json`, `request_ledger.json`, `environment_manifest.json`,
  `root_inventory.json`; and
- `hardening_summary.json` last, only for a locally validated fake-transport
  run. No live summary is created in M19A.

The fake-run root is exact when passing: `public_metadata/` contains the 12
canonical V2 children; `logs/` contains only the three named log artifacts;
and the root contains only `public_metadata/`, `logs/`, route manifest, request
ledger, environment manifest, root inventory, and summary. The route manifest
is the canonical JSON representation of the exact schema above and is
published before worker start. A failed run may contain a strict subset plus
one permitted sibling temporary; it is retained as invalid residue and has no
summary.

Before worker start, the parent creates separate stdout/stderr pipes, passes
only each write descriptor to the worker, closes its inherited write copies,
and registers both read descriptors with a selector in nonblocking mode. Every
supervisor loop drains ready descriptors in chunks no larger than `65,536`,
updates a streaming SHA-256 and non-boolean integer observed-byte count, and
immediately discards the bytes. It never buffers content. At the 65,537th byte
on either stream the parent records overflow and sends the worker group
`SIGTERM` immediately; it continues nonblocking draining through EOF, the
entry+`185` hard-kill point, or the absolute cutoff. Descriptors are closed on
all paths. An inherited descriptor preventing EOF is incomplete/timeout, never
a pass. This design bounds memory while the process-group/watchdog deadlines
bound an infinite writer or blocked drain.

`logs/stdout.json` uses schema `ra-literature-survey-m19-stdout-v1` and has
exactly `schema_version`, `status`, `observed_byte_count`, `capture_cap_bytes`,
`overflowed`, `stream_complete`, `sha256`, `digest_scope`, and `content_saved`.
Status is `empty`, `unexpected_output`, or `overflow`; observed count is a
non-boolean nonnegative integer; cap is integer `65536`; the two flags are
booleans; SHA-256 is the lowercase streaming digest of exactly every byte
observed before EOF or cutoff; digest scope is exactly
`observed_bytes_until_eof_or_absolute_cutoff`; and content saved is false.
`empty` requires count zero, no overflow, complete EOF, and the standard empty
digest. `unexpected_output` requires count `1..65536`, no overflow, and may be
incomplete only when another termination classification fired. `overflow`
requires count at least `65537` and overflow true. A completed stream means EOF
was observed; overflow may still be complete after draining.

`logs/stderr.log` is UTF-8 and exactly one sanitized line with fields in this
order:
`status=(empty|unexpected_output|overflow) observed_bytes=[0-9]+
capture_cap_bytes=65536 overflowed=(true|false)
stream_complete=(true|false) sha256=[0-9a-f]{64}
digest_scope=observed_bytes_until_eof_or_absolute_cutoff
content_saved=false\n`. Its values obey the same schema and compatibility.
Neither artifact contains worker content or raw exception text. Catching tests
cover zero, one, exactly `65,536`, `65,537`, and sustained-output cases,
immediate termination, complete and cutoff-prefix hashes/counts, missing EOF,
memory-bounded streaming, and descriptor closure.

`logs/command_exit.json` uses schema
`ra-literature-survey-m19-command-exit-v1` and has exact keys
`schema_version`, `status`,
`worker_started`, `worker_pid`, `worker_pgid`,
`soft_termination_initiated`, `hard_kill_initiated`, `signals_sent`,
`worker_exit_code`, `total_wall_time_seconds`, and
`normalized_exit_classification`. Status is `complete` only for classification
`completed`, otherwise `incomplete`. Booleans are exact. PID/PGID are positive
non-boolean integers iff the worker started, otherwise both null. Exit code is
a non-boolean integer when reaped and otherwise null. Signals are an ordered
unique array drawn only from `SIGTERM`, `SIGKILL`; soft/hard flags equal
presence of their signal. Wall time is a finite nonnegative number no greater
than `187`. Classification is `completed`, `worker_error`,
`worker_start_failed`, `supervisor_soft_timeout`, `supervisor_hard_kill`, or
`invalid_ipc`, or `unexpected_worker_output`. `completed` requires a complete
valid envelope, exit zero, no signal, empty output, and reaped worker; soft
timeout requires SIGTERM but no SIGKILL; hard kill requires both; worker start
failure requires no worker/PID/signal/exit; unexpected output requires at least
one nonempty capped stream summary; all other cross-field combinations are
rejected. A pre-root preflight block creates no output root or command-exit
artifact.

`environment_manifest.json` uses schema
`ra-literature-survey-m19-environment-v1` and has exactly `schema_version`,
`python_version`, `os`, `git_commit`, `git_branch`, `conda_environment`,
`cuda_visible_devices`, `python_dont_write_bytecode`, `git_optional_locks`,
`python_pycacheprefix_present`, `pythonpath_present`,
`proxy_variables_present`, and `credential_variables_present`. Version, OS,
branch are nonempty strings; commit is lowercase 40-hex; conda environment is
nonempty string or null; CUDA is `-1`; `python_dont_write_bytecode` is `1`,
`git_optional_locks` is `0`; and all four presence booleans are false. It is an allowlisted projection
and never stores the full environment, credentials, or removed values.

`root_inventory.json` uses schema
`ra-literature-survey-m19-root-inventory-v1` and has exactly `schema_version`,
`hash_scope`, `artifact_count`, `tree_sha256`, and `artifacts`. Hash scope is
`all_regular_files_before_inventory_excluding_inventory_and_summary`;
artifact count is a non-boolean integer equal to list length; tree hash is the
lowercase digest of canonical JSON over `artifacts`; and rows are sorted unique
objects with exactly `path`, `kind`, `size_bytes`, and `sha256`. Paths are
relative, normalized, in-root strings; kind is `regular_file`; sizes are
non-boolean nonnegative integers; hashes are lowercase SHA-256. The scope is
every regular file present before inventory publication except inventory and
later summary. A symlink, directory outside the two named directories, unknown
kind, missing file, duplicate/path drift, or hash mismatch is invalid.

`hardening_summary.json` uses schema
`ra-literature-survey-m19-hardening-summary-v1` and has exactly
`schema_version`, `status`, `boundary_valid`, `hardening_commit`,
`route_manifest_sha256`, `request_ledger_sha256`, `command_exit_sha256`,
`environment_manifest_sha256`, `root_inventory_sha256`,
`public_metadata_manifest_sha256`, and `what_is_not_concluded`. Status is
`passed`; boundary valid is true; commit and every digest are lowercase exact
hex; each digest matches the named artifact; and the nonclaim value is exactly
the sorted unique array `['live provider behavior', 'metadata quality',
'north-star completion', 'product readiness', 'scientific correctness',
'source support']`. No failed/incomplete run may publish this file.

Atomic publication may create only
`.<final-name>.<ASCII-alnum_-random>.tmp` beside one named final file, with
exclusive regular-file creation, flush/fsync, atomic replace, and directory
fsync. Any surviving temp, unknown file/kind, partial canonical child, or
outside write is retained as invalid residue and forbids summary/promotion;
the supervisor never cleans and retries.

The validation root is exactly
`docs/validation/literature_survey_m19_transport_hardening_2026-07-14/`. Its
only paths are the five exact JUnit files `junit/<gate>.xml`, five logs
`logs/<gate>.log`, and five basetemp trees `pytest_tmp/<gate>/**`, where gate is
one of `transport`, `supervisor`, `affected_phase7`, `cumulative_m16_m17`, or
`full_cli`; exact fake-run root `fake_run/` as defined above; and root files
`run_manifest.json`, `code_test_manifest.json`, `static_audit.json`,
`decision_table.json`, `inference_status.json`, `post_run_red_team.json`, and
`result_hashes.json`. No generic `logs/*.log`, other basetemp, cache, bytecode,
or unlisted path is allowed. The overall final validation root is absent once
before the ordered five-gate sequence; it is then append-only under the exact
grammar. Before each gate, that gate's one JUnit target, one log target, and
`pytest_tmp/<gate>/` subtree must individually be absent, while earlier gate
artifacts remain immutable. A failed local repair may use a distinct
disposable `/tmp/ra_m19_transport_repair_<round>/` root, which is not evidence
and must not be copied into the final validation root. Every pytest command
uses its matching fresh basetemp and disables cache/bytecode. Any preexisting
gate target, mutation of an earlier gate artifact, or unlisted path vetoes the
final evidence set; it is never deleted and retried in place.

## Required No-Network Catching Tests

The tests must fail on any real socket/DNS attempt and cover at least:

- all four exact request constructions and a fifth-dispatch rejection;
- exact one seed, provider order `arxiv,openalex`, `max_records=10`, route
  manifest/request hash/header binding, and rejection of any changed value;
- tripwires that `_resolve_openalex_seed_metadata`, `_openalex_cited_by`, and
  any other inactive/fallback transport helper are never called;
- wrong method/scheme/host/port/path/query, userinfo, fragment, final URL drift;
- proxy variables set in every supported case while the fake no-proxy opener
  remains direct;
- every redirect code, zero-follow behavior, and later planned dispatch;
- content-length and streaming exact-cap/cap+1 cases plus aggregate byte cap;
- timeout, DNS, TLS, connection, closed HTTP, malformed JSON/XML, and unknown
  exception sanitization;
- no raw body/exception/query-value persistence;
- exact status/class/code compatibility, nonfinite/bool/unknown-key rejection,
  topology/sum closure;
- collector/build-path tests proving boundary/sink/ledger exceptions never
  collapse into provider `unavailable`;
- one valid worker frame, truncated/oversized/duplicate/extra/missing-EOF
  frames, worker error, stdout/stderr exact-cap/overflow/sustained-output,
  soft timeout, kill grace, process-group cleanup;
- absent/existing/symlink/nonregular/outside output roots, mid-write failure,
  manifest-last durability, and no outside writes; and
- unchanged existing public-metadata fixture behavior when no outcome sink is
  supplied.

## Required Checks And Reviews

After plan agreement and implementation:

1. compile only the touched Python files with `CUDA_VISIBLE_DEVICES=-1`;
2. run exact new transport and supervisor tests in a fresh validation root;
3. unconditionally run all `tests/unit/test_literature_survey_m16_phase7.py`
   into `junit/affected_phase7.xml`;
4. unconditionally run the exact ten-path M16/M17 cumulative suite from M18
   into `junit/cumulative_m16_m17.xml` and full
   `tests/integration/test_cli_commands.py` into `junit/full_cli.xml`;
5. run static no-network tripwires, JSON/JUnit parse, diff hygiene, exact
   allowlist, protected-path hash, package import, and write-root audits;
6. create an identified local hardening commit as a direct child of M18
   closeout, excluding protected/unrelated work;
7. validate it from an isolated clone and offline wheel with no network;
8. write the M19A result, decision table, inference status, run manifest, and
   post-run red team; and
9. obtain one terminal read-only implementation/result review.

All Python/test commands set `CUDA_VISIBLE_DEVICES=-1`; deliberate no-network
tests must monkeypatch or otherwise tripwire sockets before imports that could
initialize network clients. No GPU probe is needed or permitted.

## Repair Loop

For a fixable plan or local implementation finding, patch visibly within the
allowlist, rerun the smallest catching test and affected regression, then
rereview only if the issue is material. Local harness/serialization repairs
may continue under the unchanged contract and budget. Preserve failed local
attempts only in fresh disposable `/tmp/ra_m19_transport_repair_<round>/`
roots; never overwrite or append to the final validation root or pass evidence.

Stop after five review rounds on the same material blocker. A reviewer is
advisory and cannot authorize live access, source retrieval, human decisions,
scientific claims, defaults, release, or funding.

## Required Artifacts

- Reviewed M19A subplan and plan verdict.
- Identified hardening commit and exact code/test manifest.
- No-network JUnit/log/static evidence.
- M19A result with decision table, inference status, run manifest, and red
  team.
- Terminal implementation/result verdict.
- Refreshed M19 parent with actual hashes and observed environment.
- Compact exact live approval packet naming the one command, commit, topic,
  seed, routes, query values, caps, absent output root, and no-rerun rule.

## Forbidden Claims And Actions

- `DO_NOT_EXECUTE_LIVE`: no DNS, socket, OpenAlex, arXiv, proxy, source,
  PDF/full-text, citation-frontier, credential, private/paid, model-worker, or
  GPU action.
- Do not treat the product's persisted public-discovery confirmation as
  authorization for this development validation run.
- Do not use the old Phase 11 plan or old approvals as live authority.
- Do not hide boundary violations as provider `unavailable`.
- Do not change provider results, route/cap criteria, or failure classes after
  observing live output.
- Do not mutate protected/unrelated work, push, release, amend, reset, restore,
  clean, stash, rebase, or use wildcard staging.
- Do not claim live behavior, source support, completeness, ranking,
  scientific correctness, product readiness, or north-star completion.

## Exact Next-Phase Handoff Conditions

M19 may request fresh exact live approval only when:

1. this plan and local implementation/result reviews agree;
2. the identified hardening commit passes all no-network/isolated checks;
3. the parent M19 plan is refreshed with actual commit/code/test/manifest
   hashes, exact route/query/cap values, environment, command, absent output
   root, and one-attempt budget;
4. the approval packet is complete and reviewed; and
5. current controls still say `DO_NOT_EXECUTE_LIVE` until the user approves
   that exact frozen packet.

No M20/source/citation/product authority is handed off by M19A.

## Stop Conditions

Stop with a blocker result if the M18 lineage is wrong, protected overlap
cannot be preserved, a closed boundary cannot be represented, no-network
tests reveal an uncontrollable real network path, implementation needs a
material scope/default/dependency change, evidence is corrupt, the local
campaign budget is exhausted, or five material review rounds do not converge.

Do not stop for a fixable fake-opener, ledger, IPC, serialization, output-root,
or harness failure inside the unchanged local hardening contract.

## Skeptical Plan Audit

Pre-review audit result: `PASS`; material read-only plan review converged
`AGREE` at round 4 on `2026-07-14`.

- Baseline: corrected from dirty-tree M16/Phase 11 to the exact M18
  candidate/closeout lineage.
- Proxy discipline: provider availability and record counts are not promotion
  criteria; boundary closure is primary.
- Stop logic: provider unavailable is not a continuation veto; invalid
  boundary/harness/artifact is.
- Fairness: no provider ranking or stochastic comparison occurs.
- Hidden assumptions: `urllib`, four dispatches, 2 MB, 30 seconds, and 187
  seconds are explicitly hypotheses/defaults with catching tests.
- Environment: inherited WSL/Python 3.11/system-site-package limits are
  recorded; a future live attempt must name its actual environment.
- Artifact fitness: the plan requires exact ledgers, process/write closure,
  identified commit, and isolated no-network evidence before live approval.
- Governance: retired approval-token ceremony is removed while the actual
  network boundary remains human-gated.

The round-2 and round-3 repairs close the known local audit findings. Round-4
focused review found no material regression. Implementation may proceed only
inside the exact allowlist and with `DO_NOT_EXECUTE_LIVE` unchanged.

## End-Of-Subphase Sequence

Run local checks; write the M19A result/close record; refresh the M19 parent and
exact live approval packet; review them for consistency, correctness,
feasibility, artifact coverage, inherited conditions, and boundary safety;
then request fresh exact live approval. If approval is absent, stop with
`DO_NOT_EXECUTE_LIVE`, not a false program blocker.
