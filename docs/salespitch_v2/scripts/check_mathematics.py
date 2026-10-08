#!/usr/bin/env python3
"""Deterministic CPU algebra checks, not bank-data performance experiments."""
import json
import os
from pathlib import Path
os.environ['CUDA_VISIBLE_DEVICES'] = '-1'
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
checks = []

def check(name, actual, expected, atol=1e-9, rtol=1e-8):
    a, b = np.asarray(actual), np.asarray(expected)
    error = float(np.max(np.abs(a-b)))
    passed = bool(np.allclose(a,b,atol=atol,rtol=rtol))
    checks.append(dict(name=name,passed=passed,max_absolute_error=error))
    assert passed, (name,a,b)

# Scalar Gaussian chain: direct joint conditioning is independent of filter code.
T=5; A=.72; Q=.3; R=.4; P0=.8
y=np.array([.2,-.1,.7,.25,.4])
G=np.zeros((T+1,T+1))
for t in range(T+1):
    G[t,0]=A**t
    for j in range(1,t+1): G[t,j]=A**(t-j)
C=G@np.diag([P0]+[Q]*T)@G.T
Cy=C[1:,1:]+R*np.eye(T)
direct_mean=C[:,1:]@np.linalg.solve(Cy,y)
direct_cov=C-C[:,1:]@np.linalg.solve(Cy,C[1:,:])
m=np.zeros(T+1); P=np.zeros(T+1); P[0]=P0
pred=np.zeros(T+1); a=np.zeros(T+1)
for t in range(1,T+1):
    a[t]=A*m[t-1]; pred[t]=A*A*P[t-1]+Q
    gain=pred[t]/(pred[t]+R)
    m[t]=a[t]+gain*(y[t-1]-a[t]);P[t]=pred[t]*(1-gain)
check('filter endpoint vs joint conditioning',m[-1],direct_mean[-1])
sm=m.copy(); sp=P.copy(); lag=np.zeros(T)
for t in range(T-1,-1,-1):
    J=P[t]*A/pred[t+1]
    sm[t]=m[t]+J*(sm[t+1]-a[t+1])
    sp[t]=P[t]+J*J*(sp[t+1]-pred[t+1])
    lag[t]=sp[t+1]*J
check('smoothing means vs joint conditioning',sm,direct_mean)
check('smoothing variances vs joint conditioning',sp,np.diag(direct_cov))
check('lag covariance identity vs joint conditioning',lag,np.diag(direct_cov,k=1))
S00=np.sum(sp[:-1]+sm[:-1]**2)
S10=np.sum(lag+sm[1:]*sm[:-1]); S11=np.sum(sp[1:]+sm[1:]**2)
An=S10/S00; Qn=(S11-S10*S10/S00)/T
def transition_objective(a,q):
    return -T/2*np.log(q)-(S11-2*a*S10+a*a*S00)/(2*q)
assert transition_objective(An,Qn)>=transition_objective(A,Q)
checks.append(dict(name='EM transition update increases expected complete likelihood',passed=True))

# Capture invariance and partial-identification bounds.
check('capture rescaling invariance',.25*400,.5*200)
lo=1/.8-.8/.5; hi=1/.5-.8/.8
check('capture interval endpoints',[lo,hi],[-.35,1.0])
check('net variance with natural hedge',100000**2+100000**2-2*.9*100000**2,2e9)

# Hurdle mean derivative, with fixed residual-state distribution.
sig=lambda x:1/(1+np.exp(-x))
def mean(g): return sig(-.4+.2*g)*np.exp(1+.3*g+.5*.16)
eps=1e-5
numeric=(np.log(mean(eps))-np.log(mean(-eps)))/(2*eps)
check('GDP derivative of log hurdle mean',numeric,(1-sig(-.4))*.2+.3)
check('negative autoregression reverses positive impulse',(-.5)**np.arange(3),[1,-.5,.25])

# Froot investment model with concave quadratic output and convex finance cost.
aa=5.; bb=.7; kk=1.2; ww=1.3
def profit(w):
    investment=(aa-1+kk*w)/(bb+kk)
    return aa*investment-.5*bb*investment**2-investment-.5*kk*(investment-w)**2
step=1e-3
curvature=(profit(ww+step)-2*profit(ww)+profit(ww-step))/step**2
check('Froot continuation curvature',curvature,-bb*kk/(bb+kk),atol=1e-7)
In=(aa-1+kk*ww)/(bb+kk)
check('total value includes marginal internal funds',1+(profit(ww+step)-profit(ww-step))/(2*step),1+kk*(In-ww))

# Normal CARA expectation via deterministic Gauss-Hermite integration.
nodes,weights=np.polynomial.hermite.hermgauss(64)
mu=1.4;sd=.8;gamma=.3
moment=np.sum(weights*np.exp(-gamma*(mu+np.sqrt(2)*sd*nodes)))/np.sqrt(np.pi)
check('CARA normal certainty equivalent',-np.log(moment)/gamma,mu-gamma*sd**2/2)
g=1e-6;v=.05**2;X=200000.;cost=30.
check('exporter net hedge benefit',.5*g*X**2*v-cost,20.)
delta=.002;kappa=2e-8;c=X*v
q=(delta+g*c)/(g*v+kappa)
check('hedge optimal first-order condition',delta+g*c-(g*v+kappa)*q,0.)

# Conditional-logit gradient/Hessian by finite differences.
design=np.array([[1.,-.4],[0.,.2],[-.3,1.1]])
theta=np.array([.4,-.2]); chosen=1
def probabilities(th):
    z=design@th; v=np.exp(z-z.max());return v/v.sum()
def ll(th):return np.log(probabilities(th)[chosen])
p=probabilities(theta);bar=p@design
grad=design[chosen]-bar
center=design-bar;hessian=-(center.T*p)@center
e=np.eye(2)*1e-5
numeric_grad=np.array([(ll(theta+x)-ll(theta-x))/(2e-5) for x in e])
numeric_hess=np.column_stack([((design[chosen]-probabilities(theta+x)@design)-(design[chosen]-probabilities(theta-x)@design))/(2e-5) for x in e])
check('logit score',grad,numeric_grad)
check('logit Hessian',hessian,numeric_hess)
check('logit common-shift invariance',p,np.exp(design@theta+3)/np.exp(design@theta+3).sum())
panel=np.mean(np.array([.9,.1])**2)
independent=np.mean([.9,.1])**2
check('persistent-taste panel probability',panel,.41)
check('redrawn-taste panel probability',independent,.25)

# Exact AIPW expectation and product-bias identity.
true_e=.35;mu1=5.;mu0=2.;m1=4.2;m0=2.4
def aipw_mean(e,a,b):
    return a-b+true_e/e*(mu1-a)-(1-true_e)/(1-e)*(mu0-b)
check('AIPW correct propensity',aipw_mean(true_e,m1,m0),mu1-mu0)
check('AIPW correct outcomes',aipw_mean(.55,mu1,mu0),mu1-mu0)
et=.55
check('AIPW product bias',aipw_mean(et,m1,m0)-(mu1-mu0),(et-true_e)*((m1-mu1)/et+(m0-mu0)/(1-et)))

out={'scope':'deterministic algebra only; no empirical forecasting or causal validation',
     'hardware':'CPU only; CUDA_VISIBLE_DEVICES=-1; NumPy only, no GPU framework imported',
     'checks':checks,'passed':all(x['passed'] for x in checks)}
(ROOT/'review/mathematical_checks.json').write_text(json.dumps(out,indent=2)+'\n')
print(f"PASS: {len(checks)} deterministic checks; review/mathematical_checks.json")
