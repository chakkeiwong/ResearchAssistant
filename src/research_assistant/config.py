from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class AppPaths:
    root: Path
    local_research: Path
    analysis: Path
    papers_raw: Path
    papers_extracted: Path
    papers_source: Path
    metadata: Path
    summaries: Path
    links: Path
    reviews: Path
    review_metadata: Path
    indices: Path
    caches: Path
    derivations: Path
    experiments: Path
    graph_reports: Path
    benchmarks: Path
    benchmark_runs: Path
    synthesis: Path
    governance: Path
    jobs: Path
    exports: Path
    traceability: Path
    model_policies: Path
    collaboration: Path
    artifact_indices: Path
    service_contracts: Path
    operations: Path
    sops: Path


def get_paths(root: Path | None = None) -> AppPaths:
    project_root = (root or Path(__file__).resolve().parents[2]).resolve()
    local_research = project_root / "local_research"
    return AppPaths(
        root=project_root,
        local_research=local_research,
        analysis=local_research / "analysis",
        papers_raw=local_research / "papers" / "raw",
        papers_extracted=local_research / "papers" / "extracted",
        papers_source=local_research / "papers" / "source",
        metadata=local_research / "metadata",
        summaries=local_research / "summaries",
        links=local_research / "links",
        reviews=local_research / "reviews",
        review_metadata=local_research / "reviews" / "metadata",
        indices=local_research / "indices",
        caches=local_research / "caches",
        derivations=local_research / "analysis" / "derivations",
        experiments=local_research / "experiments",
        graph_reports=local_research / "analysis" / "citation_graph_reports",
        benchmarks=local_research / "benchmarks" / "manifests",
        benchmark_runs=local_research / "benchmarks" / "runs",
        synthesis=local_research / "analysis" / "synthesis",
        governance=local_research / "governance",
        jobs=local_research / "jobs",
        exports=local_research / "exports",
        traceability=local_research / "analysis" / "traceability",
        model_policies=local_research / "governance" / "model_policies",
        collaboration=local_research / "collaboration",
        artifact_indices=local_research / "indices" / "artifacts",
        service_contracts=local_research / "contracts" / "tools",
        operations=local_research / "governance" / "operations",
        sops=local_research / "governance" / "sops",
    )
