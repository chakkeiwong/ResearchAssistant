# M23 Versioned Clean-Checkout Close Result

Date: `2026-07-19`
Status: `ACCOMPLISHED_WITHIN_RECORDED_LOCAL_EXPLORATORY_SCOPE`
Plan: `docs/plans/literature_survey_north_star_m23_versioned_clean_checkout_close_subplan_2026-07-19.md`

## Outcome

The M17-M23 north-star program is closed within its recorded local exploratory
scope. The complete 101-path runtime, test, document, review, compact-authority,
and cited-source closure is versioned in commit
`6149818ab25791ca01c9d84fbbbb580f1e121841`, tree
`60467239d7ccfd5f035049f6ca6913a880d3ba23`. No raw archive body, wheel, virtual
environment, command transcript, copied execution source, log, provider call,
credential access, PDF fallback, push, or release entered the commit.

## Required Evidence

| Evidence | Result |
| --- | --- |
| Exact include manifest | `101` paths; SHA-256 `d5e3965530a20e1fb4993e61a2bda920faf4ef2761c23794f3604f8129f0fb1f` |
| Exact exclude manifest | SHA-256 `9d31aaa615c9f83deb91d8c65cfc60d9c3ecc4b2db93aa63aaa04e4a7ba28157` |
| Integration commit/tree | `6149818ab25791ca01c9d84fbbbb580f1e121841` / `60467239d7ccfd5f035049f6ca6913a880d3ba23` |
| Clean status | `worktree_dirty=false` in the authoritative M23 manifest |
| Compile/diff | Passed |
| Focused M22/M23 | `23 passed` |
| Exact affected gate | `263 passed, 77 deselected` |
| M23 primary criterion | `9/9`; `M23_OPERATIONAL_ACCEPTANCE_PASSED` |
| Installed replay | Passed from `/tmp` with `PYTHONPATH` unset |
| Command boundary | One external cwd; all stderr files empty |
| Artifact parse | `75` JSON files parsed |
| Source/wheel M23 module | Equal; SHA-256 `14173a0f5dedfa9c7e087dfa1f880ad245fab7038ab6dd15ed6b75176903bc6b` |
| Terminal review | Fresh Codex fallback Round 4: `AGREE` |

## Authoritative M23 Hashes

| Artifact | SHA-256 |
| --- | --- |
| wheel | `fdd58293702371e4f85efe1f667e5310e597073d35ca3a945b6b831d1cbe7899` |
| terminal result | `ed316d62ff267794be3663fa521240a195c3b4b5710aa7ff06ef251bc135a712` |
| case results | `7d6371d54ead28c9a5c4b2be2704b91918883244c157798ad61beb67274743cc` |
| offline replay | `9642387064bcb46215bff91c96bb7a499f22d8c459c6b7d83d0fe45698aee612` |
| run manifest | `e2b0cfc6ecbdca83ae8ad5770495bcb84d697584d4afca92c1f752dfb5c91f5f` |
| command ledger | `37c00668d5769311f3bc5bf385aa24299ce27658d90e64b5ae47cc3dbeab5f0c` |
| capability matrix | `872b426de8f9c2c9cacb065bdd6f2213392734c7af5f720b1c95b6d15a9ecb9f` |
| documentation report at integration commit | `b8941c0b081c4932b1790a9ac1a860667a948bbee8e7897b1ad6601a8c093a3a` |
| artifact inventory | `03ed356898925a41df0f5d63e03cd49c841ab4ebe105a93fca18c2e12ddeed3d` |

## Scientific State

- Forward-citation coverage is unavailable, permanently out of scope for the
  credential-free campaign, and non-blocking. It is neither zero nor complete.
- Fifty identifier-bearing omission rows remain provisional title-context
  risks; they are not fifty equally important missing papers.
- The 195 identifier-free units remain unresolved bibliography units; their
  unique-paper count and relevance are unknown.
- `claim_support_allowed=false` and `ready_for_prose=false` remain authoritative.
- Publication/retraction checking, live topic quality, broader source coverage,
  final claim support, prose promotion, cross-platform support, product
  readiness, push, and release require separate scoped work or a real human
  boundary.

## Decision Table

| Decision | Primary criterion | Veto status | Main uncertainty | Next justified action | Not concluded |
| --- | --- | --- | --- | --- | --- |
| Close the program within recorded local exploratory scope | Exact versioned clean checkout, affected gate, fresh acceptance, installed replay, and terminal review pass | No continuation veto remains | Scientific coverage and publication limitations remain explicit | Preserve this close; open a new scoped plan only for a genuinely new scientific/product objective | Completeness, scientific truth, live topic quality, prose/publication readiness, human usability, product readiness, release readiness |

## Post-Run Red Team

The strongest alternative explanation was hidden dependence on dirty source,
ignored validation roots, or repository build scratch. The exact tree was
reviewed before integration and reproduced after integration in a detached
clean checkout. M23 generated its own M22 replay root, installed commands ran
outside the checkout, the installed replay used the wheel environment, and the
wheel-embedded M23 module matched source bytes.

The weakest evidence is scientific coverage rather than engineering validity.
Those open limitations are preserved above and do not become completion claims.

## Review And Boundary

Claude export remained unavailable under the environment's external-data
policy. It was not retried or routed around. Fresh Codex fallback Review Round
4 found no material defect and returned `AGREE`. The review is advisory; the
local evidence contract, not reviewer availability, supports this close.

The proposed completed-state documentation patch then received the final
allowed material Review Round 5 and returned `REVISE` on three documentation
contradictions: historical `_r7` wording in the authoritative outcome, stale
current-state labels for retired provider/human gates, and an inaccurate reset-
memo description of the selected cited TeX evidence. All three findings were
patched. The five-round cap is exhausted; post-repair `git diff --check`, stale-
state searches, completed-state documentation replay, exact TeX-boundary
inspection, and focused documentation/capability tests pass. No sixth review is
invented.

No push or release was performed or authorized by this close.
