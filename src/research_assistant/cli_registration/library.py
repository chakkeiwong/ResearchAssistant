from __future__ import annotations

from dataclasses import dataclass

from research_assistant.cli_registration.common import Handler, Subparsers


@dataclass(frozen=True, slots=True)
class LibraryHandlers:
    ingest: Handler
    find: Handler
    show: Handler
    export_context: Handler
    review_list: Handler
    review_show: Handler
    review_mark: Handler
    review_write: Handler
    link_add: Handler


def register_library_commands(sub: Subparsers, handlers: LibraryHandlers) -> None:
    """Register local paper-library ingestion, query, and review commands."""
    ingest = sub.add_parser('ingest')
    ingest.add_argument('--pdf')
    ingest.add_argument('--query')
    ingest.add_argument('--arxiv-id')
    ingest.set_defaults(func=handlers.ingest)

    find = sub.add_parser('find')
    find.add_argument('--query', required=True)
    find.add_argument('--review-status')
    find.add_argument('--author')
    find.add_argument('--year', type=int)
    find.set_defaults(func=handlers.find)

    show = sub.add_parser('show')
    show.add_argument('--paper-id', required=True)
    show.set_defaults(func=handlers.show)

    export_context = sub.add_parser('export-context')
    export_context.add_argument('--output')
    export_context.add_argument('--review-status')
    export_context.set_defaults(func=handlers.export_context)

    review_list = sub.add_parser('review-list')
    review_list.add_argument('--status')
    review_list.add_argument('--json', action='store_true')
    review_list.set_defaults(func=handlers.review_list)

    review_show = sub.add_parser('review-show')
    review_show.add_argument('--paper-id', required=True)
    review_show.set_defaults(func=handlers.review_show)

    review_mark = sub.add_parser('review-mark')
    review_mark.add_argument('--paper-id', required=True)
    review_mark.add_argument('--status', required=True)
    review_mark.set_defaults(func=handlers.review_mark)

    review_write = sub.add_parser('review-write', help='Prototype explicit confirmation flow for review-state writes')
    review_write_sub = review_write.add_subparsers(dest='review_write_action', required=True)
    review_write_status_cmd = review_write_sub.add_parser('status')
    review_write_status_cmd.set_defaults(func=handlers.review_write)
    review_write_propose = review_write_sub.add_parser('propose-status')
    review_write_propose.add_argument('--paper-id', required=True)
    review_write_propose.add_argument('--status', required=True)
    review_write_propose.add_argument('--expires-minutes', type=int, default=30)
    review_write_propose.set_defaults(func=handlers.review_write)
    review_write_apply = review_write_sub.add_parser('apply')
    review_write_apply.add_argument('--confirmation-id', required=True)
    review_write_apply.set_defaults(func=handlers.review_write)
    review_write_cleanup = review_write_sub.add_parser('cleanup-expired')
    review_write_cleanup.add_argument('--apply', action='store_true')
    review_write_cleanup.set_defaults(func=handlers.review_write)

    link = sub.add_parser('link-add')
    link.add_argument('--paper-id', required=True)
    link.add_argument('--target', required=True)
    link.add_argument('--relationship', required=True)
    link.add_argument('--target-type', default='code_file')
    link.add_argument('--source-type', default='paper')
    link.add_argument('--source-ref')
    link.add_argument('--target-ref')
    link.set_defaults(func=handlers.link_add)
