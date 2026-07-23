from __future__ import annotations

import argparse

from research_assistant.cli_registration.common import Handler, Subparsers


def register_survey_commands(sub: Subparsers, handler: Handler) -> None:
    """Register evidence-packet, review, and mission survey commands."""
    survey = sub.add_parser('survey', help='Build literature-survey evidence packets')
    survey_sub = survey.add_subparsers(dest='survey_action', required=True)
    survey_build = survey_sub.add_parser(
        'build',
        help='Build a topic+seed survey evidence packet; metadata mode never fetches source/PDF/full text',
        description='Build a topic+seed survey evidence packet. Public metadata mode never fetches source/PDF/full text.',
    )
    survey_build.add_argument('--topic', required=True)
    survey_build.add_argument('--seed', action='append', required=True, help='Seed paper identifier; repeat for multiple seeds')
    survey_build.add_argument('--out', required=True, help='Output directory for the evidence packet')
    survey_build.add_argument(
        '--mode',
        default='offline-skeleton',
        choices=['offline-skeleton', 'offline-replay', 'public-metadata'],
        help='offline-skeleton writes a planning packet; offline-replay uses fixture evidence; public-metadata uses bounded public metadata only',
    )
    survey_build.add_argument('--replay-task', help='Visible replay task JSON for offline-replay mode')
    survey_build.add_argument('--replay-responses-dir', help='Visible replay responses directory for offline-replay mode')
    survey_build.add_argument(
        '--public-metadata-provider',
        action='append',
        choices=['openalex', 'arxiv'],
        help='Public metadata provider for public-metadata mode; repeat to include both OpenAlex and arXiv',
    )
    survey_build.add_argument('--max-records', type=int, default=25, help='Maximum public metadata records; capped at 25')
    survey_build.add_argument('--force', action='store_true')
    survey_build.set_defaults(func=handler)
    survey_anchors = survey_sub.add_parser('anchors', help='Extract checked source-anchor ledgers from local structured source records')
    survey_anchors.add_argument('--paper-id', action='append', required=True, help='Local structured source paper id; repeat for multiple papers')
    survey_anchors.add_argument('--out', required=True, help='Output directory for source-anchor ledgers')
    survey_anchors.add_argument('--topic')
    survey_anchors.add_argument('--max-anchors-per-paper', type=int, default=24)
    survey_anchors.add_argument('--force', action='store_true')
    survey_anchors.set_defaults(func=handler)
    survey_packet = survey_sub.add_parser(
        'packet',
        help='Compose a public-source writer packet from prior-phase ledgers without upgrading blocked claims to prose readiness',
        description='Compose a public-source writer packet from prior-phase ledgers without upgrading blocked claims to prose readiness.',
    )
    survey_packet.add_argument('--topic', required=True)
    survey_packet.add_argument('--out', required=True, help='Output directory for the public-source evidence packet')
    survey_packet.add_argument('--metadata-dir', required=True, help='Directory containing public metadata ledgers')
    survey_packet.add_argument('--source-status-dir', required=True, help='Directory containing Phase 4 source intake status')
    survey_packet.add_argument('--anchor-dir', required=True, help='Directory containing Phase 5 source-anchor ledgers')
    survey_packet.add_argument('--force', action='store_true')
    survey_packet.set_defaults(func=handler)
    survey_coverage = survey_sub.add_parser(
        'coverage-ledgers',
        help='Compose local coverage and snowballing ledgers from existing packet artifacts without live expansion',
        description='Compose backward_snowball.json, forward_snowball.json, citation_venue_metadata.json, paper_classifications.json, and omitted_paper_risks.json from existing local packet artifacts. This does not run live metadata/source expansion and does not claim literature completeness.',
    )
    survey_coverage.add_argument('--topic', required=True)
    survey_coverage.add_argument('--packet-dir', required=True, help='Existing public-source packet directory; command runs without live expansion')
    survey_coverage.add_argument('--out', required=True, help='Output directory for coverage and snowballing ledgers')
    survey_coverage.add_argument('--force', action='store_true')
    survey_coverage.set_defaults(func=handler)
    survey_process = survey_sub.add_parser(
        'process-plan',
        help='Build a bounded source-first survey process plan from a local campaign snapshot',
        description='Build coverage, source-availability, and deterministic next-action reports from a local campaign snapshot. This command does not run network, source, PDF, credential, or human-review actions and does not claim literature completeness.',
    )
    survey_process.add_argument('--snapshot', required=True, help='Local canonical campaign snapshot JSON')
    survey_process.add_argument('--out', required=True, help='Output directory for process-plan artifacts')
    survey_process.add_argument('--force', action='store_true')
    survey_process.set_defaults(func=handler)
    survey_centrality = survey_sub.add_parser(
        'assess-centrality',
        help='Assess local candidate centrality from checked evidence without metadata-score promotion',
        description='Validate a topic contract and local centrality evidence bundle, then write deterministic candidate verdicts. This command performs no network, source, PDF, credential, benchmark-label, or human-review action.',
    )
    survey_centrality.add_argument('--topic-contract', required=True, help='Canonical local topic contract JSON')
    survey_centrality.add_argument('--evidence', required=True, help='Canonical local candidate centrality evidence JSON')
    survey_centrality.add_argument('--out', required=True, help='Output directory for assessment and manifest JSON')
    survey_centrality.add_argument('--force', action='store_true')
    survey_centrality.set_defaults(func=handler)
    survey_mission_plan = survey_sub.add_parser(
        'mission-plan',
        help='Project a read-only product workflow plan from an existing mission root',
        description='Replay the active mission state and write a deterministic workflow plan. This command performs no discovery, download, PDF, credential, review, or claim-promotion action.',
    )
    survey_mission_plan.add_argument('--mission-root', required=True, help='Existing mission root')
    survey_mission_plan.add_argument('--out', help='Mission-local output path; defaults to mission_plan.json')
    survey_mission_plan.set_defaults(func=handler)
    survey_continue = survey_sub.add_parser(
        'continue-topic',
        help='Create an isolated explicit-seed mission from a selected topic bootstrap',
        description='Validate a selected topic bootstrap authority and create a fresh explicit-seed child mission. This performs no provider, source, PDF, credential, claim, or review action.',
    )
    survey_continue.add_argument('--mission-root', required=True, help='Selected topic mission root')
    survey_continue.add_argument('--out', required=True, help='Fresh child mission root')
    survey_continue.set_defaults(func=handler)
    survey_seeds = survey_sub.add_parser(
        'seed-papers',
        help='Find bounded multi-provider seed-paper candidates for a scholarly topic',
        description='Query or replay OpenAlex, Crossref, and Semantic Scholar metadata, reconcile identities, and write a seed-candidate report. Metadata ranks and provider agreement cannot establish topic centrality or paper correctness.',
    )
    survey_seeds.add_argument('--topic', required=True)
    survey_seeds.add_argument('--out', required=True, help='Fresh or replayable seed campaign output directory')
    survey_seeds.add_argument('--confirm-public-discovery', action='store_true', help='Allow bounded public OpenAlex, Crossref, and Semantic Scholar metadata requests')
    survey_seeds.add_argument('--resume', action='store_true', help='Replay and validate an existing completed campaign without provider calls')
    survey_seeds.add_argument('--observation-bundle', help='Local raw provider bundle for offline execution; evaluator labels are forbidden')
    survey_seeds.add_argument('--max-selected', type=int, default=12, help='Maximum selected seed candidates (1-50; default: 12)')
    survey_seeds.add_argument('--required-facet', action='append', help='Explicit required topic facet; repeat as needed')
    survey_seeds.add_argument('--alias', action='append', help='Controlled topic alias or abbreviation; repeat as needed')
    survey_seeds.add_argument('--exclude', action='append', help='Explicit out-of-scope term or phrase; repeat as needed')
    survey_seeds.add_argument('--scope-note', help='Operator-supplied scope note retained in the topic contract')
    survey_seeds.add_argument('--venue-metrics-registry', help='Optional canonical venue-metrics registry; required again on resume')
    survey_seeds.set_defaults(func=handler)
    survey_continue_seeds = survey_sub.add_parser(
        'continue-seeds',
        help='Create an explicit-seed mission from a replay-valid seed campaign',
        description='Replay the complete seed campaign, transfer only resolved selected IDs, and bind parent and child hashes in seed_handoff.json. This performs no live provider call.',
    )
    survey_continue_seeds.add_argument('--seed-campaign', required=True, help='Completed seed-papers campaign root')
    survey_continue_seeds.add_argument('--out', required=True, help='Fresh explicit-seed child mission root')
    survey_continue_seeds.add_argument('--venue-metrics-registry', help='Original registry required for a venue-enriched parent campaign')
    survey_continue_seeds.set_defaults(func=handler)
    survey_central_papers = survey_sub.add_parser(
        'central-papers',
        help='Run a bounded topic-to-central-papers campaign with explicit blockers and nonclaims',
        description='Discover, inspect, snowball, assess, and report central-paper candidates from a topic. Live OpenAlex/arXiv access requires --confirm-public-discovery. Citation and venue metadata remain prioritization signals only.',
    )
    survey_central_papers.add_argument('--topic', required=True)
    survey_central_papers.add_argument('--out', required=True, help='Fresh or resumable campaign output directory')
    survey_central_papers.add_argument('--confirm-public-discovery', action='store_true', help='Allow bounded public OpenAlex metadata and arXiv structured-source requests')
    survey_central_papers.add_argument('--resume', action='store_true', help='Replay or continue the identical topic, budget, and capability without repeating recorded calls')
    survey_central_papers.add_argument('--observation-bundle', help='Local raw observation bundle for offline execution; cannot contain topic-fit, role, or evaluator labels')
    survey_central_papers.set_defaults(func=handler)
    survey_document = survey_sub.add_parser(
        "draft-document",
        help="Build a source-bound LaTeX document scaffold from reviewed evidence",
        description=(
            "Build an argument-first, evidence-bound LaTeX scaffold from an explicit reviewed evidence bundle. "
            "This does not claim prose, literature, scientific, or publication readiness."
        ),
    )
    survey_document.add_argument("--evidence", required=True, help="Reviewed document evidence bundle JSON")
    survey_document.add_argument("--contract", required=True, help="Document contract JSON")
    survey_document.add_argument("--out", required=True, help="Fresh document-run output directory")
    survey_document.add_argument("--dynaremcp-command", help="Optional DynareMCP executable command")
    survey_document.add_argument("--compile-latex", action="store_true", help="Compile the generated LaTeX source when a local tool is available")
    survey_document.set_defaults(func=handler)
    survey_literature_review = survey_sub.add_parser(
        "literature-review",
        help="Run a topic-to-source-attributed survey campaign",
        description=(
            "Discover and inspect central papers, project checked source statements, synthesize a LaTeX survey candidate, "
            "optionally compile it, and optionally run DynareMCP QA. The result preserves open risks and does not claim "
            "literature completeness, scientific correctness, or publication readiness."
        ),
    )
    survey_literature_review.add_argument("--topic", required=True)
    survey_literature_review.add_argument("--out", required=True, help="Fresh or resumable topic-to-survey output root")
    survey_literature_review.add_argument("--confirm-public-discovery", action="store_true", help="Allow bounded public OpenAlex/arXiv discovery and source requests")
    survey_literature_review.add_argument("--observation-bundle", help="Offline raw central-paper observation bundle for replay/testing")
    survey_literature_review.add_argument("--resume", action="store_true", help="Replay or continue the same topic and capability")
    survey_literature_review.add_argument("--dynaremcp-command", help="Optional DynareMCP executable command")
    survey_literature_review.add_argument(
        "--compile-latex",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Compile LaTeX with the local toolchain (default: enabled)",
    )
    survey_literature_review.set_defaults(func=handler)
    survey_reviewed_packet = survey_sub.add_parser(
        'compose-reviewed-final-packet',
        help='Compose the current immutable reviewed packet for hostile review',
        description='Replay the current selected queue, packet, coverage, four reviewed sidecars, merge, and exact claim evidence into one immutable packet. This does not establish prose readiness, literature completeness, or scientific correctness.',
    )
    survey_reviewed_packet.add_argument('--mission-root', required=True, help='Current mission root; external replay authority')
    survey_reviewed_packet.add_argument('--review-queue', required=True, help='Current selected V2 review_queue.json')
    survey_reviewed_packet.add_argument('--packet-dir', required=True, help='Original packet directory recorded by current mission control')
    survey_reviewed_packet.add_argument('--anchor-dir', required=True, help='Anchor directory recorded by current mission control')
    survey_reviewed_packet.add_argument('--local-evidence-root', help='Mission-local evidence root required only for reviewed project-derivation or implementation-evidence claims')
    survey_reviewed_packet.add_argument('--out', required=True, help='Must be <mission-root>/reviewed_final_packet')
    survey_reviewed_packet.add_argument('--force', action='store_true')
    survey_reviewed_packet.set_defaults(func=handler)
    survey_hostile = survey_sub.add_parser(
        'hostile-review',
        help='Gate reviewed-scope prose readiness from one replay-valid reviewed packet',
        description='Replay the immutable reviewed final packet against current external mission authority and write one authoritative hostile result plus a digest-bound readiness view. This does not run live expansion or establish literature completeness, product readiness, or scientific correctness.',
    )
    survey_hostile.add_argument('--reviewed-final-packet', required=True, help='Fixed mission-local reviewed_final_packet.json; raw reviewed_evidence_status.json is not accepted')
    survey_hostile.add_argument('--mission-root', required=True, help='Current mission root; external replay authority')
    survey_hostile.add_argument('--review-queue', required=True, help='Current selected V2 review_queue.json')
    survey_hostile.add_argument('--packet-dir', required=True, help='Original packet directory recorded by current mission control')
    survey_hostile.add_argument('--anchor-dir', required=True, help='Anchor directory recorded by current mission control')
    survey_hostile.add_argument('--local-evidence-root', help='Mission-local evidence root required only for reviewed project-derivation or implementation-evidence claims')
    survey_hostile.add_argument('--out', required=True, help='Output directory for hostile_review_result.json and final_packet_readiness.json')
    survey_hostile.add_argument('--force', action='store_true')
    survey_hostile.set_defaults(func=handler)
    survey_run = survey_sub.add_parser(
        'run-public-source-workflow',
        help='Supervise the public-source survey workflow with one public-discovery confirmation',
        description='Supervise the public-source survey workflow from a topic alone or from topic+seed. Topic-only mode records a mission-bound bootstrap outcome without fabricating a paper seed. --confirm-public-discovery records the durable mission confirmation; it does not allow credentials, private databases, paid model workers, hidden evaluator material, unbounded crawling, claim support from metadata, or final prose readiness.',
    )
    survey_run.add_argument('--topic', required=True)
    survey_run.add_argument('--seed', action='append', default=None, help='Optional seed paper identifier; repeat for multiple seeds. Omission selects topic-only bootstrap mode; an explicit empty value remains invalid.')
    survey_run.add_argument('--out', required=True, help='Output directory for mission_control.json and local orchestration artifacts')
    survey_run.add_argument(
        '--run-safe-local',
        action='store_true',
        help=(
            'Run the bounded typed local supervisor through every currently eligible deterministic stage; '
            'stops before live/API/download, source transport, or human-review actions'
        ),
    )
    survey_run.add_argument('--confirm-public-discovery', action='store_true', help='Record the single mission confirmation for bounded public discovery and run implemented bounded discovery steps such as public metadata')
    survey_run.add_argument('--resume', action='store_true', help='Reuse existing local mission artifacts and discover reviewed sidecars without regenerating review_queue.json or running live/API/download actions')
    survey_run.add_argument('--metadata-dir', help='Existing public metadata ledger directory, if already approved and available')
    survey_run.add_argument('--source-status-dir', help='Existing Phase 4 source intake status directory, if already approved and available')
    survey_run.add_argument('--anchor-dir', help='Existing Phase 5 source-anchor directory, if already available')
    survey_run.add_argument('--packet-dir', help='Existing or intended public-source packet directory')
    survey_run.add_argument('--coverage-dir', help='Existing coverage-ledger directory for local resume discovery')
    survey_run.add_argument('--reviewed-claims-dir', help='Existing reviewed_claims.json sidecar directory for local resume discovery')
    survey_run.add_argument('--reviewed-source-safety-dir', help='Existing reviewed_source_safety.json sidecar directory for local resume discovery')
    survey_run.add_argument('--reviewed-omissions-dir', help='Existing reviewed_omission_risks.json sidecar directory for local resume discovery')
    survey_run.add_argument('--reviewed-workflow-blockers-dir', help='Existing reviewed_workflow_blockers.json sidecar directory for local resume discovery')
    survey_run.add_argument('--reviewed-evidence-dir', help='Existing reviewed_evidence_status.json merge directory for local resume discovery')
    survey_run.add_argument('--local-evidence-root', help='Mission-local root used only to replay reviewed project-derivation or implementation-evidence claims')
    survey_run.add_argument('--venue-metrics-registry', help='Optional canonical local venue-metrics registry for citation/impact-factor prioritization; topic mode only')
    survey_run.add_argument('--force', action='store_true')
    survey_run.set_defaults(func=handler)

    _register_review_imports(survey_sub, handler)


def _register_review_imports(survey_sub: Subparsers, handler: Handler) -> None:
    survey_claim_review = survey_sub.add_parser(
        'import-claim-review',
        help='Validate reviewed claim decisions from review_queue.json without marking prose or source safety ready',
        description='Import reviewed claim decisions from a local review_queue.json sidecar. This validates reviewed anchor-mapped claim rows but does not run live lookup, clear source safety, resolve omissions, or mark final prose ready.',
    )
    survey_claim_review.add_argument('--review-queue', required=True, help='Path to review_queue.json from run-public-source-workflow')
    survey_claim_review.add_argument('--decisions', required=True, help='JSON file containing reviewed claim decisions')
    survey_claim_review.add_argument('--out', required=True, help='Output directory for reviewed_claims.json')
    survey_claim_review.add_argument('--human-attestation-receipt', help='Validated M22 human receipt for a V4 human decision envelope')
    survey_claim_review.add_argument('--force', action='store_true')
    survey_claim_review.set_defaults(func=handler)
    survey_source_safety_review = survey_sub.add_parser(
        'import-source-safety-review',
        help='Validate reviewed source-safety decisions without marking final prose ready',
        description='Import reviewed source-safety decisions from a local review_queue.json sidecar. This validates evidence-bearing source-safety rows but does not run live lookup, resolve omissions, merge claims, or mark final prose ready.',
    )
    survey_source_safety_review.add_argument('--review-queue', required=True, help='Path to review_queue.json from run-public-source-workflow')
    survey_source_safety_review.add_argument('--decisions', required=True, help='JSON file containing reviewed source-safety decisions')
    survey_source_safety_review.add_argument('--out', required=True, help='Output directory for reviewed_source_safety.json')
    survey_source_safety_review.add_argument('--human-attestation-receipt', help='Validated M22 human receipt for a V4 human decision envelope')
    survey_source_safety_review.add_argument('--force', action='store_true')
    survey_source_safety_review.set_defaults(func=handler)
    survey_omission_review = survey_sub.add_parser(
        'import-omission-review',
        help='Validate reviewed omission-risk decisions without claiming literature completeness',
        description='Import reviewed omission-risk decisions from a local review_queue.json sidecar. This validates rationale-bearing omission rows but does not run live lookup, merge claims, clear source safety, claim literature completeness, or mark final prose ready.',
    )
    survey_omission_review.add_argument('--review-queue', required=True, help='Path to review_queue.json from run-public-source-workflow')
    survey_omission_review.add_argument('--decisions', required=True, help='JSON file containing reviewed omission-risk decisions')
    survey_omission_review.add_argument('--out', required=True, help='Output directory for reviewed_omission_risks.json')
    survey_omission_review.add_argument('--force', action='store_true')
    survey_omission_review.set_defaults(func=handler)
    survey_workflow_blocker_review = survey_sub.add_parser(
        'import-workflow-blocker-review',
        help='Validate exact workflow-blocker dispositions without clearing upstream or prose gates',
        description='Import decisions for every current workflow_blocker queue item. Review-resolvable blockers require the exact embedded current evidence scope; upstream-only blockers must remain open. This does not run live lookup or mark final prose ready.',
    )
    survey_workflow_blocker_review.add_argument('--review-queue', required=True, help='Path to the selected review_queue.json')
    survey_workflow_blocker_review.add_argument('--decisions', required=True, help='Bound V2 JSON decision envelope for workflow blockers')
    survey_workflow_blocker_review.add_argument('--out', required=True, help='Output directory for reviewed_workflow_blockers.json')
    survey_workflow_blocker_review.add_argument('--force', action='store_true')
    survey_workflow_blocker_review.set_defaults(func=handler)
    survey_merge_reviewed = survey_sub.add_parser(
        'merge-reviewed-evidence',
        help='Merge reviewed sidecars into exact readiness or blocker status',
        description='Merge exact reviewed claim, source-safety, omission, and workflow-blocker sidecars with selected-queue provenance. This does not run live lookup, emit final prose readiness, or establish product/scientific readiness.',
    )
    survey_merge_reviewed.add_argument('--review-queue', required=True, help='Path to review_queue.json used by all sidecars')
    survey_merge_reviewed.add_argument('--reviewed-claims', required=True, help='Path to reviewed_claims.json')
    survey_merge_reviewed.add_argument('--reviewed-source-safety', required=True, help='Path to reviewed_source_safety.json')
    survey_merge_reviewed.add_argument('--reviewed-omissions', required=True, help='Path to reviewed_omission_risks.json')
    survey_merge_reviewed.add_argument('--reviewed-workflow-blockers', required=True, help='Path to reviewed_workflow_blockers.json')
    survey_merge_reviewed.add_argument('--out', required=True, help='Output directory for reviewed_evidence_status.json')
    survey_merge_reviewed.add_argument('--force', action='store_true')
    survey_merge_reviewed.set_defaults(func=handler)
    survey_prepare_human = survey_sub.add_parser(
        "prepare-human-review",
        help="Prepare an exact non-attesting operator packet for the selected review queue",
        description="Write the exact machine review packet, an explicitly incomplete self-attestation template, and plain-language Markdown/CSV review materials. This performs no review, makes no network call, and cannot mark evidence or prose ready.",
    )
    survey_prepare_human.add_argument("--review-queue", required=True, help="Current selected review_queue.json")
    survey_prepare_human.add_argument("--out", required=True, help="Fresh output directory for the packet and unattested template")
    survey_prepare_human.add_argument("--force", action="store_true")
    survey_prepare_human.set_defaults(func=handler)
    survey_validate_human = survey_sub.add_parser(
        "validate-human-attestation",
        help="Bind a completed human self-attestation to four exact decision files",
        description="Validate a real person's self-attestation, current queue lineage, exact four-type decision coverage, reviewer consistency, privacy/conflict declarations, and file hashes. Decision semantics remain subject to the existing import commands; this is not identity proof or prose readiness.",
    )
    survey_validate_human.add_argument("--review-queue", required=True)
    survey_validate_human.add_argument("--packet", required=True)
    survey_validate_human.add_argument("--attestation", required=True)
    survey_validate_human.add_argument("--claim-decisions", required=True)
    survey_validate_human.add_argument("--source-safety-decisions", required=True)
    survey_validate_human.add_argument("--omission-decisions", required=True)
    survey_validate_human.add_argument("--workflow-blocker-decisions", required=True)
    survey_validate_human.add_argument("--out", required=True)
    survey_validate_human.add_argument("--force", action="store_true")
    survey_validate_human.set_defaults(func=handler)
    survey_render_human = survey_sub.add_parser(
        "render-human-review",
        help="Render plain-language worksheets for an existing exact review packet",
        description="Render reviewer-facing Markdown/CSV materials from the current packet without changing packet JSON, queue lineage, or packet hashes.",
    )
    survey_render_human.add_argument("--packet", required=True, help="Existing human_review_packet.json")
    survey_render_human.add_argument("--out", help="Output directory; defaults to the packet directory")
    survey_render_human.add_argument("--force", action="store_true")
    survey_render_human.set_defaults(func=handler)
    survey_qualitative = survey_sub.add_parser(
        "qualitative-assessment",
        help="Write a concise source-grounded merits/concerns/uncertainties assessment",
        description="Record a bounded qualitative assessment. This is the active M22 scholarly review representation; it never clears provenance, source-safety, claim-support, or prose gates.",
    )
    survey_qualitative.add_argument("--subject-id", required=True)
    survey_qualitative.add_argument("--assessment-type", required=True, choices=["paper", "claim", "omission"])
    survey_qualitative.add_argument("--summary", required=True)
    survey_qualitative.add_argument("--merit", action="append", required=True)
    survey_qualitative.add_argument("--concern", action="append", required=True)
    survey_qualitative.add_argument("--uncertainty", action="append", required=True)
    survey_qualitative.add_argument("--evidence-ref", action="append", required=True)
    survey_qualitative.add_argument("--next-action", required=True)
    survey_qualitative.add_argument("--out", required=True, help="Output JSON assessment path")
    survey_qualitative.add_argument("--force", action="store_true")
    survey_qualitative.set_defaults(func=handler)
