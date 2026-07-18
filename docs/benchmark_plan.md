# Benchmark Corpus Plan

## Goal

This benchmark corpus supports a larger product goal:

```text
ra survey build --topic "<topic>" --seed "<paper>" --out <packet-dir>
```

The product goal is to let another agent or user perform the literature-survey
evidence workflow in an easy, preferably one-command way:

```text
topic + seed paper -> backward lineage -> forward citations
-> adjacent clusters -> source/download status -> paper classifications
-> citation map -> survey-ready evidence packet
```

The benchmark corpus is the calibration and regression harness for that command.
It is not the mission by itself.

The corpus has two jobs:

1. stabilize parser and metadata behavior so development stops depending on
   one-off manual debugging;
2. measure whether the tool actually helps an agent start from a topic, find
   papers, acquire reviewable sources, inspect technical evidence, and write a
   grounded literature survey.

The second job is the new priority. Parser quality is necessary, but it is only
one component of the agent workflow. A benchmark that only scores title,
authors, abstract, and section headings can pass while Codex, Claude Code, or
Copilot still produce mediocre literature surveys.

The target user story for the second job is:

> Given a topic and one seed paper, for example "write a literature survey for
> an idea in Neural Optimal Transport starting from this paper", the tool
> should find the major works that led to the seed, major works that cite it,
> related adjacent papers, downloadable sources/PDFs, and evidence summaries;
> then it should produce a citation map and survey-ready packet for an agent to
> write from.

The benchmark should therefore reward the behavior that `ra survey build` must
eventually provide: production of a citation map and evidence packet, not
merely a prose answer.

## Evidence Contract

Question: Given a research topic, does `research-assistant` improve an agent's
ability to produce a defensible literature survey with checked paper coverage,
local source support, and claim-level evidence?

Baseline:
- the current parser benchmark over synthetic PDF fixtures;
- a generic agent using normal web search and ad hoc notes;
- the same agent using `research-assistant` CLI/MCP surfaces.

Primary promotion criteria:
- the agent retrieves the required seed and competitor papers for the task;
- the workflow produces a citation map with lineage, forward citations, and
  adjacent-paper clusters;
- papers selected into the citation map have explicit download/source status;
- generated claims in the survey are mapped to checked source anchors or marked
  unsupported;
- omitted important papers are recorded with explicit reasons;
- unsafe or unsupported conclusions are abstained from rather than asserted.

Veto diagnostics:
- a survey claim cites only title, abstract, citation count, or venue prestige
  for a technical statement;
- the citation map has no backward or forward snowball layer when those layers
  are available in the fixture or metadata source;
- the workflow marks generated/parser-derived material as approved technical
  audit without review;
- the benchmark task can pass without downloading, locating, or inspecting any
  full text/source;
- a private or live-network artifact is committed when the tier requires
  sanitized metadata only.

Explanatory diagnostics:
- parser title/author/section scores;
- runtime and tool-call count;
- number of candidate papers;
- number of source-extraction failures;
- survey readability scores or LLM-judge preferences.

What will not be concluded:
- a passing benchmark does not prove mathematical correctness of any paper;
- a passing live arXiv tier does not prove broad web-search coverage;
- a good parser score does not prove literature-survey usefulness;
- a good survey draft does not approve the local workspace for release.

Artifacts:
- deterministic benchmark reports under `local_research/benchmarks/` or test
  output directories;
- citation-map JSON and Graphviz/HTML export under benchmark output
  directories;
- survey-ready packet containing candidate, source, snowball, omission, and
  claim ledgers;
- sanitized release evidence in docs only when no private source text, raw PDF,
  grant file, audit log, or local private path is included.

## Benchmark Families

### 1. Parser And Metadata Benchmarks

Purpose: stabilize extraction from known documents.

Current coverage:
- synthetic transport paper with compiled PDF fixture;
- synthetic long-title/subtitle paper with compiled PDF fixture;
- synthetic author-footnote paper with compiled PDF fixture;
- parser scoring harness that preserves expected-record-only rows when PDFs are
  absent and scores parser outputs when PDFs are present.

Expected fields:
- title;
- authors;
- year;
- abstract;
- section headings;
- equations when source-derived ground truth is available;
- theorem-like blocks when source-derived ground truth is available;
- bibliography/citation keys when source-derived ground truth is available.

Gate status: CI-friendly smoke only. This family is not enough to claim survey
usefulness.

### 2. Discovery And Candidate Ranking Benchmarks

Purpose: measure whether topic queries produce a reviewable candidate set
without drowning the agent in noise.

Fixtures should include:
- a topic prompt;
- mocked Semantic Scholar/OpenAlex/arXiv query responses;
- expected included papers;
- seeded false positives with plausible titles;
- seeded duplicates with DOI/arXiv/title variants;
- expected exclusion reasons.

Example topics:
- `transport maps HMC`;
- `normalizing flows for probabilistic inference`;
- `differentiable state-space models`;
- `particle filters for nonlinear macroeconomic models`;
- `Nelson-Siegel curvature identification`;
- `mixed-frequency DSGE estimation`.

Candidate ledger schema:

```json
{
  "schema_version": "ra-surveybench-candidate-ledger-v1",
  "task_id": "transport_hmc_survey_v1",
  "query": "transport maps HMC",
  "candidate_count": 10,
  "included": [
    {
      "paper_key": "neutra_hmc",
      "title": "NeuTra-lizing Bad Geometry in Hamiltonian Monte Carlo Using Neural Transport",
      "reason": "direct method seed",
      "source": "fixture_semantic_scholar"
    }
  ],
  "excluded": [
    {
      "paper_key": "transport_maps_unrelated_pde",
      "reason": "topic false positive"
    }
  ],
  "duplicates": [
    {
      "canonical_key": "paper_a",
      "duplicate_keys": ["paper_a_openalex", "paper_a_semantic_scholar"],
      "match_reason": "doi"
    }
  ]
}
```

Primary metrics:
- required-seed recall;
- false-positive rate in top K;
- duplicate-detection recall;
- exclusion-reason accuracy.

Veto:
- top-ranked candidates omit a known direct seed when it is present in the
  fixture response;
- duplicate records are silently treated as independent papers.

### 3. Source Acquisition And Reviewability Benchmarks

Purpose: measure whether candidates become local review material with explicit
source status.

Fixtures should cover:
- arXiv source available;
- arXiv PDF available but source unavailable;
- DOI/metadata available but full text blocked;
- malformed PDF or parser failure;
- duplicate candidate already present in the workspace.

Source support ledger schema:

```json
{
  "schema_version": "ra-surveybench-source-support-v1",
  "task_id": "transport_hmc_survey_v1",
  "papers": [
    {
      "paper_key": "neutra_hmc",
      "local_record_id": "paper_example",
      "source_status": "available",
      "primary_source_type": "arxiv_latex",
      "checked_anchors": [
        {"kind": "section", "label": "sec:method"},
        {"kind": "equation", "label": "eq:transport_target"}
      ],
      "allowed_claims": ["method description"],
      "forbidden_claims": ["empirical dominance without inspected experiments"]
    }
  ]
}
```

Primary metrics:
- source-status accuracy;
- full-text/source acquisition success where fixture policy permits it;
- no-overwrite and duplicate policy correctness;
- anchor extraction recall for labels, equations, sections, theorem-like blocks,
  and citations.

Veto:
- blocked or unavailable full text is treated as inspected source;
- parser-derived output is promoted to accepted technical audit without review;
- a download/intake path writes outside the benchmark workspace.

### 4. Snowballing And Omission-Risk Benchmarks

Purpose: test whether the agent uses references and citations rather than only
the initial query result list.

Each task should provide:
- seed papers;
- expected backward references from related-work sections or `.bib` files;
- expected forward-citation candidates from mocked metadata;
- paper classifications: foundational, direct method, competitor,
  survey/tutorial, implementation/software, empirical example, background,
  peripheral, superseded, source-blocked, retracted/quarantined;
- omission risks with severity.

Omission-risk ledger schema:

```json
{
  "schema_version": "ra-surveybench-omission-risk-v1",
  "task_id": "transport_hmc_survey_v1",
  "risks": [
    {
      "paper_key": "normalizing_flows_review",
      "risk": "survey/tutorial omitted",
      "severity": "medium",
      "expected_action": "include as background or explain exclusion"
    }
  ]
}
```

Primary metrics:
- backward-snowball recall;
- forward-snowball recall;
- classification accuracy;
- high-severity omission risk recall.

Veto:
- the final survey ignores a high-severity direct competitor that the fixture
  made discoverable;
- a retracted/quarantined source is used without a warning.

### 5. Citation Map Automation Benchmarks

Purpose: test the product behavior that users actually want before survey
writing: seed-to-map automation.

A citation map task begins with:
- one topic string;
- one seed paper identifier, DOI, arXiv ID, title, or local paper ID;
- a bounded budget for candidate expansion;
- allowed metadata sources;
- allowed download/source-intake modes.

The expected output is a graph, not a paragraph. The graph should let an agent
see:
- which papers led to the seed;
- which papers cite the seed and related papers;
- which adjacent clusters matter;
- which papers are surveys/tutorials, direct methods, competitors,
  implementations, empirical examples, or background;
- which papers have local full text/source available;
- which claims or survey sections each paper can support.

Citation-map schema:

```json
{
  "schema_version": "ra-surveybench-citation-map-v1",
  "task_id": "neural_ot_seed_survey_v1",
  "topic": "Neural Optimal Transport for generative modeling and inference",
  "seed_papers": ["seed_neural_ot"],
  "expansion_policy": {
    "backward_depth": 1,
    "forward_depth": 1,
    "adjacent_query_count": 3,
    "max_nodes": 40,
    "max_downloads": 20
  },
  "nodes": [
    {
      "paper_key": "seed_neural_ot",
      "title": "Seed Neural Optimal Transport Paper",
      "year": 2021,
      "roles": ["seed", "direct_method"],
      "cluster": "neural_optimal_transport",
      "local_source_status": "available",
      "download_status": "downloaded",
      "review_status": "requires_human_review",
      "survey_relevance": "central"
    },
    {
      "paper_key": "benamou_brenier",
      "title": "A Computational Fluid Mechanics Solution to the Monge-Kantorovich Mass Transfer Problem",
      "year": 2000,
      "roles": ["foundational"],
      "cluster": "classical_optimal_transport",
      "local_source_status": "metadata_only",
      "download_status": "not_attempted",
      "survey_relevance": "lineage"
    }
  ],
  "edges": [
    {
      "source": "seed_neural_ot",
      "target": "benamou_brenier",
      "edge_type": "cites",
      "evidence": "seed bibliography",
      "confidence": "fixture_ground_truth"
    },
    {
      "source": "followup_neural_ot",
      "target": "seed_neural_ot",
      "edge_type": "cites",
      "evidence": "forward citation metadata",
      "confidence": "fixture_ground_truth"
    },
    {
      "source": "seed_neural_ot",
      "target": "normalizing_flows_review",
      "edge_type": "adjacent_method",
      "evidence": "topic expansion",
      "confidence": "requires_review"
    }
  ],
  "clusters": [
    {
      "cluster_id": "classical_optimal_transport",
      "label": "Classical optimal transport and dynamic formulations",
      "node_keys": ["benamou_brenier"],
      "survey_section_hint": "mathematical lineage"
    }
  ],
  "survey_packet_paths": {
    "candidate_ledger": "candidate_ledger.json",
    "source_support": "source_support.json",
    "claim_support": "claim_support.json",
    "omission_risk": "omission_risk.json"
  }
}
```

Required map layers:
- seed node;
- backward lineage from bibliography/references;
- forward citation layer from citing-work metadata;
- adjacent-method layer from topic expansion and related-paper queries;
- source/download status layer;
- classification layer;
- omission-risk layer.

Primary metrics:
- seed identity accuracy;
- backward-lineage recall for required foundational/direct predecessor papers;
- forward-citation recall for required major citing works;
- adjacent-cluster recall;
- node classification accuracy;
- edge-type accuracy;
- source/download status accuracy;
- graph export completeness.

Veto:
- no citation-map artifact is produced;
- the map contains only a flat search-result list with no typed edges;
- the map omits a required lineage or major citing paper present in fixtures;
- downloaded/source-blocked papers have no status recorded;
- adjacent papers are included without a cluster or relevance reason.

### 6. Claim-Support And Survey Benchmarks

Purpose: test the hard part: can the agent write a useful survey while keeping
claims grounded?

Each task should define:
- required survey claims;
- forbidden claims;
- expected anchor types for each technical claim;
- allowed source gaps;
- expected caveats.

Claim-support ledger schema:

```json
{
  "schema_version": "ra-surveybench-claim-support-v1",
  "task_id": "transport_hmc_survey_v1",
  "claims": [
    {
      "claim_id": "claim_transport_reparameterizes_hmc",
      "claim": "Neural transport methods reparameterize the target geometry before HMC.",
      "support_class": "primary_technical_support",
      "paper_keys": ["neutra_hmc"],
      "anchors": [
        {"paper_key": "neutra_hmc", "kind": "section", "label": "sec:method"}
      ],
      "status": "supported"
    },
    {
      "claim_id": "claim_best_for_dsge",
      "claim": "The method is the best available sampler for DSGE posteriors.",
      "support_class": "unsupported",
      "paper_keys": [],
      "anchors": [],
      "status": "forbidden"
    }
  ]
}
```

Survey output requirements:
- concise field taxonomy;
- direct method comparison table;
- source-support caveats;
- omission-risk paragraph;
- claim-support appendix or linked ledger;
- explicit `what_is_not_concluded` section.

Primary metrics:
- supported-claim precision;
- required-claim recall;
- forbidden-claim avoidance;
- anchor correctness;
- caveat recall;
- survey structure completeness.

Veto:
- any forbidden claim appears as a conclusion;
- any technical claim lacks a checked anchor or explicit source-gap label;
- the survey cites papers that are not present in the candidate/source ledgers.
- the survey makes a historical-lineage or influence claim that is not backed
  by the citation map.

### 7. Offline Binding And Interface Benchmarks

Purpose: measure whether the tool surface is usable by an agent-like workflow
without requiring a live Codex, Claude Code, Copilot, or other paid/runtime
subject launch.

Run modes:
- CLI-scripted: a deterministic local runner may call `ra` commands and inspect
  files;
- replay-worker: a bounded local runner consumes replayed endpoint responses and
  must emit the required ledgers in the correct order;
- MCP-read-only simulation: local scripts or tests exercise exposed MCP tools
  against a prebuilt workspace;
- web-search baseline simulation: a fixture baseline omits
  `research-assistant`-specific helper outputs and is scored on the same packet
  schema.

Observed metrics:
- task completion status;
- tool-call count;
- shell-command count;
- failed or confusing tool calls;
- manual intervention points still required by the scripted workflow;
- elapsed time;
- whether the citation map is generated before survey prose;
- whether expected ledgers are produced;
- whether final survey artifacts satisfy claim-support gates.

Veto:
- a mode requires undocumented maintainer knowledge to complete the task;
- the MCP simulation cannot discover the next safe action from tool
  descriptions or status payloads;
- the tool returns unstructured prose where a benchmark artifact requires JSON;
- the benchmark requires a live model subject or runtime credential to pass.

## Corpus Tiers

### Tier A: Offline Synthetic CI Corpus

Purpose: fast, deterministic, no network, no private files.

Contents:
- current synthetic PDF/LaTeX parser fixtures;
- mocked discovery API payloads;
- synthetic `.bib` and related-work sections with seeded missing references;
- seeded false positives and duplicate records;
- expected citation-map nodes, edges, and clusters;
- expected candidate/source/claim/omission ledgers.

Gate:
- run in normal tests;
- no live network;
- no generated private files;
- every task has machine-checkable expected outputs.

### Tier A2: Online-Replay CI Corpus

Purpose: simulate online literature-survey work without live network
instability.

This tier addresses the process:

`topic + seed paper -> backward lineage -> forward citations -> adjacent clusters -> downloads/source status -> paper classifications -> citation map -> survey-ready evidence packet`

Design:
- the agent sees only replayed online-like endpoint calls;
- the scorer sees separate hidden gold through evaluator-only configuration;
- each replay call appends a trusted event log with concrete budget counters;
- every scored field must be recoverable from an agent-visible evidence
  channel or explicitly marked `insufficient_evidence`/out of scope.

Current implementation:
- task schema: `ra-surveybench-online-replay-task-v1`;
- event-log schema: `ra-surveybench-online-replay-event-log-v1`;
- session manifest schema: `ra-surveybench-online-replay-session-v1`;
- score report schema: `ra-surveybench-online-replay-score-report-v1`;
- CLI endpoints:
  - `ra surveybench replay-call`;
  - `ra surveybench replay-audit`;
  - `ra surveybench replay-score`.

Current fixture:
- `tests/fixtures/surveybench/online_replay/neural_ot_seed_replay/`;
- seed: `arxiv:2201.12220v3`;
- surfaces: search, paper lookup, references, citations, adjacent candidates,
  download status, source status, source anchors, evidence context;
- seeded complications: duplicate metadata, noisy adjacent results, simulated
  Semantic Scholar rate limit, sparse metadata, source-blocked statuses.

Gate:
- no live network;
- no raw PDFs or private source text;
- agent-facing task files must not expose expected outputs, hidden-gold paths,
  answer keys, or scorer-only endpoints;
- scoring must reject missing event logs, untrusted event logs, budget blocks,
  missing required calls, prose-only submissions, missing packet files,
  unsupported or forbidden claims, and actual/gold path overlap;
- evaluator example outputs must not be available to benchmarked agents in
  trials with broad filesystem access.

What this tier does not prove:
- real web coverage;
- Neural OT survey completeness;
- scientific priority or mathematical correctness;
- adversarial anti-cheat;
- production download reliability.

### Tier B: Public arXiv Source/PDF Corpus

Purpose: realistic source extraction with public papers.

Candidate starting topics:
- Neural Optimal Transport and neural transport maps;
- transport maps and HMC;
- normalizing flows for inference;
- differentiable state-space models;
- tensor-train filtering or sequential state/parameter learning;
- particle filters and differentiable resampling.

Rules:
- store only allowed public fixture metadata in git;
- fetch source/PDF during approved validation or cache sanitized expected
  metadata;
- record exact arXiv IDs, versions, source status, and checksum for live runs;
- never treat the arXiv tier as proof of broad web coverage.

Gate:
- release evidence, not always CI;
- failures are classified as source unavailable, parser failure, metadata
  failure, or benchmark harness failure.

### Tier C: Local Sanitized Research Corpus

Purpose: reflect real local use without committing private papers or outputs.

Candidate sources on this machine:
- `latex/CIP_monograph` chapters and bibliography;
- `MacroFinance` docs/plans and tests for HMC, Kalman, AFNS, and
  identification tasks;
- `BayesFilter` docs/plans, benchmark scripts, and third-party audit notes;
- local DSGE PDF folders, recorded only through sanitized manifests.

Rules:
- commit only manifests, task definitions, and redacted expected ledgers;
- never commit private PDFs, extracted text, raw source archives, local paths
  beyond approved generic placeholders, or agent transcripts containing private
  material;
- use this tier for colleague/release evidence, not routine unit tests.

Gate:
- manual or scripted validation with a private manifest;
- report must distinguish "not run", "blocked by privacy", "source blocked",
  and "failed".

## Task Definition Schema

Each SurveyBench task should be a JSON file:

```json
{
  "schema_version": "ra-surveybench-task-v1",
  "task_id": "neural_ot_seed_survey_v1",
  "topic": "Neural Optimal Transport for generative modeling and inference",
  "seed_papers": [
    {
      "paper_key": "seed_neural_ot",
      "identifier": "arxiv-or-doi-or-title",
      "role": "seed"
    }
  ],
  "tier": "offline_synthetic",
  "allowed_sources": ["fixture_discovery", "fixture_pdf", "fixture_latex"],
  "citation_map_policy": {
    "backward_depth": 1,
    "forward_depth": 1,
    "adjacent_query_count": 3,
    "max_nodes": 40,
    "max_downloads": 20
  },
  "required_outputs": [
    "citation_map",
    "candidate_ledger",
    "source_support",
    "backward_snowball",
    "forward_snowball",
    "claim_support",
    "omission_risk",
    "survey"
  ],
  "required_papers": ["seed_neural_ot", "classical_ot_foundation", "major_citing_work"],
  "required_edges": [
    {"source": "seed_neural_ot", "target": "classical_ot_foundation", "edge_type": "cites"},
    {"source": "major_citing_work", "target": "seed_neural_ot", "edge_type": "cites"}
  ],
  "required_clusters": ["classical_optimal_transport", "neural_ot", "adjacent_normalizing_flows"],
  "forbidden_claims": ["this citation map proves scientific priority"],
  "vetoes": ["missing_citation_map", "unsupported_technical_claim", "missing_direct_seed"],
  "timeouts": {"offline_seconds": 60, "simulated_subject_seconds": 900}
}
```

Expected-output files should live next to the task file for offline tiers. Live
or private tiers should provide expected redacted summaries and a manifest path
rather than full source material.

## Scoring Summary

Report top-level fields:

```json
{
  "schema_version": "ra-surveybench-report-v1",
  "task_id": "neural_ot_seed_survey_v1",
  "status": "passed",
  "primary_scores": {
    "required_seed_recall": 1.0,
    "top_k_false_positive_rate": 0.1,
    "citation_map_node_recall": 1.0,
    "citation_map_edge_recall": 1.0,
    "adjacent_cluster_recall": 0.8,
    "source_status_accuracy": 1.0,
    "anchor_recall": 0.8,
    "supported_claim_precision": 1.0,
    "high_severity_omission_recall": 1.0
  },
  "vetoes": [],
  "explanatory": {
    "parser_title_score": 1.0,
    "tool_call_count": 18,
    "elapsed_seconds": 42.5
  }
}
```

Initial pass thresholds:
- required-seed recall: 1.0 for offline tasks;
- citation-map node recall: 1.0 for required seed, lineage, and major citing
  nodes in offline tasks;
- citation-map edge recall: 1.0 for required typed edges in offline tasks;
- adjacent-cluster recall: at least 0.8 once fixtures are stable;
- supported-claim precision: 1.0;
- forbidden-claim count: 0;
- high-severity omission-risk recall: 1.0;
- source-status accuracy: at least 0.9;
- top-k false-positive rate: explanatory at first, then gate once fixtures are
  stable.

Any veto makes the task fail even if numeric scores look good.

## Relationship To MathDevMCP

MathDevMCP is a useful model because its tool matrix names the problem, the v1
tools, later tools, and success metric. `research-assistant` should adopt the
same discipline:

| Problem | V1 tools | Later tools | Success metric |
| --- | --- | --- | --- |
| Topic-to-candidate discovery | `discover`, `arxiv-batch discover`, fixture discovery runner | MCP query discovery, multi-source ranker | required seed recall and low top-k noise |
| Source reviewability | `ingest`, `source-fetch`, `parse-pdf`, `source-show` | batch source/PDF MCP tools with grants | source-status accuracy and anchor recall |
| Citation-map automation | `citation-neighborhood`, source citations/bibliography, graph cache | `citation-map build`, graph export, MCP citation-map tools | required node/edge recall and typed cluster coverage |
| Snowballing | `citation-neighborhood`, source citations/bibliography | backward/forward snowball ledgers | high-severity omission-risk recall |
| Claim grounding | `audit-note`, `source-section`, `source-equation`, `source-theorem` | real claim-support extractor | supported-claim precision and forbidden-claim avoidance |
| Workflow binding | `ra survey build`, MCP tools, benchmark runner | scripted offline binding harness | completion without undocumented maintainer hints |

## Implementation Roadmap

### Phase 1: Offline SurveyBench Skeleton

Add:
- `tests/fixtures/surveybench/tasks/neural_ot_seed_synthetic.task.json`;
- fixture discovery/citation payloads with one seed, predecessor papers, major
  citing works, adjacent papers, duplicates, and false positives;
- expected citation map with typed nodes, edges, and clusters;
- expected candidate, source, omission, and claim ledgers linked from the map;
- `tests/scripts/run_survey_benchmark.py`;
- unit tests for schema validation and scoring.

Acceptance:
- benchmark runs without network;
- report emits `ra-surveybench-report-v1`;
- citation-map node/edge scoring catches missing predecessor and major citing
  papers;
- seeded false positive and forbidden claim are caught.

### Phase 2: Source And Claim Anchors

Extend synthetic LaTeX fixtures to include:
- labeled method section;
- labeled equation;
- theorem-like block;
- citation keys;
- a related-work paragraph with one expected omission risk.

Acceptance:
- source anchor recall is scored;
- claim-support ledger can point to labels;
- benchmark fails if a technical claim has no anchor.

### Phase 3: Public arXiv Pilot

Add one public task for Neural Optimal Transport or neural transport maps,
starting from a single public seed paper with a known arXiv ID or DOI. If the
Neural OT seed is not available in arXiv source form, use metadata/PDF status
honestly and keep source inspection limited to available material.

Acceptance:
- exact arXiv IDs and versions are recorded;
- source/PDF availability is reported;
- citation map records backward, forward, and adjacent layers with typed edges;
- run can be marked `not_run`, `blocked`, `narrow`, or `passed`;
- no raw downloaded artifacts are committed.

### Phase 4: Offline Binding Harness

Create a scripted subject packet and deterministic/local runner for an
agent-like workflow without a live model launch:
- task prompt;
- allowed tools;
- required artifacts;
- privacy boundary;
- expected output directory;
- fixed replay inputs or deterministic packet composer behavior.

Acceptance:
- at least one scripted or deterministic harness run is scored against the same
  ledgers;
- the harness is required to produce the citation map before prose survey text;
- report records manual intervention points and failed tool calls;
- failures produce actionable tool/interface gaps without needing a live model
  transport.

### Phase 5: Local Sanitized Research Corpus

Add manifest support for private/local corpora shaped like:
- `latex/CIP_monograph`;
- `MacroFinance`;
- `BayesFilter`;
- DSGE PDF folders.

Acceptance:
- validation can run from an external manifest;
- reports redact private paths and source text;
- benchmark distinguishes privacy-blocked from failed.

## Current Status

Currently present:
- synthetic parser benchmark fixtures;
- parser scoring harness;
- local MCP setup validation;
- grant-bound arXiv source/PDF validation records;
- source extraction for sections, equations, theorem-like blocks, labels,
  citations, bibliography, and macros.
- offline SurveyBench citation-map task schema and synthetic Neural OT fixture;
- citation-map, candidate-ledger, source-support, claim-support, and
  omission-risk scoring;
- CLI command `ra surveybench run`;
- local sanitized manifest validator;
- online-replay Neural OT fixture;
- replay schema, endpoint, budget, event-log, and session-manifest validators;
- replay CLI calls and leakage/interface audit;
- replay scorer with trusted-event-log and gold/actual separation gates;
- agent prompt packet and evaluator-side example output for the online-replay
  task.
- mission-control artifacts for the one-command workflow;
- initial `ra survey build` offline skeleton command that writes the expected
  packet layout without claiming discovery/source/claim completion.

Still missing or intentionally follow-up:
- MCP exposure for the online-replay tier;
- stronger offline binding coverage across CLI, replay-worker, and MCP
  simulation surfaces;
- live capture/calibration runs beyond the replay fixture;
- public arXiv source/PDF benchmark pairs with broader source inspection;
- more domains from MathDevMCP, DSGE/HMC, MacroFinance, LaTeX, and BayesFilter;
- stronger artifact-to-call derivation checks beyond trusted local harness
  provenance.

## Near-Term Recommendation

Do not start by broadening live web search. Start with a small offline
SurveyBench citation-map task that can fail deterministically when the agent:

- misses a known seed paper;
- misses a required predecessor paper;
- misses a required major citing paper;
- produces a flat paper list instead of typed citation-map edges;
- fails to identify adjacent-paper clusters;
- includes a seeded false positive;
- treats a duplicate as new evidence;
- downloads or blocks a paper without recording source/download status;
- writes a technical claim without a source anchor;
- omits a high-severity related paper;
- asserts a forbidden conclusion.

Once that is green, use the same schema for public arXiv and local sanitized
corpus tiers. This keeps iteration honest: every new tool should improve one
measured failure mode rather than merely adding another command.
