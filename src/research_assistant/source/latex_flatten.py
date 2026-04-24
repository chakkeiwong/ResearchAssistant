from __future__ import annotations

import re
from pathlib import Path
from typing import Any

_INCLUDE_RE = re.compile(r'^(?P<prefix>\s*)\\(?P<kind>input|include)\{(?P<target>[^}]+)\}', re.MULTILINE)


def _resolve_include(target: str, current_dir: Path, source_root: Path) -> Path | None:
    raw = Path(target)
    if raw.suffix != '.tex':
        raw = raw.with_suffix('.tex')
    candidate = (current_dir / raw).resolve()
    try:
        candidate.relative_to(source_root.resolve())
    except ValueError:
        return None
    return candidate if candidate.exists() else None


def flatten_latex_bundle(main_path: Path, source_root: Path, output_path: Path) -> dict[str, Any]:
    visited: set[Path] = set()
    included_files: list[str] = []
    unresolved: list[dict[str, str]] = []

    def expand(path: Path) -> str:
        resolved = path.resolve()
        if resolved in visited:
            unresolved.append({'target': str(path), 'reason': 'include cycle skipped'})
            return ''
        visited.add(resolved)
        included_files.append(str(resolved))
        text = resolved.read_text(errors='ignore')

        def replace(match: re.Match[str]) -> str:
            target = match.group('target')
            include_path = _resolve_include(target, resolved.parent, source_root)
            if include_path is None:
                unresolved.append({'target': target, 'reason': 'not found or outside source root'})
                return match.group(0)
            return expand(include_path)

        return _INCLUDE_RE.sub(replace, text)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    flattened = expand(main_path)
    output_path.write_text(flattened)
    report = {
        'main_path': str(main_path),
        'flattened_path': str(output_path),
        'included_files': included_files,
        'unresolved_includes': unresolved,
    }
    (output_path.parent / 'flatten_report.json').write_text(__import__('json').dumps(report, indent=2, sort_keys=True))
    return report
