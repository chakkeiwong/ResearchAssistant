# M17 Idea And Topic Bootstrap Subplan

Date: `2026-07-13`
Status: `EXECUTABLE_AFTER_PROGRAM_SETUP_AGREE_LOCAL_ONLY`
Milestone: `M17_idea_topic_bootstrap`
Closes: `G0_idea_topic_bootstrap`

## Phase Objective

Make the north-star command honestly accept an idea or topic with no initial
paper seed, while preserving the exact M16 explicit-seed behavior, immutable
mission identity, one persisted public-discovery confirmation, fail-closed
lineage, and honest bootstrap outcomes.

This phase establishes local engineering semantics with deterministic fixtures.
It does not establish production provider quality or run a live bootstrap.

## Claimed Target And Current Quantity

| Item | Value |
| --- | --- |
| Claimed target | `ra survey run-public-source-workflow --topic <idea-or-topic> --out <mission-dir>` creates a stable topic-input mission and, only after persisted confirmation, consumes an explicit bootstrap capability outcome without inventing a paper identity. |
| Quantity currently computed | The CLI requires `--seed`; `normalize_seeds` and persisted V2 validators reject an empty seed set; orchestration assumes normalized seeds when constructing public metadata actions. |
| Verdict | `wrong relative to the stated idea/topic interface`; correct for the existing explicit-seed-only M16 interface. |
| Source anchors | `src/research_assistant/cli.py`, `src/research_assistant/survey/mission_state.py`, `src/research_assistant/survey/orchestrate.py`, and `docs/plans/literature_survey_automation_milestones.json`. |
| Remains unproved | Live topic discovery quality, candidate relevance or importance, citation completeness, source availability, human review, clean-install reproducibility, and product readiness. |

## Entry Conditions Inherited From M16

All conditions must hold before the first M17 product edit:

1. The M16 close status remains
   `PASSED_LOCAL_ENGINEERING_GIT_INTEGRATION_PENDING`.
2. The following exact hashes match:
   - Phase 10 result:
     `5280cc6d3459fabb8bbba727f088a075be86253c6eb873be6ec4a16aee3ebded`;
   - Phase 10 change manifest:
     `23246fcb259140aefeb8bd4f3df865a8279ac6ea69bbebf0ee1c964b759bcd28`;
   - round-5 bundle:
     `a4a1749a2c4611dc3113d50c90f6504ac78e13c3ab59e93636963f0d539d0960`;
   - round-5 verdict:
     `87eb6e208d031d9606f533e859ce73b84a66e0ec564ba9648ab5c6242c67a875`.
3. The Phase 10 direct manifest replays, and the `1,137`-row transitive
   inventory re-enumerates exactly inside its declared scope: every regular
   file and symlink below the frozen Phase 10 `positive/**` and `negative/**`
   roots plus `e2e_static_audit.json`. Newly created repository planning files
   are outside that inventory and are not "extra" rows.
4. Every preexisting initial M17 product/test edit candidate resolves to its
   latest accepted direct hash row in the M16 Phase 1-9 change manifests. The
   current byte hash must equal that latest row before snapshot creation. The
   resolution table records all candidate rows, source-manifest hashes, phase
   order, selected latest row, current hash, and zero ambiguity/mismatch.
   A passed test or Phase 10 validation-tree inventory is not substituted for a
   missing direct product-file hash. The nine source manifests must first match
   the literal hashes in `Frozen Historical Source Manifests` below; an
   unlisted or mismatched manifest cannot define
   `m16_latest_direct_hash_bound` authority.
5. Program setup records `PROGRAM_SETUP_PASSED_M17_READY_NOT_STARTED` and its
   independent read-only review ends `VERDICT: AGREE`.
6. No Git mutation, network/provider action, source/PDF/full-text action,
   credential use, package install, model-worker action, or GPU use is needed
   or authorized.
7. The M17 validation root and pre-edit snapshot root do not exist. Existing
   unexpected paths are a collision, not reusable evidence.
8. The exact product/test edit allowlist below has been compared with current
   dirty work. Any unexplained overlapping change stops execution before edit.

## Skeptical Plan Audit

Run and append the audit to the visible ledger before implementation:

- Baseline is M16 explicit-seed local behavior, not a clean commit or live
  provider.
- A fixture-selected candidate is a local contract check, not evidence of live
  retrieval quality, relevance, importance, or completeness.
- The topic string must not be passed to an existing title/identifier seed path
  merely to make tests pass.
- Bootstrap selection must not retroactively alter the mission fingerprint or
  genesis input.
- Confirmation must be durably selected before the capability can run, so a
  crash cannot leave unrecorded public authority.
- Empty, ambiguous, unavailable, capped, corrupt, and stale outcomes are
  first-class evidence, not exceptions collapsed into a generic success or
  silently retried.
- Existing V2 explicit-seed bytes and fixed vectors must remain valid; a schema
  migration is not allowed to rewrite historical authority.
- M17 artifacts must answer identity, authority, resume, and regression
  questions. Counts, scores, or latency are explanatory only.
- The M17 successor manifest, not the old M16 current-path hashes, governs
  intentionally changed current files. Old bytes remain provable in the
  historical snapshot with per-path provenance. Do not call an entry-cutoff
  hash "M16 hash-bound" when no accepted M16 direct row exists.

A material failure of this audit requires plan repair and review before code.

## Research Intent Ledger

| Field | M17 contract |
| --- | --- |
| Main question | Can the local state machine represent an idea/topic start without a fabricated seed and safely turn a confirmed bootstrap outcome into downstream seed authority? |
| Candidate/mechanism | A topic-input mission schema plus immutable, mission-bound bootstrap attempt sets and a closed injectable bootstrap capability. |
| Expected failure mode | Selected candidates leak into original identity, capability runs before confirmation, or downstream code accepts stale/ambiguous authority. |
| Promotion criterion | Exact local input-mode, confirmation, outcome, lineage, crash/replay, and explicit-seed regression predicates all pass. |
| Promotion veto | Fabricated seed identity; changed M16 V2 behavior; pre-confirmation call; false readiness; stale/foreign/corrupt authority accepted; old evidence mutated. |
| Continuation veto | Invalid M16 entry snapshot, unexplained overlapping user work, unrepresentable identity without V2 regression, corrupt harness, or five-round review nonconvergence. |
| Repair trigger | Catching-test failure, schema mismatch, crash orphan, stale-lineage acceptance, unclear terminal, or independent `REVISE`. |
| Explanatory only | Candidate counts, fixture labels, execution time, artifact size, and any relevance/ranking value. |
| Must not be concluded | Live quality, completeness, scientific importance, clean-install reproducibility, genuine review, product readiness, or mission completion. |

## Evidence Contract

| Field | Contract |
| --- | --- |
| Engineering question | Can a user genuinely start the one-command workflow from an idea/topic without an initial paper identity while retaining exact authority and M16 compatibility? |
| Baseline/comparator | Unchanged M16 explicit-seed V2 behavior and its frozen local matrix. |
| Primary pass criterion | Deterministic topic-input missions reach exact selected or honest boundary outcomes after confirmation, replay with stable identity and bootstrap authority, and all explicit-seed gates remain unchanged. |
| Hard vetoes | Topic treated as paper seed; mission fingerprint changes after selection; pre-confirmation capability call; ambiguous/empty/unavailable/capped result disappears; stale/foreign/corrupt authority accepted; M16 V2 fixed vector or resume regression; network/Git/outside-write tripwire. |
| Explanatory diagnostics | Candidate count, ordering, fixture relevance fields, runtime, artifact bytes, and log volume. |
| Not concluded | Production discovery quality, paper relevance/truth, literature completeness, source support, scientific correctness, human review, clean checkout, product/release readiness. |
| Preserving artifacts | Pre-edit historical snapshot, M17 fixtures and test logs, bootstrap attempt artifacts, run manifest, decision table, post-run red team, result, review trail, and cumulative successor manifest. |

## Input-Mode And Mission-Identity Contract

### Existing Explicit-Seed Missions

1. An invocation with one or more `--seed` values remains the implicit
   `explicit_seed` input mode.
2. New and resumed explicit-seed missions continue using the exact M16 V2
   contract, fingerprint, genesis, generation, migration, normalization, and
   fixed-vector semantics. Do not add fields to persisted V2 bytes.
3. Existing V1-to-V2 explicit-seed migration remains unchanged. There is no
   automatic V2-to-topic migration.
4. Supplying selected bootstrap candidates as `--seed` when resuming a
   topic-input mission is an input-mode/identity mismatch, not a shortcut.

### New Idea/Topic Missions

1. CLI `--seed` changes from required to optional with an omitted default of
   `None`. Omission selects the explicit input mode
   `idea_or_topic_without_initial_paper_seed` and passes `seeds=[]` plus that
   mode to mission state. Supplying `--seed ""` produces a nonempty raw seed
   list whose normalization fails; it must not be reinterpreted as omission.
   Programmatic callers with an empty list must also pass the topic input mode
   explicitly, so an accidental empty list is never silently upgraded.
2. Only this mode permits an empty `normalized_initial_seeds` list. The topic
   remains nonempty after NFKC normalization, whitespace folding, and casefold
   key derivation.
3. A versioned topic-input mission contract and fingerprint must bind:
   - schema version;
   - input mode;
   - normalized topic display/key;
   - the exact empty initial-seed list;
   - immutable discovery budget including resolved mission write root; and
   - existing mission ID/genesis/generation authority.
4. The mission fingerprint is computed before bootstrap and never includes a
   selected candidate, provider result, score, rank, title, DOI, or paper ID.
5. Bootstrap-selected paper identities are downstream derived authority. They
   are never copied into `normalized_initial_seeds`, never rewrite GENESIS, and
   never change the mission ID or fingerprint.
6. Common read APIs may expose `input_mode`, `initial_seeds`, and
   `effective_seed_authority`, but must preserve the original V2 persisted
   contract byte-for-byte for explicit-seed missions.

### Exact Sibling Schema And Dispatch Contract

M17 adds a sibling schema family for topic-input missions. It does not add
optional keys to an existing V2 object and does not serialize an existing
explicit-seed mission through the new family.

| Role | Existing explicit-seed schema | New topic-input schema |
| --- | --- | --- |
| Fingerprint payload | `ra-survey-public-source-mission-fingerprint-v2` | `ra-survey-public-source-mission-fingerprint-v3` |
| GENESIS | `ra-survey-public-source-genesis-anchor-v1` | `ra-survey-public-source-genesis-anchor-v2` |
| Mission contract | `ra-survey-public-source-mission-contract-v2` | `ra-survey-public-source-mission-contract-v3` |
| Mission control | `ra-survey-public-source-mission-control-v2` | `ra-survey-public-source-mission-control-v3` |

The V3 fingerprint canonical payload has exactly these keys:

```text
schema_version
input_mode
normalized_topic_key
normalized_initial_seed_keys
discovery_budget
```

For M17 topic input, `input_mode` is exactly
`idea_or_topic_without_initial_paper_seed` and
`normalized_initial_seed_keys` is exactly `[]`. The discovery budget includes
the resolved mission write root exactly as V2 does. The canonical SHA-256 of
this payload is the immutable mission fingerprint. No candidate, capability,
attempt, score, provider result, or effective seed is part of it.

Topic GENESIS V2 has exactly these keys:

```text
schema_version
mission_id
mission_fingerprint
input_mode
normalized_topic
normalized_initial_seeds
discovery_budget
public_discovery_confirmation
created_at
migration
```

`normalized_initial_seeds` is exactly `[]`; `migration` is exactly `null`; a
new topic mission uses a validated random UUIDv4 exactly as a new explicit-seed
mission does. No V1 or explicit-seed V2 mission may migrate to topic GENESIS
V2.

Topic mission contract V3 has exactly these keys:

```text
schema_version
mission_id
mission_fingerprint
input_mode
generation
lineage
normalized_topic
normalized_initial_seeds
discovery_budget
public_discovery_confirmation
created_at
updated_at
migration
```

Its lineage object and generation/transaction/manifest mechanics remain the
existing exact M16 structures. Its digest excludes only the same mutable
lineage/update fields that the existing contract digest excludes. Contract V3
must equal topic GENESIS V2 for mission ID, fingerprint, input mode, normalized
topic, empty initial seeds, discovery budget, creation time, and null migration.

Topic mission-control V3 is the topic-mode counterpart of existing
mission-control V2. Its final committed payload has exactly these keys:

```text
schema_version
status
created_at
updated_at
topic
seeds
input_mode
initial_seeds
effective_seeds
bootstrap_attempt_state
bootstrap_outcome
bootstrap_authority
output_dir
resume
phase_statuses
reviewed_artifacts
coverage_artifacts
final_artifacts
source_intake_metadata_authority
public_discovery_confirmation
actions
next_gate
next_action_path
next_action
workflow_state
artifact_state
review_queue_path
review_queue_counts
review_queue_reused
safe_next_commands
forbidden_actions
what_is_not_concluded
local_supervisor
mission_contract
mission_id
mission_fingerprint
generation_id
```

- `input_mode` is exactly the persisted topic-input value;
- `seeds` remains exactly `[]` and means original user-supplied seeds only; it
  never contains bootstrap results;
- `initial_seeds` is exactly `[]`;
- `effective_seeds` is exactly `[]` unless `bootstrap_attempt_state` is
  `selected_complete`, `bootstrap_outcome` is `selected`, and the current
  pointer plus selected/reconciled journal row validate the exact prepared set;
  only then does it contain the canonical displays from that set;
- `bootstrap_attempt_state` is one of `confirmation_required`, `not_started`,
  `intent`, `call_started_indeterminate`, `result_recorded`, `prepared`, or
  `selected_complete`;
- `bootstrap_outcome` is `null` until a complete prepared result exists and
  otherwise one of `selected`, `empty`, `ambiguous`, `unavailable`, or
  `capped`;
- `bootstrap_authority` is `null` unless `bootstrap_attempt_state` is
  `selected_complete`, `bootstrap_outcome` is `selected`, and the current
  pointer plus selected/reconciled journal row validate the exact prepared set;
  only then is it the exact set ID, manifest SHA-256, request ID/digest,
  capability identity/version, confirmed ancestor generation, and effective
  normalized seed keys; and
- `source_intake_metadata_authority` and `local_supervisor` are always present
  and `null` until their existing typed stages produce exact validated values;
  and
- embedded `mission_contract` is contract V3.

The V3 validator requires the complete key set above, rejects unknown or
missing fields, and validates state/outcome/authority/effective-seed
compatibility. Existing explicit-seed mission-control V2 bytes and fields do
not acquire these keys; its validator remains behavior-compatible. The durable
topic confirmation checkpoint must emit this same full V3 object with closed
empty/null defaults, rather than a smaller transient mission-control shape.

A complete `prepared` result may expose its closed `bootstrap_outcome` for
recovery diagnostics, including `selected`, but it is still pre-pointer and
non-authoritative: `effective_seeds` must be `[]`, `bootstrap_authority` must be
`null`, and no terminal or downstream stage may consume it. A
`selected_complete` state with outcome `selected` requires nonempty effective
seeds and matching validated authority. A `selected_complete` nonselected
outcome requires empty effective seeds and null authority. Any other
state/outcome/authority combination fails closed.

Validation dispatch is by the exact on-disk `schema_version`, not by whether a
seed list happens to be empty:

1. Existing GENESIS V1 selects only the existing explicit-seed validators,
   exact keys, fingerprint V2, contract V2, migration logic, and request-match
   rules.
2. Topic GENESIS V2 selects only the new exact validators, fingerprint V3, and
   contract V3. The requesting input mode must be topic and its recomputed
   fingerprint must match before any repair, capability, or downstream action.
3. Unknown schemas, a contract family inconsistent with GENESIS, a topic
   contract containing `normalized_seeds`, an explicit contract containing
   `input_mode`/`normalized_initial_seeds`, or any extra/missing field fails
   closed.
4. A mission-control V2/V3 payload embeds contract V2/V3 respectively. Its
   generation-manifest artifact row records the actual mission-control schema.
   Cross-family pairs fail before mirror repair or downstream use.
5. Read-only ancestry/binding helpers dispatch from persisted schemas without
   fabricating dummy request identity. They return a validated common view plus
   the exact persisted contract; they never rewrite one family as the other.
6. Add fixed canonical-byte and fingerprint vectors for both families. All
   existing V2 vectors must remain byte-identical.

The existing transaction V1, generation-manifest V1, current-pointer V1, and
next-action V1 schemas may remain unchanged only because their exact structures
are generic and already bind mission ID/fingerprint, genesis digest, contract
digest, and artifact schema/hash. Tests must prove topic V3 artifacts replay
under those unchanged containers and that a wrong mission-control artifact-row
schema fails closed. If implementation needs any new field in one of those
containers, stop and patch/review this subplan with a sibling schema rather than
silently changing the V1 meaning.

Add one schema-aware accessor for common consumers:

```text
mission_input_view(contract)
  -> input_mode
  -> normalized_topic
  -> normalized_initial_seed_rows
```

For contract V2 it returns implicit `explicit_seed` and the existing
`normalized_seeds` rows without changing bytes. For contract V3 it returns the
persisted topic mode and empty `normalized_initial_seeds`. Consumers must use a
separate validated bootstrap selection to obtain `effective_seed_rows`; the
common input view never returns selected candidates as original inputs.

Topic-mode public orchestration uses sibling schema
`ra-survey-public-source-orchestration-result-v3`. Its public payload has
exactly these keys:

```text
schema_version
status
topic
seed_count
input_mode
initial_seeds
effective_seeds
effective_seed_count
bootstrap_attempt_state
bootstrap_outcome
bootstrap_authority
output_dir
mission_control_path
next_action_path
mission_id
mission_fingerprint
generation_id
artifact_paths
next_gate
next_action
public_discovery_confirmation
review_queue_path
review_queue_counts
review_queue_reused
artifact_state
phase_statuses
reviewed_artifacts
coverage_artifacts
final_artifacts
safe_next_commands
what_is_not_concluded
local_supervisor
```

For topic mode, inherited `seed_count` remains `0` because it counts original
inputs; `initial_seeds` is `[]`; derived candidates appear only in
`effective_seeds`, `effective_seed_count`, and hash-bound
`bootstrap_authority`. The public result never adds a `seeds` key because the
existing V2 public result does not expose one. Unconfirmed or nonselected
results have empty effective seeds and null authority. Existing explicit-seed
orchestration-result V2 schema, fields, `seed_count`, and bytes remain
unchanged. `local_supervisor` is always present and null until the typed local
supervisor closes; private in-process `_mission_control_payload` and
`_next_action_payload` transport keys are not part of the public schema.

The public V3 result enforces the same pointer-selection rule as mission
control. In particular, a prepared result whose closed outcome is `selected`
still reports empty effective seeds, zero `effective_seed_count`, and null
authority. It may populate those fields only after the attempt becomes
`selected_complete` through a validated current pointer and selected/reconciled
journal row.

## Bootstrap Capability Contract

Add a small immutable `MissionBootstrapCapability` protocol/object. The
callable receives only a validated request containing:

- schema version and unique request ID;
- mission ID, fingerprint, and current confirmed generation anchor;
- normalized topic display/key and input mode;
- the persisted discovery budget and exact output root;
- capability/provider name and version supplied by the caller; and
- no mission-state path handle, reviewer authority, source capability, or
  mutable global state.

It returns one closed, canonical outcome. M17 supplies deterministic fixture
capabilities only. Ordinary CLI execution after confirmation, when no
production capability exists, must persist and report `unavailable`; it must
not call existing provider code or reinterpret the topic as a seed. M20 will
implement production adapters.

## Bootstrap Outcome Contract

| Outcome | Exact meaning | Candidate rule | Workflow action |
| --- | --- | --- | --- |
| `selected` | The capability returned a deterministic, internally unambiguous selected set under its recorded local contract | Nonempty, unique, canonical-key-sorted candidates; each binds a stable paper key and the exact identifier/title evidence the capability supplied | Persist authority; derive effective seeds; continue only through consumers that validate this authority |
| `empty` | The capability completed its bounded attempt with zero candidates | Candidate and ambiguity lists empty | Honest stop `terminal_blocked_bootstrap_empty`; no downstream metadata/source action |
| `ambiguous` | More than one incompatible selection remains or identity conflict is unresolved | Nonempty candidate/ambiguity records; selected list empty | Honest stop `terminal_blocked_bootstrap_ambiguous`; request explicit future resolution, never auto-pick |
| `unavailable` | No production capability exists or the bounded capability reports unavailable | Selected list empty; closed reason enum required | Honest stop `terminal_blocked_bootstrap_unavailable`; no retry in the same invocation |
| `capped` | The cap prevents a valid complete selection decision | Selected list empty; cap and observed disposition recorded | Honest stop `terminal_blocked_bootstrap_capped`; no highest-score auto-selection |

Scores, ranks, citation counts, venue fields, abstracts, and result order are
descriptive routing fields only. They cannot convert ambiguity to selection or
serve as scientific/technical support.

## Immutable Bootstrap Authority And Crash Contract

1. Store bootstrap attempts below a dedicated mission-state subtree using
   immutable generation directories and an atomically selected current pointer.
   Names and schemas must be versioned and exact-key validated.
2. An attempt binds mission ID/fingerprint, input mode, genesis/current ancestor
   generation, persisted confirmation timestamp/source, request digest,
   capability identity/version, budget, outcome, exact candidates,
   dispositions, and artifact hashes.
3. The writer uses the existing mission lock, regular-file/non-symlink path
   checks, atomic temporary writes, file and directory fsync, manifest-last
   finalization, and atomic current-pointer selection.
4. A crash before pointer selection leaves non-authoritative journal/set
   evidence. Recovery follows only the exact lifecycle below: `intent` may make
   its first call; `result_recorded` may continue from its recorded bytes;
   `prepared` may select the exact validated set; and
   `call_started_indeterminate` blocks. It may never overwrite evidence,
   silently adopt partial/corrupt bytes, or append a new request outside a
   separately reviewed explicit retry/refresh transition.
5. A crash after pointer selection must replay the selected complete attempt
   without calling the capability again.
6. Corrupt pointers, missing members, extra files, hash mismatch, nonregular
   paths, ancestry mismatch, foreign mission identity, and unknown fields fail
   closed before downstream writes.
7. Each downstream topic-mode artifact binds the selected bootstrap set ID,
   manifest digest, request digest, effective normalized seed keys, and an
   ancestor mission generation. Changing current bootstrap authority makes all
   dependent old artifacts stale.

### Exact Capability-Call Lifecycle

Exactly-once knowledge is impossible if a process dies after invoking an
arbitrary capability but before durably recording its return. M17 therefore
uses an at-most-once, fail-closed request journal. One canonical transaction
record binds request ID/digest, mission identity, confirmed ancestor,
capability identity/version, budget, status, timestamps, result digest when
present, prepared-manifest digest when present, and prior-status digest.

```text
intent
-> call_started
-> result_recorded
-> prepared
-> selected
```

1. Under the mission lock, write/fsync `intent` before a call. A crash with
   only valid `intent` proves the call site was not crossed; ordinary resume may
   perform the first call with the same request ID/digest.
2. Atomically write/fsync `call_started` immediately before invocation. Once
   durable, a crash or exception without a valid complete prepared manifest is
   `call_started_indeterminate`: the capability may have run, so ordinary
   resume must not invoke it again, select partial bytes, or continue
   downstream.
3. After a normal return, validate the closed outcome before writing it. Write
   and fsync canonical result bytes, then atomically write/fsync
   `result_recorded` with their digest.
4. Write/fsync every set member, write the manifest last, fsync the set, rename
   to its final immutable directory, fsync the parent, then atomically
   write/fsync `prepared` with the manifest digest.
   On ordinary resume, a valid `result_recorded` may continue from its recorded
   bytes through set preparation without another capability call; the result
   digest and request lineage must match exactly.
5. Only a complete `prepared` transaction whose files/hashes validate may be
   selected without another call. Before pointer selection, every control or
   public projection remains `prepared`; even a prepared `selected` outcome has
   empty effective seeds, null authority, and zero downstream calls. Atomically
   select/fsync the current pointer, then mark the journal `selected`. A crash
   after pointer selection replays the selected set; reconciliation may advance
   a matching `prepared` row to `selected` without a call. Only after the
   pointer and selected/reconciled journal row validate may mission control
   commit `selected_complete`, expose matching effective seeds/authority, and
   permit downstream use. Thus a valid `prepared` may select the exact validated
   set on ordinary resume and must make zero capability calls.
6. A partial result, result without matching journal digest, manifest without
   `prepared`, prepared digest mismatch, or `call_started` without a valid
   prepared set is non-authoritative. Preserve it and emit
   `terminal_blocked_bootstrap_call_indeterminate` with the request ID and
   exact smallest next action.
7. M17 has no automatic/ordinary-resume retry for an indeterminate call. A
   future explicit retry/refresh requires a separately reviewed transition
   declaring idempotency/side effects, preserving the indeterminate request,
   and creating new request lineage. M20 must either use a provider-supported
   idempotency key or retain this fail-closed behavior.

## Confirmation, Resume, Refresh, And Migration

1. The initial unconfirmed topic invocation may create only mission identity,
   control, next-action, and their state-machine artifacts. It stops at the
   existing one-confirmation boundary and calls no bootstrap capability.
2. On `--resume --confirm-public-discovery`, the confirmation transition is
   checkpointed durably before capability invocation. A crash after checkpoint
   resumes without reprompting.
3. A selected or nonselected complete attempt is idempotently replayed on
   ordinary resume. A durable `intent` may perform its first call; any
   `call_started_indeterminate` state blocks. Ordinary resume never performs a second call for a request that reached `call_started`.
4. If a refresh surface is necessary, it must be explicit, confirmation-bound,
   mutually compatible with resume, and create a new immutable attempt. It must
   not delete old attempts, change mission identity, or silently invalidate
   downstream artifacts. Add it only with catching tests; do not invent it
   merely for convenience.
5. Changed normalized topic, changed output root/budget, added seed, removed
   seed, changed input mode, or a topic-mode invocation against an explicit-seed
   root fails with a direct identity mismatch before capability or downstream
   action.
6. Legacy explicit-seed migration remains V2-only. A legacy mission cannot be
   reclassified as topic-only. Topic-only state has no legacy migration path in
   M17.
7. A capability version change alone does not auto-refresh. The current
   immutable authority remains selected until an explicit reviewed refresh
   transition exists.

## Downstream Boundary

M17 may make existing local metadata/coverage consumers accept a validated
`effective_seed_authority`, but only as an explicit parameter or validated
context. It must not mutate the original mission input or let a consumer infer
effective seeds directly from arbitrary candidate JSON.

The orchestration public observation and mission-control view for topic mode
must follow the exact V3 schemas above. Original `seeds`/`seed_count` remain
empty/zero; derived effective seeds and selected authority stay separate.
Existing explicit-seed public JSON remains compatible; do not rename its
`seeds` field or add a persisted V3 mission contract beneath an existing V2
root.

Before a selected topic-mode mission advances, every affected consumer must
verify the bootstrap manifest and identity binding. For nonselected outcomes,
no metadata builder, source capability, claim/omission importer, merge,
reviewed-packet, or hostile-review stage may run.

M17 does not add a network provider. The production bootstrap and citation
frontier remain M20 work after M18-M19 authority.

## Immutable Pre-Edit M16 Historical Snapshot

The first write action of M17, before any product/test edit, creates:

`docs/validation/literature_survey_m17_2026-07-13/pre_edit_m16_snapshot/`

### Frozen Historical Source Manifests

Only these exact accepted manifests may supply an M16 direct product/test row:

| Phase | Manifest | SHA-256 |
| --- | --- | --- |
| 1 | `docs/validation/literature_survey_m16_phase1_2026-07-10/change_manifest.json` | `874b87d73266c2662398ff949b01b4ee8b48dbb102fd893063e2153a09af259e` |
| 2 | `docs/validation/literature_survey_m16_phase2_2026-07-10/change_manifest.json` | `9ab2565f2f3d290b9cc14b3807b2bed6f1507cb4941675db7280373c850d597a` |
| 3 | `docs/validation/literature_survey_m16_phase3_2026-07-11/change_manifest.json` | `8812b4180f3d8a64027eeb3ee226541a4c4d8cd575e5f052ec82b9c3ddb405b0` |
| 4 | `docs/validation/literature_survey_m16_phase4_2026-07-11/change_manifest.json` | `50e319b374772362c18f76a8c4f3ecd7d5a528e27b7b3654374c3ea5d3b47fb7` |
| 5 | `docs/validation/literature_survey_m16_phase5_2026-07-11/change_manifest.json` | `98ecfcfe8c0e98bd8b2a41a9c641dc0bcf6e36c6fe2d82c3333d374f99f454a2` |
| 6 | `docs/validation/literature_survey_m16_phase6_2026-07-12/change_manifest.json` | `f67a118a3e0effd0579d83dc6a28ba969ba8dfeddeb6955966bf4fba883c3aac` |
| 7 | `docs/validation/literature_survey_m16_phase7_2026-07-12/change_manifest.json` | `ad410f920b84a57d605a8ea60928227df746accf0601c9f4a7b528d9335d8ed2` |
| 8 | `docs/validation/literature_survey_m16_phase8_2026-07-12/change_manifest.json` | `d628ce0b76725e70dbe6bf7bd29013b4d9a473562c747a50084b802ecb4c3897` |
| 9 | `docs/validation/literature_survey_m16_phase9_2026-07-12/change_manifest.json` | `9a5e1736d1587a80d8b9c976b996291e1aaf42c67b44368712c7e4db285f0443` |

Verify all nine file hashes before parsing any product row. A mismatch stops
M17 before snapshot or edit; do not silently fall back to an altered manifest.
A later reviewed scope expansion with no row in this exact set receives only
`m17_entry_cutoff_only` provenance.

Required contents:

- `entry_replay.json`: exact replay of the four frozen Phase 10 authority
  artifacts and exact re-enumeration of the `1,137`-row Phase 10 validation
  inventory within its declared `positive/**`, `negative/**`, and
  `e2e_static_audit.json` scope;
- `authority_resolution.json`: hashes of the accepted M16 Phase 1-9 change
  manifests and one row per preexisting initial edit candidate, listing all
  direct hash occurrences in phase order, the selected latest accepted row,
  current file type/mode/size/hash, and one provenance classification:
  `m16_latest_direct_hash_bound` or `m17_entry_cutoff_only`;
- `snapshot_manifest.json`: every preexisting allowlisted file that M17 will
  edit, with original path, snapshot path, file type/mode, size, SHA-256, and
  exact authority-resolution row/digest; and
- `files/<repository-relative-path>`: exact bytes for each preexisting mutable
  path; and
- `snapshot_check.json`: independent source-to-copy verification and, for every
  `m16_latest_direct_hash_bound` row, copy-to-selected-authority verification,
  with zero mismatch or ambiguity fields.

The snapshot root becomes immutable after `snapshot_check.json` is finalized.
Do not place logs or later M17 results inside it. If the final edit set expands,
stop before editing the new path, capture and verify that path from the still
unmodified source, resolve all accepted M16 direct rows, and patch/review the
allowlist. If no accepted direct row exists, classify the copy honestly as
`m17_entry_cutoff_only`; it preserves pre-edit bytes but is not retroactive M16
hash authority. Append a new versioned snapshot manifest, review the scope
delta, then proceed. Never overwrite the first manifest.

The initial allowlist deliberately excludes any preexisting path without a
known accepted direct M16 hash. New M17 files have no pre-edit bytes. The
historical snapshot plus the accepted source manifests are immutable evidence;
the later cumulative successor manifest governs intentionally changed current
paths without asserting that old and new hashes are equal.

## Exact Edit And Write Allowlist

### Product And Test Edits

Only these paths may be added or edited during implementation:

- `src/research_assistant/cli.py`;
- `src/research_assistant/survey/mission_state.py`;
- `src/research_assistant/survey/bootstrap.py` (new);
- `src/research_assistant/survey/orchestrate.py`;
- `src/research_assistant/survey/build.py`;
- `src/research_assistant/survey/discovery_quality.py`;
- `src/research_assistant/survey/source_intake.py`;
- `src/research_assistant/survey/supervisor.py`;
- `tests/unit/test_literature_survey_m17.py` (new);
- `tests/unit/test_literature_survey_m16.py`;
- `tests/unit/test_literature_survey_m16_phase7.py`;
- `tests/integration/test_cli_commands.py`;
- `tests/fixtures/literature_survey_m17/**` (new, deterministic sanitized
  local fixtures only); and
- `scripts/literature_survey_m17_local_validation.py` (new).

An allowlisted file should be touched only if a catching test proves it is
needed. Formatting or refactoring unrelated code is forbidden. Any additional
product/test path requires a visible subplan patch, pre-edit snapshot capture,
overlap audit, and focused read-only review before edit.

### Evidence And Control Writes

- `docs/validation/literature_survey_m17_2026-07-13/**`;
- `docs/plans/literature_survey_north_star_m17_idea_topic_bootstrap_result_2026-07-13.md`;
- `docs/plans/literature_survey_north_star_m18_reproducible_git_integration_subplan_2026-07-13.md`;
- `docs/plans/literature_survey_north_star_visible_execution_ledger_2026-07-13.md`;
- `docs/plans/literature_survey_north_star_visible_stop_handoff_2026-07-13.md`;
- `docs/plans/literature_survey_north_star_gap_closure_master_program_2026-07-13.md`;
- `docs/plans/literature_survey_automation_milestones.json`;
- `docs/plans/reset_memo_2026-07-10.md` only after a meaningful state change;
  and
- bounded M17 review bundle/verdict files under `docs/reviews/`.

Temporary test missions must be created only under pytest-managed temporary
directories or `/tmp/literature_survey_m17_*` and removed only by their owning
test fixture. Do not modify frozen M16 validation/review artifacts.

## Required Artifacts

1. Immutable pre-edit M16 historical snapshot described above.
2. Versioned topic-input mission and fingerprint schemas with fixed vectors.
3. `MissionBootstrapCapability` and closed outcome schemas.
4. Immutable bootstrap attempt/set writer, selector, replay, and validator.
5. CLI and orchestration behavior for omitted seeds, confirmation, selected and
   nonselected outcomes, and exact safe next actions.
6. Deterministic positive/adversarial fixture matrix.
7. M17 local validation harness and logs.
8. `docs/validation/literature_survey_m17_2026-07-13/run_manifest.json`.
9. `decision_table.json`, `post_run_red_team.json`, and
   `successor_manifest.json` (or equivalently named cumulative manifest).
10. M17 result/close record.
11. Refreshed M18 subplan based on actual M17 hashes and included paths.
12. Compact review bundle and material read-only verdict.

## Required Checks And Tests

Every Python/test command sets `CUDA_VISIBLE_DEVICES=-1`. Full output goes to
predeclared logs below
`docs/validation/literature_survey_m17_2026-07-13/logs/`; JUnit/JSON summaries
go beside them.

Run in this order:

1. Entry authority resolution, scoped Phase 10 inventory replay, and immutable
   snapshot verification.
2. Syntax and schema checks:
   - `python -m py_compile` for changed Python files;
   - parse every new/changed JSON artifact; and
   - canonical-byte/fixed-vector tests for V2 and topic-input schemas.
3. Catching M17 unit tests covering:
   - omitted seed versus explicit empty seed;
   - stable topic-input mission ID/fingerprint and unchanged explicit-seed V2
     vectors;
   - exact GENESIS/contract schema-family dispatch, cross-family rejection, and
     common read-view behavior;
   - mission-control V2/V3 pairing, actual artifact-row schema binding, and
     unchanged generic-container replay;
   - exact mission-control/public-result original/effective-seed, attempt-state,
     outcome, and authority compatibility;
   - zero capability calls before durable confirmation;
   - exact selected, empty, ambiguous, unavailable, and capped outcomes;
   - ordinary resume idempotence and no implicit retry;
   - resume from `result_recorded` completes preparation with zero new calls,
     and resume from `prepared` selects with zero new calls;
   - crash/resume after `prepared` but before pointer selection exposes null
     authority, empty effective seeds, and zero downstream calls, then populates
     authority/effective seeds only after validated pointer selection and
     `selected_complete` reconciliation;
   - crash points before `intent`, after `intent`, after `call_started`, after
     capability return, during result write/fsync, after `result_recorded`,
     during each set-member/manifest/finalize step, after `prepared`, before and
     after pointer selection, and before/after journal reconciliation;
   - partial/corrupt/orphan/nonregular/symlink/foreign/stale attempts;
   - topic/input/output/budget/seed mismatch;
   - effective seed authority binding and stale downstream invalidation; and
   - zero downstream calls for every nonselected outcome.
4. Focused CLI tests covering command discovery, help, optional `--seed`,
   unconfirmed stop, confirmed unavailable stop without provider/network call,
   explicit-seed compatibility, and resume error messages.
5. Focused orchestration/build/source tests for selected fixture continuation
   and exact bootstrap lineage.
6. All M16 phase unit tests and CLI integration tests affected by the core
   mission contract.
7. The predeclared M17 persistent matrix:
   - one selected topic mission plus byte-identical resume;
   - one unconfirmed mission;
   - one each empty, ambiguous, unavailable, and capped;
   - identity-change, stale-authority, corrupt-pointer, orphan-crash,
     pre-confirmation-tripwire, and explicit-seed-regression cases.
8. Broader repository gates equivalent to the M16 close surface: full unit,
   full CLI, exact survey script tests, and affected non-CLI integration tests.
9. Static audit for network/provider/source/subprocess/model/GPU/outside-write
   tripwires, allowlist compliance, artifact closure, and no changes to frozen
   M16 artifacts.
10. Cumulative successor-manifest replay against current M16+M17 paths,
    independent replay of the historical snapshot against each selected M16
    direct authority row, and explicit separation of any reviewed
    `m17_entry_cutoff_only` row.
11. `git diff --check` and a trailing-whitespace scan limited to changed files.
12. Fresh material read-only review of identity, confirmation, immutable
    authority, crash/replay, downstream lineage, regressions, and claim scope.

No old Phase 10 canonical artifact may be overwritten by rerunning its harness.
M17 uses a new output root and treats the old M16 frozen evidence as read-only.

## Test Matrix Pass Predicates

| Case | Pass predicate |
| --- | --- |
| Topic unconfirmed | Stable mission exists; next action asks once; capability/provider/source calls are zero |
| Topic selected | Confirmation is an ancestor; state is `selected_complete`; one current-pointer-selected authority exists; effective seeds match it; original fingerprint is unchanged |
| Prepared before pointer | Closed outcome may be visible, but authority is null, effective seeds are empty, downstream calls are zero, and ordinary resume selects/reconciles with zero new capability calls before any authority is exposed |
| Empty | Exact empty terminal; no selected candidates and no downstream calls |
| Ambiguous | Exact ambiguity terminal; all conflicts visible; no auto-selection or downstream calls |
| Unavailable | Exact unavailable terminal; closed reason; no same-invocation retry |
| Capped | Exact capped terminal; cap/observed dispositions visible; no score-based choice |
| Resume | Same bytes and selected authority are reused; capability calls remain unchanged |
| Crash/orphan | Partial evidence never becomes authority; complete same-byte orphan recovery is deterministic and tested |
| Call indeterminate | Durable `call_started` without a valid prepared set emits the exact indeterminate terminal and ordinary resume makes zero further capability calls |
| Stale/corrupt/foreign | Fails closed before any downstream write |
| Explicit seed | Existing V2 vectors, migration, confirmation, resume, and full M16 terminal behavior remain unchanged |
| Manifest | Every directly bound old snapshot row replays its latest accepted M16 phase-manifest authority; any entry-only row is separately labelled; the scoped Phase 10 validation inventory replays; current tree replays the cumulative M17 successor manifest |

## Result And Review Contract

The M17 result must include:

- claimed target versus quantity implemented;
- exact changed paths and pre-edit snapshot rows;
- commands actually run, CPU-only environment, seeds/fixtures, wall time, and
  output paths;
- test/JUnit aggregates and every hard-veto status;
- decision table with primary criterion, uncertainty, next action, and
  nonclaims;
- separate engineering-correctness, live-evidence, and scientific-interpretation
  ledgers;
- post-run red-team: strongest alternative explanation, overturning evidence,
  and weakest evidence;
- successor manifest digest and historical snapshot digest;
- reviewer provenance, all findings, repairs, and final verdict; and
- exact M18 handoff or blocker.

Use a fresh compact packet. If Claude export remains environment-policy
rejected, do not retry or route around it; use a fresh Codex read-only reviewer
and record downgraded provenance. Repair material findings visibly and rerun
focused/affected checks for at most five rounds on the same blocker.

## Forbidden Claims And Actions

- Do not call the topic an identifier, title seed, selected paper, or technical
  claim support.
- Do not claim live discovery quality, relevance, completeness, scientific
  importance, source safety, human review, product readiness, or mission
  completion from fixtures.
- Do not change or migrate persisted M16 V2 explicit-seed bytes merely to
  simplify the new mode.
- Do not add optional topic fields to existing GENESIS V1, fingerprint V2, or
  contract V2 objects, and do not select a validator merely because a list is
  empty.
- Do not let selection change the original mission ID/fingerprint or overwrite
  GENESIS/current historical generations.
- Do not run a bootstrap capability before the durable confirmation checkpoint.
- Do not auto-select by score/order when ambiguity exists, auto-retry an
  unavailable/capped outcome, or hide a nonselected disposition.
- Do not run network, public provider, source/PDF/full-text, credential,
  paid-model, subprocess-agent, or GPU actions.
- Do not stage, commit, push, reset, restore, stash, clean, or create a Git
  worktree.
- Do not edit outside the allowlist or modify frozen M16 evidence.
- Do not create the M18 result or claim clean-checkout reproducibility.

## Exact Next-Phase Handoff Conditions

M18 may become the active planning lane only when all are true:

1. The M17 result is `PASSED_LOCAL_ENGINEERING_GIT_INTEGRATION_PENDING`.
2. Every primary predicate and hard-veto check above passes; no unexplained
   skipped test exists.
3. Existing explicit-seed behavior and frozen V2 vectors remain unchanged.
4. The immutable pre-edit snapshot independently replays each selected latest
   accepted M16 direct row; any reviewed entry-cutoff-only row remains explicit
   and is never called old M16 hash authority.
5. The cumulative successor manifest replays every current M16+M17 product,
   schema, test, fixture, governing-document, and canonical evidence path.
6. The final material review is `AGREE`, or any unavailable-review provenance
   is explicitly downgraded and local evidence is independently audited by a
   fresh Codex reviewer.
7. The M18 subplan is refreshed with actual M17 paths, hashes, dependency
   closure, dirty-work classifications, exact intended Git commands, result
   paths, and rollback-free validation procedure.
8. The refreshed M18 plan passes consistency, correctness, feasibility,
   artifact coverage, inherited-condition, and boundary-safety review.
9. The milestone JSON, master index, ledger, reset memo, and stop/handoff agree
   that M17 passed and M18 is planning-only.
10. No Git action occurs until a fresh user approval names the reviewed exact
    integration procedure.

## Stop Conditions

Write an M17 blocker result and stop only if:

- a frozen M16 entry hash/inventory does not replay and the cause is not a
  safely separable expected change;
- unknown user work overlaps a needed edit and cannot be preserved;
- an honest topic-input identity cannot be represented without changing M16 V2
  explicit-seed semantics;
- selected, empty, ambiguous, unavailable, and capped outcomes cannot be
  distinguished fail-closed;
- confirmation cannot be durably ordered before capability execution;
- the harness/artifact is corrupt or cannot test the claimed boundary;
- passing would require network, Git mutation, source access, credentials,
  package installation, GPU, or another absent authority;
- primary criteria would need to change after results; or
- the same material review blocker does not converge after five rounds.

Do not stop merely because a deterministic candidate is empty, ambiguous,
unavailable, or capped, or because a fixable catching test/review finding
fails. Those outcomes are required cases or repair triggers unless they expose
an invalid harness or unrepresentable state.

## End-Of-Phase Sequence

1. Run the complete required local checks.
2. Write the M17 result/close record and freeze its successor manifest.
3. Refresh M18 from the actual result and exact dependency closure.
4. Review M18 for consistency, correctness, feasibility, artifact coverage,
   inherited conditions, and boundary safety.
5. Update the visible ledger and stop/handoff before any advance.
