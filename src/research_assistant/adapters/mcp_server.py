from __future__ import annotations

from research_assistant.query.paper_lookup import find_paper, get_paper_summary, paper_code_links, claim_support_audit


def tool_find_paper(query: str):
    return find_paper(query)


def tool_get_paper_summary(paper_id: str):
    return get_paper_summary(paper_id)


def tool_paper_code_links(paper_id: str):
    return paper_code_links(paper_id)


def tool_claim_support_audit(claim: str, paper_ids: list[str]):
    return claim_support_audit(claim, paper_ids)


def main() -> int:
    # This remains a thin wrapper. A later step can replace this with the full
    # MCP server SDK once the backend interface stabilizes.
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
