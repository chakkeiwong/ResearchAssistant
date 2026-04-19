from __future__ import annotations

import argparse
from pathlib import Path

from research_assistant.config import get_paths
from research_assistant.ingest.source_manifest import canonical_paper_id, store_raw_source
from research_assistant.ingest.pdf_extract import extract_pdf_text
from research_assistant.ingest.normalize_text import normalize_extracted_text
from research_assistant.ingest.metadata_resolve import resolve_metadata
from research_assistant.ingest.filename_parse import parse_paper_filename
from research_assistant.schemas.link_record import LinkRecord
from research_assistant.summarize.draft_summary import build_draft_summary
from research_assistant.summarize.claim_support import audit_claim
from research_assistant.storage.file_store import FileStore
from research_assistant.query.paper_lookup import find_paper, get_paper_summary, claim_support_audit


def cmd_ingest(args: argparse.Namespace) -> int:
    paths = get_paths(Path(args.root) if args.root else None)
    source = args.pdf or args.query
    if not source:
        raise SystemExit('ingest requires --pdf or --query')
    paper_id = canonical_paper_id(source)
    text = ''
    filename_hints = None
    if args.pdf:
        raw_path = store_raw_source(args.pdf, paths.papers_raw, paper_id)
        text = normalize_extracted_text(extract_pdf_text(raw_path))
        (paths.papers_extracted / f'{paper_id}.txt').write_text(text)
        filename_hints = parse_paper_filename(args.pdf).__dict__
    metadata = resolve_metadata(args.query or source, arxiv_id=args.arxiv_id, extracted_text=text, filename_hints=filename_hints)
    summary = build_draft_summary(paper_id, metadata, text)
    store = FileStore(paths.local_research)
    store.write_json(paths.metadata / f'{paper_id}.json', metadata)
    store.write_json(paths.summaries / f'{paper_id}.json', summary.to_dict())
    print(paper_id)
    return 0


def cmd_find(args: argparse.Namespace) -> int:
    paths = get_paths(Path(args.root) if args.root else None)
    for rec in find_paper(args.query, root=paths.root):
        print(f"{rec['paper_id']}\t{rec['year']}\t{rec['title']}")
    return 0


def cmd_show(args: argparse.Namespace) -> int:
    paths = get_paths(Path(args.root) if args.root else None)
    result = get_paper_summary(args.paper_id, root=paths.root)
    import json
    print(json.dumps(result, indent=2, sort_keys=True))
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
    find.set_defaults(func=cmd_find)

    show = sub.add_parser('show')
    show.add_argument('--paper-id', required=True)
    show.set_defaults(func=cmd_show)

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

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == '__main__':
    raise SystemExit(main())
