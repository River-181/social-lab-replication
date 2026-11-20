"""RQ7 Hawkes 자기흥분 과정 (지수커널, numpy MLE + scipy 최적화).
실행: python3 scripts/analysis/rq7_hawkes.py   (work/lab_260119b.db 사본, 시드 260119)
- 시간 단위: 시간(h). λ(t) = μ_k + α_k Σ_{t_i<t} exp(-β_k (t - t_i)),  k = t가 속한 국면. 분기비 n = α/β.
- 국면별 적합은 이전 국면 사건을 '이력'으로 넣고(조건부 우도) 해당 구간 우도만 최대화한다.
- 적합도: 시간 재조정 τ_i = Λ(t_{i-1}, t_i) ~ Exp(1) 이어야 함 → KS 검정.
- 반사실: 공개검증(07:30~08:37) 외생 충격을 '고발 국면 파라미터'로 대체하고 Ogata 솎아내기로 1,000회 시뮬."""
import sys, os, json
sys.path.insert(0, os.path.dirname(__file__))
import numpy as np, pandas as pd, sqlite3, matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from scipy.optimize import minimize
from scipy import stats
from common import to_kst, yt_items, KST
plt.rcParams['font.family'] = 'AppleGothic'; plt.rcParams['axes.unicode_minus'] = False

DB = '/Users/river/social-lab/work/lab_260119b.db'
FIND = '/Users/river/social-lab/findings'
SEED = 260119
T = lambda s: pd.Timestamp(s, tz=KST)
ACCUSE, VERIFY, MISSING, FOUND = T('2026-11-18 09:00'), T('2026-11-19 07:30'), T('2026-11-19 08:37'), T('2026-11-19 13:12')
# 장기 수집 갤(갤별 키워드 검색 + 전용갤 전수). 11/19 14:12 이후 통합검색으로 들어온 갤은 '그 외'
DC_LONG = {'fkgjwks', 'cta', 'csatlecture', 'singlebungle1472', 'chzzk', 'lawschool', 'leetkorea'}


def load_dc():
    c = sqlite3.connect(DB)
    d = pd.read_sql("select item_id,title,published_at,extra from items where item_id like 'dc_%'", c)
    d['ts'] = to_kst(d.published_at)
    d['gall'] = d.extra.map(lambda s: json.loads(s).get('gall_id'))
    d['sec_prec'] = d.published_at.str.len() >= 19
    return d[d.ts.notna()].copy()


def load_yt():
    c = sqlite3.connect(DB)
    y = yt_items(c)
    return y[y.rel & y.ts.notna()].copy()


def to_hours(ts, t0, rng, minute_level=None):
    """KST 시각 → t0 기준 시간. 동시각 동점 해소용으로 초 단위 정밀도면 U(0,1s), 분 단위면 U(0,60s) 지터."""
    base = (ts - t0).dt.total_seconds().to_numpy()
    width = np.where(minute_level, 60.0, 1.0) if minute_level is not None else 1.0
    return np.sort((base + rng.uniform(0, 1, len(base)) * width) / 3600.0)


# ---------------- Hawkes 우도 ----------------
def kernel_state(t, beta):
    """A_i = Σ_{j<i} exp(-β (t_i - t_j)) (재귀)."""
    A = np.zeros(len(t))
    for i in range(1, len(t)):
        A[i] = np.exp(-beta * (t[i] - t[i - 1])) * (1 + A[i - 1])
    return A


def nll_window(theta, t, a, b):
    """구간 [a,b)의 음의 로그우도. t 전체(이력 포함), 파라미터 log(μ,α,β)."""
    mu, alpha, beta = np.exp(theta)
    t = t[t < b]
    A = kernel_state(t, beta)
    m = (t >= a) & (t < b)
    lam = mu + alpha * A[m]
    h = t[t < b]
    comp = mu * (b - a) + (alpha / beta) * np.sum(np.exp(-beta * np.clip(a - h, 0, None)) - np.exp(-beta * (b - h)))
    return -(np.sum(np.log(lam)) - comp)


def fit_window(t, a, b):
    k = int(((t >= a) & (t < b)).sum())
    best = None
    for b0 in (0.3, 2.0, 10.0):
        for n0 in (0.2, 0.6, 0.9):
            x0 = np.log([max(k / (b - a), 1e-3) * (1 - n0), n0 * b0, b0])
            r = minimize(nll_window, x0, args=(t, a, b), method='L-BFGS-B',
                         bounds=[(-12, 8), (-12, 8), (np.log(0.05), np.log(120))])
            if best is None or r.fun < best.fun:
                best = r
    mu, al, be = np.exp(best.x)
    # 관측 정보행렬(수치 헤시안)로 log n 의 표준오차 → n 95% CI
    try:
        H = num_hess(lambda x: nll_window(x, t, a, b), best.x)
        cov = np.linalg.inv(H)
        g = np.array([0, 1, -1])  # log n = log α - log β
        se = float(np.sqrt(max(g @ cov @ g, 0)))
    except np.linalg.LinAlgError:
        se = np.nan
    n = al / be
    return dict(k=k, hours=b - a, mu=mu, alpha=al, beta=be, n=n, n_lo=n * np.exp(-1.96 * se), n_hi=n * np.exp(1.96 * se),
                decay_min=60 / be, nll=best.fun, theta=best.x)


def num_hess(f, x, h=1e-3):
    k = len(x); H = np.zeros((k, k))
    for i in range(k):
        for j in range(k):
            e_i = np.eye(k)[i] * h; e_j = np.eye(k)[j] * h
            H[i, j] = (f(x + e_i + e_j) - f(x + e_i - e_j) - f(x - e_i + e_j) + f(x - e_i - e_j)) / (4 * h * h)
    return H


def poisson_nll(t, a, b):
    """비교용: 상수율 포아송(자기흥분 없음) 음의 로그우도."""
    k = ((t >= a) & (t < b)).sum(); mu = k / (b - a)
    return -(k * np.log(mu) - mu * (b - a)) if k else 0.0


def rescaled_gaps(t, bounds, fits):
    """국면별 파라미터로 Λ(t_{i-1},t_i) 계산. bounds=[t0,t1,...,tK], fits=국면별 dict."""
    taus = []
    for (a, b), f in zip(zip(bounds[:-1], bounds[1:]), fits):
        mu, al, be = f['mu'], f['alpha'], f['beta']
        idx = np.where((t >= a) & (t < b))[0]
        prev = a
        for i in idx:
            h = t[:i]; h = h[h < t[i]]
            Lam = mu * (t[i] - prev) + (al / be) * np.sum(np.exp(-be * np.clip(prev - h, 0, None)) - np.exp(-be * (t[i] - h)))
            taus.append(Lam); prev = t[i]
    return np.array(taus)


# ---------------- 시뮬레이션 (Ogata thinning, 지수커널 상태 갱신) ----------------
def simulate(hist, start, end, params_at, rng, mmax, cap=50000):
    """hist: start 이전 관측 사건. params_at(t)->(μ,α,β). 상한은 현 시점 강도 + 다음 경계까지 μ 최대."""
    ev = []
    t = start
    pts = list(hist[hist < start])
    while t < end and len(ev) < cap:
        mu, al, be = params_at(t)
        S = np.sum(np.exp(-be * (t - np.array(pts[-3000:])))) if pts else 0.0
        lam_bar = mmax(t, end) + al * S + 1e-9
        t = t + rng.exponential(1 / lam_bar)
        if t >= end:
            break
        mu, al, be = params_at(t)
        S = np.sum(np.exp(-be * (t - np.array(pts[-3000:])))) if pts else 0.0
        if rng.uniform() * lam_bar <= mu + al * S:
            ev.append(t); pts.append(t)
    return np.array(ev)


def main():
    rng = np.random.default_rng(SEED)
    dc = load_dc(); yt = load_yt()
    out = []
    P = lambda *a: out.append(' '.join(str(x) for x in a))

    # ---- 데이터셋 정의
    fk = dc[dc.gall == 'fkgjwks']
    t0_fk = fk.ts.min().floor('h')
    end_fk = fk.ts.max().ceil('h')
    sets = {}
    sets['전용갤(fkgjwks)'] = (to_hours(fk.ts, t0_fk, rng, ~fk.sec_prec.to_numpy()), t0_fk, end_fk)
    t0_p = T('2026-11-14 00:00')  # codebook A: 커뮤니티 의혹 onset
    lg = dc[dc.gall.isin(DC_LONG) & (dc.ts >= t0_p)]
    sets['디시 장기수집 7갤'] = (to_hours(lg.ts, t0_p, rng, ~lg.sec_prec.to_numpy()), t0_p, T('2026-11-19 22:00'))
    al_ = dc[dc.ts >= t0_p]
    sets['디시 전체(통합검색 포함)'] = (to_hours(al_.ts, t0_p, rng, ~al_.sec_prec.to_numpy()), t0_p, T('2026-11-19 22:00'))
    y = yt[yt.ts >= t0_p]
    sets['유튜브 업로드'] = (to_hours(y.ts, t0_p, rng), t0_p, T('2026-11-19 17:30'))

    P(f"fkgjwks 글번호 최대 {int(fk.item_id.str.split('_').str[-1].astype(int).max())} vs 수집 {len(fk)} → 잔존율 {len(fk)/fk.item_id.str.split('_').str[-1].astype(int).max():.1%} (삭제·미수집 글은 시각 불명)")

    phases4 = [('고발 이전', None, ACCUSE), ('고발~검증', ACCUSE, VERIFY), ('검증~발견', VERIFY, FOUND), ('발견 이후', FOUND, None)]
    phases5 = [('고발 이전', None, ACCUSE), ('고발~검증', ACCUSE, VERIFY), ('검증 생중계', VERIFY, MISSING), ('실종', MISSING, FOUND), ('발견 이후', FOUND, None)]
    h = lambda ts, t0: (ts - t0).total_seconds() / 3600

    table = []; fits_keep = {}
    for name, (t, t0, end) in sets.items():
        for split_name, phases in (('4국면', phases4), ('5국면', phases5)):
            if split_name == '5국면' and name != '전용갤(fkgjwks)':
                continue
            bounds = [0.0] + [h(p[2], t0) for p in phases[:-1]] + [h(end, t0)]
            fits = []
            for (pn, _, _), a, b in zip(phases, bounds[:-1], bounds[1:]):
                f = fit_window(t, a, b); f['phase'] = pn; fits.append(f)
                lr = 2 * (poisson_nll(t, a, b) - f['nll'])
                table.append(dict(data=name, split=split_name, phase=pn, N=f['k'], hours=round(f['hours'], 2),
                                  mu=round(f['mu'], 2), n=round(f['n'], 3), n_CI=f"{f['n_lo']:.2f}–{f['n_hi']:.2f}",
                                  decay_min=round(f['decay_min'], 1), LR_vs_Poisson=round(lr, 1)))
            taus = rescaled_gaps(t, bounds, fits)
            ks = stats.kstest(taus, 'expon')
            tau_n = rescaled_gaps(t, bounds, [dict(mu=((t >= a) & (t < b)).sum() / (b - a), alpha=1e-12, beta=1.0)
                                              for a, b in zip(bounds[:-1], bounds[1:])])
            ks0 = stats.kstest(tau_n, 'expon')
            P(f"[{name} {split_name}] 사건 {len(t)}  KS(Hawkes) D={ks.statistic:.3f} p={ks.pvalue:.3g} | KS(국면별 포아송) D={ks0.statistic:.3f} p={ks0.pvalue:.3g}")
            fits_keep[(name, split_name)] = (t, t0, bounds, fits, taus)

    # 전 구간 단일 국면 적합(비교: 비정상성 무시하면 n이 부풀려지는지)
    for name, (t, t0, end) in sets.items():
        f = fit_window(t, 0.0, h(end, t0))
        table.append(dict(data=name, split='단일(국면 무시)', phase='전체', N=f['k'], hours=round(f['hours'], 1), mu=round(f['mu'], 2),
                          n=round(f['n'], 3), n_CI=f"{f['n_lo']:.2f}–{f['n_hi']:.2f}", decay_min=round(f['decay_min'], 1), LR_vs_Poisson=np.nan))
    tab = pd.DataFrame(table)
    P('\n## 국면별 Hawkes 적합'); P(tab.to_string(index=False))

    # ---- 반사실 시뮬 (전용갤, 5국면)
    t, t0, bounds, fits, _ = fits_keep[('전용갤(fkgjwks)', '5국면')]
    pf = {f['phase']: (f['mu'], f['alpha'], f['beta']) for f in fits}
    bnd = bounds
    def mk(over):
        def params_at(x):
            k = int(np.searchsorted(bnd, x, side='right') - 1); k = min(max(k, 0), len(fits) - 1)
            ph = fits[k]['phase']
            return over.get(ph, pf[ph])
        return params_at
    scen = {
        '실제(적합 파라미터)': {},
        'CF-A: 검증 생중계 67분만 고발 국면 파라미터로': {'검증 생중계': pf['고발~검증']},
        'CF-B: 07:30~13:12 전부 고발 국면 파라미터로': {'검증 생중계': pf['고발~검증'], '실종': pf['고발~검증']},
    }
    s, e, f_ = bnd[2], bnd[4], bnd[5]  # 07:30, 13:12, 끝
    obs = {'07:30~13:12': int(((t >= s) & (t < e)).sum()), '13:12~끝': int(((t >= e) & (t < f_)).sum())}
    P(f"\n## 반사실 시뮬 (전용갤, 1,000회, seed {SEED}) 관측: {obs}")
    sim_rows = []; curves = {}
    grid = np.arange(s, f_ + 1e-9, 0.25)
    for sn, over in scen.items():
        pa = mk(over)
        def mmax(x, end_, pa=pa):
            pts = np.r_[x, [b for b in bnd if x < b < end_]]
            return max(pa(p + 1e-9)[0] for p in pts)
        rs = np.random.default_rng(SEED)
        c1, c2, cv, capped = [], [], [], 0
        for r in range(1000):
            ev = simulate(t, s, f_, pa, rs, mmax)
            capped += len(ev) >= 50000
            c1.append(((ev >= s) & (ev < e)).sum()); c2.append((ev >= e).sum())
            cv.append(np.histogram(ev, bins=grid)[0])
        c1, c2 = np.array(c1), np.array(c2)
        curves[sn] = np.array(cv)
        sim_rows.append(dict(scenario=sn, mean_0730_1312=round(c1.mean(), 1), PI90_0730_1312=f"{np.percentile(c1,5):.0f}–{np.percentile(c1,95):.0f}",
                             mean_1312_end=round(c2.mean(), 1), PI90_1312_end=f"{np.percentile(c2,5):.0f}–{np.percentile(c2,95):.0f}", capped=capped))
    sim = pd.DataFrame(sim_rows); P(sim.to_string(index=False))

    # ---- 그림
    fig, ax = plt.subplots(3, 1, figsize=(12, 13))
    tt, t0_, bb, ff, taus = fits_keep[('전용갤(fkgjwks)', '5국면')]
    hb = np.arange(0, bb[-1] + 0.25, 0.25)
    ax[0].bar(hb[:-1], np.histogram(tt, hb)[0] * 4, width=0.25, align='edge', color='#999', label='관측 (15분 bin, 시간당 환산)')
    xs = np.linspace(0.01, bb[-1] - 0.01, 3000)
    lam = []
    for x in xs:
        k = min(int(np.searchsorted(bb, x, side='right') - 1), len(ff) - 1); f = ff[k]
        hh = tt[tt < x]; lam.append(f['mu'] + f['alpha'] * np.sum(np.exp(-f['beta'] * (x - hh))))
    ax[0].plot(xs, lam, color='#c0392b', lw=1, label='적합 강도 λ(t)')
    for b_, lab in zip(bb[1:-1], ['고발', '검증 07:30', '종료·실종 08:37', '발견 13:12']):
        ax[0].axvline(b_, color='k', ls='--', lw=.8); ax[0].text(b_, ax[0].get_ylim()[1] * .9, lab, rotation=90, ha='right', fontsize=8)
    ax[0].set_yscale('symlog'); ax[0].legend(); ax[0].set_title(f'전용갤 게시 강도와 5국면 Hawkes 적합 (x=시간, 0={t0_:%m/%d %H:%M})')
    ax[0].set_xlabel('시간(h)'); ax[0].set_ylabel('글/시간')
    sub = tab[(tab.split == '4국면')]
    for name, g in sub.groupby('data', sort=False):
        lo = g.n_CI.str.split('–').str[0].astype(float); hi = g.n_CI.str.split('–').str[1].astype(float)
        x = np.arange(len(g)) + list(sets).index(name) * 0.18 - 0.27
        ax[1].errorbar(x, g.n, yerr=[g.n - lo, hi - g.n], fmt='o', capsize=3, label=name)
    ax[1].axhline(1, color='r', ls=':'); ax[1].set_xticks(range(4)); ax[1].set_xticklabels([p[0] for p in phases4])
    ax[1].set_ylim(0, 1.5); ax[1].set_ylabel('분기비 n = α/β'); ax[1].legend(fontsize=8); ax[1].set_title('국면별 분기비 (95% CI, 빨간 점선 = 임계 1)')
    mid = (grid[:-1] + grid[1:]) / 2
    for sn, cv in curves.items():
        m = cv.mean(0) * 4; lo, hi = np.percentile(cv * 4, [5, 95], axis=0)
        ax[2].plot(mid, m, label=sn); ax[2].fill_between(mid, lo, hi, alpha=.15)
    ax[2].bar(grid[:-1], np.histogram(tt, grid)[0] * 4, width=0.25, align='edge', color='#ccc', label='관측')
    for b_ in bb[2:5]:
        ax[2].axvline(b_, color='k', ls='--', lw=.8)
    ax[2].set_title('반사실: 공개검증 외생 충격 제거 시 전용갤 주목도 (1,000회 평균, 90% 구간)'); ax[2].set_xlabel('시간(h)'); ax[2].set_ylabel('글/시간'); ax[2].legend(fontsize=8)
    fig.tight_layout(); fig.savefig(f'{FIND}/260119_RQ7_Hawkes.png', dpi=130)

    fig, ax = plt.subplots(figsize=(5, 5))
    q = np.sort(taus); ax.plot(stats.expon.ppf((np.arange(len(q)) + .5) / len(q)), q, '.', ms=3)
    ax.plot([0, q.max()], [0, q.max()], 'r-'); ax.set_xlabel('Exp(1) 이론 분위'); ax.set_ylabel('재조정 간격 τ')
    ax.set_title('전용갤 5국면 Hawkes 시간 재조정 QQ'); fig.tight_layout(); fig.savefig(f'{FIND}/260119_RQ7_Hawkes_QQ.png', dpi=130)
    tab.to_csv(f'{FIND}/260119_RQ7_Hawkes_table.csv', index=False)
    print('\n'.join(out))


if __name__ == '__main__':
    main()
