from __future__ import annotations

import io
import json
import tarfile
from pathlib import Path

import pytest

from research_assistant.survey.m20_credential_free_worker import (
    M20CredentialFreeError,
    build_credential_free_evidence,
    extract_backward_reference_candidates,
    parse_openalex_forward_candidates,
)


def _tar(rows: dict[str, bytes], *, special: tarfile.TarInfo | None = None) -> bytes:
    stream = io.BytesIO()
    with tarfile.open(fileobj=stream, mode="w:gz") as archive:
        for name, raw in rows.items():
            info = tarfile.TarInfo(name)
            info.size = len(raw)
            archive.addfile(info, io.BytesIO(raw))
        if special is not None:
            archive.addfile(special)
    return stream.getvalue()


def _source(*, with_reference: bool = True) -> bytes:
    bibliography = b"" if not with_reference else b"""
@article{villani2008,
  title={Optimal Transport: Old and New},
  doi={10.1007/978-3-540-71050-9}
}
@misc{genevay2019,
  title={Learning Generative Models with Sinkhorn Divergences},
  eprint={arXiv:1706.00292}
}
"""
    return _tar({"main.tex": b"\\documentclass{article}\n\\begin{document}\n\\cite{villani2008}\n\\end{document}", "refs.bib": bibliography})


def _work(work_id: str = "W1", *, cites_seed: bool = True) -> dict:
    return {
        "id": f"https://openalex.org/{work_id}",
        "display_name": "A citing work",
        "doi": "https://doi.org/10.1000/citing",
        "publication_year": 2024,
        "cited_by_count": 3,
        "referenced_works": ["https://openalex.org/W4226072009"] if cites_seed else [],
    }


def _forward(*, works: list[dict] | None = None, cost: float = 0.0001) -> bytes:
    rows = [_work()] if works is None else works
    return json.dumps({
        "meta": {"count": len(rows), "page": 1, "per_page": 10, "cost_usd": cost},
        "results": rows,
        "group_by": [],
    }, sort_keys=True).encode()


def test_source_archive_extracts_only_sanitized_identifier_candidates() -> None:
    result = extract_backward_reference_candidates(_source())

    assert result["candidate_count"] == 2
    assert {row["candidate_id"] for row in result["candidates"]} == {
        "arxiv:1706.00292",
        "doi:10.1007/978-3-540-71050-9",
    }
    assert all("raw" not in row for row in result["candidates"])


@pytest.mark.parametrize("name", ["../escape.tex", "/absolute.bib", "dir\\bad.bib"])
def test_source_archive_rejects_unsafe_member_paths(name: str) -> None:
    with pytest.raises(M20CredentialFreeError, match="source_member_path_invalid"):
        extract_backward_reference_candidates(_tar({name: b"text"}))


@pytest.mark.parametrize("kind", [tarfile.SYMTYPE, tarfile.LNKTYPE, tarfile.CHRTYPE])
def test_source_archive_rejects_links_and_devices(kind: bytes) -> None:
    special = tarfile.TarInfo("unsafe.tex")
    special.type = kind
    special.linkname = "target"

    with pytest.raises(M20CredentialFreeError, match="source_member_type_forbidden"):
        extract_backward_reference_candidates(_tar({"main.tex": b"text"}, special=special))


def test_source_archive_rejects_member_expansion_cap() -> None:
    with pytest.raises(M20CredentialFreeError, match="source_member_cap_exceeded"):
        extract_backward_reference_candidates(_tar({"large.bib": b"x" * 2_000_001}))


def test_bibitem_identifier_is_admitted_without_raw_text() -> None:
    source = _tar({"main.tex": b"\\bibitem{paper} Example. doi:10.1234/example.2024"})
    result = extract_backward_reference_candidates(source)

    assert result["candidates"] == [{
        "candidate_id": "doi:10.1234/example.2024",
        "identifiers": ["doi:10.1234/example.2024"],
        "bibliography_key": "paper",
        "title": None,
        "source_member": "main.tex",
    }]


def test_malformed_bibliography_identifiers_are_not_admitted() -> None:
    source = _tar({
        "refs.bib": b"@misc{bad, doi={10.1234/}, eprint={arXiv:2201.12}}",
    })
    result = extract_backward_reference_candidates(source)

    assert result["candidate_count"] == 0


def test_forward_parser_requires_each_work_to_bind_exact_seed() -> None:
    result = parse_openalex_forward_candidates(_forward())

    assert result["candidate_count"] == 1
    assert result["cost_usd"] == "0.0001"
    assert result["candidates"][0]["cites_seed_openalex_id"] == "W4226072009"

    with pytest.raises(M20CredentialFreeError, match="forward_edge_not_bound_to_seed"):
        parse_openalex_forward_candidates(_forward(works=[_work(cites_seed=False)]))


def test_forward_parser_rejects_cost_contradiction_and_empty_layer() -> None:
    with pytest.raises(M20CredentialFreeError, match="forward_cost_contradiction"):
        parse_openalex_forward_candidates(_forward(cost=0.001))
    with pytest.raises(M20CredentialFreeError, match="forward_candidates_empty"):
        build_credential_free_evidence(_source(), _forward(works=[]))


def test_forward_parser_rejects_boolean_page_number() -> None:
    value = json.loads(_forward())
    value["meta"]["page"] = True
    with pytest.raises(M20CredentialFreeError, match="forward_page_invalid"):
        parse_openalex_forward_candidates(json.dumps(value).encode())


def test_forward_parser_rejects_duplicate_work_identity() -> None:
    with pytest.raises(M20CredentialFreeError, match="forward_work_duplicate"):
        parse_openalex_forward_candidates(_forward(works=[_work(), _work()]))


def test_combined_synthetic_evidence_is_deterministic_and_non_promoting() -> None:
    source = _source()
    forward = _forward()
    first = build_credential_free_evidence(source, forward)
    second = build_credential_free_evidence(source, forward)

    assert first == second
    assert first["status"] == "passed"
    assert "m20_completion" in first["nonclaims"]


def test_empty_backward_layer_is_a_veto() -> None:
    with pytest.raises(M20CredentialFreeError, match="backward_candidates_empty"):
        build_credential_free_evidence(_source(with_reference=False), _forward())


def test_module_has_no_credential_interface() -> None:
    source = Path("src/research_assistant/survey/m20_credential_free_worker.py").read_text()
    assert "OPENALEX_API_KEY" not in source
    assert "authorization" not in source.casefold()
