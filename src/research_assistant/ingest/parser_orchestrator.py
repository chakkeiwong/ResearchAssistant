from __future__ import annotations

from pathlib import Path
from collections import Counter
import re

from research_assistant.schemas.parsed_document import ParsedDocument, ReconciledDocument
from research_assistant.ingest.parser_pdftotext import PdftotextParser
from research_assistant.ingest.parser_marker import MarkerParser
from research_assistant.ingest.parser_grobid import GROBIDParser
from research_assistant.ingest.parser_mineru import MinerUParser
from research_assistant.ingest.parser_markitdown import MarkItDownParser


TITLE_STOP_PATTERNS = [
    r'^\d{2}-\d{2}\b',
    r'january|february|march|april|may|june|july|august|september|october|november|december',
    r'working paper',
    r'board of governors',
    r'office of financial research',
    r'@',
]


def available_parsers() -> list:
    return [
        PdftotextParser(),
        MarkerParser(),
        GROBIDParser(),
        MinerUParser(),
        MarkItDownParser(),
    ]


def _clean_line(line: str) -> str:
    line = line.strip()
    line = re.sub(r'^!\[.*?\]\(.*?\)$', '', line)
    line = re.sub(r'^[#*\s]+', '', line)
    line = re.sub(r'[*`]+', '', line)
    line = re.sub(r'[†‡*∗]+', '', line)
    line = re.sub(r'\s+', ' ', line)
    return line.strip()


def _looks_like_title_noise(line: str) -> bool:
    low = line.lower()
    if len(line) < 8:
        return True
    return any(re.search(p, low) for p in TITLE_STOP_PATTERNS)


def _looks_like_author(line: str) -> bool:
    line = _clean_line(line)
    if not line or _looks_like_title_noise(line):
        return False
    words = [w for w in line.split() if w]
    if not (2 <= len(words) <= 4):
        return False
    if any(w.lower() in {'credit', 'risk', 'interest', 'rate', 'shocks'} for w in words):
        return False
    return all(w[:1].isupper() for w in words if w[:1].isalpha())


def _extract_title_candidates(lines: list[str]) -> list[str]:
    cleaned = [_clean_line(l) for l in lines]
    cleaned = [c for c in cleaned if c and not _looks_like_title_noise(c)]
    out = []
    for i, line in enumerate(cleaned[:15]):
        if _looks_like_author(line):
            continue
        out.append(line)
        if i + 1 < len(cleaned):
            nxt = cleaned[i + 1]
            if nxt and not _looks_like_author(nxt) and not _looks_like_title_noise(nxt) and len(nxt.split()) <= 6:
                joined = f"{line} {nxt}".strip()
                out.append(joined)
    scored = []
    for cand in out:
        score = 0
        if 4 <= len(cand.split()) <= 15:
            score += 2
        if any(ch.islower() for ch in cand) and any(ch.isupper() for ch in cand):
            score += 1
        if ':' not in cand and '@' not in cand:
            score += 1
        if len(cand) > 20:
            score += 1
        scored.append((score, cand))
    scored.sort(key=lambda x: (-x[0], x[1]))
    seen = set()
    uniq = []
    for _, c in scored:
        key = c.lower()
        if key not in seen:
            seen.add(key)
            uniq.append(c)
    return uniq[:8]


def _extract_authors(lines: list[str]) -> list[str]:
    authors = []
    for line in lines[:25]:
        c = _clean_line(line)
        if _looks_like_author(c):
            authors.append(c)
    seen = set()
    uniq = []
    for a in authors:
        key = a.lower()
        if key not in seen:
            seen.add(key)
            uniq.append(a)
    return uniq[:6]


def parse_with_all(pdf_path: Path) -> list[ParsedDocument]:
    outputs = []
    for parser in available_parsers():
        try:
            outputs.append(parser.parse(pdf_path))
        except Exception as exc:
            outputs.append(ParsedDocument(parser_name=parser.name, diagnostics={'error': str(exc)}, parse_status='failed'))
    return outputs


PARSER_TITLE_WEIGHTS = {
    'marker': 4,
    'markitdown': 2,
    'pdftotext': 1,
    'grobid': 3,
    'mineru': 3,
}


def reconcile_parsed_documents(outputs: list[ParsedDocument]) -> ReconciledDocument:
    title_votes = []
    weighted_title_scores = Counter()
    author_votes = []
    parser_outputs = []

    for out in outputs:
        lines = []
        if out.body_markdown:
            lines = [l for l in out.body_markdown.splitlines() if l.strip()]
        elif out.body_text:
            lines = [l for l in out.body_text.splitlines() if l.strip()]

        if out.title_candidates:
            enriched_titles = _extract_title_candidates(out.title_candidates)
            if not enriched_titles:
                enriched_titles = [_clean_line(t) for t in out.title_candidates if _clean_line(t)]
        else:
            enriched_titles = _extract_title_candidates(lines)
        enriched_authors = out.authors or _extract_authors(lines)

        weight = PARSER_TITLE_WEIGHTS.get(out.parser_name, 1)
        if enriched_titles:
            title_votes.append(enriched_titles[0].strip())
            for rank, title in enumerate(enriched_titles):
                weighted_title_scores[title.strip()] += max(1, weight - rank)
        for a in enriched_authors:
            author_votes.append(a.strip())

        parser_outputs.append({
            **out.to_dict(),
            'derived_title_candidates': enriched_titles,
            'derived_authors': enriched_authors,
        })

    title_counter = Counter(title_votes)
    author_counter = Counter(author_votes)

    consensus_title = None
    if weighted_title_scores:
        unique_titles = list(weighted_title_scores.keys())
        prefix_best = None
        for title in unique_titles:
            for other in unique_titles:
                if other != title and other.lower().startswith(title.lower()) and len(other) > len(title):
                    if prefix_best is None or len(other) > len(prefix_best):
                        prefix_best = other
        ranked_titles = []
        for title in unique_titles:
            score = weighted_title_scores[title] * 10 + len(title)
            if prefix_best and title == prefix_best:
                score += 100
            ranked_titles.append((score, title))
        ranked_titles.sort(key=lambda x: (-x[0], x[1]))
        consensus_title = ranked_titles[0][1]

    consensus_authors = [name for name, count in author_counter.items() if count >= 2][:6]
    if not consensus_authors:
        consensus_authors = [name for name, count in author_counter.items() if count >= 1][:6]

    ok_count = sum(1 for o in outputs if o.parse_status == 'ok')
    parse_confidence = 'low'
    if ok_count >= 2 and consensus_title:
        parse_confidence = 'medium'
    if ok_count >= 3 and consensus_title and len(title_counter) == 1:
        parse_confidence = 'high'

    disagreements = []
    if len(set(title_votes)) > 1:
        disagreements.append('parser title candidates disagree')
    if not consensus_title:
        disagreements.append('no parser produced a reliable title')
    if not consensus_authors:
        disagreements.append('no parser produced reliable authors')

    return ReconciledDocument(
        consensus_title=consensus_title,
        consensus_authors=consensus_authors,
        parser_agreement={
            'ok_parsers': ok_count,
            'title_votes': dict(title_counter),
            'author_votes': dict(author_counter),
        },
        disagreements=disagreements,
        parse_confidence=parse_confidence,
        requires_manual_review=parse_confidence != 'high',
        parser_outputs=parser_outputs,
    )
