# M17 Successor Artifact-Closure Repair Read-Only Review Bundle

Status: `READY_FOR_REVIEW`

## Role Contract

Codex is supervisor/executor. The reviewer is read-only. Do not edit files, run
tests or experiments, launch agents, or change state. This review cannot
authorize Git mutation or any live/source/human/scientific/product boundary.

## Exact Question

Does the narrow successor-manifest repair fully and safely close the identified
under-coverage: the original manifest bound the Phase 10 inventory record but
omitted the actual 1,137 evidence members it enumerates? Is the repaired
1,671-row manifest sufficient and honest for M17 handoff to M18 planning,
without making a clean-checkout claim?

## Prior Review

Claude Opus/max primary review returned `AGREE` on M17 code semantics, identity,
confirmation, crash handling, downstream binding, V2 compatibility, and claim
scope. That verdict remains valid for code. Afterward, Codex independently found
this artifact-coverage gap and reopened M17 before milestone advance.

## Narrow Repair

Review only:

- `docs/validation/literature_survey_m17_2026-07-13/generate_close_artifacts.py:82-183` - canonical containment, frozen-authority hash checks, exact replay of all 1,137 inventory rows, and exact 37-list-row plus singleton validation of all 38 direct logical rows.
- `docs/validation/literature_survey_m17_2026-07-13/generate_close_artifacts.py:202-379` - inclusion, deduplication, digest, scope, and nonclaims.
- `docs/validation/literature_survey_m17_2026-07-13/successor_manifest_replay.json` - focused replay result.
- `docs/validation/literature_survey_m17_2026-07-13/static_audit.json` - updated counts/hashes.
- `docs/validation/literature_survey_m17_2026-07-13/post_run_red_team.json` - transparent record of the initial under-closure.
- `docs/plans/literature_survey_north_star_m17_idea_topic_bootstrap_result_2026-07-13.md:90-122` and `:155-180` - repaired artifact and pending-handoff claims.

Out of scope: rereviewing product code already agreed, live quality, scientific
claims, M18 execution, or the contents of all 1,671 rows individually.

## Exact Evidence

- Old candidate: `502` rows; it included the inventory JSON but not all member
  files. It was never used to advance M17.
- Repaired candidate: `1,671` unique, sorted repository paths.
- Canonical Phase 10 inventory members: `1,137` present, comprising `1,136`
  regular files and one adversarial symlink.
- Remaining direct Phase 10 evidence after deduplication: `32` paths. Together
  with six overlaps, all 38 direct change-manifest rows are covered.
- Manifest payload SHA-256:
  `163f9ca026e18903d219690ed88647c1bc26ae7f45cd0752aa05a9cb891d485f`.
- Manifest file SHA-256:
  `46fd3d4e444fc5fd43b9d10f05dce110980c75bd13b98b345ae459a5b4277571`.
- Replay file SHA-256:
  `774eebfd5325a97025fca4a41d0e0fcd0fa04b943771888b18397a94b45ee72e`.
- Generator SHA-256:
  `1ccd5d0f4b3de5733125cc5ec63c2ffb5b348c379a3c884531a7ccd509755d50`.
- Focused checks: generator compiles; generator exits 0; `1,671/1,671` replay;
  zero mismatch; unique/sorted paths; exact `1,137` Phase 10 member count;
  top-level JSON parse; `git diff --check`.

The generator validates the frozen Phase 10 change-manifest and inventory file
SHA-256 values before parsing them, rejects absolute/noncanonical/parent paths
before `lstat`, enforces the inventory's declared subtree, and then validates
each member's type and content or target text.

A second Claude export for this narrow repair was policy-rejected and will not
be retried or routed around. The terminal repair review is therefore assigned
to a fresh Codex read-only reviewer under the same pass/block criteria.

The one symlink is an intentional M16 negative fixture whose target is an
absolute path inside the current repository. The generator hashes the symlink
target text without dereferencing it. M18 must decide whether an isolated
checkout should preserve that literal target, rewrite the fixture through a
reviewed deterministic setup, or treat this historical evidence row as
non-runtime canonical evidence. M17 must not call the symlink portable or use
it as clean-checkout proof.

## Pass/Block Criteria

Pass if:

- the repaired manifest really binds the actual inventory members rather than
  only their record;
- inventory rows are checked for exact kind/hash/size or symlink target before
  inclusion;
- direct Phase 10 rows are checked against their recorded SHA-256;
- deduplication cannot conceal a hash conflict;
- the digest excludes mutable downstream controls without claiming they are
  bound;
- the adversarial symlink is represented honestly and creates an explicit M18
  portability decision rather than a false M17 pass; and
- claims remain limited to dirty-tree artifact closure, not Git reproduction.

Return `REVISE` for a material omission, unsafe path treatment, digest-cycle or
replay flaw, misleading count, or unsupported clean-checkout/handoff claim.

## Requested Verdict

Findings first with exact anchors. End with exactly one line:

```text
VERDICT: AGREE
```

or

```text
VERDICT: REVISE
```
