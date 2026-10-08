"""Build v2's source catalog without changing the original proposal's manifest."""
from pathlib import Path
import hashlib, json, re, shutil, subprocess
ROOT = Path(__file__).resolve().parents[3]
STORE = ROOT / 'dcos/papers/salespitch'
CACHE = ROOT / '.localresources/bank-sales-v2-2026-10-08/papers'
DOC = ROOT / 'docs/salespitch_v2'
rows = []
old = json.loads((STORE/'manifest.json').read_text())
for row in old:
    if row['citation_key'] in ['montero2021global','salinas2020deepar','wager2021policy']:
        rows.append(row.copy())

new = [
 ('kalman1960','kalman','A New Approach to Linear Filtering and Prediction Problems','Kalman',1960,'10.1115/1.3662552','https://eceweb1.rutgers.edu/~gajic/pdffiles/519KalmanFiltering/kalman1960.pdf','Transcription of published paper','Optimal estimates and orthogonal projections; Theorem 3, equations (21)--(29); Gaussian conditions and Appendix','Optimal linear filtering; exact conditional distribution requires Gaussian assumptions.'),
 ('shumway1982','shumway','An Approach to Time Series Smoothing and Forecasting Using the EM Algorithm','Shumway',1982,'10.1111/j.1467-9892.1982.tb00349.x','https://dsstoffer.github.io/files/em.pdf','Published scan, OCR sidecar','Section 2 equations (1)--(18); missing observations discussion; Appendix (A1)--(A12)','Linear Gaussian EM; no exact hurdle-model inference or guarantee of global likelihood optimum.'),
 ('stock2002','stock','Forecasting Using Principal Components from a Large Number of Predictors','Stock',2002,'10.1198/016214502388618960','https://www.princeton.edu/~mwatson/papers/Stock_Watson_JASA_2002.pdf','Published paper','Sections 2.1--2.3, equations (1)--(6), Theorems 1--2 and proof discussion/Appendix; Section 4 empirical design','Factor compression; large N and large T assumptions do not validate 36-month causal macro estimates.'),
 ('rangapuram2018','deepstate-long','Deep State Space Models for Time Series Forecasting','Rangapuram',2018,None,'https://papers.nips.cc/paper_files/paper/2018/file/5cf68969fb67aa6082363a6d4e6468e2-Supplemental.zip','Official long version extracted from NeurIPS supplementary ZIP','Sections 3--4 equations (1)--(8); Section 5; Appendices A.1--A.4','RNN-parameterized Gaussian state-space likelihood; non-Gaussian extension is approximate and not a causal identification result.'),
 ('pearl2009','pearl','Causal Inference in Statistics - An Overview','Pearl',2009,'10.1214/09-SS057','https://ftp.cs.ucla.edu/pub/stat_ser/r350.pdf','Author technical report of published survey','Sections 3.2--3.4, intervention definitions, back-door adjustment, Definition 4 and equations (27)--(28); Section 4 causal assumptions','Structural interpretation and identification distinctions; not evidence that GDP is exogenous.'),
 ('smith1985','smith',"The Determinants of Firms' Hedging Policies",'Smith',1985,'10.2307/2330757','https://cpb-us-w2.wpmucdn.com/u.osu.edu/dist/0/30211/files/2016/05/determinantsofirms-29oslo5.pdf','Published scan, OCR sidecar','Sections II--IV: tax state prices, distress costs and managerial compensation; equations (1)--(2)','Economic reasons for corporate hedging; historical tax examples are not current tax-law claims.'),
 ('froot1993','froot','Risk Management - Coordinating Corporate Investment and Financing Policies','Froot',1993,'10.1111/j.1540-6261.1993.tb05123.x','https://www.nber.org/system/files/working_papers/w4084/w4084.pdf','NBER working paper 4084, May 1992; journal publication 1993','Working-paper Sections 3--5, equations (1)--(6), investment/financing hedge conditions and FX exposure, Appendix derivation of (24)','Concavity from costly external finance and investment opportunities; local CARA utility is a separate approximation.'),
 ('mcfadden1974','mcfadden','Conditional Logit Analysis of Qualitative Choice Behavior','McFadden',1974,None,'https://eml.berkeley.edu/reprints/mcfadden/zarembka.pdf','Published chapter scan, OCR sidecar','Section I equations (12)--(13), Section II equations (18)--(20), rank and existence conditions','Gumbel random utility yields conditional logit; not generic causal effects of prices or contacts.'),
 ('mcfadden2000','mixedlogit','Mixed MNL Models for Discrete Response','McFadden',2000,'10.1002/1099-1255(200009/10)15:5<447::AID-JAE570>3.0.CO;2-1','https://eml.berkeley.edu/wp/mcfadden0500/mcfadden0500.pdf','Author manuscript revised May 15, 2000','Section I equation (1), Section II Theorem 1 and Appendix proof structure, Section III equations (4)--(5), Section IV mixing tests','Mixed-logit integration and simulated likelihood; finite simulation log likelihood is biased; flexibility does not identify missing choice sets.'),
]
for key,cache,title,surname,year,doi,url,version,anchors,limit in new:
    filename=f'{title} {surname}({year}).pdf'
    target=STORE/filename
    source=CACHE/(cache+'.pdf')
    assert source.read_bytes().startswith(b'%PDF'), source
    if target.exists():
        assert target.read_bytes()==source.read_bytes(), 'Refuse to overwrite different source'
    else:
        shutil.copyfile(source,target)
    info=subprocess.check_output(['pdfinfo',str(target)],text=True)
    rows.append(dict(citation_key=key,title=title,first_author_surname=surname,publication_year=year,
        local_path=str(target.relative_to(ROOT)),download_url=url,doi=doi,version=version,
        pages=int(re.search(r'Pages:\s+(\d+)',info).group(1)),
        sha256=hashlib.sha256(target.read_bytes()).hexdigest(),technical_anchors=anchors,
        application_limit=limit,retrieval_date='2026-10-08'))
for r in rows:
    r['retraction_status']='No notice encountered in inspected primary records; not an exhaustive registry clearance'
(STORE/'manifest-v2.json').write_text(json.dumps(rows,indent=2,ensure_ascii=False)+'\n')
(DOC/'review/source_catalog.json').write_text(json.dumps(rows,indent=2,ensure_ascii=False)+'\n')
from urllib.parse import quote
lines=['# Sources for the cash-flow and FX-hedging proposal (v2)','',
       'Twelve cited works. Original-proposal files and manifest are preserved. Colons in titles are rendered as spaced hyphens. Filename year is publication year; the version column discloses earlier manuscripts.','']
for r in rows:
    lines += [f"- [{r['title']} ({r['publication_year']})]({quote(Path(r['local_path']).name)}). {r['version']}."]
(STORE/'README-v2.md').write_text('\n'.join(lines)+'\n')
print(f'Catalogued {len(rows)} papers, {sum(r["pages"] for r in rows)} PDF pages')
