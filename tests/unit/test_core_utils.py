from __future__ import annotations

import json
from pathlib import Path

import pytest

from research_assistant.core_utils import atomic_write_bytes, canonical_json_bytes, sha256_bytes, sha256_file


def test_canonical_json_bytes_are_deterministic_and_strict() -> None:
    assert canonical_json_bytes({"b": 2, "a": "value"}) == b'{"a":"value","b":2}'
    with pytest.raises(ValueError):
        canonical_json_bytes({"value": float("nan")})


def test_atomic_write_and_hash_helpers(tmp_path: Path) -> None:
    path = tmp_path / "nested" / "artifact.json"
    value = canonical_json_bytes({"status": "passed"}) + b"\n"
    atomic_write_bytes(path, value)
    assert json.loads(path.read_text()) == {"status": "passed"}
    assert sha256_file(path) == sha256_bytes(value)
    assert not list(path.parent.glob(f".{path.name}.*.tmp"))
