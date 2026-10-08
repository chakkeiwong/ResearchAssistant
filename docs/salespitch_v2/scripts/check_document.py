#!/usr/bin/env python3
"""Verify resolved citations, named local sources, PDF hashes and build warnings."""
import hashlib
import json
import re
import subprocess
from pathlib import Path
DOC=Path(__file__).resolve().parents[1]
ROOT=DOC.parents[1]
main='salespitch_cashflow_fx'
sources=json.loads((DOC/'review/source_catalog.json').read_text())
tex='\n'.join(p.read_text() for p in [DOC/f'{main}.tex',*sorted((DOC/'sections').glob('*.tex'))])
cites=set()
for match in re.finditer(r'\\cite\w*\*?(?:\[[^\]]*\])*\{([^}]+)\}',tex):
    cites.update(k.strip() for k in match[1].split(','))
bib=set(re.findall(r'@\w+\{([^,]+),',(DOC/'references.bib').read_text()))
catalog={r['citation_key'] for r in sources}
assert cites==bib==catalog,(cites,bib,catalog)
for r in sources:
    p=ROOT/r['local_path']
    assert p.read_bytes().startswith(b'%PDF'),p
    assert hashlib.sha256(p.read_bytes()).hexdigest()==r['sha256'],p
    assert p.name.endswith(f" {r['first_author_surname']}({r['publication_year']}).pdf"),p
    info=subprocess.check_output(['pdfinfo',str(p)],text=True)
    assert int(re.search(r'Pages:\s+(\d+)',info)[1])==r['pages']
log=(DOC/'build'/f'{main}.log').read_text()
bad=[line for line in log.splitlines() if re.search(r'Warning|Overfull|Underfull|Undefined control|^!',line)]
assert not bad,bad
assert 'Warning--' not in (DOC/'build/bibtex.stdout').read_text()
info=subprocess.check_output(['pdfinfo',str(DOC/f'{main}.pdf')],text=True)
pages=int(re.search(r'Pages:\s+(\d+)',info)[1])
result=dict(passed=True,cited_papers=len(cites),local_paper_pages=sum(r['pages'] for r in sources),
            manuscript_pages=pages,unresolved_citations=0,latex_warnings=bad,
            pdf_sha256=hashlib.sha256((DOC/f'{main}.pdf').read_bytes()).hexdigest(),
            limitation='Checks document and citation integrity, not completeness of the literature or empirical validity.')
(DOC/'review/document_checks.json').write_text(json.dumps(result,indent=2)+'\n')
print(f'PASS: {pages} manuscript pages, {len(cites)} citations/PDFs, no LaTeX warnings.')
