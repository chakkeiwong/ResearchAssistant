"""Create a paper catalog from already retrieved, inspected source PDFs."""
from pathlib import Path
import hashlib, json, shutil, subprocess
ROOT = Path(__file__).resolve().parents[3]
ORIGIN = ROOT / '.localresources/bank-sales-2026-10-08/papers'
DEST = ROOT / 'dcos/papers/salespitch'
records = [
('global','montero2021global','Principles and Algorithms for Forecasting Groups of Time Series: Locality and Globality','Montero-Manso',2021,'https://arxiv.org/pdf/2008.00444','10.1016/j.ijforecast.2021.03.004','Author manuscript; journal citation 2021','Sections 2--3, Proposition 1 and finite-memory qualification; Section 4 setup and evaluation design','Pooling is a design rationale; no bank-specific accuracy or independence guarantee.'),
('survival','singer1993time',"It's About Time: Using Discrete-Time Survival Analysis to Study Duration and the Timing of Events",'Singer',1993,'https://gseacademic.harvard.edu/~willetjo/pdf%20files/Singer%20%26%20Willett%201993.pdf','10.3102/10769986018002155','Published article scan','Printed pages 158--166; hazard, censoring, person-period likelihood, Equation 3; modeling discussion','Monthly logistic hazards; recurrent use supported separately by Willett/Singer 1995.'),
('recurrent','willett1995multiple',"It's Déjà Vu All Over Again: Using Multiple-Spell Discrete-Time Survival Analysis",'Willett',1995,'https://gseacademic.harvard.edu/~willetjo/pdf%20files/Willett_and_Singer_JEBS1995.pdf','10.3102/10769986020001041','Published article scan, sideways two-page sheets, includes journal contents','Multiple-spell definitions; conditional likelihood Equations 5--19; person-spell-period construction, worked teaching example, heterogeneity discussion pp.60--61','Risk clocks must be defined; Bernoulli likelihood shape does not justify independent-client standard errors for repeated rows.'),
('bgnbd','fader2005counting','Counting Your Customers the Easy Way: An Alternative to the Pareto/NBD Model','Fader',2005,'https://www.brucehardie.com/papers/018/fader_et_al_mksc_05.pdf','10.1287/mksc.1040.0098','Published article PDF','Model assumptions, likelihood and prediction formulas; Appendix A; application and extension discussion','Exact timing required by original likelihood; discrete monthly analogue is a local adaptation. Active beta factor is B(a,b+x).'),
('crosssell','li2005cross','Cross-Selling Sequentially Ordered Products: An Application to Consumer Banking Services','Li',2005,'https://www.ckgsb.edu.cn/userfiles/doc/ck_faculty_bhsun_crossselling.pdf','10.1509/jmkr.42.2.233.62288','Published article PDF','Equations 1--5 pp.234--235; data and estimation footnote 3; household holdout and model comparisons pp.236--238','D is previous-month purchase, not ownership. Competitor opening indicator unavailable here. Exact priors/sampler unpublished in article; document supplies explicitly labeled reconstruction.'),
('boosting','friedman2001greedy','Greedy Function Approximation: A Gradient Boosting Machine','Friedman',2001,'https://www.cmi.ac.in/~madhavan/courses/dmml2026/literature/Friedman-Gradient-Boosting-Machine-2001.pdf','10.1214/aos/1013203451','Published article scan on academic course mirror','Algorithm 1; Section 4.5 logistic Algorithm 5; Section 5 shrinkage; Sections 6 and 9 simulation and empirical design','Original publisher/author endpoints failed; unmodified primary paper retrieved from academic mirror. Logistic score coding carefully converted.'),
('deepar','salinas2020deepar','DeepAR: Probabilistic Forecasting with Autoregressive Recurrent Networks','Salinas',2020,'https://arxiv.org/pdf/1704.04110','10.1016/j.ijforecast.2019.07.001','arXiv v3, 22 February 2019, three authors; journal 2020 lists Januschowski as fourth author','Section 3 Equations 1--7, training/prediction algorithms, scaling; evaluation setup; supplement architecture/hyperparameters and missing values','No transferred bank hyperparameters or superiority claim. Manuscript/journal authorship distinction disclosed.'),
('uplift','gutierrez2017causal','Causal Inference and Uplift Modelling: A Review of the Literature','Gutierrez',2017,'https://proceedings.mlr.press/v67/gutierrez17a/gutierrez17a.pdf',None,'PMLR proceedings full text','Sections 2--3 potential outcomes, assumptions, separate models, transformed outcomes and tree approaches','Source is a methodological review. Illustrative split-gain algebra is derived locally, not attributed to every reviewed tree.'),
('policy','wager2021policy','Policy Learning with Observational Data','Athey',2021,'https://arxiv.org/pdf/1702.02896','10.3982/ECTA15732','arXiv accepted manuscript, 2020; journal citation 2021','Binary-treatment score, Section 2.3 policy objective, assumptions and nuisance-rate discussion; scope of theoretical argument','Local finite-class bound is explanatory, not a reproduction of general source regret theorem or a bank-panel guarantee.'),
('pu','elkan2008pu','Learning Classifiers from Only Positive and Unlabeled Data','Elkan',2008,'https://cseweb.ucsd.edu/~elkan/posonly.pdf','10.1145/1401890.1401920','Published conference paper PDF','Lemma 1; pp.214--215 SCAR, e1 labeling-rate argument and weighted-example derivation; empirical setup','SCAR identity retained. Local counterexample shows e1 justification insufficient with overlapping classes; bank capture also violates constant-c assumption.')]
manifest=[]
for slug,key,title,surname,year,url,doi,version,anchors,limitation in records:
    src=ORIGIN/f'{slug}.pdf'
    assert src.read_bytes().startswith(b'%PDF'), src
    # Keep the complete title, changing only punctuation unsafe in common filesystems.
    filename=title.replace(':',' -').replace('/','-')+f' {surname}({year}).pdf'
    target=DEST/filename
    digest=hashlib.sha256(src.read_bytes()).hexdigest()
    for old in DEST.glob('*.pdf'):
        if old != target and hashlib.sha256(old.read_bytes()).hexdigest()==digest:
            old.rename(target)
            break
    if not target.exists(): shutil.copy2(src,target)
    assert hashlib.sha256(target.read_bytes()).hexdigest()==digest
    info=subprocess.check_output(['pdfinfo',str(target)],text=True)
    pages=int(next(x.split(':',1)[1] for x in info.splitlines() if x.startswith('Pages:')))
    manifest.append(dict(citation_key=key,title=title,first_author_surname=surname,publication_year=year,
        local_path=str(target.relative_to(ROOT)),download_url=url,doi=doi,version=version,
        pages=pages,sha256=digest,technical_anchors=anchors,application_limit=limitation,
        retrieval_date='2026-10-08'))
(DEST/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
lines=['# Downloaded papers for the bank-sales survey','',
'All ten cited papers have a local full text. Filenames preserve the complete title and first-author surname followed by publication year; colons and the Pareto/NBD slash are replaced by hyphens for portability. Publication year names the cited work; author-manuscript dates can differ, as recorded below. Source PDFs are unchanged.','',
'Checksums, page counts, retrieval addresses and reading anchors are also in `manifest.json`.','']
from urllib.parse import quote
for r in manifest:
    name=Path(r['local_path']).name
    lines += [f"## {r['title']} — {r['first_author_surname']} ({r['publication_year']})",'',
      f"[{name}]({quote(name)})",'',f"Citation key: `{r['citation_key']}`. Version: {r['version']}. Pages: {r['pages']}.",
      f"Source: {r['download_url']}",f"DOI: {r['doi'] or 'No DOI supplied by proceedings page.'}",'',
      f"Inspected: {r['technical_anchors']}.",f"Use and limits: {r['application_limit']}",'',f"SHA-256: `{r['sha256']}`",'']
(DEST/'README.md').write_text('\n'.join(lines))
print(f'Cataloged {len(manifest)} verified PDFs; manifest: {DEST / "manifest.json"}')
