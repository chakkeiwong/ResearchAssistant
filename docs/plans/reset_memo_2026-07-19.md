# Reset Memo: Post-M23 Reboot Handoff - 2026-07-19

## Objective

Provide a clean restart point after completion of the literature-survey
north-star M17-M23 program. A rebooted agent should be able to determine the
current authority, reproduce the local result if needed, preserve the
scientific limitations, and avoid reopening retired governance or provider
loops.

## Current Status

- Branch: `main`.
- Program status: `ACCOMPLISHED_WITHIN_RECORDED_LOCAL_EXPLORATORY_SCOPE`.
- Integration commit:
  `6149818ab25791ca01c9d84fbbbb580f1e121841`.
- Integration tree:
  `60467239d7ccfd5f035049f6ca6913a880d3ba23`.
- Program close commit:
  `33db3a33d8fcccb33185cb1772e2ebfe1af03df0`.
- Reboot-memo commit: the commit containing this file; verify with
  `git log -1 --oneline -- docs/plans/reset_memo_2026-07-19.md`.
- No M17-M23 continuation task remains active.
- No credential, provider, PDF fallback, publication, push, or release
  authority is inherited from the completed program.

## Authoritative Reading Order

1. `docs/plans/literature_survey_north_star_m23_versioned_clean_checkout_close_result_2026-07-19.md`
2. `docs/plans/literature_survey_north_star_gap_closure_master_program_2026-07-13.md`
3. `docs/plans/literature_survey_north_star_m23_operational_acceptance_result_2026-07-19.md`
4. `docs/literature_survey_operator_guide.md`
5. `docs/known_limitations.md`

Older OpenAlex, approval-token, numeric-scoring, generic-human-attestation,
and custom terminal-control plans are historical artifacts. They are not
active prerequisites or next actions.

## Verified Local Result

The exact 101-path implementation and compact-evidence closure was reproduced
from a detached clean checkout of the integration commit.

| Check | Result |
| --- | --- |
| Focused M22/M23 tests | `23 passed` |
| Affected M16/M17/M20/M22/M23/CLI gate | `263 passed, 77 deselected` |
| M23 operational acceptance | `9/9`; `M23_OPERATIONAL_ACCEPTANCE_PASSED` |
| Installed replay | Passed from `/tmp` with `PYTHONPATH` unset |
| Captured stderr | Empty |
| JSON parsing | `75` artifacts parsed |
| Source/wheel M23 module | Byte-identical; SHA-256 `14173a0f5dedfa9c7e087dfa1f880ad245fab7038ab6dd15ed6b75176903bc6b` |
| Authoritative wheel | SHA-256 `fdd58293702371e4f85efe1f667e5310e597073d35ca3a945b6b831d1cbe7899` |
| Documentation consistency | Passed in completed state |

Generated acceptance roots are local evidence and are not the authority by
themselves. The versioned code, compact evidence, result notes, manifests, and
Git identities form the durable restart boundary.

## Scientific State

- The active scientific route is credential-free arXiv source intake and
  backward-reference analysis. OpenAlex and credentialed citation providers
  are permanently out of scope for this completed program.
- Forward-citation coverage is unavailable and non-blocking. It is neither
  zero nor complete.
- Fifty identifier-bearing omission rows remain provisional title-context
  risks. They are not fifty equally important missing papers.
- The 195 identifier-free units are unresolved bibliography units. Their
  unique-paper count and relevance are unknown.
- Selected cited TeX source members are versioned to support scoped technical
  inspection. Bulk archives, PDFs, uncited source bodies, wheels, environments,
  logs, and copied execution roots remain excluded.
- `claim_support_allowed=false` and `ready_for_prose=false` remain
  authoritative.
- Publication/retraction status and official implementation checks are not
  comprehensive.

## What Is Not Concluded

The completed program does not establish:

- literature completeness;
- scientific or mathematical truth of survey claims;
- live topic-discovery quality;
- citation-provider coverage or reliability;
- publication-ready prose or publication safety;
- autonomous expert judgment or human usability;
- macOS or native-Windows support;
- general product readiness or release readiness.

## Repository Boundary

Versioned:

- runtime source, CLI changes, scripts, tests, operator documentation, plans,
  results, and review records needed for M22/M23;
- compact M20/M21/M22 authorities and ledgers used by deterministic replay;
- exact cited TeX members needed for the recorded technical inspections.

Excluded or local-only:

- bulk downloaded archives, PDFs, uncited source bodies, raw private intake,
  generated validation roots, virtual environments, wheels, build scratch,
  logs, command transcripts, caches, and local reviewer transcripts.

Do not add excluded bulk artifacts merely to make a replay pass. Repair the
reconstruction path or write an honest blocker instead.

## Reboot Procedure

1. Confirm `git status --short --branch` is clean and `main` is synchronized
   with `origin/main`.
2. Read the authoritative files in the order above.
3. Do not resume M17-M23 execution; the program is closed.
4. If reproducing M23, use a fresh output root, deliberate CPU-only execution,
   no package-index access, and the commands recorded in the versioned-close
   subplan/result.
5. If new work is requested, identify whether it changes scientific scope,
   external access, publication state, product direction, or compute budget.
   Create a new concise plan when it does.
6. Preserve the open omission and forward-coverage limitations in every future
   summary unless new evidence directly changes them.

## Next Work Decision

There is no automatic next milestone. The next justified action depends on a
new user objective:

- live topic-quality evaluation: new scientific campaign and evidence contract;
- additional source inspection: new bounded omission-risk plan;
- forward citations: only a genuinely credential-free route, with unavailable
  coverage remaining acceptable;
- claim or prose promotion: primary-source claim mapping, publication-status
  checks, and separate review;
- cross-platform or product validation: new engineering program;
- push, release, or publication: explicit action at that boundary.

Do not infer any of these objectives from this reboot memo.

## Final Hygiene

- Working tree was clean before this memo was written.
- The prior two local commits were ahead of `origin/main` and are intended to
  be pushed together with the commit containing this memo.
- No live experiment, network/provider request, credential access, source
  download, GPU action, or release action is required to validate this memo.
