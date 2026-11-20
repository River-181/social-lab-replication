"""RQ10 비난 이동 + RQ9 조기경보 후보 플래그(R·O·L). haiku-v2 1,800건, 국면 내 비율만 비교.
실행: python3 scripts/analysis/rq10_blame.py"""
import sys, re, sqlite3; sys.path.insert(0, '/Users/river/social-lab/scripts/analysis')
import numpy as np, pandas as pd, matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from scipy.stats import chi2_contingency, norm
from lab_codes import load, PHASES, DB, md

plt.rcParams['font.family'] = 'AppleGothic'; plt.rcParams['axes.unicode_minus'] = False
OUT = '/Users/river/social-lab/findings/260119_RQ10_'
rng = np.random.default_rng(0)
d = load()
BG = {'세무냥이': '당사자', '리트냥이': '당사자'}
d['tb'] = d.target_of_blame.map(lambda x: BG.get(x, x))
CAT = ['당사자', '냥이일반', '주변인', '제도', '메타', '없음']
def ph(p): return [x for x in PHASES if x in set(d[d.platform == p].phase)]
def wilson(k, n, z=1.96):
    if n == 0: return (np.nan,) * 3
    p = k / n; c = (p + z*z/2/n) / (1 + z*z/n); h = z*np.sqrt(p*(1-p)/n + z*z/4/n/n) / (1 + z*z/n)
    return p, c-h, c+h
def chi(ct):
    ct = ct.loc[:, ct.sum() > 0]; c2, p, dof, _ = chi2_contingency(ct)
    return c2, dof, p, np.sqrt(c2 / ct.values.sum() / (min(ct.shape) - 1))

# 1 target_of_blame 이동
print('## n'); print(md(pd.crosstab(d.platform, d.phase)[PHASES]))
fig, ax = plt.subplots(2, 2, figsize=(14, 9))
for j, pf in enumerate(['유튜브', '디시']):
    for i, ex in enumerate([False, True]):
        s = d[(d.platform == pf) & ((d.tb != '없음') if ex else True)]; P = ph(pf)
        cols = [c for c in CAT if not (ex and c == '없음')]
        ct = pd.crosstab(s.phase, s.tb).reindex(index=P, columns=cols, fill_value=0); pc = ct.div(ct.sum(1), axis=0) * 100
        pc.plot.bar(stacked=True, ax=ax[i, j], colormap='Set2', rot=0); ax[i, j].set_title(f'{pf} 비난 대상 — "없음" {"제외" if ex else "포함"} (국면 내 %)'); ax[i, j].legend(fontsize=7)
        c2, dof, p, v = chi(ct)
        print(f'\n## 비난대상 {pf} 없음{"제외" if ex else "포함"}  chi2={c2:.1f} dof={dof} p={p:.2g} V={v:.2f}')
        rows = []
        for c in cols:
            r = {'대상': c}
            for p_ in P:
                x = (s[s.phase == p_].tb == c).values.astype(float); b = rng.choice(x, (2000, len(x))).mean(1)
                r[p_] = f'{x.mean()*100:.1f} [{np.percentile(b,2.5)*100:.0f}-{np.percentile(b,97.5)*100:.0f}] (n={int(x.sum())}/{len(x)})' if c in ('주변인','제도','메타') else f'{x.mean()*100:.1f}'
            rows.append(r)
        print(md(pd.DataFrame(rows), index=False))
plt.tight_layout(); plt.savefig(OUT + '비난이동.png', dpi=130); plt.close()

# 인접 국면 차이(없음 제외)
print('\n## 인접 국면 차이(없음 제외, 95% 부트스트랩 CI, 0 미포함만)')
for pf in ['유튜브', '디시']:
    s = d[(d.platform == pf) & (d.tb != '없음')]; P = ph(pf)
    for a_, b_ in zip(P, P[1:]):
        for c in CAT[:-1]:
            xa = (s[s.phase == a_].tb == c).values.astype(float); xb = (s[s.phase == b_].tb == c).values.astype(float)
            df = rng.choice(xb, (2000, len(xb))).mean(1) - rng.choice(xa, (2000, len(xa))).mean(1); lo, hi = np.percentile(df, [2.5, 97.5])
            if lo > 0 or hi < 0: print(f'- {pf} {a_}→{b_} {c}: {(xb.mean()-xa.mean())*100:+.1f}%p [{lo*100:+.1f}, {hi*100:+.1f}]')

# 2 주변인 누구인가 (note 키워드; 규칙은 위에서 아래로 첫 일치)
RULE = [('정치·고위층·배후', '정치|고위층|장관|배후|청부|음모|공범|국정원'), ('변호사(선임·출연)', '변호사|REDACTED_LAWYER_A|이동원|선임|수임|전문직'),
        ('학원·강사·과외·업체', '학원|강사|과외|업체|브로커|치터|치팅|단톡'), ('가족·부모', '부모|가족|가정|엄마|아빠'),
        ('모텔·현장 관계자', '모텔|업주|위치'), ('유튜버·방송·영상 출연자', '유튜버|영상|방송|출연|렉카'), ('멸칭·댓글러·기타', '.')]
def cat(n):
    for k, r in RULE:
        if re.search(r, n or ''): return k
p = d[d.target_of_blame == '주변인'].copy(); p['who'] = p.note.map(cat)
c = sqlite3.connect(DB)
txt = pd.concat([pd.read_sql("select item_id target_id, coalesce(title,'')||' '||coalesce(description,'') t from items where item_id like 'dc_%'", c),
                 pd.read_sql("select comment_id target_id, text t from comments", c)])
p = p.merge(txt, on='target_id', how='left')
p['REDACTED_HOST_A'] = p.t.fillna('').str.contains('REDACTED_HOST_A|미미미'); p['학원강사_본문'] = p.t.fillna('').str.contains('학원|강사')
print(f'\n## 주변인 n={len(p)} / 전체 {len(d)}  본문에 REDACTED_HOST_A 언급 {int(p.REDACTED_HOST_A.sum())}건, 노트에 {int(p.note.fillna("").str.contains("REDACTED_HOST_A").sum())}건; 전체 코딩 본문 중 REDACTED_HOST_A 언급:',
      int(d.merge(txt, on='target_id').t.fillna('').str.contains('REDACTED_HOST_A').sum()))
print(md(pd.crosstab(p.who, p.phase).reindex(columns=[x for x in PHASES if x in set(p.phase)], fill_value=0).assign(합계=lambda x: x.sum(1)).sort_values('합계', ascending=False)))
print(md(pd.crosstab(p.who, p.platform).assign(합계=lambda x: x.sum(1))))
fig, a = plt.subplots(figsize=(9, 4.5)); pt = pd.crosstab(p.phase, p.who).reindex(PHASES, fill_value=0); pt.plot.bar(stacked=True, ax=a, colormap='tab10', rot=0)
a.set_title('주변인 비난의 대상 (건수, 두 플랫폼 합산 — 층화라 국면 간 건수 비교 주의)'); a.legend(fontsize=7); plt.tight_layout(); plt.savefig(OUT + '주변인.png', dpi=130); plt.close()

# 3 플래그 R·O·L
fig, ax = plt.subplots(2, 3, figsize=(15, 8))
FL = {'f_R': 'R 자해·자살 언급', 'f_O': 'O 오프라인 행동', 'f_L': 'L 멸칭'}
for i, pf in enumerate(['유튜브', '디시']):
    P = ph(pf)
    for k, (f, nm) in enumerate(FL.items()):
        s = d[d.platform == pf]; ms = [wilson(int(s[s.phase == q][f].sum()), (s.phase == q).sum()) for q in P]
        a = ax[i, k]; a.errorbar(range(len(P)), [m[0]*100 for m in ms], yerr=[[(m[0]-m[1])*100 for m in ms], [(m[2]-m[0])*100 for m in ms]], marker='o', capsize=3)
        a.set_xticks(range(len(P))); a.set_xticklabels(P); a.set_title(f'{pf} {nm} (%, Wilson 95%)')
plt.tight_layout(); plt.savefig(OUT + '플래그_RO_L.png', dpi=130); plt.close()
for f, nm in FL.items():
    print(f'\n## 플래그 {nm}: 건수/n (비율% [Wilson 95%])')
    rows = []
    for pf in ['유튜브', '디시', '합산']:
        s = d if pf == '합산' else d[d.platform == pf]; r = {'플랫폼': pf}
        for q in PHASES:
            n = (s.phase == q).sum(); k = int(s[s.phase == q][f].sum())
            r[q] = '-' if n == 0 else f'{k}/{n} ({wilson(k,n)[0]*100:.1f} [{wilson(k,n)[1]*100:.1f}-{wilson(k,n)[2]*100:.1f}])'
        rows.append(r)
    print(md(pd.DataFrame(rows), index=False))
    ct = pd.crosstab(d.phase, d[f]).reindex(PHASES, fill_value=0); ct = ct.loc[ct.sum(1) > 0]
    c2, pv, dof, _ = chi2_contingency(ct); print(f'합산 국면 간 chi2={c2:.1f} dof={dof} p={pv:.2g}')

# 검증 이전(전사·의혹·고발) 추이: Cochran-Armitage 추세검정, 플랫폼별
print('\n## 검증·실종 이전(전사·의혹·고발) 추세검정 (Cochran-Armitage, 양측)')
def ca(k, n, sc):
    k, n, sc = map(np.asarray, (k, n, sc)); N = n.sum(); pb = k.sum() / N
    t = (sc * (k - n * pb)).sum(); v = pb * (1 - pb) * ((n * sc**2).sum() - (n * sc).sum()**2 / N)
    return t / np.sqrt(v) if v > 0 else np.nan
for pf in ['유튜브', '디시', '합산']:
    s = d if pf == '합산' else d[d.platform == pf]; P = [q for q in PHASES[:3] if (s.phase == q).sum() > 0]
    for f in ['f_R', 'f_O', 'f_L']:
        k = [int(s[s.phase == q][f].sum()) for q in P]; n = [int((s.phase == q).sum()) for q in P]; z = ca(k, n, list(range(len(P))))
        print(f'- {pf} {f[2]}: {dict(zip(P, zip(k, n)))} z={z:.2f} p={2*(1-norm.cdf(abs(z))) if z==z else float("nan"):.2g}')
# R·O 겸유, 사망 이전 R 플래그의 프레임·stance 구성(원문 비인용)
r = d[d.f_R]; print('\n## R 플래그 구성(원문 비공개) n=', len(r)); print(md(pd.crosstab(r.frame, r.phase).reindex(columns=PHASES, fill_value=0)))
print(md(pd.crosstab(r.stance, r.phase).reindex(columns=PHASES, fill_value=0)))
o = d[d.f_O]; print('\n## O 플래그 n=', len(o)); print(md(pd.crosstab(o.frame, o.phase).reindex(columns=PHASES, fill_value=0)))
print('R·O 동시:', int((d.f_R & d.f_O).sum()))
print('\n## 사망 이전 R(검증·실종 이전)의 시각 분포'); b = d[d.f_R & d.phase.isin(['전사','의혹','고발'])]; print(md(b[['platform','phase','ts','frame','stance']].assign(ts=b.ts.dt.strftime('%m-%d %H:%M')).sort_values('ts')[['platform','phase','ts','frame','stance']], index=False))
