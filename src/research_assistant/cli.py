from __future__ import annotations

import argparse
from pathlib import Path

from research_assistant.adapters.workspace_exports import export_paper_context
from research_assistant.config import get_paths
from research_assistant.ingest.source_manifest import canonical_paper_id, store_raw_source
from research_assistant.ingest.pdf_extract import extract_pdf_text
from research_assistant.ingest.normalize_text import normalize_extracted_text
from research_assistant.ingest.metadata_resolve import resolve_metadata
from research_assistant.ingest.identity_validate import validate_identity
from research_assistant.ingest.filename_parse import parse_paper_filename
from research_assistant.schemas.link_record import LinkRecord
from research_assistant.summarize.draft_summary import build_draft_summary
from research_assistant.summarize.claim_support import audit_claim
from research_assistant.storage.file_store import FileStore
from research_assistant.query.paper_lookup import find_paper, get_paper_summary, claim_support_audit
from research_assistant.query.review import list_review_items, mark_review_status, show_review_item
from research_assistant.query.discovery import discover_papers, discover_papers_with_status
from research_assistant.query.downloads import download_to_inbox, list_download_proposals, persist_download_proposal, propose_download, show_download_proposal
from research_assistant.query.citation_graph import citation_neighborhood, papers_cited_by, papers_citing
from research_assistant.ingest.parser_orchestrator import parse_with_all, reconcile_parsed_documents
from research_assistant.ingest.parser_preflight import preflight_all
from research_assistant.source.arxiv_source import fetch_arxiv_structured_source
from research_assistant.source.structured_source import source_record_path


def cmd_ingest(args: argparse.Namespace) -> int:
    paths = get_paths(Path(args.root) if args.root else None)
    source = args.pdf or (f'arxiv:{args.arxiv_id}' if args.arxiv_id else args.query)
    if not source:
        raise SystemExit('ingest requires --pdf, --query, or --arxiv-id')
    paper_id = canonical_paper_id(source)
    text = ''
    filename_hints = None
    parser_hints = None
    structured_source = None
    if args.arxiv_id:
        structured_source = fetch_arxiv_structured_source(args.arxiv_id, root=paths.root, paper_id=paper_id)
    if args.pdf:
        raw_path = store_raw_source(args.pdf, paths.papers_raw, paper_id)
        text = normalize_extracted_text(extract_pdf_text(raw_path))
        paths.papers_extracted.mkdir(parents=True, exist_ok=True)
        (paths.papers_extracted / f'{paper_id}.txt').write_text(text)
        filename_hints = parse_paper_filename(args.pdf).__dict__
        parsed_outputs = parse_with_all(raw_path)
        reconciled = reconcile_parsed_documents(parsed_outputs)
        parser_hints = {
            'consensus_title': reconciled.consensus_title,
            'consensus_authors': reconciled.consensus_authors,
            'consensus_abstract': reconciled.consensus_abstract,
            'consensus_section_headings': reconciled.consensus_section_headings,
            'parse_confidence': reconciled.parse_confidence,
            'requires_manual_review': reconciled.requires_manual_review,
            'parser_agreement': reconciled.parser_agreement,
            'disagreements': reconciled.disagreements,
            'parser_outputs': reconciled.parser_outputs,
        }
    metadata = resolve_metadata(args.query or source, arxiv_id=args.arxiv_id, extracted_text=text, filename_hints=filename_hints, parser_hints=parser_hints)
    if structured_source is not None:
        metadata['structured_source'] = {
            'paper_id': structured_source.paper_id,
            'source_type': structured_source.source_type,
            'status': structured_source.status,
            'primary_for_audit': structured_source.primary_for_audit,
            'record_path': str(source_record_path(paths.papers_source, paper_id)),
        }
        metadata.setdefault('source_statuses', []).extend(structured_source.provenance.get('source_statuses', []))
    metadata['identity_validation'] = validate_identity(metadata)
    summary = build_draft_summary(paper_id, metadata, text)
    store = FileStore(paths.local_research)
    store.write_json(paths.metadata / f'{paper_id}.json', metadata)
    store.write_json(paths.summaries / f'{paper_id}.json', summary.to_dict())
    print(paper_id)
    return 0


def cmd_find(args: argparse.Namespace) -> int:
    paths = get_paths(Path(args.root) if args.root else None)
    for rec in find_paper(args.query, root=paths.root, review_status=args.review_status, author=args.author, year=args.year):
        print(f"{rec['paper_id']}\t{rec['year']}\t{rec['review_status']}\t{rec['title']}")
    return 0


def cmd_show(args: argparse.Namespace) -> int:
    paths = get_paths(Path(args.root) if args.root else None)
    result = get_paper_summary(args.paper_id, root=paths.root)
    import json
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


def cmd_export_context(args: argparse.Namespace) -> int:
    out = export_paper_context(
        Path(args.output) if args.output else None,
        root=Path(args.root) if args.root else None,
        review_status=args.review_status,
    )
    print(out)
    return 0


def cmd_review_list(args: argparse.Namespace) -> int:
    import json
    rows = list_review_items(root=Path(args.root) if args.root else None, status=args.status)
    if args.json:
        print(json.dumps(rows, indent=2, sort_keys=True))
        return 0
    for row in rows:
        print(f"{row['paper_id']}\t{row['year']}\t{row['review_status']}\t{row['title']}")
    return 0


def cmd_review_show(args: argparse.Namespace) -> int:
    import json
    payload = show_review_item(args.paper_id, root=Path(args.root) if args.root else None)
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


def cmd_review_mark(args: argparse.Namespace) -> int:
    import json
    payload = mark_review_status(args.paper_id, args.status, root=Path(args.root) if args.root else None)
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


def cmd_link_add(args: argparse.Namespace) -> int:
    paths = get_paths(Path(args.root) if args.root else None)
    link = LinkRecord(
        id=f'link_{abs(hash((args.paper_id, args.target, args.relationship))) }',
        paper_id=args.paper_id,
        target_type=args.target_type,
        target=args.target,
        relationship=args.relationship,
    )
    FileStore(paths.local_research).write_json(paths.links / f'{link.id}.json', link.to_dict())
    print(link.id)
    return 0


def cmd_audit_claim(args: argparse.Namespace) -> int:
    paths = get_paths(Path(args.root) if args.root else None)
    claim = args.claim or Path(args.claim_file).read_text()
    result = claim_support_audit(claim, args.papers or [], root=paths.root)
    import json
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


def cmd_discover(args: argparse.Namespace) -> int:
    import json
    payload = discover_papers_with_status(args.query, per_page=args.limit)
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


def cmd_download_paper(args: argparse.Namespace) -> int:
    import json
    payload = discover_papers_with_status(args.query, per_page=args.limit)
    results = payload['results']
    downloadable = [r for r in results if r.get('open_access_pdf_url')]
    if not downloadable:
        reason = 'no open access pdf found'
        if payload['status'] == 'unavailable':
            reason = 'discovery unavailable'
        print(json.dumps({
            'query': args.query,
            'downloaded': False,
            'reason': reason,
            'discovery': payload,
        }, indent=2, sort_keys=True))
        return 0
    chosen = downloadable[0]
    proposal = propose_download(chosen, root=Path(args.root) if args.root else None, query=args.query)
    downloaded_path = download_to_inbox(chosen['open_access_pdf_url'], filename_hint=proposal.proposed_name.removesuffix('.pdf'), root=Path(args.root) if args.root else None)
    proposal_path = persist_download_proposal(proposal, root=Path(args.root) if args.root else None)
    print(json.dumps({
        'query': args.query,
        'downloaded': True,
        'discovery': payload,
        'result': chosen,
        'proposal': proposal.to_dict(),
        'proposal_path': str(proposal_path),
        'downloaded_path': str(downloaded_path),
    }, indent=2, sort_keys=True))
    return 0


def cmd_papers_citing(args: argparse.Namespace) -> int:
    import json
    results = papers_citing(args.paper_id, limit=args.limit)
    print(json.dumps(results, indent=2, sort_keys=True))
    return 0


def cmd_papers_cited_by(args: argparse.Namespace) -> int:
    import json
    results = papers_cited_by(args.paper_id, limit=args.limit)
    print(json.dumps(results, indent=2, sort_keys=True))
    return 0


def cmd_citation_neighborhood(args: argparse.Namespace) -> int:
    import json
    results = citation_neighborhood(args.paper_id, limit=args.limit)
    print(json.dumps(results, indent=2, sort_keys=True))
    return 0


def cmd_inbox_list(args: argparse.Namespace) -> int:
    import json
    rows = list_download_proposals(root=Path(args.root) if args.root else None, duplicate_status=args.duplicate_status)
    if args.json:
        print(json.dumps(rows, indent=2, sort_keys=True))
        return 0
    for row in rows:
        print(f"{row['proposed_name']}\t{row.get('duplicate_status', 'unknown')}\t{row.get('duplicate_count', 0)}\t{row['source']}\t{row['title']}")
    return 0


def cmd_inbox_show(args: argparse.Namespace) -> int:
    import json
    payload = show_download_proposal(args.proposed_name, root=Path(args.root) if args.root else None)
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


def cmd_parse_pdf(args: argparse.Namespace) -> int:
    import json
    outputs = parse_with_all(Path(args.pdf).expanduser())
    reconciled = reconcile_parsed_documents(outputs)
    print(json.dumps(reconciled.to_dict(), indent=2, sort_keys=True))
    return 0


def cmd_parser_preflight(args: argparse.Namespace) -> int:
    import json
    checks = [c.to_dict() for c in preflight_all()]
    print(json.dumps(checks, indent=2, sort_keys=True))
    return 0


def cmd_source_fetch(args: argparse.Namespace) -> int:
    import json
    paths = get_paths(Path(args.root) if args.root else None)
    source = args.paper_id or f'arxiv:{args.arxiv_id}'
    paper_id = args.paper_id or canonical_paper_id(source)
    record = fetch_arxiv_structured_source(args.arxiv_id, root=paths.root, paper_id=paper_id)
    print(json.dumps(record.to_dict(), indent=2, sort_keys=True))
    return 0


def cmd_source_show(args: argparse.Namespace) -> int:
    import json
    paths = get_paths(Path(args.root) if args.root else None)
    store = FileStore(paths.local_research)
    payload = store.read_json(source_record_path(paths.papers_source, args.paper_id))
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog='ra')
    parser.add_argument('--root', help='Research assistant project root')
    sub = parser.add_subparsers(dest='cmd', required=True)

    ingest = sub.add_parser('ingest')
    ingest.add_argument('--pdf')
    ingest.add_argument('--query')
    ingest.add_argument('--arxiv-id')
    ingest.set_defaults(func=cmd_ingest)

    find = sub.add_parser('find')
    find.add_argument('--query', required=True)
    find.add_argument('--review-status')
    find.add_argument('--author')
    find.add_argument('--year', type=int)
    find.set_defaults(func=cmd_find)

    show = sub.add_parser('show')
    show.add_argument('--paper-id', required=True)
    show.set_defaults(func=cmd_show)

    export_context = sub.add_parser('export-context')
    export_context.add_argument('--output')
    export_context.add_argument('--review-status')
    export_context.set_defaults(func=cmd_export_context)

    review_list = sub.add_parser('review-list')
    review_list.add_argument('--status')
    review_list.add_argument('--json', action='store_true')
    review_list.set_defaults(func=cmd_review_list)

    review_show = sub.add_parser('review-show')
    review_show.add_argument('--paper-id', required=True)
    review_show.set_defaults(func=cmd_review_show)

    review_mark = sub.add_parser('review-mark')
    review_mark.add_argument('--paper-id', required=True)
    review_mark.add_argument('--status', required=True)
    review_mark.set_defaults(func=cmd_review_mark)

    link = sub.add_parser('link-add')
    link.add_argument('--paper-id', required=True)
    link.add_argument('--target', required=True)
    link.add_argument('--relationship', required=True)
    link.add_argument('--target-type', default='code_file')
    link.set_defaults(func=cmd_link_add)

    audit = sub.add_parser('audit-claim')
    audit.add_argument('--claim')
    audit.add_argument('--claim-file')
    audit.add_argument('--papers', nargs='*')
    audit.set_defaults(func=cmd_audit_claim)

    discover = sub.add_parser('discover')
    discover.add_argument('--query', required=True)
    discover.add_argument('--limit', type=int, default=10)
    discover.set_defaults(func=cmd_discover)

    download_paper = sub.add_parser('download-paper')
    download_paper.add_argument('--query', required=True)
    download_paper.add_argument('--limit', type=int, default=10)
    download_paper.set_defaults(func=cmd_download_paper)

    papers_citing_cmd = sub.add_parser('papers-citing')
    papers_citing_cmd.add_argument('--paper-id', required=True)
    papers_citing_cmd.add_argument('--limit', type=int, default=10)
    papers_citing_cmd.set_defaults(func=cmd_papers_citing)

    papers_cited_by_cmd = sub.add_parser('papers-cited-by')
    papers_cited_by_cmd.add_argument('--paper-id', required=True)
    papers_cited_by_cmd.add_argument('--limit', type=int, default=10)
    papers_cited_by_cmd.set_defaults(func=cmd_papers_cited_by)

    citation_neighborhood_cmd = sub.add_parser('citation-neighborhood')
    citation_neighborhood_cmd.add_argument('--paper-id', required=True)
    citation_neighborhood_cmd.add_argument('--limit', type=int, default=5)
    citation_neighborhood_cmd.set_defaults(func=cmd_citation_neighborhood)

    inbox_list = sub.add_parser('inbox-list')
    inbox_list.add_argument('--duplicate-status')
    inbox_list.add_argument('--json', action='store_true')
    inbox_list.set_defaults(func=cmd_inbox_list)

    inbox_show = sub.add_parser('inbox-show')
    inbox_show.add_argument('--proposed-name', required=True)
    inbox_show.set_defaults(func=cmd_inbox_show)

    parse_pdf = sub.add_parser('parse-pdf')
    parse_pdf.add_argument('--pdf', required=True)
    parse_pdf.set_defaults(func=cmd_parse_pdf)

    parser_preflight = sub.add_parser('parser-preflight')
    parser_preflight.set_defaults(func=cmd_parser_preflight)

    source_fetch = sub.add_parser('source-fetch')
    source_fetch.add_argument('--arxiv-id', required=True)
    source_fetch.add_argument('--paper-id')
    source_fetch.set_defaults(func=cmd_source_fetch)

    source_show = sub.add_parser('source-show')
    source_show.add_argument('--paper-id', required=True)
    source_show.set_defaults(func=cmd_source_show)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == '__main__':
    raise SystemExit(main())
