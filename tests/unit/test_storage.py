from __future__ import annotations

from pathlib import Path

from research_assistant.storage.file_store import FileStore


def test_file_store_round_trip(tmp_path: Path) -> None:
    store = FileStore(tmp_path)
    target = tmp_path / 'x.json'
    store.write_json(target, {'a': 1})
    assert store.read_json(target) == {'a': 1}
