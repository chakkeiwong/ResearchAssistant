from __future__ import annotations

import re
from pathlib import Path
from typing import Any

_INCLUDE_RE = re.compile(r'\\(?:input|include)\{([^}]+)\}')


def _candidate_score(path: Path, text: str, all_tex_files: list[Path]) -> dict[str, Any]:
    score = 0
    reasons = []
    if '\\documentclass' in text:
        score += 50
        reasons.append('has documentclass')
    if '\\begin{document}' in text:
        score += 30
        reasons.append('has begin document')
    if re.search(r'\\title\s*\{', text):
        score += 5
        reasons.append('has title')
    if re.search(r'\\begin\s*\{abstract\}', text):
        score += 5
        reasons.append('has abstract')
    includes = _INCLUDE_RE.findall(text)
    score += min(len(includes), 10)
    if includes:
        reasons.append('has includes')
    if path.name.lower() in {'main.tex', 'paper.tex', 'article.tex', 'ms.tex'}:
        score += 3
        reasons.append('common main filename')
    return {
        'path': str(path),
        'score': score,
        'reasons': reasons,
        'include_count': len(includes),
        'tex_file_count': len(all_tex_files),
    }


def detect_main_tex(source_root: Path) -> dict[str, Any]:
    tex_files = sorted(path for path in source_root.rglob('*.tex') if path.is_file())
    candidates = []
    for path in tex_files:
        text = path.read_text(errors='ignore')
        candidates.append(_candidate_score(path, text, tex_files))
    candidates.sort(key=lambda row: row['score'], reverse=True)
    return {
        'main_path': candidates[0]['path'] if candidates and candidates[0]['score'] > 0 else None,
        'candidates': candidates,
    }
