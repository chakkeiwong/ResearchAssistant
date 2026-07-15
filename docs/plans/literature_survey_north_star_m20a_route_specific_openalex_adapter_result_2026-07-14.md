# M20A Route-Specific OpenAlex Adapter Result

Date: `2026-07-14`
Status: `PASSED_LOCAL_NO_NETWORK_ENGINEERING_M20B_BOUNDARY_PENDING`
Milestone: `M20_live_discovery_and_citation_frontier`

## Outcome

The checked official OpenAlex singleton/list semantics are now represented by
strict, non-executable request descriptors and no-network response parsers.
The implementation feeds the existing M20 normalized-response, identity,
frontier, and three-axis composition runtime. The final material review found
no remaining defect.

This is local engineering evidence only. No provider API was called, no API
key was read or stored, no live response was parsed, and no search relevance,
citation completeness, provider availability, cost acceptability, M20B
readiness, or north-star completion is established.

## Skeptical Audit

The executed slice passed its pre-execution audit:

- the baseline is the retained official singleton/list operation contract,
  not legacy M19 OpenAlex syntax;
- `per_page` and `sort=-cited_by_count` are required, while `per-page` and
  `cited_by_count:desc` are rejected;
- provider-returned identifiers are exact canonical URLs rather than values
  accepted by a permissive local seed normalizer;
- descriptors contain no URL, header, cookie, credential value, environment
  lookup, network import, callback, opener, or dispatch method;
- synthetic parser success is an engineering criterion, not provider or
  scientific evidence; and
- malformed backward lineage cannot be silently admitted or erase a valid
  independent direct identity.

No material baseline, proxy, stop-condition, environment, or artifact-fitness
defect remained after the review repair loop.

## Implementation Evidence

| Artifact | SHA-256 |
| --- | --- |
| `src/research_assistant/survey/openalex_adapter.py` | `e079e50a5e6024eda3425393816ecfe75e05608a1e8c99890648af3c28ffd31e` |
| `tests/unit/test_literature_survey_m20_openalex_adapter.py` | `a2a4603828ef6846df908df521f198a66d2161b0d4ba82f7f42fc3ccf8738c73` |
| `src/research_assistant/survey/discovery_capability.py` | `317929ad18e933380efda3d9f4e11895389365953f88d65a41fe1215d42ce464` |
| `tests/unit/test_literature_survey_m20_discovery.py` | `a2ddc705b3396ffeb7491e8d96e79f86a305432a71182524e34817903d62593e` |
| canonical automaton | `a1f3d6126de27880ebb9804dcb075091b9694fc9b8d36f005e327b29bdefc0b7` |
| code/test manifest | `b0c02feebe7ad3993907f0b0afeb83a97818b8a979c44bd827b053e3d0f35872` |

Baseline Git `HEAD` was
`ad4e2d52ab9df7198547b3cb98d8acbd1b9680a5`. The M20A changes are currently
identified by exact file hashes in the preserved dirty worktree. They have not
yet been integrated into an identified successor commit or installed wheel;
that is an M20B3 pre-live packet-freeze condition, not a claim made by this
result and not an M20B0 planning entry condition.

## Checks

All Python checks used
`CUDA_VISIBLE_DEVICES=-1`, `PYTHONPATH=src`, and
`/home/chakwong/anaconda3/envs/tf-gpu/bin/python`. No network was used.

| Gate | Result | Preserved evidence |
| --- | --- | --- |
| Focused adapter after strict ID repair | `59 passed` | independently reproduced during terminal review |
| M19 transport/supervisor plus M20 discovery/adapter | `188 passed in 4.59s` | `junit/m19_m20_adapter_round3.xml`, SHA-256 `f5cfa7d423c464ceaafd76e97b7804fdef03fa0bcf65bdc9936693384ce64bfe` |
| Affected M16/M17 durable regression | `846 passed in 493.19s` | `junit/affected_m16_m17.xml`, SHA-256 `03c86ad9a6f5b14748ee102ec1874bb701b0cbc03bd8b8ff41bf7e47fb7868a9` |
| Manifest JSON | parsed successfully | exact manifest above |
| Diff hygiene | `git diff --check` passed | local closeout check |

Evidence root:
`docs/validation/literature_survey_m20_route_specific_adapter_2026-07-14/`.

## Review And Repair Record

Round 1 found missing normalized-field, provenance, envelope, descriptor, and
malformed-row constraints; they were repaired. Round 2 found that
provider-returned IDs used the permissive generic normalizer and could accept
wrong-host URLs. The final repair introduced exact canonical provider URL
validation and adversarial tests. Claude was alive, but the substantive export
was policy-rejected. A fresh Codex read-only fallback reviewed the compact
round-3 packet and returned `AGREE`.

Review artifacts:

- `docs/reviews/literature_survey_m20a_route_specific_adapter_code_review_bundle_round3_2026-07-14.md`;
- `docs/reviews/literature_survey_m20a_route_specific_adapter_code_review_verdict_round3_2026-07-14.md`.

## Decision Table

| Decision | Primary criterion status | Veto status | Main uncertainty | Next justified action | Not concluded |
| --- | --- | --- | --- | --- | --- |
| Pass route-specific local engineering | Exact descriptors, parsers, replay, classifiers, cumulative gates, and material review pass | No local parser, authority, replay, or regression veto fired | Credential handling, official pricing, cost budget, identified installed execution bytes, and live provider behavior | Freeze a planning-only M20B credential/privacy/cost decision subplan; obtain the required human decisions before any live packet or call | Provider quality, search relevance, citation completeness, cost acceptability, M20 completion, M21 authority, or north-star completion |

## Inference Status

| Evidence class | Status |
| --- | --- |
| Hard veto screen | Local no-network engineering passes. Credential and cost authority remain absent and prohibit M20B. |
| Statistically supported ranking | Not applicable; no stochastic or provider comparison ran. |
| Descriptive-only differences | Test duration, synthetic fields, row counts, and citation values only. |
| Default readiness | Not established; no provider path or product default was activated. |
| Next evidence needed | Credential/privacy/cost decision, identified installed execution bytes, frozen live campaign contract, explicit human authorization, then one bounded live attempt. |

## Post-Run Red Team

The strongest alternative explanation is that strict synthetic parsing only
proves consistency with retained documentation, not the provider's future live
behavior. A live schema change, key-placement leak, unexpected billed cost, or
installed-byte mismatch would invalidate M20B even though these tests pass.
Those risks remain explicit entry vetoes for the next phase.
