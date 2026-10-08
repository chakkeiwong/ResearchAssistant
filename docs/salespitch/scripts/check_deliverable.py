"""Check citation coverage, preserved paper files, and the final LaTeX log."""
import hashlib
import json
from pathlib import Path
import re

root = Path(__file__).resolve().parents[3]
doc = root / "docs/salespitch"
manifest = json.loads((root / "dcos/papers/salespitch/manifest.json").read_text())
tex = "\n".join(p.read_text() for p in [doc / "salespitch_survey_proposal.tex", *sorted((doc / "sections").glob("*.tex"))])
citations = {key.strip() for group in re.findall(r"\\cite\w*\*?(?:\[[^\]]*\]){0,2}\{([^}]+)\}", tex) for key in group.split(",")}
bibkeys = set(re.findall(r"@\w+\s*\{\s*([^,]+),", (doc / "references.bib").read_text()))
catalog_keys = {entry["citation_key"] for entry in manifest}
assert citations == bibkeys == catalog_keys, (citations, bibkeys, catalog_keys)
for entry in manifest:
    path = root / entry["local_path"]
    data = path.read_bytes()
    assert data.startswith(b"%PDF"), path
    assert hashlib.sha256(data).hexdigest() == entry["sha256"], path
    assert path.name.endswith(f'{entry["first_author_surname"]}({entry["publication_year"]}).pdf'), path
log = (doc / "build/salespitch_survey_proposal.log").read_text()
warnings = [line for line in log.splitlines() if re.search(r"undefined|Overfull|Underfull|LaTeX Warning|Package .* Warning|^!", line)]
assert not warnings, warnings
assert (doc / "salespitch_survey_proposal.pdf").read_bytes() == (doc / "build/salespitch_survey_proposal.pdf").read_bytes()
result = {"status": "PASS", "cited_papers": len(citations), "bibliography_entries": len(bibkeys), "verified_downloaded_pdfs": len(manifest), "latex_warnings": warnings, "cpu_only": True, "scope": "File and citation integrity; not empirical validation of a bank model."}
(doc / "review/deliverable_checks.json").write_text(json.dumps(result, indent=2) + "\n")
print(json.dumps(result, indent=2))
