from __future__ import annotations

from dataclasses import dataclass, field
import re


TITLE_STOP_PATTERNS = [
    r'^\d{2}-\d{2}\b',
    r'january|february|march|april|may|june|july|august|september|october|november|december',
    r'working paper',
    r'board of governors',
    r'office of financial research',
    r'^abstract$',
    r'@',
]

AUTHOR_STOPWORDS = {
    'abstract',
    'introduction',
    'conclusion',
    'method',
    'discussion',
    'experiment',
    'appendix',
    'references',
}

SECTION_HEADINGS = {
    'abstract',
    'introduction',
    'method',
    'methods',
    'experiment',
    'experiments',
    'discussion',
    'conclusion',
    'references',
    'appendix',
}

TITLE_SUFFIX_WORDS = {
    'authors',
    'workflow',
}


@dataclass
class FrontMatterExtraction:
    title_candidates: list[str] = field(default_factory=list)
    authors: list[str] = field(default_factory=list)
    section_headings: list[str] = field(default_factory=list)


def clean_line(line: str) -> str:
    line = ''.join(ch for ch in line if ch.isprintable() or ch.isspace())
    line = line.strip()
    line = re.sub(r'^!\[.*?\]\(.*?\)$', '', line)
    line = re.sub(r'^[#*\s]+', '', line)
    line = re.sub(r'\(cid:\d+\)', '', line)
    line = re.sub(r'\|\s*-{2,}\s*', ' ', line)
    line = re.sub(r'\|', ' ', line)
    line = re.sub(r'\\+', ' ', line)
    line = re.sub(r'[*`]+', '', line)
    line = re.sub(r'[†‡*∗]+', '', line)
    line = re.sub(r'\s+', ' ', line)
    return line.strip(' -')


def normalize_title_candidate(candidate: str) -> str:
    candidate = clean_line(candidate)
    candidate = candidate.replace('Workow', 'Workflow').replace('workow', 'workflow')
    candidate = re.sub(r'\s+\d+(?:\.\d+)*\s+(?:introduction|method|discussion|experiment|conclusion)\b.*$', '', candidate, flags=re.IGNORECASE)
    return candidate.strip()


def looks_like_title_noise(line: str) -> bool:
    low = line.lower()
    if len(line) < 8 and line.lower() not in TITLE_SUFFIX_WORDS:
        return True
    if low.startswith('this benchmark is designed'):
        return True
    return any(re.search(p, low) for p in TITLE_STOP_PATTERNS)


def section_heading(line: str) -> str | None:
    cleaned = clean_line(line)
    if not cleaned:
        return None
    heading = re.sub(r'^\d+(?:\.\d+)*\s+', '', cleaned).strip()
    normalized = heading.lower()
    if normalized in SECTION_HEADINGS:
        return heading[:1].upper() + heading[1:]
    return None


def looks_like_section_heading(line: str) -> bool:
    heading = section_heading(line)
    return bool(heading and heading.lower() in AUTHOR_STOPWORDS)


def looks_like_author(line: str) -> bool:
    line = clean_line(line)
    if not line or looks_like_title_noise(line) or looks_like_section_heading(line):
        return False
    words = [w for w in line.split() if w]
    if not (2 <= len(words) <= 6):
        return False
    if any(any(ch.isdigit() for ch in w) for w in words):
        return False
    if any(w.lower() in {'and'} for w in words):
        return False
    if any(w.lower() in AUTHOR_STOPWORDS for w in words):
        return False
    if any(len(w) > 30 for w in words):
        return False
    if any(w.lower() in {'credit', 'risk', 'interest', 'rate', 'shocks', 'subtitle', 'evidence', 'synthetic', 'research'} for w in words):
        return False
    if len(words) >= 4 and not (' and ' in line.lower()):
        even_pairs = len(words) % 2 == 0 and len(words) >= 6
        marker_tokens = any(token in line for token in ('†', '‡', '∗', '*'))
        if not even_pairs and not marker_tokens:
            return False
        if len(words) == 4 and not marker_tokens and not any('-' in w for w in words):
            return False
    alpha_words = [w for w in words if any(ch.isalpha() for ch in w)]
    return len(alpha_words) >= 2 and all(w[:1].isupper() for w in alpha_words if w[:1].isalpha())


def split_joined_authors(line: str) -> list[str]:
    has_author_markers = any(token in line for token in ('†', '‡', '∗', '*'))
    cleaned = clean_line(line)
    parts = [p.strip() for p in re.split(r'\s+and\s+', cleaned) if p.strip()]
    if len(parts) > 1:
        return [p for p in parts if looks_like_author(p)]
    words = cleaned.split()
    if len(words) >= 4 and len(words) % 2 == 0:
        pairs = [' '.join(words[i:i + 2]) for i in range(0, len(words), 2)]
        author_pairs = [pair for pair in pairs if looks_like_author(pair)]
        if len(author_pairs) >= 2 and sum('-' in pair for pair in author_pairs) == 0:
            return author_pairs
    if has_author_markers:
        pairs = [' '.join(words[i:i + 2]) for i in range(0, len(words) - 1, 2)]
        author_pairs = [pair for pair in pairs if looks_like_author(pair)]
        if len(author_pairs) >= 2:
            return author_pairs
    return [cleaned] if looks_like_author(cleaned) else []


def extract_frontmatter(lines: list[str], limit: int = 30) -> FrontMatterExtraction:
    cleaned = [normalize_title_candidate(line) for line in lines if clean_line(line)]
    window = cleaned[:limit]

    section_headings = []
    for line in cleaned:
        heading = section_heading(line)
        if heading and heading not in section_headings:
            section_headings.append(heading)

    front = []
    for line in window:
        heading = section_heading(line)
        if heading and heading.lower() == 'abstract':
            break
        if re.match(r'^\d+(?:\.\d+)*\s+(?:introduction|method|discussion|experiment|conclusion)\b', line, flags=re.IGNORECASE):
            break
        front.append(line)

    authors = []
    title_lines = []
    seen_author = False
    for line in front:
        found_authors = split_joined_authors(line)
        if found_authors:
            seen_author = True
            authors.extend(found_authors)
            continue
        if seen_author:
            continue
        if not looks_like_title_noise(line) and not looks_like_section_heading(line):
            if len(line.split()) == 1 and title_lines and line[:1].isupper() and line.lower() not in TITLE_SUFFIX_WORDS:
                continue
            title_lines.append(line)

    if title_lines and len(title_lines[-1].split()) == 1 and title_lines[-1].lower() not in TITLE_SUFFIX_WORDS:
        title_lines = title_lines[:-1]

    title_candidates = []
    if title_lines:
        title_candidates.append(' '.join(title_lines).strip())
        title_candidates.extend(title_lines)

    seen = set()
    unique_titles = []
    for title in title_candidates:
        key = title.lower()
        if title and key not in seen:
            seen.add(key)
            unique_titles.append(title)

    seen = set()
    unique_authors = []
    for author in authors:
        key = author.lower()
        if key not in seen:
            seen.add(key)
            unique_authors.append(author)

    return FrontMatterExtraction(
        title_candidates=unique_titles[:8],
        authors=unique_authors[:6],
        section_headings=[h for h in section_headings if h.lower() != 'abstract'],
    )
