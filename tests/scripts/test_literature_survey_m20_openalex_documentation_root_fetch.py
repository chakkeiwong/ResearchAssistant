from __future__ import annotations

import importlib.util
import json
import shutil
from email.message import Message
from pathlib import Path

import pytest


SCRIPT = Path("scripts/literature_survey_m20_openalex_documentation_root_fetch.py").resolve()
SPEC = importlib.util.spec_from_file_location("m20_openalex_root", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class Response:
    def __init__(self, body: bytes, url: str, *, content_type: str = "text/html") -> None:
        self.body = body
        self.offset = 0
        self.status = 200
        self.url = url
        self.headers = Message()
        self.headers["Content-Type"] = content_type
        self.headers["Content-Length"] = str(len(body))

    def read(self, size: int = -1) -> bytes:
        chunk = self.body[self.offset:self.offset + size]
        self.offset += len(chunk)
        return chunk

    def geturl(self) -> str:
        return self.url

    def getcode(self) -> int:
        return self.status

    def close(self) -> None:
        pass


class Opener:
    def __init__(self, response: Response) -> None:
        self.response = response
        self.requests = []

    def open(self, request, timeout):  # noqa: ANN001, ANN201
        self.requests.append((request, timeout))
        return self.response


def _prior(tmp_path: Path) -> Path:
    tmp_path.mkdir(parents=True, exist_ok=True)
    path = tmp_path / "prior.json"
    shutil.copyfile(MODULE.PRIOR_MANIFEST, path)
    return path


def _ledger(tmp_path: Path) -> tuple[Path, dict]:
    prior = _prior(tmp_path)
    ledger_path = tmp_path / "ledger.json"
    output = tmp_path / "output"
    ledger = {
        "schema_version": MODULE.SCHEMA,
        "status": "reviewed_ready",
        "script_path": str(SCRIPT),
        "script_sha256": MODULE.sha256_path(SCRIPT),
        "base_script_path": str(MODULE.BASE_SCRIPT),
        "base_script_sha256": MODULE.sha256_path(MODULE.BASE_SCRIPT),
        "prior_manifest_path": str(MODULE.PRIOR_MANIFEST),
        "prior_manifest_sha256": MODULE.PRIOR_MANIFEST_SHA256,
        "command": [MODULE.sys.executable, str(SCRIPT), "--ledger", str(ledger_path), "--output-root", str(output)],
        "prior_transaction_count": 2,
        "prior_accepted_response_body_bytes": 160783,
        "campaign_transaction_cap": 6,
        "campaign_body_byte_cap": 8000000,
        "request": {
            "request_index": 3,
            "document_id": "openalex_documentation_root",
            "provider": "openalex",
            "url": MODULE.TARGET_URL,
            "semantic_role": "current_official_documentation_link_inventory",
            "requirement": "indispensable",
        },
    }
    ledger_path.write_text(json.dumps(ledger))
    return ledger_path, ledger


def test_ledger_binds_prior_budget_script_and_exact_request(tmp_path: Path) -> None:
    ledger_path, ledger = _ledger(tmp_path)
    assert MODULE.validate_ledger(ledger_path, script_path=SCRIPT)["request"]["url"] == MODULE.TARGET_URL
    ledger["request"]["url"] = "https://developers.openalex.org/other"
    ledger_path.write_text(json.dumps(ledger))
    with pytest.raises(MODULE.BASE.FetchContractError, match="reviewed row"):
        MODULE.validate_ledger(ledger_path, script_path=SCRIPT)

    ledger_path, ledger = _ledger(tmp_path / "prior-drift")
    prior_path = Path(ledger["prior_manifest_path"])
    prior = json.loads(prior_path.read_text())
    prior["aggregate_received_response_body_bytes"] += 1
    substitute = tmp_path / "prior-drift" / "substitute.json"
    substitute.parent.mkdir(parents=True, exist_ok=True)
    substitute.write_text(json.dumps(prior))
    ledger["prior_manifest_path"] = str(substitute)
    ledger["prior_manifest_sha256"] = MODULE.sha256_path(substitute)
    ledger_path.write_text(json.dumps(ledger))
    with pytest.raises(MODULE.BASE.FetchContractError, match="identity differs"):
        MODULE.validate_ledger(ledger_path, script_path=SCRIPT)

    ledger_path, ledger = _ledger(tmp_path / "redirect-drift")
    prior = json.loads(MODULE.PRIOR_MANIFEST.read_text())
    prior["requests"][1]["location"] = "https://developers.openalex.org/other"
    substitute = tmp_path / "redirect-drift" / "substitute.json"
    substitute.write_text(json.dumps(prior))
    ledger["prior_manifest_path"] = str(substitute)
    ledger["prior_manifest_sha256"] = MODULE.sha256_path(substitute)
    ledger_path.write_text(json.dumps(ledger))
    with pytest.raises(MODULE.BASE.FetchContractError, match="identity differs"):
        MODULE.validate_ledger(ledger_path, script_path=SCRIPT)


def test_command_and_remaining_campaign_cap_fail_closed(tmp_path: Path, monkeypatch) -> None:  # noqa: ANN001
    ledger_path, ledger_raw = _ledger(tmp_path)
    ledger = MODULE.validate_ledger(ledger_path, script_path=SCRIPT)
    with pytest.raises(MODULE.BASE.FetchContractError, match="argv differs"):
        MODULE.validate_command(ledger, argv=["wrong"])

    monkeypatch.setattr(MODULE.BASE, "PER_RESPONSE_CAP", MODULE.REMAINING_BODY_BYTE_CAP + 1)
    with pytest.raises(MODULE.BASE.FetchContractError, match="remaining campaign cap"):
        MODULE.validate_ledger(ledger_path, script_path=SCRIPT)
    assert ledger_raw["campaign_body_byte_cap"] == 8_000_000


def test_success_retains_root_and_only_same_host_links(tmp_path: Path) -> None:
    ledger_path, _ = _ledger(tmp_path)
    ledger = MODULE.validate_ledger(ledger_path, script_path=SCRIPT)
    body = b'''<a href="/api-reference/works">Works</a><a href="https://developers.openalex.org/api-reference/works#x">Dup</a><a href="https://api.openalex.org/works">API</a><a href="https://example.org/">Other</a>'''
    opener = Opener(Response(body, MODULE.TARGET_URL))
    result = MODULE.execute(ledger, output_root=tmp_path / "result", opener=opener)
    assert result["status"] == "fetched_pending_contract_extraction"
    assert result["campaign_attempted_transaction_count"] == 3
    assert result["campaign_transactions_remaining"] == 3
    assert result["campaign_accepted_response_body_bytes"] == 160783 + len(body)
    inventory = json.loads((tmp_path / "result" / "link_inventory.json").read_text())
    assert inventory["links"] == [{"link_text": "Works", "url": "https://developers.openalex.org/api-reference/works"}]
    assert len(opener.requests) == 1


def test_no_same_host_links_is_blocker_and_existing_root_fails(tmp_path: Path) -> None:
    ledger_path, _ = _ledger(tmp_path)
    ledger = MODULE.validate_ledger(ledger_path, script_path=SCRIPT)
    output = tmp_path / "result"
    result = MODULE.execute(ledger, output_root=output, opener=Opener(Response(b"<p>none</p>", MODULE.TARGET_URL)))
    assert result["status"] == "blocked_no_same_host_documentation_links"
    assert result["campaign_request_index"] == 3
    assert result["link_inventory_error_code"] == "no_same_host_documentation_links"
    second_opener = Opener(Response(b"x", MODULE.TARGET_URL))
    with pytest.raises(FileExistsError):
        MODULE.execute(ledger, output_root=output, opener=second_opener)
    assert second_opener.requests == []


def test_invalid_utf8_retains_fetch_evidence_and_writes_campaign_blocker(tmp_path: Path) -> None:
    ledger_path, _ = _ledger(tmp_path)
    ledger = MODULE.validate_ledger(ledger_path, script_path=SCRIPT)
    output = tmp_path / "result"
    result = MODULE.execute(ledger, output_root=output, opener=Opener(Response(b"\xff", MODULE.TARGET_URL)))
    assert result["status"] == "blocked_link_inventory_error"
    assert result["link_inventory_error_code"] == "invalid_document"
    assert (output / "fetch_manifest.json").is_file()
    assert (output / "campaign_manifest.json").is_file()


def test_text_plain_cannot_be_promoted_to_html_link_inventory(tmp_path: Path) -> None:
    ledger_path, _ = _ledger(tmp_path)
    ledger = MODULE.validate_ledger(ledger_path, script_path=SCRIPT)
    output = tmp_path / "result"
    response = Response(b'<a href="/docs">Docs</a>', MODULE.TARGET_URL, content_type="text/plain")
    result = MODULE.execute(ledger, output_root=output, opener=Opener(response))
    assert result["status"] == "blocked_link_inventory_error"
    assert result["link_inventory"] is None
    assert result["link_inventory_error_code"] == "not_html"
    assert not (output / "link_inventory.json").exists()


def test_inventory_write_failure_does_not_advertise_artifact(tmp_path: Path, monkeypatch) -> None:  # noqa: ANN001
    ledger_path, _ = _ledger(tmp_path)
    ledger = MODULE.validate_ledger(ledger_path, script_path=SCRIPT)
    original_write = MODULE.Path.write_bytes

    def fail_inventory(path: Path, raw: bytes) -> int:
        if path.name == "link_inventory.json":
            raise OSError("forced")
        return original_write(path, raw)

    monkeypatch.setattr(MODULE.Path, "write_bytes", fail_inventory)
    output = tmp_path / "result"
    result = MODULE.execute(
        ledger,
        output_root=output,
        opener=Opener(Response(b'<a href="/docs">Docs</a>', MODULE.TARGET_URL)),
    )
    assert result["status"] == "blocked_link_inventory_error"
    assert result["link_inventory"] is None
    assert result["link_inventory_error_code"] == "link_inventory_io_error"
    assert not (output / "link_inventory.json").exists()


def test_inherited_compression_blocker_closes_campaign_manifest(tmp_path: Path) -> None:
    ledger_path, _ = _ledger(tmp_path)
    ledger = MODULE.validate_ledger(ledger_path, script_path=SCRIPT)
    response = Response(b"compressed", MODULE.TARGET_URL)
    response.headers["Content-Encoding"] = "gzip"
    output = tmp_path / "result"
    result = MODULE.execute(ledger, output_root=output, opener=Opener(response))
    assert result["status"] == "blocked"
    fetch = json.loads((output / "fetch_manifest.json").read_text())
    assert fetch["requests"][0]["error_code"] == "compressed_response"
    assert (output / "campaign_manifest.json").is_file()


def test_campaign_postcheck_blocks_impossible_aggregate(monkeypatch, tmp_path: Path) -> None:  # noqa: ANN001
    ledger_path, _ = _ledger(tmp_path)
    ledger = MODULE.validate_ledger(ledger_path, script_path=SCRIPT)
    monkeypatch.setattr(MODULE, "PRIOR_ACCEPTED_BODY_BYTES", MODULE.CAMPAIGN_BODY_BYTE_CAP)
    output = tmp_path / "result"
    result = MODULE.execute(ledger, output_root=output, opener=Opener(Response(b"x", MODULE.TARGET_URL)))
    assert result["status"] == "blocked_campaign_body_cap_exceeded"
    assert result["link_inventory"] is None
    assert result["link_inventory_error_code"] == "campaign_body_cap_exceeded"
