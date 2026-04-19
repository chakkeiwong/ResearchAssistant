from __future__ import annotations

import hashlib
import shutil
from pathlib import Path
from urllib.parse import urlparse

from research_assistant.paths import slugify


def canonical_paper_id(source: str) -> str:
    parsed = urlparse(source)
    if parsed.scheme and parsed.netloc:
        base = parsed.path.rsplit('/', 1)[-1] or parsed.netloc
    else:
        base = Path(source).stem or source
    slug = slugify(base)
    digest = hashlib.sha1(source.encode('utf-8')).hexdigest()[:8]
    return f"paper_{slug}_{digest}"


def store_raw_source(source: str, destination_dir: Path, paper_id: str) -> Path:
    destination_dir.mkdir(parents=True, exist_ok=True)
    src = Path(source).expanduser().resolve()
    suffix = src.suffix or '.pdf'
    dst = destination_dir / f"{paper_id}{suffix}"
    shutil.copy2(src, dst)
    return dst
