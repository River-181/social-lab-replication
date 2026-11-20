"""RQ3 프레임 이동: 국면(phase_platform) x 프레임. haiku-v2 1,800건(층화표본 -> 국면 내 비율만 비교).
실행: python3 scripts/analysis/rq3_frames.py   (표는 stdout, 그림은 findings/*.png)"""
import sys; sys.path.insert(0, '/Users/river/social-lab/scripts/analysis')
import numpy as np, pandas as pd, matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from scipy.stats import chi2_contingency
from lab_codes import load, PHASES, md

plt.rcParams['font.family'] = 'AppleGothic'; plt.rcParams['axes.unicode_minus'] = False
OUT = '/Users/river/social-lab/findings/260119_RQ3_'
rng = np.random.default_rng(0)
FR = [f'F{i:02d}' for i in range(1, 16)] + ['unclear']
# 코드북 이동 경로(의혹->처벌요구->조롱->애도->책임전가->정치화)의 프레임 대응(운영 가정)
PATH = {'의혹(F01·F02)': ['F01', 'F02'], '처벌요구(F03)': ['F03'], '조롱(F04)': ['F04'],
        '애도(F06)': ['F06'], '책임전가(F09·F10)': ['F09', 'F10'], '정치화(F08)': ['F08']}
G = {f: k for k, v in PATH.items() for f in v}
d = load()
d['grp'] = d.frame.map(lambda f: G.get(f, 'unclear' if f == 'unclear' else '기타'))
GR = list(PATH) + ['기타', 'unclear']

def ph(p): return [x for x in PHASES if x in set(d[d.platform == p].phase)]

def chi(ct):
    ct = ct.loc[:, ct.sum() > 0]
    c2, p, dof, _ = chi2_contingency(ct)
    return c2, dof, p, np.sqrt(c2 / ct.values.sum() / (min(ct.shape) - 1))

def boot(x, B=2000):  # x: 0/1 배열 -> 비율, 95% 부트스트랩 CI
    m = rng.choice(x, (B, len(x))).mean(1); return x.mean(), *np.percentile(m, [2.5, 97.5])

print('## n'); print(md(pd.crosstab(d.platform, d.phase)[PHASES]))
print('\n## unclear 비율 (국면 / 배치)')
print(md((d.assign(u=d.frame == 'unclear').pivot_table(index='platform', columns='phase', values='u')[PHASES] * 100).round(1)))
print(md((d.assign(u=d.frame == 'unclear').pivot_table(index='batch', columns='platform', values='u') * 100).round(1)))
print(md(pd.crosstab(d.batch, [d.platform])))

# 1 히트맵 (분모 포함 / 제외)
fig, ax = plt.subplots(2, 2, figsize=(15, 9))
for j, pf in enumerate(['유튜브', '디시']):
    s = d[d.platform == pf]; P = ph(pf)
    for i, ex in enumerate([False, True]):
        cols = FR[:-1] if ex else FR
        t = s[s.frame.isin(cols)]
        ct = pd.crosstab(t.phase, t.frame).reindex(index=P, columns=cols, fill_value=0)
        pc = ct.div(ct.sum(1), axis=0) * 100
        a = ax[i, j]; im = a.imshow(pc.values, cmap='YlOrRd', aspect='auto', vmin=0, vmax=45)
        a.set_xticks(range(len(cols))); a.set_xticklabels(cols, rotation=60); a.set_yticks(range(len(P)))
        a.set_yticklabels([f'{p}\n(n={ct.loc[p].sum()})' for p in P])
        for y in range(len(P)):
            for x in range(len(cols)): a.text(x, y, f'{pc.values[y, x]:.0f}', ha='center', va='center', fontsize=8)
        a.set_title(f'{pf} — unclear {"제외" if ex else "포함"} (국면 내 %)')
        c2, dof, p, v = chi(ct)
        print(f'\n## 히트맵 {pf} unclear {"제외" if ex else "포함"}  chi2={c2:.1f} dof={dof} p={p:.2g} V={v:.2f}')
        print(md(pc.round(1)))
plt.tight_layout(); plt.savefig(OUT + '프레임이동_히트맵.png', dpi=130); plt.close()

# 2 경로 그룹: 국면별 비율 + 부트스트랩 CI, 분모 포함/제외
fig, ax = plt.subplots(2, 2, figsize=(14, 9))
for j, pf in enumerate(['유튜브', '디시']):
    s0 = d[d.platform == pf]; P = ph(pf)
    for i, ex in enumerate([False, True]):
        s = s0[s0.grp != 'unclear'] if ex else s0
        ct = pd.crosstab(s.phase, s.grp).reindex(index=P, columns=[g for g in GR if not (ex and g == 'unclear')], fill_value=0)
        c2, dof, p, v = chi(ct)
        print(f'\n## 경로그룹 {pf} unclear {"제외" if ex else "포함"}  chi2={c2:.1f} dof={dof} p={p:.2g} V={v:.2f}')
        rows = []
        for g in list(PATH) + ['기타'] + ([] if ex else ['unclear']):
            r = {'그룹': g}
            for p_ in P:
                x = (s[s.phase == p_].grp == g).values.astype(float); m, lo, hi = boot(x)
                r[p_] = f'{m*100:.1f} [{lo*100:.0f}-{hi*100:.0f}]'
            rows.append(r)
            if g in PATH:
                a = ax[i, j]; ms = [boot((s[s.phase == p_].grp == g).values.astype(float)) for p_ in P]
                a.errorbar(range(len(P)), [m[0]*100 for m in ms], yerr=[[(m[0]-m[1])*100 for m in ms], [(m[2]-m[0])*100 for m in ms]], marker='o', capsize=3, label=g)
        print(md(pd.DataFrame(rows), index=False))
        a = ax[i, j]; a.set_xticks(range(len(P))); a.set_xticklabels(P); a.set_ylabel('국면 내 %'); a.set_title(f'{pf} 이동 경로 프레임 — unclear {"제외" if ex else "포함"} (95% 부트스트랩)')
        if i == 0 and j == 0: a.legend(fontsize=8)
plt.tight_layout(); plt.savefig(OUT + '프레임이동_경로.png', dpi=130); plt.close()

# 인접 국면 차이(부트스트랩 CI, unclear 제외): CI가 0을 포함하지 않는 것만
print('\n## 인접 국면 비율 차이(unclear 제외, 95% 부트스트랩 CI, 0 미포함만)')
for pf in ['유튜브', '디시']:
    s = d[(d.platform == pf) & (d.grp != 'unclear')]; P = ph(pf)
    for a_, b_ in zip(P, P[1:]):
        for g in list(PATH) + ['기타']:
            xa = (s[s.phase == a_].grp == g).values.astype(float); xb = (s[s.phase == b_].grp == g).values.astype(float)
            df = rng.choice(xb, (2000, len(xb))).mean(1) - rng.choice(xa, (2000, len(xa))).mean(1)
            lo, hi = np.percentile(df, [2.5, 97.5])
            if lo > 0 or hi < 0: print(f'- {pf} {a_}→{b_} {g}: {(xb.mean()-xa.mean())*100:+.1f}%p [{lo*100:+.1f}, {hi*100:+.1f}]')

# 3 stance / emotion
ST = ['공격', '의심', '중립', '옹호', '애도', '무관']; EM = ['분노', '조롱·쾌감', '불안·공포', '슬픔', '호기심', '냉소', '없음']
fig, ax = plt.subplots(2, 2, figsize=(15, 9))
for i, (col, vals) in enumerate([('stance', ST), ('emotion', EM)]):
    for j, pf in enumerate(['유튜브', '디시']):
        s = d[d.platform == pf]; P = ph(pf)
        ct = pd.crosstab(s.phase, s[col]).reindex(index=P, columns=vals, fill_value=0); pc = ct.div(ct.sum(1), axis=0) * 100
        pc.plot.bar(stacked=True, ax=ax[i, j], colormap='tab20', rot=0); ax[i, j].set_title(f'{pf} {col} (국면 내 %)'); ax[i, j].legend(fontsize=7, bbox_to_anchor=(1, 1))
        c2, dof, p, v = chi(ct)
        print(f'\n## {col} {pf}  chi2={c2:.1f} dof={dof} p={p:.2g} V={v:.2f}'); print(md(pc.round(1)))
plt.tight_layout(); plt.savefig(OUT + '프레임이동_stance_emotion.png', dpi=130); plt.close()

# 4 L-flag 보조: 애도 프레임이 사망 이전에도 있었나(원문 인용 없이 건수만)
print('\n## F06 건수'); print(md(pd.crosstab(d.platform, [d.phase], values=(d.frame == 'F06'), aggfunc='sum')[PHASES]))
