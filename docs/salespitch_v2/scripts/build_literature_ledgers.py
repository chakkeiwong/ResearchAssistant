#!/usr/bin/env python3
"""Preserve source support separately from discovery metadata."""
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[3]
DOC=ROOT/'docs/salespitch_v2'
LOG=ROOT/'.localresources/bank-sales-v2-2026-10-08/logs'
rows=json.loads((DOC/'review/source_catalog.json').read_text())
date='2026-10-08'
venues={
'montero2021global':'International Journal of Forecasting',
'salinas2020deepar':'International Journal of Forecasting',
'wager2021policy':'Econometrica','kalman1960':'Journal of Basic Engineering',
'shumway1982':'Journal of Time Series Analysis','stock2002':'Journal of the American Statistical Association',
'rangapuram2018':'NeurIPS 31','pearl2009':'Statistics Surveys',
'smith1985':'Journal of Financial and Quantitative Analysis','froot1993':'Journal of Finance',
'mcfadden1974':'Frontiers in Econometrics (book chapter)','mcfadden2000':'Journal of Applied Econometrics'}
support=[]; metadata=[]; forward=[]
for r in rows:
    key=r['citation_key']; rr=dict(r)
    rr['support_class']='PRIMARY_TECHNICAL_SUPPORT for explicitly scoped methods; PROJECT_DERIVATION for bank-specific extensions'
    rr['full_text_status']='Downloaded, technically inspected, ResearchAssistant-ingested; scanned sources have OCR sidecars'
    rr['implementation_status']='No trained bank model. Neural reference code inspected separately; no complete source-code parity claim.'
    support.append(rr)
    metadata.append(dict(key=key,venue=venues[key],citation_count=None,
        citation_source='Semantic Scholar metadata requests were rate-limited (HTTP 429); counts unavailable, not zero',
        venue_rank=None,venue_rank_source='Not available; primary publication identity verified, no ranking inferred',
        access_date=date,version=r['version'],doi=r.get('doi')))
    p=LOG/f'forward-{key}.json'
    if p.exists():
        data=json.loads(p.read_text()); data=data.get('data',[]) if isinstance(data,dict) else []
        papers=[a['citingPaper'] for a in data]
        highest=sorted(papers,key=lambda a:a.get('citationCount') or 0,reverse=True)[:5]
        recent=sorted(papers,key=lambda a:a.get('year') or 0,reverse=True)[:5]
        relevant=[a for a in papers if any(w in a.get('title','').lower() for w in ['cash','hedg','corporate','forecast','choice','counterfactual','target','policy'])][:8]
        forward.append(dict(seed=key,source='Semantic Scholar citations endpoint',query_identifier='DOI:'+r['doi'],
            access_date=date,raw_file=str(p.relative_to(ROOT)),records=len(papers),highest_cited_in_returned_sample=highest,
            recent_in_returned_sample=recent,topic_screen_candidates=relevant,
            disposition='Metadata-only discovery. Not used as technical support or manuscript citations. Relevant contemporary methods merit separate benchmark-stage review.',
            limitation='First 100 returned records, largely recent. Highest cited means within this sample, not globally. No exhaustive forward coverage.'))
    else:
        forward.append(dict(seed=key,access_date=date,status='Seed-title lookup attempted; API rate limited; citing-paper query could not be resolved',
            evidence='logs/searchmeta-0.json for deep state-space; logs/searchmeta-1.json for conditional logit',
            known_followup='Mixed MNL Models for Discrete Response included for conditional logit; no exhaustive follow-up search'))

back={
'montero2021global':[
 ('DeepAR','DIRECT_METHOD','Included; shared probabilistic recurrent forecasting'),
 ('M4 competition and global forecasting comparisons','COMPETITOR','Not used for bank performance claims; no directly transferable macro-counterfactual evidence'),
 ('Local statistical and pooled forecasting literature','BACKGROUND','Transparent local and pooled baselines constructed explicitly')],
'salinas2020deepar':[
 ('Deep State Space Models for Time Series Forecasting','DIRECT_METHOD','Included'),
 ('Deep Factors for Forecasting','COMPETITOR','Omitted as additional neural competitor; first implementation uses explicit low-dimensional factors'),
 ('Bayesian Intermittent Demand Forecasting for Large Inventories (Seeger et al.)','COMPETITOR','Omitted from core: count/inventory emphasis; hurdle amounts derived locally, targeted follow-up needed before production zero-process selection')],
'kalman1960':[
 ('Wiener, The Extrapolation, Interpolation and Smoothing of Stationary Time Series','FOUNDATIONAL','Historical predecessor; discrete Gaussian recursion derived in manuscript'),
 ('Zadeh and Ragazzini, An Extension of Wiener\'s Theory of Prediction','BACKGROUND','Historical prediction theory; no incremental banking mechanism'),
 ('Bode and Shannon, A Simplified Derivation of Linear Least-Squares Smoothing and Prediction Theory','BACKGROUND','Historical smoothing theory; current recursion derived')],
'shumway1982':[
 ('Dempster, Laird and Rubin, Maximum Likelihood from Incomplete Data via the EM Algorithm','FOUNDATIONAL','EM likelihood identity and monotonicity derived locally; not claiming general convergence'),
 ('Anderson and Moore, Optimal Filtering','BACKGROUND','Filtering reference; selected linear Gaussian derivations are self-contained'),
 ('Kalman filtering literature','FOUNDATIONAL','Kalman included')],
'stock2002':[
 ('Bai and Ng, Determining the Number of Factors in Approximate Factor Models','DIRECT_METHOD','Omitted because no asymptotic factor-number criterion is implemented; fixed small ranks validated under short T'),
 ('Forni, Hallin, Lippi and Reichlin, The Generalized Dynamic Factor Model: Identification and Estimation','COMPETITOR','Omitted spectral alternative; needed if a rich macro-factor forecasting comparison is commissioned'),
 ('Chamberlain and Rothschild, Arbitrage, Factor Structure, and Mean-Variance Analysis on Large Asset Markets','FOUNDATIONAL','Background factor theory, no portfolio-pricing theorem imported'),
 ('Geweke, The Dynamic Factor Analysis of Economic Time Series','FOUNDATIONAL','Historical dynamic-factor alternative; small explicit state model suffices for present design')],
'rangapuram2018':[
 ('DeepAR','COMPETITOR','Included'),
 ('Durbin and Koopman, Time Series Analysis by State Space Methods','FOUNDATIONAL','Book omitted; relevant Gaussian and approximate inference derived here'),
 ('Hyndman and coauthors, Forecasting with Exponential Smoothing','COMPETITOR','Classical smoothing baseline represented by transparent shared level/seasonal model'),
 ('Seeger and coauthors intermittent-demand forecasting','COMPETITOR','See DeepAR omission above')],
'pearl2009':[
 ('Rubin potential-outcomes literature','FOUNDATIONAL','Exchangeability and consistency derived explicitly for adjustment; no separate historical treatment'),
 ('Robins longitudinal g-computation literature','DIRECT_METHOD','Sequential identification acknowledged; no longitudinal treatment estimator claimed'),
 ('Pearl, Causality','FOUNDATIONAL','Book omitted; selected survey definitions and checked arguments supply required formalism')],
'smith1985':[
 ('Stulz, Optimal Hedging Policies','FOUNDATIONAL','Related corporate-hedging theory; current mechanisms reconstructed from Smith-Stulz and Froot'),
 ('Modigliani-Miller corporate-finance benchmark','BACKGROUND','Frictionless motivation stated conditionally; no new theorem attributed'),
 ('Managerial compensation and diversification literature','BACKGROUND','Relevant composition-curvature mechanism derived without empirical compensation claims')],
'froot1993':[
 ('Smith and Stulz, The Determinants of Firms\' Hedging Policies','FOUNDATIONAL','Included'),
 ('Myers and Majluf, Corporate Financing and Investment Decisions When Firms Have Information That Investors Do Not Have','FOUNDATIONAL','Omitted microfoundation of costly finance; reduced financing cost explicitly assumed'),
 ('Townsend costly-state-verification model','FOUNDATIONAL','Omitted alternative microfoundation; no contract-optimality claim'),
 ('Stulz optimal hedging and DeMarzo-Duffie hedging information models','COMPETITOR','Broader mechanisms omitted; utility parameters not claimed identified')],
'mcfadden1974':[
 ('Luce choice axiom literature','FOUNDATIONAL','IIA property derived explicitly; historical proof not needed for model'),
 ('Random utility and Thurstone choice literature','FOUNDATIONAL','Gumbel construction derived directly; probit a possible alternative, not evaluated')],
'mcfadden2000':[
 ('McFadden conditional logit','FOUNDATIONAL','Included'),
 ('Revelt and Train, Mixed Logit with Repeated Choices','DIRECT_METHOD','Panel integrated likelihood derived here; omitted separate appliance application'),
 ('Boyd-Mellman and Cardell-Dunbar random-coefficient choice models','FOUNDATIONAL','Historical mixtures; no extra mechanism needed'),
 ('Train, Halton Sequences for Mixed Logit','IMPLEMENTATION_OR_SOFTWARE','No quasi-random efficiency claim; draw convergence must be checked')],
'wager2021policy':[
 ('Kitagawa and Tetenov, Who Should Be Treated? Empirical Welfare Maximization Methods for Treatment Choice','COMPETITOR','Alternative policy-learning theory; constrained value target derived, no comparative regret claim'),
 ('Doubly robust and orthogonal estimation literature','FOUNDATIONAL','AIPW and product-bias identity derived; not claiming a general semiparametric theorem'),
 ('Causal forests','COMPETITOR','Possible effect estimator; no trained treatment-effect model in scope')]
}
backward=[dict(seed=k,candidate=p,classification=c,action=a,scope='Discovery entry, not a manuscript citation or technical-support claim') for k,v in back.items() for p,c,a in v]
claims=[
 ('Pooling short panels','03_dynamics.tex', 'montero2021global', 'Local Gaussian posterior derivation; paper motivates shared vs local question'),
 ('Exact Gaussian filtering and likelihood','03_dynamics.tex','kalman1960','Conditional normal projection; checked against independent joint conditioning'),
 ('Smoothing, lag covariance and EM updates','03_dynamics.tex','shumway1982','Appendix source plus local conditional-Markov derivation and deterministic check'),
 ('PCA factor extraction','03_dynamics.tex','stock2002','Constrained least squares derivation; no causal factor identification'),
 ('Neural conditional distribution and covariate-only SSM parameter generator','03_dynamics.tex','salinas2020deepar;rangapuram2018','Paper model sections and bounded official-code inspection'),
 ('Bank capture nonidentification','02_observation.tex',None,'PROJECT_DERIVATION: exact rescaling and interval proof'),
 ('Joint hurdle likelihood, mean and covariance','04_joint_model.tex',None,'PROJECT_DERIVATION: proposed synthesis, not a cited bank implementation'),
 ('Conditional posterior concavity','04_joint_model.tex',None,'PROJECT_DERIVATION under fixed parameters and affine predictors; proper Gaussian prior'),
 ('Conditional vs interventional vs unit counterfactual','05_counterfactual.tex','pearl2009','Sections 3.2-3.4 plus linear confounding derivation'),
 ('Nonnegative GDP mean response','05_counterfactual.tex',None,'PROJECT_DERIVATION with invariant residual-state law, fixed variance/capture, nonnegative lag kernel'),
 ('Corporate hedging mechanisms','06_utility.tex','smith1985;froot1993','Tax pricing weights; compensation curvature; costly-finance value. Total value includes w+P(w).'),
 ('CARA normal CE and nonnormal caveat','06_utility.tex',None,'PROJECT_DERIVATION: square completion, moments, unbounded lognormal negative-wealth warning'),
 ('Covariance hedge solution','06_utility.tex',None,'PROJECT_DERIVATION: mean-variance optimization with deterministic costs'),
 ('Logit and mixed panel likelihood','07_choice.tex','mcfadden1974;mcfadden2000','Gumbel integral, Hessian, E(product) panel integration; no endogenous-price identification claim'),
 ('Outreach score','08_outreach.tex','wager2021policy','AIPW identity and conditional product-bias derivation; no unmeasured-confounding remedy'),
 ('Forecast and sales superiority', '09_delivery.tex',None,'NOT ESTABLISHED: no bank data, fitted model or randomized commercial trial')]
claim_rows=[dict(claim=a,section=b,sources=c,support=d) for a,b,c,d in claims]
risks=[
 dict(topic='Structural macroeconomic identification; Lucas/Sims and policy-shock literature',reason='Current GDP response is an explicit scenario restriction, not identified policy transmission',risk='High if reader treats GDP coefficients as causal elasticities',next_action='Commission shock-specific identification before causal macro deployment',disposition='Acceptable for qualified proposal; blocks stronger causal claim'),
 dict(topic='Intermittent-demand and dynamic generalized-linear-model literature',reason='Local amount-hurdle likelihood and inference derived; not an exhaustive distribution survey',risk='Moderate: another occurrence/amount model could dominate',next_action='Compare occurrence dependence and tail families on bank data',disposition='Production model-selection expansion'),
 dict(topic='Modern time-series foundation models and recent corporate-budgeting pooled forecasts',reason='Metadata discovery only; not used as evidence. Scenario interpretability and partial wallet remain unresolved by flexibility alone',risk='High for a claim of best forecasting performance; no such claim made',next_action='Inspect technical methods of selected recent competitors before benchmark campaign',disposition='Acceptable for architecture proposal; not complete current benchmark survey'),
 dict(topic='Nested logit, probit, continuous/discrete hedge choice',reason='Conditional and mixed logit are enough to make the modular proposal explicit',risk='Moderate if menus are near duplicates or notional is continuous',next_action='Choose richer substitution/sizing model after actual choice-set audit',disposition='Deferred extension'),
 dict(topic='Full corporate-finance structural estimation and empirical hedging demand',reason='Transactions alone cannot identify investment technology, financing costs and private beliefs',risk='High if effective risk aversion is presented as measured',next_action='Collect financing constraints and repeated offers; test preference/belief identification',disposition='Blocks measured-preference claim until evidence exists'),
 dict(topic='Forward coverage and correction registries',reason='Bounded citation samples and rate-limited metadata, primary pages inspected',risk='Unseen recent extension or correction may exist',next_action='Repeat bibliographic review before publication or model promotion',disposition='Recorded limitation, not fabricated completeness')]
for name,data in [('source_support',support),('citation_venue_metadata',metadata),('backward_snowball',backward),('forward_snowball',forward),('claim_support',claim_rows),('omitted_paper_risks',risks)]:
    (DOC/'review'/f'{name}.json').write_text(json.dumps(data,indent=2,ensure_ascii=False)+'\n')
print('Wrote six literature ledgers; 12 sources; '+str(len(backward))+' backward candidates; '+str(len(claim_rows))+' claims.')
