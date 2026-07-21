from __future__ import annotations

from typing import Any, Iterable


NONCLAIM_METADATA_KEYS = {
    "abstentions",
    "caveats",
    "limitations",
    "non_claims",
    "not_concluded",
    "out_of_scope",
    "what_is_not_concluded",
}

NONCLAIM_ROW_ID_TOKENS = (
    "abstention",
    "caveat",
    "limitation",
    "nonclaim",
    "non_claim",
    "not_concluded",
    "out_of_scope",
)

NONCLAIM_ROW_PHRASES = (
    "cannot conclude",
    "does not conclude",
    "does not establish",
    "does not prove",
    "insufficient evidence to conclude",
    "is not established",
    "no claim is made",
    "not assessed",
    "not concluded",
    "not enough evidence",
    "not established",
    "not evaluated",
    "not evidence of",
    "not prove",
    "out of scope",
    "what is not concluded",
)

def normalize_claim_text(value: Any) -> str:
    return " ".join(str(value).lower().strip().split())


def is_nonclaim_claim_row(row: dict[str, Any]) -> bool:
    claim_id = normalize_claim_text(row.get("claim_id", ""))
    claim_text = normalize_claim_text(row.get("claim", ""))
    if any(token in claim_id for token in NONCLAIM_ROW_ID_TOKENS):
        return True
    return any(phrase in claim_text for phrase in NONCLAIM_ROW_PHRASES)


def nonclaim_rows_in_claims(claims: Iterable[Any]) -> list[str]:
    rows: list[str] = []
    for row in claims:
        if not isinstance(row, dict):
            continue
        if is_nonclaim_claim_row(row):
            rows.append(str(row.get("claim_id", "unknown_claim")))
    return sorted(set(rows))


def supported_claim_texts(claims: Iterable[Any]) -> dict[str, str]:
    supported: dict[str, str] = {}
    for row in claims:
        if not isinstance(row, dict):
            continue
        if str(row.get("status", "")) != "supported":
            continue
        claim_text = normalize_claim_text(row.get("claim", ""))
        if not claim_text:
            continue
        claim_id = str(row.get("claim_id", "unknown_claim"))
        supported[claim_id] = claim_text
    return supported


def claim_laundering_hits(payload: Any, gold_claims: Iterable[Any]) -> list[str]:
    expected = tuple(supported_claim_texts(gold_claims).values())
    hits: list[str] = []
    for path, value in _iter_nonclaim_metadata_strings(payload):
        normalized = normalize_claim_text(value)
        if not normalized:
            continue
        for claim_text in expected:
            if _metadata_contains_claim(normalized, claim_text):
                hits.append(path)
                break
    return sorted(set(hits))


def _metadata_contains_claim(metadata_text: str, claim_text: str) -> bool:
    if not claim_text:
        return False
    if claim_text in metadata_text:
        return True
    metadata_words = metadata_text.split()
    return len(metadata_words) >= 6 and metadata_text in claim_text


def _iter_nonclaim_metadata_strings(value: Any, path: str = "$") -> Iterable[tuple[str, str]]:
    if isinstance(value, dict):
        for key, child in value.items():
            key_path = f"{path}.{key}"
            if key in NONCLAIM_METADATA_KEYS:
                yield from _iter_strings(child, key_path)
            elif key != "claims":
                yield from _iter_nonclaim_metadata_strings(child, key_path)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from _iter_nonclaim_metadata_strings(child, f"{path}[{index}]")


def _iter_strings(value: Any, path: str) -> Iterable[tuple[str, str]]:
    if isinstance(value, str):
        yield path, value
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from _iter_strings(child, f"{path}[{index}]")
    elif isinstance(value, dict):
        for key, child in value.items():
            yield from _iter_strings(child, f"{path}.{key}")
