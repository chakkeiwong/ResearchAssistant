"""Deterministic CPU-only checks of manuscript identities; no model fitting."""
import os
os.environ['CUDA_VISIBLE_DEVICES'] = '-1'
from pathlib import Path
import itertools, json, math, platform, subprocess
import numpy as np
import scipy
from scipy.integrate import quad
from scipy.special import beta, gamma, hyp2f1, expit
from scipy.stats import nbinom, poisson
ROOT = Path(__file__).resolve().parents[3]
checks=[]
def close(name, computed, reference, tolerance=1e-8):
    err=abs(float(computed)-float(reference))
    passed=err <= tolerance * max(1.,abs(float(reference)))
    checks.append(dict(name=name,computed=float(computed),reference=float(reference),absolute_error=err,tolerance=tolerance,passed=passed))
    assert passed, checks[-1]
# Beta/gamma integration of each BG/NBD likelihood component.
r,alpha,a,b,x,tx,T,H=1.3,4.2,1.7,3.4,3,7.,12.,4.
gam=lambda lam: alpha**r*lam**(r-1)*math.exp(-alpha*lam)/gamma(r)
bet=lambda p:p**(a-1)*(1-p)**(b-1)/beta(a,b)
A=beta(a,b+x)/beta(a,b)*alpha**r*gamma(r+x)/(gamma(r)*(alpha+T)**(r+x))
D=beta(a+1,b+x-1)/beta(a,b)*alpha**r*gamma(r+x)/(gamma(r)*(alpha+tx)**(r+x))
A_integral=quad(lambda p:(1-p)**x*bet(p),0,1,epsabs=1e-12)[0]*quad(lambda lam:lam**x*math.exp(-T*lam)*gam(lam),0,np.inf,epsabs=1e-12)[0]
D_integral=quad(lambda p:p*(1-p)**(x-1)*bet(p),0,1,epsabs=1e-12)[0]*quad(lambda lam:lam**x*math.exp(-tx*lam)*gam(lam),0,np.inf,epsabs=1e-12)[0]
close('BG/NBD active likelihood integral',A_integral,A,1e-10)
close('BG/NBD dropout likelihood integral',D_integral,D,1e-10)
alive=A/(A+D)
close('BG/NBD posterior active ratio',alive,1/(1+a/(b+x-1)*((alpha+T)/(alpha+tx))**(r+x)))
c,q=alpha+T,r+x
future_integral=alive/beta(a,b+x)*quad(lambda p:p**(a-2)*(1-p)**(b+x-1)*(-math.expm1(-q*math.log1p(p*H/c))),0,1,epsabs=1e-10)[0]
future_closed=alive*(a+b+x-1)/(a-1)*(1-(c/(c+H))**q*hyp2f1(q,b+x,a+b+x-1,H/(c+H)))
close('BG/NBD future-count integral vs hypergeometric form',future_integral,future_closed)
# The integral remains finite below a=1. Independently integrate expected active intensity.
a2=.7
f1=quad(lambda p:p**(a2-2)*(1-p)**(b+x-1)*(-math.expm1(-q*math.log1p(p*H/c))),0,1,epsabs=1e-9)[0]/beta(a2,b+x)
f2=quad(lambda u:quad(lambda p:p**(a2-1)*(1-p)**(b+x-1)*(q/c)*(1+p*u/c)**(-q-1),0,1,epsabs=1e-9)[0]/beta(a2,b+x),0,H,epsabs=1e-8)[0]
close('BG/NBD a<1 future expectation vs intensity integration',f1,f2)
# Double-robust score: direct expectation vs product-of-errors expression.
for label,e,eh,m1,m0,h1,h0 in [('both_wrong',.3,.45,5.,2.,4.,2.7),('propensity_correct',.3,.3,5.,2.,4.,2.7),('outcome_correct',.3,.45,5.,2.,5.,2.)]:
    expected=h1-h0+e/eh*(m1-h1)-(1-e)/(1-eh)*(m0-h0)
    bias=(eh-e)*((h1-m1)/eh+(h0-m0)/(1-eh))
    close('AIPW '+label,expected,m1-m0+bias)
# PU identity, weighted risk, and the overlapping-class counterexample.
f,c=.4,.5;g=c*f
close('PU heldout-positive estimator counterexample',g,.2)
close('PU erroneous calibrated probability in counterexample',g/g,1.)
w=(1-c)*g/(c*(1-g)); p_hat=.3
risk=g*(1-p_hat)**2+(1-g)*(w*(1-p_hat)**2+(1-w)*p_hat**2)
close('PU weighted Brier risk equals full-data risk',risk,f*(1-p_hat)**2+(1-f)*p_hat**2)
# NB moments, normalization, zero-truncated mean.
mu,k=12.,2.5; ns=np.arange(1000); probs=nbinom.pmf(ns,k,k/(k+mu))
close('Negative-binomial normalization',sum(probs),1.)
close('Negative-binomial mean',sum(ns*probs),mu)
close('Negative-binomial variance',sum((ns-mu)**2*probs),mu+mu*mu/k)
close('Zero-truncated NB mean',sum(ns[1:]*probs[1:])/(1-probs[0]),mu/(1-probs[0]))
# Logistic parameterization: Newton steps for full versus half log odds.
y=np.array([0.,1.,1.,0.]); eta=np.array([-.7,.2,1.4,-.2]); p=expit(eta)
step_eta=sum(y-p)/sum(p*(1-p)); yp=2*y-1; F=eta/2
rF=2*yp/(1+np.exp(2*yp*F)); hF=abs(rF)*(2-abs(rF))
close('Logistic half/full log-odds Newton conversion',step_eta,2*sum(rF)/sum(hF))
close('Horizon survival product',1-np.prod(1-np.array([.1,.2,.1])),.352)
# Monthly hidden-state forward algorithm independently compared with all state paths.
lam,drop=.8,.3
for obs in [(0,1,0),(1,0,0),(1,2,0),(0,0,0)]:
    active,dead=1.,0.
    for n in obs:
        pm=poisson.pmf(n,lam)
        active,dead=active*pm*(1-drop*(n>0)),dead*(n==0)+active*pm*drop*(n>0)
    direct=0.
    for states in itertools.product([0,1],repeat=len(obs)): # 1 active after month
        prev=1; prob=1.
        for n,state in zip(obs,states):
            if prev:
                pm=poisson.pmf(n,lam)
                prob*=pm*((1-drop*(n>0)) if state else drop*(n>0))
            else: prob*=int(n==0 and state==0)
            prev=state
        direct+=prob
    close('Monthly forward recursion '+str(obs),active+dead,direct)
# Independent enumeration of the worked constrained queue.
values=[-10,400,250,350]; hours=[1,2,1,2]
choices=[(sum(v*z for v,z in zip(values,Z)),Z) for Z in itertools.product([0,1],repeat=4) if sum(h*z for h,z in zip(hours,Z))<=3]
best,Z=max(choices)
close('Worked allocation optimal net margin',best,650.)
assert Z==(0,1,1,0)
report=dict(purpose='Deterministic algebra/numerical verification only; no bank-model experiment or performance claim',
    cpu_only=True,cuda_visible_devices=os.environ['CUDA_VISIBLE_DEVICES'],python=platform.python_version(),
    scipy=scipy.__version__,numpy=np.__version__,git_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
    command='python3 docs/salespitch/scripts/check_derivations.py',random_seeds='N/A: deterministic quadrature and enumeration',
    checks=checks,passed=all(c['passed'] for c in checks))
out=ROOT/'docs/salespitch/review/derivation_checks.json';out.write_text(json.dumps(report,indent=2)+'\n')
print(f'{len(checks)} deterministic checks passed. Report: {out}')
