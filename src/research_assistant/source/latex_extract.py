from __future__ import annotations

import re
from pathlib import Path
from typing import Any

SECTION_COMMANDS = ['part', 'chapter', 'section', 'subsection', 'subsubsection', 'paragraph', 'subparagraph']
MATH_ENVIRONMENTS = ['equation', 'equation*', 'align', 'align*', 'gather', 'gather*', 'multline', 'multline*']
COMMON_THEOREM_ENVIRONMENTS = {'theorem', 'lemma', 'proposition', 'definition', 'assumption', 'corollary', 'proof', 'remark'}


def _line_number(text: str, index: int) -> int:
    return text.count('\n', 0, index) + 1


def _latex_braced_argument(text: str, start: int) -> tuple[str, int] | None:
    # LaTeX titles and macro bodies often contain nested braces; a flat regex would truncate those audit anchors.
    if start >= len(text) or text[start] != '{':
        return None
    depth = 0
    out = []
    for index in range(start, len(text)):
        char = text[index]
        if char == '{':
            depth += 1
            if depth > 1:
                out.append(char)
        elif char == '}':
            depth -= 1
            if depth == 0:
                return ''.join(out), index + 1
            out.append(char)
        else:
            out.append(char)
    return None


def _section_matches(text: str) -> list[dict[str, Any]]:
    command_pattern = re.compile(r'\\(' + '|'.join(SECTION_COMMANDS) + r')\*?\s*')
    matches = []
    for match in command_pattern.finditer(text):
        arg = _latex_braced_argument(text, match.end())
        if arg is None:
            continue
        title, end = arg
        matches.append({'match': match, 'command': match.group(1), 'title': title.strip(), 'end': end})
    return matches


def _extract_sections(text: str) -> list[dict[str, Any]]:
    matches = _section_matches(text)
    sections = []
    for index, section_match in enumerate(matches):
        match = section_match['match']
        command = section_match['command']
        end = matches[index + 1]['match'].start() if index + 1 < len(matches) else len(text)
        body = text[section_match['end']:end].strip()
        # Keep section-local raw LaTeX so a reviewer can inspect evidence before turning it into human audit notes.
        labels = re.findall(r'\\label\{([^}]+)\}', body)
        sections.append({
            'level': SECTION_COMMANDS.index(command) + 1,
            'command': command,
            'title': section_match['title'],
            'line': _line_number(text, match.start()),
            'labels': labels,
            'raw_latex': body,
        })
    return sections


def _extract_environments(text: str, names: set[str] | list[str]) -> list[dict[str, Any]]:
    escaped = '|'.join(re.escape(name) for name in sorted(names, key=len, reverse=True))
    pattern = re.compile(r'\\begin\{(' + escaped + r')\}(.*?)\\end\{\1\}', re.DOTALL)
    blocks = []
    for match in pattern.finditer(text):
        body = match.group(2).strip()
        labels = re.findall(r'\\label\{([^}]+)\}', body)
        blocks.append({
            'environment': match.group(1),
            'line': _line_number(text, match.start()),
            'labels': labels,
            'raw_latex': match.group(0),
        })
    return blocks


def _extract_display_math(text: str) -> list[dict[str, Any]]:
    blocks = []
    for pattern in [re.compile(r'\\\[(.*?)\\\]', re.DOTALL), re.compile(r'\$\$(.*?)\$\$', re.DOTALL)]:
        for match in pattern.finditer(text):
            blocks.append({
                'environment': 'display_math',
                'line': _line_number(text, match.start()),
                'labels': re.findall(r'\\label\{([^}]+)\}', match.group(1)),
                'raw_latex': match.group(0),
            })
    blocks.sort(key=lambda row: row['line'])
    return blocks


def _theorem_environment_names(text: str) -> set[str]:
    names = set(COMMON_THEOREM_ENVIRONMENTS)
    for match in re.finditer(r'\\newtheorem\{([^}]+)\}', text):
        names.add(match.group(1))
    return names


def _extract_labels(text: str) -> list[dict[str, Any]]:
    return [{'key': match.group(1), 'line': _line_number(text, match.start())} for match in re.finditer(r'\\label\{([^}]+)\}', text)]


def _extract_references(text: str) -> list[dict[str, Any]]:
    pattern = re.compile(r'\\(ref|eqref|pageref|autoref|cref|Cref)\{([^}]+)\}')
    refs = []
    for match in pattern.finditer(text):
        refs.append({'command': match.group(1), 'key': match.group(2), 'line': _line_number(text, match.start())})
    return refs


def _extract_citations(text: str) -> list[dict[str, Any]]:
    pattern = re.compile(r'\\(cite|citet|citep|citealp|parencite|textcite)(?:\[[^]]*\])*\{([^}]+)\}')
    citations = []
    for match in pattern.finditer(text):
        keys = [key.strip() for key in match.group(2).split(',') if key.strip()]
        citations.append({'command': match.group(1), 'keys': keys, 'line': _line_number(text, match.start())})
    return citations


def _extract_macros(text: str) -> list[dict[str, Any]]:
    pattern = re.compile(r'\\(newcommand|renewcommand|providecommand|DeclareMathOperator)\s*\{?\\([^}\s]+)\}?((?:\[[^]]*\])*)\s*')
    macros = []
    for match in pattern.finditer(text):
        definition = ''
        arg = _latex_braced_argument(text, match.end())
        if arg is not None:
            definition = arg[0]
        macros.append({
            'command': match.group(1),
            'name': match.group(2),
            'arguments': match.group(3).strip(),
            'definition': definition,
            'line': _line_number(text, match.start()),
        })
    return macros


def _extract_bibliography(source_root: Path) -> list[dict[str, Any]]:
    entries = []
    entry_pattern = re.compile(r'@(\w+)\s*\{\s*([^,]+),(.*?)\n\}', re.DOTALL)
    field_pattern = re.compile(r'(\w+)\s*=\s*[\{\"]([^}\"]+)[\}\"]')
    for bib_path in sorted(source_root.rglob('*.bib')):
        text = bib_path.read_text(errors='ignore')
        for match in entry_pattern.finditer(text):
            fields = {field.group(1): field.group(2).strip() for field in field_pattern.finditer(match.group(3))}
            entries.append({'type': match.group(1), 'key': match.group(2).strip(), 'fields': fields, 'path': str(bib_path)})
    return entries


def extract_latex_structure(flattened_path: Path, *, source_root: Path | None = None) -> dict[str, Any]:
    text = flattened_path.read_text(errors='ignore')
    theorem_names = _theorem_environment_names(text)
    equations = _extract_environments(text, MATH_ENVIRONMENTS) + _extract_display_math(text)
    equations.sort(key=lambda row: row['line'])
    theorem_like_blocks = _extract_environments(text, theorem_names)
    bibliography = _extract_bibliography(source_root or flattened_path.parent)
    limitations = [
        # Source extraction is evidence for review, not a mathematical normalizer or macro expander.
        {'field': 'mathematics', 'status': 'raw_latex', 'note': 'Mathematical expressions are preserved as raw LaTeX, not normalized.'},
        {'field': 'macros', 'status': 'requires_review', 'note': 'Custom macro semantics are extracted but not expanded.'},
    ]
    return {
        'sections': _extract_sections(text),
        'equations': equations,
        'theorem_like_blocks': theorem_like_blocks,
        'labels': _extract_labels(text),
        'references': _extract_references(text),
        'citations': _extract_citations(text),
        'bibliography': bibliography,
        'macros': _extract_macros(text),
        'limitations': limitations,
    }
