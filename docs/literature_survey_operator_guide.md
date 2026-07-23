# Literature Survey Operator Guide

The active workflow is a local, auditable evidence workflow. It preserves
mission identity, source and omission limitations, and concise qualitative
assessments. It does not automatically produce a complete or publication-ready
survey.

## Choose The Input Mode

Topic-only mode preserves an empty original seed list:

```bash
ra survey run-public-source-workflow \
  --topic "Neural Optimal Transport" \
  --out /tmp/ra-survey-topic
```

The first run should return `status=blocked_at_gate` with
`next_action.action_id=confirm_public_discovery`. The confirmation covers only
the active credential-free arXiv scope. It does not authorize credentials,
private or paid sources, PDF fallback, unbounded crawling, claim promotion, or
public release.

The installed default uses a bounded generic topic-bootstrap adapter after
confirmation. It may still close with `terminal_blocked_bootstrap_unavailable`
when the provider is unavailable, the response is invalid, or the configured
scope cannot run. That is an honest provider/capability stop, not evidence that
the topic has no literature.

Topic bootstrap output is a candidate nomination, not a verified seed claim.
Read the strategy/profile, query-layer consumption, identity duplicates and
conflicts, capped frontiers, citation/venue priority signals, and
open-access-location fields before choosing sources for inspection. The
generic profile is topic-neutral; specialized profiles are explicit regression
strategies and must not become hidden topic assumptions.

For a standalone multi-provider seed-candidate queue, use:

```bash
ra survey seed-papers \
  --topic "Particle filtering for nonlinear state-space models" \
  --out /tmp/ra-seed-papers \
  --confirm-public-discovery
```

The command records `provider_bundle.json`, `provider_observations.json`,
`seed_report.json`, and `seed_manifest.json`. It queries OpenAlex, Crossref,
and Semantic Scholar with bounded exact-host HTTPS requests. Provider-local
citation ranks are retained separately; counts are never added across
providers. DOI/arXiv/OpenAlex matches are fused, while title/author/year
conflicts remain `BLOCKED_IDENTITY_CONFLICT`. `not_available` and `empty` are
different outcomes, and capped routes remain explicit coverage gaps.

`SELECTED_SEED_CANDIDATE` means "queue this identity for inspection", not
"this paper is central". Continue by inspecting a lawful primary source,
checking retraction/version status, classifying its scholarly role, and
running backward/forward snowballing. Google Scholar is reported as an
unsupported automated route because it has no supported public API; a manual
export can be reviewed separately but is not part of this command.

For multi-facet topics, pass explicit `--required-facet`, `--alias`,
`--exclude`, and `--scope-note` values. The bounded route planner does not
invent domain synonyms. The report exposes `facet_coverage`, `role_coverage`,
`uncovered_facets`, `uncovered_roles`, and per-candidate `selection_reasons`.
Abstract and concept evidence can make a paraphrased title eligible, but these
remain metadata signals.

Transfer a completed queue with `ra survey continue-seeds --seed-campaign
<campaign> --out <fresh-child>`. The command replay-validates the full parent,
rejects conflicted or quarantined selected rows, writes `seed_handoff.json`,
and starts a fresh explicit-seed mission from exactly the selected IDs. A venue
registry used during selection must be supplied again for replay and handoff.

Manual repeated `--seed` transfer remains possible, but `continue-seeds` is
the provenance-preserving default. The `central-papers` command still performs
its own discovery; it does not consume `seed_report.json` directly.

Explicit-seed mode accepts an exact paper identifier:

```bash
ra survey run-public-source-workflow \
  --topic "Neural Optimal Transport" \
  --seed arxiv:2201.12220v3 \
  --out /tmp/ra-survey-seed \
  --run-safe-local
```

`--run-safe-local` builds the deterministic local evidence skeleton and stops
before public metadata or source transport. Inspect `mission_control.json`,
`next_action.json`, and `offline_skeleton/build_manifest.json`.

## Read The Terminal Correctly

Use the mission plan to see the whole workflow without opening each artifact:

```bash
ra survey mission-plan --mission-root /path/to/mission
```

It reports the first incomplete stage, required artifacts, next bounded action,
and the boundary that still requires source evidence, human review, or release
approval. It is a refreshable projection, not an authority file.

For a selected topic mission, continue the nominated identities into a fresh
explicit-seed mission:

```bash
ra survey continue-topic \
  --mission-root /path/to/selected-topic-mission \
  --out /path/to/fresh-child-mission
```

The child records the parent mission, bootstrap request/set/manifest hashes,
and exact effective seed list in `topic_handoff.json`. Parent and child roots
must be disjoint. The handoff transfers nominated identities only; it does not
transfer source availability, technical support, human review, or release
approval.

After source inspection and snowball review, write a canonical topic contract
and centrality evidence bundle, then assess them locally:

```bash
ra survey assess-centrality \
  --topic-contract /path/to/topic_contract.json \
  --evidence /path/to/centrality_evidence.json \
  --out /path/to/mission/centrality
ra survey mission-plan --mission-root /path/to/mission
```

Use the mission-local `centrality/` path when the assessment should appear in
the mission plan. The assessment command performs no discovery, download,
parsing, source-safety check, or human review. It evaluates supplied checked
evidence and returns `VALIDATED_CENTRAL`, `VALIDATED_RELEVANT`, `PERIPHERAL`,
`REJECTED_OFF_TOPIC`, `BLOCKED`, or `QUARANTINED`. A citation count, venue
metric, title match, metadata rank, or available download cannot promote a
paper. A source-blocked paper remains blocked; unavailable forward coverage is
not converted to zero.

To construct and assess these artifacts in one bounded campaign, use:

```bash
ra survey central-papers \
  --topic "Neural optimal transport" \
  --out /tmp/ra-central-papers \
  --confirm-public-discovery
```

Inspect `campaign_report.json` first, then the six `ledgers/*.json` files and
`centrality_evidence.json`. A source-blocked role is an unverified hypothesis
from inspected citation context and title metadata; it may keep a candidate
visible as `BLOCKED` but cannot promote it. Citation and venue metadata remain
prioritization signals only.

- `blocked_at_gate` means the next boundary is explicit and no false progress
  was claimed.
- `terminal_blocked_bootstrap_unavailable` means the bounded public topic
  provider or its configured capability was unavailable; it does not mean
  that live topic selection is absent or that the topic has no literature.
- `ASSESSED_TERMINAL_WITHIN_RECORDED_SCOPE` is an M22 validation state. It
  means the recorded source, omission, and qualitative evidence can be replayed
  coherently. It does not mean truth, completeness, reviewed prose, or expert
  consensus.
- A source-format gap means technical text was not inspected. Metadata or title
  context cannot replace it.
- Forward coverage `unavailable_out_of_scope` is a visible non-blocking
  limitation, not zero citations.

## Write A Qualitative Assessment

Use `ra survey qualitative-assessment` to record:

- one bounded summary;
- merits grounded in inspected evidence;
- concerns about assumptions, scope, failure modes, or overstatement;
- unresolved uncertainties;
- exact evidence paths and line/anchor identifiers; and
- the smallest next action.

Every assessment is written with `claim_support_allowed=false` and
`ready_for_prose=false`. Corrections are ordinary research edits: update the
assessment visibly, retain the evidence reference and reasoning, and rerun the
focused validation. No identity ceremony or approval token is required for a
local correction.

## Resume And Recovery

Resume only with the same topic, seed list, output root, and active discovery
budget:

```bash
ra survey run-public-source-workflow \
  --topic "Neural Optimal Transport" \
  --seed arxiv:2201.12220v3 \
  --out /tmp/ra-survey-seed \
  --run-safe-local \
  --resume
```

The state manager validates `GENESIS`, `CURRENT`, generation manifests,
artifact hashes, and mission identity before continuing. If the root is stale,
foreign, corrupt, or belongs to a historical provider budget, do not edit its
state files. Preserve it and start a fresh versioned root under the active
arXiv-only contract.

## Current Scientific Boundaries

- Forward-citation coverage is bounded and provider-dependent, not complete.
- Fifty identifier-bearing omission risks remain source-uninspected.
- The 195 identifier-free bibliography units do not establish 195 unique
  important papers.
- Official code and publication/retraction status are not checked for all
  assessed papers.
- Five omission-frontier sources have scoped technical inspections; title-only
  grouping for the remaining rows is provisional.
- No method ranking is statistically or scientifically established.
- The topic-input central-paper benchmark covers three reviewed topics. It does
  not establish universal recall, literature completeness, expert semantic
  judgment, or comprehensive source safety for a new topic.

## Privacy And External Actions

Keep paper bodies, private notes, datasets, credentials, browser state, and
`local_research/` out of support bundles. The local operator commands above do
not authorize network dispatch, credential access, PDF fallback, Git push,
release, or public messaging. Request explicit human approval at the actual
external or irreversible boundary.
## Drafting a bounded scholarly document scaffold

## Run A Topic-To-Survey Candidate

For a generic offline replay or a bounded confirmed public campaign, use the
single topic command:

```bash
ra survey literature-review \
  --topic "Particle filtering for nonlinear state-space models" \
  --out /tmp/particle-filtering-survey \
  --confirm-public-discovery \
  --dynaremcp-command dynaremcp
```

For deterministic local acceptance, replace discovery with a raw observation
bundle:

```bash
ra survey literature-review \
  --topic "Neural optimal transport" \
  --out /tmp/neural-transport-survey \
  --observation-bundle tests/fixtures/central_papers_e2e/neural_optimal_transport/observations.json \
  --dynaremcp-command dynaremcp
```

The command writes `central_papers/`, `document_projection/`, and `document/`
under one append-only campaign root. It resumes only after validating the
topic, campaign, projection, and final artifact hashes:

```bash
ra survey literature-review \
  --topic "Neural optimal transport" \
  --out /tmp/neural-transport-survey \
  --observation-bundle tests/fixtures/central_papers_e2e/neural_optimal_transport/observations.json \
  --resume
```

The current topic path produces `source_attributed_evidence_survey`. This is a
real source-bound candidate, not a claim that the checked sources are true or
that the literature is complete. Open competitor, foundational, source-safety,
and snowball risks are rendered in the limitations section and retained in the
six ledgers. A `reviewed_survey_candidate_synthesized` status requires a
separate hostile-review-ready reviewed final packet projection.

After source inspection, claim review, source-safety review, omission review,
and hostile review have produced an explicit document evidence bundle, create
an argument-first LaTeX scaffold with:

```bash
ra survey draft-document \
  --evidence /path/to/document_evidence.json \
  --contract /path/to/document_contract.json \
  --out /path/to/fresh-document-run
```

The evidence bundle is deliberately explicit. Every allowed body claim must
use `PRIMARY_TECHNICAL_SUPPORT`, identify an available and `checked_clear`
paper, and cite at least one anchor whose permitted use is
`technical_claim_support`. Metadata, citation counts, venue indicators,
quarantined sources, and unchecked source text cannot support body claims.

To request optional DynareMCP structure and exact consistency diagnostics:

```bash
ra survey draft-document \
  --evidence /path/to/document_evidence.json \
  --contract /path/to/document_contract.json \
  --out /path/to/fresh-document-run \
  --dynaremcp-command dynaremcp
```

DynareMCP is an external optional utility. ResearchAssistant owns the argument,
source text, run state, and final interpretation. A missing provider produces
`external_document_qa_not_run`; it does not prevent scaffold creation and is
not reported as a QA pass.

The current writer is deterministic and authority-aware. A central-paper
projection produces `source_attributed_evidence_survey` only when at least two
topic-relevant inspected papers are available; thinner runs return
`insufficient_survey_evidence`. A hostile-review-passed packet can produce
`reviewed_survey_candidate_synthesized`. These statuses do not establish
literature completeness, scientific correctness, semantic PDF review,
publication readiness, or autonomous expert authorship. Use a fresh output
directory for every new run; prior runs are never overwritten.
