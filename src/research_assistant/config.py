from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class AppPaths:
    root: Path
    local_research: Path
    papers_raw: Path
    papers_extracted: Path
    metadata: Path
    summaries: Path
    links: Path
    reviews: Path
    indices: Path
    caches: Path


def get_paths(root: Path | None = None) -> AppPaths:
    project_root = (root or Path(__file__).resolve().parents[2]).resolve()
    local_research = project_root / "local_research"
    return AppPaths(
        root=project_root,
        local_research=local_research,
        papers_raw=local_research / "papers" / "raw",
        papers_extracted=local_research / "papers" / "extracted",
        metadata=local_research / "metadata",
        summaries=local_research / "summaries",
        links=local_research / "links",
        reviews=local_research / "reviews",
        indices=local_research / "indices",
        caches=local_research / "caches",
    )
