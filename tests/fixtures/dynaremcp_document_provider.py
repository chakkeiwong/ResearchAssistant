from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path


def _hash(value: dict) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(raw).hexdigest()


def main(argv: list[str]) -> int:
    if len(argv) != 6 or argv[:2] != ["document-utility", "check"]:
        return 2
    request_path = Path(argv[3])
    output_path = Path(argv[5])
    request = json.loads(request_path.read_text(encoding="utf-8"))
    result = {
        "schema_version": "dynaremcp.document_utility_result.v1",
        "request_id": request["request_id"],
        "request_sha256": _hash(request),
        "accepted": True,
        "findings": [],
        "index": {"entry_path": request["entry_document"]},
    }
    result["result_sha256"] = _hash(result)
    output_path.write_text(json.dumps(result), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
