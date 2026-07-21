# M18 Reproducible Git Integration Result

Date: `2026-07-14`
Status: `PASSED_LOCAL_GIT_INSTALL_REPRODUCIBILITY`
Milestone: `M18_reproducible_git_integration`

## Result

M18's identified candidate commit
`654e6e1a1213bc03b7693ff1a8aea945a5bf08ac` passed its exact isolated
clone, offline wheel, import-origin, topic/seed, cumulative regression,
payload, static, trace, and protected-work gates on authoritative attempt 1.
No candidate repair child was needed.

The commit is the exact single-parent child of
`1b36af06efc7e1c2c086934cd8800691ae8a6da7`. It contains `1,725` paths:
`1,684` payload paths, `40` control paths, and `stage_record.json`. The payload
digest is
`0d225f29575778e606f096fda058cb0386dcd967a82284f5aa37a4c5638bd318`.
The six protected dirty worktree paths remained byte-identical, were absent
from the candidate delta, and remain intentionally dirty outside the index.

## Evidence Summary

| Gate | Result |
| --- | --- |
| Candidate audit | Passed; exact `1,725` paths and `17` frozen historical whitespace exceptions |
| Payload replay | `1,684/1,684`; zero mismatch |
| Offline wheel | Built and force-installed with `PIP_NO_INDEX=1` |
| Package origin | All `49` discovered imports, including the package root, under the attempt venv |
| Wheel/source coverage | `89/89` Python files; zero missing or extra package code |
| Focused M17 | `65 passed` |
| Cumulative M16+M17 | `846 passed` |
| Persistent M17 matrix | `13/13 passed` |
| Exact script suite | `12 passed` |
| Full unit | `1,047 passed` |
| Full CLI | `125 passed` |
| arXiv compatibility | `18 passed` |
| SurveyBench restricted/agent | `22 passed` |
| Phase 10 path portability | `2 passed` |
| Targeted traces | No dirty-checkout path and no `socket`, `connect`, or `sendto` occurrence |
| Protected source | Six before/after hashes identical |

All authoritative JUnit records have zero failures, errors, and skips. The
zero-test `phase10_path_rebase.xml` was a mistaken-selector diagnostic and is
not evidence; `phase10_path_rebase_pass.xml` is the passing authority.

The wheel SHA-256 is
`891e1e152d4d53fec3287b8209514b47383d9d2d85a02671b9e4358b343dcee2`.
The retained attempt root is
`/tmp/ra_m18_candidate_654e6e1a1213bc03b7693ff1a8aea945a5bf08ac_attempt01`.
Compact hash-bound evidence is under
`docs/validation/literature_survey_m18_2026-07-14/`.

Terminal review round 1 found that the initial compact package preserved only
aggregate import/wheel claims and omitted the exact command ledger. The focused
evidence repair added `import_origin_inventory.json` with all `49` module
origins and hashes, `wheel_source_inventory.json` with all `89` source/wheel
member pairs and byte hashes, and `command_manifest.json` with the actual
environment and corrected command sequence. `generate_inventory.py` makes the
two byte inventories reproducible from the retained attempt root. This did not
change or rerun the candidate.

## Boundary Interpretation

The targeted passing traces establish only their declared scope. The payload
trace uses `readlink` on the intentional historical absolute symlink and opens
a distinct clone-local `outside_packet.json`; it does not open the dirty
absolute target. The untraced full suites ran inside the platform
network-restricted sandbox, but M18 makes no universal claim that they
attempted no socket syscall.

Every Python/test action used `CUDA_VISIBLE_DEVICES=-1`. No live provider,
source, PDF/full-text, credential, model-worker, GPU, push, public release, or
destructive/history-rewriting action occurred.

## Decision Table

| Decision | Primary criterion | Veto status | Main uncertainty | Next justified action | Not concluded |
| --- | --- | --- | --- | --- | --- |
| Pass the M18 candidate, subject to terminal result review and closeout replay | Passed from isolated candidate clone and installed wheel | No M18 hard veto fired | Third-party packages came from `--system-site-packages`; bare-machine/cross-platform dependency closure is not proven | Review result/M19, make docs-only child, replay relationship/import/CLI, then stop at M19 live gate | Live behavior, source support, human review, scientific correctness, product/release or north-star readiness |

## Engineering, Numerical, And Scientific Ledgers

- Engineering correctness: M18's exact Git/install question passed.
- Numerical or sampler validity: not applicable; no numerical-method or
  stochastic comparison ran.
- Scientific interpretation: unchanged. The result says nothing about paper
  relevance, claim truth, literature completeness, or survey quality.

## Post-Run Red Team

The strongest alternative explanation is environment assistance: the wheel
was installed into a venv with system site packages, so Git contains the RA
code and test evidence but not a complete offline third-party wheelhouse. That
limits the claim to the observed Python 3.11/WSL environment. M23 must still
test the documented operator install contract.

The result would be overturned by a mismatch when replaying the candidate from
a fresh clone, an RA import outside the attempt venv, a required uncommitted
file, a protected-path delta, or a required-gate failure. None was observed.

## Review And Handoff

The material M18 plan converged in round 4 with fresh Codex read-only
`VERDICT: AGREE`; Claude export was policy-rejected before invocation and was
not retried. Terminal result/M19 review round 1 returned `REVISE` solely for
missing provenance inventories and the actual-command ledger; the focused
evidence repair required one command-fidelity correction in round 2. Round 3
returned `VERDICT: AGREE`. The separate M18 close record carries the phase
handoff; the future docs/evidence-only child is replayed after commit.

M19 is refreshed as planning-only and remains
`DO_NOT_EXECUTE_LIVE`. M18 supplies no live authority.
