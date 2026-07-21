"""Small, bounded BibTeX field readers used by source-evidence workers."""

from __future__ import annotations

import re


def read_text_field(entry: str, field: str, *, max_length: int = 500) -> str | None:
    """Read one braced or quoted BibTeX text field, including nested braces."""
    match = re.search(rf"(?is)\b{re.escape(field)}\s*=\s*", entry)
    if match is None or match.end() >= len(entry):
        return None

    opener = entry[match.end()]
    if opener not in {'{', '"'}:
        return None
    start = match.end() + 1
    escaped = False
    if opener == '"':
        depth = 0
        end = start
        while end < len(entry):
            char = entry[end]
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == "{":
                depth += 1
            elif char == "}" and depth:
                depth -= 1
            elif char == '"' and depth == 0:
                break
            end += 1
    else:
        depth = 1
        end = start
        while end < len(entry) and depth:
            char = entry[end]
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == "{":
                depth += 1
            elif char == "}":
                depth -= 1
                if depth == 0:
                    break
            end += 1

    if end >= len(entry):
        return None
    value = entry[start:end].replace("{", "").replace("}", "")
    value = " ".join(value.replace("\n", " ").split())
    return value[:max_length] or None


__all__ = ["read_text_field"]
