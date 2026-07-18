# M20/G3 ArXiv-Only Close Result

Date: `2026-07-18`
Status: `PASSED_REVISED_M20_G3_SOURCE_GROUNDED_BACKWARD_DISCOVERY`
Plan: `docs/plans/literature_survey_north_star_m20_arxiv_only_500mb_attempt_plan_2026-07-18.md`
Migration: `docs/plans/literature_survey_north_star_m20_arxiv_only_governance_migration_2026-07-18.md`
Evidence root: `docs/validation/literature_survey_m20_arxiv_only_live_2026-07-18_20260718_150000/`

## Result

The single authorized arXiv-only invocation passed the revised M20/G3
contract. It dispatched exactly one public arXiv source request, made zero
retries, retained the exact `2201.12220v3` source package, extracted `62`
unique canonical backward-reference candidates, wrote complete preliminary
classification and scholarly-audit ledgers, recorded forward coverage as
`unavailable_out_of_scope` with `blocking=false`, and passed deterministic
offline replay.

M20/G3 is closed under the source-grounded backward-discovery definition. The
old provider-dependent exit criteria remain retired historical artifacts.

## Run Manifest

| Field | Observed value |
| --- | --- |
| Git commit/tree | `3890a41c75ab7d7db7ef45d5c3d98b6784170217` / `38152358cdacb457a4429e6b396aff56edf79cb3` |
| Worktree | dirty; exact plan, migration, runner, and worker bytes preserved under `execution_sources/` |
| Command | `CUDA_VISIBLE_DEVICES=-1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -m research_assistant.survey.m20_arxiv_only_live_runner --repository-root /home/chakwong/research-assistant --output-root /home/chakwong/research-assistant/docs/validation/literature_survey_m20_arxiv_only_live_2026-07-18_20260718_150000` |
| Environment/hardware | project Python; deliberate CPU-only; GPU hidden |
| Data version | exact arXiv seed `2201.12220v3`; access record in run manifest |
| Random seeds | N/A; deterministic intake and parse |
| Wall time | `6.720952` seconds, monotonic |
| Requests/retries | `1` / `0` |
| Source body | `26,842,514` bytes; SHA-256 `2eb686b1f5dd9b2fa95ed5185cfe5da4d8e93a2b7d8a294902962e9dac66bd0f` |
| Final evidence-root disk usage | `26,998,565` bytes by `du -sb`, below `500,000,000` |

The output-root suffix `20260718_150000` is a preselected unique version label,
not observed clock evidence. Use only the manifest timestamps and monotonic
duration for execution timing.

## Scientific Evidence

- Archive inspection observed `106` members and `27,857,376` declared expanded
  bytes, with `5` relevant text members totaling `190,654` bytes.
- The parser observed `264` bibliography units. `69` contained an admitted
  DOI/arXiv identifier and deduplicated to `62` candidates. The remaining `195`
  identifier-free units are an explicit omission risk, not silently discarded
  evidence of completeness.
- Every candidate is `NOT_CHECKED`, has `SOURCE_GAP_BLOCKER`, and requires
  `inspect_primary_source`. Metadata titles and identifiers do not establish
  relevance or technical support.
- All six scholarly ledgers exist: source support, citation/venue metadata,
  backward snowball, forward snowball, claim support, and omitted-paper risks.
- Forward coverage is unavailable and outside scope. It is neither zero nor a
  continuation veto.

## Decision Table

| Decision | Primary criterion | Veto diagnostics | Main uncertainty | Next justified action | Not concluded |
| --- | --- | --- | --- | --- | --- |
| Close revised M20/G3 | Passed | Identity, route, response/root, archive, member, path/type, empty-layer, raw-confinement, and replay vetoes did not fire | Identifier-free reference recall and all candidate relevance/source status remain unchecked | Refresh M21 planning around exact retained source and candidate/omission ledgers | Forward coverage, completeness, technical support, retraction/version safety, scientific correctness, M21/north-star completion |

## Inference Status

| Evidence class | Status |
| --- | --- |
| Hard veto screen | Passed for the revised M20 source/backward-discovery contract |
| Statistically supported ranking | Not applicable; no stochastic candidate or provider ranking was performed |
| Descriptive-only differences | Source size, archive/member counts, identifier yield, and elapsed time are descriptive |
| Default-readiness | Not established; this is one bounded research-validation seed, not a product default decision |
| Next evidence needed | Primary-source identity/status/technical-anchor inspection and human-reviewed relevance/omission decisions under later milestones |

## Verification

- Focused arXiv-only tests: `15 passed`.
- Related M20 regression slice: `115 passed`.
- Worker/runner/test compilation: passed.
- Milestone JSON parse, active route/interface scan, retained identity preflight,
  fresh-root preflight, and scoped diff hygiene: passed.
- Post-run offline replay independently returned `status=passed`, source hash
  above, `candidate_count=62`, and forward status
  `unavailable_out_of_scope`.
- All `13` root JSON artifacts parsed; candidate IDs were unique; classifications
  and backward rows matched; three omission-risk rows were present.
- All four preserved execution-source hashes and all `17` artifact-inventory
  rows replayed; accepted-body confinement passed.

## Post-Run Red Team

The strongest alternative explanation is that identifier-only parsing found a
convenient subset while omitting many relevant identifier-free references. The
`195` identifier-free units and forward-unavailable state prevent a
completeness claim. A later primary-source audit could also classify some or
all `62` candidates as irrelevant, superseded, quarantined, or source-blocked;
that would not invalidate this intake/replay result but would change the
scientific candidate set. The weakest evidence is therefore recall and
relevance, not transport or replay integrity.

## Handoff

M21 planning may consume the retained exact seed source, `62` preliminary
candidates, six ledgers, and explicit omission risks. M21 must define which
candidate sources and technical anchors to inspect and preserve source status,
version, quarantine, and claim-support boundaries. This close record does not
authorize M21 execution, another network request, PDF fallback, credentials,
Git integration, push, release, or a north-star completion claim.
