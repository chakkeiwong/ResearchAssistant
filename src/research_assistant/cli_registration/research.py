from __future__ import annotations

from dataclasses import dataclass

from research_assistant.cli_registration.common import Handler, Subparsers


@dataclass(frozen=True, slots=True)
class ResearchHandlers:
    audit_claim: Handler
    audit_note: Handler
    discover: Handler
    download_paper: Handler
    papers_citing: Handler
    papers_cited_by: Handler
    citation_neighborhood: Handler
    citation_graph_build: Handler
    citation_graph_show: Handler
    citation_graph_export: Handler
    graph_node_download_proposal: Handler
    inbox_list: Handler
    inbox_show: Handler
    literature_audit_propose: Handler
    literature_audit_show: Handler
    literature_audit_approve: Handler
    parse_pdf: Handler
    parser_preflight: Handler
    evidence_context: Handler
    source_inspection: SourceInspectionHandlers


def register_research_commands(sub: Subparsers, handlers: ResearchHandlers) -> None:
    """Register audits, discovery, citations, PDF parsing, and source inspection."""
    audit = sub.add_parser('audit-claim')
    audit.add_argument('--claim')
    audit.add_argument('--claim-file')
    audit.add_argument('--papers', nargs='*')
    audit.set_defaults(func=handlers.audit_claim)

    audit_note = sub.add_parser('audit-note')
    audit_note_sub = audit_note.add_subparsers(dest='audit_action', required=True)

    audit_note_show = audit_note_sub.add_parser('show')
    audit_note_show.add_argument('--paper-id', required=True)
    audit_note_show.set_defaults(func=handlers.audit_note)

    audit_note_set = audit_note_sub.add_parser('set')
    audit_note_set.add_argument('--paper-id', required=True)
    audit_note_set.add_argument('--field', required=True)
    audit_note_set.add_argument('--value', required=True)
    audit_note_set.set_defaults(func=handlers.audit_note)

    audit_note_append = audit_note_sub.add_parser('append')
    audit_note_append.add_argument('--paper-id', required=True)
    audit_note_append.add_argument('--field', required=True)
    audit_note_append.add_argument('--value', required=True)
    audit_note_append.set_defaults(func=handlers.audit_note)

    audit_note_remove = audit_note_sub.add_parser('remove')
    audit_note_remove.add_argument('--paper-id', required=True)
    audit_note_remove.add_argument('--field', required=True)
    audit_note_remove.add_argument('--value', required=True)
    audit_note_remove.set_defaults(func=handlers.audit_note)

    audit_note_link_section = audit_note_sub.add_parser('link-section')
    audit_note_link_section.add_argument('--paper-id', required=True)
    audit_note_link_section.add_argument('--label', required=True)
    audit_note_link_section.set_defaults(func=handlers.audit_note)

    audit_note_link_equation = audit_note_sub.add_parser('link-equation')
    audit_note_link_equation.add_argument('--paper-id', required=True)
    audit_note_link_equation.add_argument('--label', required=True)
    audit_note_link_equation.set_defaults(func=handlers.audit_note)

    audit_note_link_theorem = audit_note_sub.add_parser('link-theorem')
    audit_note_link_theorem.add_argument('--paper-id', required=True)
    audit_note_link_theorem.add_argument('--label', required=True)
    audit_note_link_theorem.set_defaults(func=handlers.audit_note)

    audit_note_link_citation = audit_note_sub.add_parser('link-citation')
    audit_note_link_citation.add_argument('--paper-id', required=True)
    audit_note_link_citation.add_argument('--citation-key', required=True)
    audit_note_link_citation.set_defaults(func=handlers.audit_note)

    discover = sub.add_parser('discover')
    discover.add_argument('--query', required=True)
    discover.add_argument('--limit', type=int, default=10)
    discover.set_defaults(func=handlers.discover)

    download_paper = sub.add_parser('download-paper')
    download_paper.add_argument('--query', required=True)
    download_paper.add_argument('--limit', type=int, default=10)
    download_paper.set_defaults(func=handlers.download_paper)

    papers_citing_cmd = sub.add_parser('papers-citing')
    papers_citing_cmd.add_argument('--paper-id', required=True)
    papers_citing_cmd.add_argument('--limit', type=int, default=10)
    papers_citing_cmd.set_defaults(func=handlers.papers_citing)

    papers_cited_by_cmd = sub.add_parser('papers-cited-by')
    papers_cited_by_cmd.add_argument('--paper-id', required=True)
    papers_cited_by_cmd.add_argument('--limit', type=int, default=10)
    papers_cited_by_cmd.set_defaults(func=handlers.papers_cited_by)

    citation_neighborhood_cmd = sub.add_parser('citation-neighborhood')
    citation_neighborhood_cmd.add_argument('--paper-id', required=True)
    citation_neighborhood_cmd.add_argument('--limit', type=int, default=5)
    citation_neighborhood_cmd.set_defaults(func=handlers.citation_neighborhood)

    citation_graph_build = sub.add_parser('citation-graph-build')
    citation_graph_build.add_argument('--paper-id', required=True)
    citation_graph_build.add_argument('--depth', type=int, default=1)
    citation_graph_build.add_argument('--limit', type=int, default=5)
    citation_graph_build.add_argument('--refresh', action='store_true')
    citation_graph_build.set_defaults(func=handlers.citation_graph_build)

    citation_graph_show = sub.add_parser('citation-graph-show')
    citation_graph_show.add_argument('--paper-id', required=True)
    citation_graph_show.set_defaults(func=handlers.citation_graph_show)

    citation_graph_export = sub.add_parser('citation-graph-export')
    citation_graph_export.add_argument('--paper-id', required=True)
    citation_graph_export.add_argument('--output', required=True)
    citation_graph_export.set_defaults(func=handlers.citation_graph_export)

    graph_node_download = sub.add_parser('graph-node-download-proposal')
    graph_node_download.add_argument('--paper-id', required=True)
    graph_node_download.add_argument('--node-id', required=True)
    graph_node_download.set_defaults(func=handlers.graph_node_download_proposal)

    inbox_list = sub.add_parser('inbox-list')
    inbox_list.add_argument('--duplicate-status')
    inbox_list.add_argument('--json', action='store_true')
    inbox_list.set_defaults(func=handlers.inbox_list)

    inbox_show = sub.add_parser('inbox-show')
    inbox_show.add_argument('--proposed-name', required=True)
    inbox_show.set_defaults(func=handlers.inbox_show)

    literature_audit_propose = sub.add_parser('literature-audit-propose')
    literature_audit_propose.add_argument('--paper-id', required=True)
    literature_audit_propose.set_defaults(func=handlers.literature_audit_propose)

    literature_audit_show = sub.add_parser('literature-audit-show')
    literature_audit_show.add_argument('--paper-id', required=True)
    literature_audit_show.set_defaults(func=handlers.literature_audit_show)

    literature_audit_approve = sub.add_parser('literature-audit-approve')
    literature_audit_approve.add_argument('--paper-id', required=True)
    literature_audit_approve.set_defaults(func=handlers.literature_audit_approve)

    parse_pdf = sub.add_parser('parse-pdf')
    parse_pdf.add_argument('--pdf', required=True)
    parse_pdf.set_defaults(func=handlers.parse_pdf)

    parser_preflight = sub.add_parser('parser-preflight')
    parser_preflight.set_defaults(func=handlers.parser_preflight)

    evidence_context = sub.add_parser('evidence-context')
    evidence_context.add_argument('--paper-id', required=True)
    evidence_context.add_argument('--label')
    evidence_context.add_argument('--citation-key')
    evidence_context.set_defaults(func=handlers.evidence_context)

    register_source_inspection_commands(sub, handlers.source_inspection)


@dataclass(frozen=True, slots=True)
class SourceInspectionHandlers:
    source_fetch: Handler
    source_show: Handler
    source_sections: Handler
    source_equations: Handler
    source_theorems: Handler
    source_citations: Handler
    source_bibliography: Handler
    source_macros: Handler
    source_labels: Handler
    source_section: Handler
    source_refs: Handler
    source_equation: Handler
    source_theorem: Handler


def register_source_inspection_commands(sub: Subparsers, handlers: SourceInspectionHandlers) -> None:
    """Register structured-source inspection commands."""
    source_fetch = sub.add_parser('source-fetch')
    source_fetch.add_argument('--arxiv-id', required=True)
    source_fetch.add_argument('--paper-id')
    source_fetch.set_defaults(func=handlers.source_fetch)

    source_show = sub.add_parser('source-show')
    source_show.add_argument('--paper-id', required=True)
    source_show.set_defaults(func=handlers.source_show)

    source_sections = sub.add_parser('source-sections')
    source_sections.add_argument('--paper-id', required=True)
    source_sections.set_defaults(func=handlers.source_sections)

    source_equations = sub.add_parser('source-equations')
    source_equations.add_argument('--paper-id', required=True)
    source_equations.set_defaults(func=handlers.source_equations)

    source_theorems = sub.add_parser('source-theorems')
    source_theorems.add_argument('--paper-id', required=True)
    source_theorems.set_defaults(func=handlers.source_theorems)

    source_citations = sub.add_parser('source-citations')
    source_citations.add_argument('--paper-id', required=True)
    source_citations.set_defaults(func=handlers.source_citations)

    source_bibliography = sub.add_parser('source-bibliography')
    source_bibliography.add_argument('--paper-id', required=True)
    source_bibliography.set_defaults(func=handlers.source_bibliography)

    source_macros = sub.add_parser('source-macros')
    source_macros.add_argument('--paper-id', required=True)
    source_macros.set_defaults(func=handlers.source_macros)

    source_labels = sub.add_parser('source-labels')
    source_labels.add_argument('--paper-id', required=True)
    source_labels.set_defaults(func=handlers.source_labels)

    source_section = sub.add_parser('source-section')
    source_section.add_argument('--paper-id', required=True)
    source_section.add_argument('--title')
    source_section.add_argument('--label')
    source_section.set_defaults(func=handlers.source_section)

    source_refs = sub.add_parser('source-refs')
    source_refs.add_argument('--paper-id', required=True)
    source_refs.set_defaults(func=handlers.source_refs)

    source_equation = sub.add_parser('source-equation')
    source_equation.add_argument('--paper-id', required=True)
    source_equation.add_argument('--label', required=True)
    source_equation.set_defaults(func=handlers.source_equation)

    source_theorem = sub.add_parser('source-theorem')
    source_theorem.add_argument('--paper-id', required=True)
    source_theorem.add_argument('--label', required=True)
    source_theorem.set_defaults(func=handlers.source_theorem)
