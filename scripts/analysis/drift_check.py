import json,collections
from sklearn.metrics import cohen_kappa_score
S={}
for l in open('data/raw/codes_skeptic_drift.jsonl'):
    d=json.loads(l);S[d['target_id']]=d
ids=[l.split('\t') for l in open('work/skeptic_ids.txt')]
H={}
for b in ['aa','ab','ac','ad']:
    for l in open(f'data/raw/codes_haikuv2_{b}.jsonl'):
        d=json.loads(l);H[(b,d['target_id'])]=d['frame']
def merge(f): return {'F01':'F01','F02':'F01'}.get(f,f)
for b in ['aa','ab','ac','ad','ALL']:
    P=[(S[i.strip()]['frame'],H[(bb,i.strip())]) for bb,i in ids if b in(bb,'ALL')]
    s,h=zip(*P);n=len(P)
    agree=sum(a==c for a,c in P)/n
    k=cohen_kappa_score(s,h)
    k2=cohen_kappa_score([merge(x) for x in s],[merge(x) for x in h])
    nu=lambda L:sum(x=='unclear' for x in L)
    # unclear 제외 일치
    P2=[p for p in P if 'unclear' not in p]
    a2=sum(a==c for a,c in P2)/len(P2)
    print(f'{b}: n={n} agree={agree:.2f} kappa={k:.2f} kappa(F01+F02 merged)={k2:.2f} | unclear skeptic={nu(s)} haiku={nu(h)} | agree excl-unclear={a2:.2f} (n={len(P2)})')
    sc=collections.Counter(s);hc=collections.Counter(h)
    print('  frame(sk/hk) diff>=3:',{f:(sc[f],hc[f]) for f in sorted(set(sc)|set(hc)) if abs(sc[f]-hc[f])>=3})
    if b!='ALL':
        c=collections.Counter((a,c) for a,c in P if a!=c and 'unclear' in (a,c))
        print('  unclear flips (sk,hk):',dict(c))

# --- 추가: 배치 효과 크기, phase 영향
import sqlite3
from scipy.stats import chi2_contingency
db=sqlite3.connect('work/lab_260119b.db')
CUT=[('2026-10-28','세무냥이'),('2026-11-15T12:00','의혹'),('2026-11-18T09:00','고발'),('2026-11-19T07:30','검증'),('2026-11-19T08:37','실종'),('2026-11-19T13:12','사망'),('2026-11-20','사후')]
def phase(i):
    r=db.execute('select published_at from comments where comment_id=?',(i,)).fetchone() or db.execute('select published_at from items where item_id=?',(i,)).fetchone()
    t=(r[0] if r and r[0] else '')[:16]
    if not t: return '?'
    p='전사'
    for c,n in CUT:
        if t>=c: p=n
    return p
full=collections.defaultdict(list)
for (b,i),f in H.items(): full[b].append((phase(i),f))
print('\n[haiku 전체 배치] phase별 unclear 비율 / n')
phs=['전사','세무냥이','의혹','고발','검증','실종','사망','사후','?']
for b,L in full.items():
    print(b,{p:f'{sum(f=="unclear" for q,f in L if q==p)}/{sum(q==p for q,f in L)}' for p in phs if any(q==p for q,f in L)})
print('\n[phase x frame, haiku 4배치 합, unclear 포함 vs 제외 vs ac 제외]')
def share(L,excl_ac=False):
    c=collections.defaultdict(collections.Counter)
    for b,LL in full.items():
        if excl_ac and b=='ac': continue
        for q,f in LL:
            if f!='unclear': c[q][f]+=1
    return {q:{f:round(v/sum(cc.values()),2) for f,v in cc.most_common(3)} for q,cc in c.items() if sum(cc.values())>=40}
a,b2=share(full),share(full,True)
for q in a: print(q,'전체',a[q],'| ac제외',b2.get(q))
for who,get in [('skeptic',lambda b,i:S[i]['frame']),('haiku',lambda b,i:H[(b,i)])]:
    t=collections.defaultdict(collections.Counter)
    for b,i in ids: i=i.strip();t[b]['unclear' if get(b,i)=='unclear' else 'x']+=1
    print(who,'unclear x batch chi2 p=%.3f'%chi2_contingency([[t[b]['unclear'],t[b]['x']] for b in t])[1],{b:t[b]['unclear'] for b in t})
