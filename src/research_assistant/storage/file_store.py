from __future__ import annotations

from pathlib import Path
import json
from typing import Type, TypeVar

T = TypeVar("T")


class FileStore:
    def __init__(self, base: Path):
        self.base = base
        self.base.mkdir(parents=True, exist_ok=True)

    def write_json(self, path: Path, data: dict) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, indent=2, sort_keys=True))

    def read_json(self, path: Path) -> dict:
        return json.loads(path.read_text())

    def load_record(self, path: Path, cls: Type[T]) -> T:
        return cls.from_dict(self.read_json(path))
