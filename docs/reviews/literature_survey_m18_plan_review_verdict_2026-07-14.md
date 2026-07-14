# M18 Material Plan Review Verdict

Date: `2026-07-14`
Reviewer: fresh Codex read-only reviewer (`/root/m18_plan_review`)
Round: `1`
Status: `HISTORICAL_FINDINGS_ACCEPTED_REVIEWER_DISQUALIFIED`

Claude export was policy-rejected before invocation. It was not retried or
routed around. Codex remains supervisor/executor. This reviewer returned useful
material findings, but then ran the helper `plan` action and compile checks
despite its read-only role. The reviewer was interrupted and is disqualified
from supplying the required converged verdict. A fresh reviewer must evaluate
the repaired frozen packet.

## Material Findings

1. Source modes `0444` and `0600` were used as clean-clone expectations even
   though Git stores only executable-bit class for regular files. Repair:
   preserve `source_mode_octal`, bind Git-replay mode, and validate Git index
   mode plus filesystem executable class.
2. The advertised attempt-2 descendant repair was infeasible because `stage`
   accepted only the M17 baseline. Repair: separate fail-closed `stage-repair`
   action bound to the failed direct child, exact repair rows, preserved
   attempt evidence, unchanged boundaries, and one index transaction.
3. Frozen Phase 10 CLI evidence contained absolute paths that the test opened
   in the original dirty checkout. Repair: validate canonical suffix and
   artifact shape, rebase reads to supplied clone-local output, add a regression
   that rejects dirty-checkout reads, and trace the full script suite.
4. The ten-unit and five-script suites were not enumerated, and ambient
   `pytest` could use host Python. Repair: freeze exact paths and invoke every
   gate through the attempt venv's `python -m pytest` with external JUnit.
5. Staging did not require equality with the reviewed manifest or bind row
   blobs. Repair: require byte-identical canonical recomputation and record
   path, Git mode, SHA-256, size, and blob OID for every non-self stage row.
6. Retry evidence was self-attested and repair paths were semantically broad.
   Repair: hash-check regular evidence under preserved attempt 1 and require a
   Codex supervisor audit binding exact repair paths, class, failed candidate,
   and unchanged scope before staging.
7. Closeout prose implied a tracked artifact could contain its own commit hash.
   Repair: tracked closeout records parent/candidate provenance and a self-hash
   nonclaim; the actual closeout hash is written only to a post-commit `/tmp`
   record.
8. Exact script count changed from 11 to 12 after the portability regression.
   Repair: update the declared gate and require fresh disposable committed-clone
   evidence.
9. No-network and no-dirty-read conclusions exceeded the original trace scope.
   Repair: trace every authoritative command for network and the full 12-test
   script suite for file access; retain pre/post clone status evidence.

Finding 9's proposed universal trace repair was later shown infeasible: ptrace
terminated the multiprocessing-heavy suite before JUnit. The final repair uses
the platform's network-restricted sandbox for all authoritative commands,
untraced JUnit for full suites, and syscall traces only for payload replay,
installed CLI smokes, and the path-sensitive Phase 10 tests. No universal
absence-of-socket-attempt claim is made for untraced suites.

## Required Before Round 2

- Regenerate frozen helper/payload/dependency/plan/review-bundle hashes.
- Create an actual disposable candidate commit and a separate fresh clone.
- Require payload replay with zero mismatch and protected baseline bytes.
- Require exact 12-test script suite pass under the candidate environment and
  zero original-checkout reads in its trace.
- Exercise fail-closed attempt-2 descendant staging and rejection paths in a
  disposable repository.

All requested repairs were implemented and bound in
`docs/validation/literature_survey_m18_2026-07-14/disposable_preflight_record.json`.
Because this reviewer violated the read-only role, those repairs require a
fresh round-2 review rather than converting this historical verdict to
`AGREE`.

VERDICT: REVISE
