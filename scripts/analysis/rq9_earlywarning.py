"""RQ9 조기경보: 실종(08:37)·발견(13:12) 이전에 임계 신호가 있었나. 사후(offline) vs 실시간(online) 구분.
실행: python3 scripts/analysis/rq9_earlywarning.py   (work/lab_260119b.db 사본, 시드 260119)
지표: (a) 디시 시간당 글 수 + 이동창 분산·lag-1 자기상관(임계 감속) (b) Hawkes 분기비 이동창(과거 24h만)
      (c) 생방송 개시·동시 진행·채팅 속도 (d) 층화표본 코딩 공격 stance·R·O flag 비율(Wilson CI)
      (e) 제목 키워드(자해/행방) 전수 카운트 — 조잡한 대리지표
변화점: 오프라인 PELT(포아송 비용) / 온라인 CUSUM(과거 24h 평균·분산으로 표준화, 미래 데이터 미사용)."""
import sys, os, json, glob
sys.path.insert(0, os.path.dirname(__file__))
import numpy as np, pandas as pd, sqlite3, matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from scipy import stats
from common import to_kst, KST
from rq7_hawkes import DB, FIND, SEED, T, ACCUSE, VERIFY, MISSING, FOUND, DC_LONG, load_dc, load_yt, to_hours, fit_window
plt.rcParams['font.family'] = 'AppleGothic'; plt.rcParams['axes.unicode_minus'] = False

S0, E0 = T('2026-11-12 00:00'), T('2026-11-19 22:00')
IDX = pd.date_range(S0, E0, freq='h', inclusive='left')
RWORD = '자살|자해|극단|투신|유서|목숨|뛰어내|한강'
CONTACT = '연락 ?두절|연락이 안|연락 ?안 ?받|폰 꺼'
GONE = '잠적|연락두절|실종|도망|튀었|튐|런침|런했|잠수|안 ?나타|안 ?나올|안 ?온다'


def hourly(ts, idx=IDX):
    return ts.dt.floor('h').value_counts().reindex(idx, fill_value=0).sort_index()


def wilson(k, n, z=1.96):
    if n == 0: return (np.nan, np.nan, np.nan)
    p = k / n; d = 1 + z * z / n; c = (p + z * z / (2 * n)) / d; w = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return p, c - w, c + w


def pelt(x, pen, minseg=2):
    """포아송 평균 변화 PELT. cost = -2 logL(구간 상수율)."""
    cs = np.r_[0, np.cumsum(x)]; n = len(x)
    def cost(a, b):
        s = cs[b] - cs[a]; L = b - a
        return 0.0 if s == 0 else -2 * (s * np.log(s / L) - s)
    F = np.full(n + 1, np.inf); F[0] = -pen; last = np.zeros(n + 1, int); R = [0]
    for b in range(minseg, n + 1):
        cand = [(F[a] + cost(a, b) + pen, a) for a in R if b - a >= minseg]
        if not cand: continue
        F[b], last[b] = min(cand)
        R = [a for a in R if b - a < minseg or F[a] + cost(a, b) <= F[b]] + [b - minseg + 1]
    cps, b = [], n
    while b > 0:
        b = last[b]
        if b > 0: cps.append(b)
    return sorted(cps)


def online_cusum(x, win=24, k=0.5, h=5.0, minbase=1.0):
    """t시점 판단에 x[t-win:t]만 사용. z=(x_t-m)/sqrt(max(v,m,minbase)). 경보 후 리셋."""
    S, alarms, zs = 0.0, [], []
    for i in range(len(x)):
        if i < win: zs.append(np.nan); continue
        past = x[i - win:i]; m = past.mean(); v = max(past.var(ddof=1), m, minbase)
        z = (x[i] - m) / np.sqrt(v); zs.append(z)
        S = max(0.0, S + z - k)
        if S > h: alarms.append(i); S = 0.0
    return alarms, np.array(zs)


def ews(x, win):
    """인과적 잔차(과거 win 평균 제거) 후 이동창 분산·lag-1 자기상관."""
    s = pd.Series(x, dtype=float)
    resid = s - s.shift(1).rolling(win).mean()
    var = resid.rolling(win).var()
    ac1 = resid.rolling(win).apply(lambda w: pd.Series(w).autocorr(1) if np.std(w) > 0 else np.nan, raw=True)
    return var.to_numpy(), ac1.to_numpy()


def kendall_with_surrogates(x, win, t_from, t_to, rng, nsur=1000):
    """[t_from,t_to) 구간 지표의 Kendall τ와, AR(1) 대리계열(같은 평균·분산·lag1)에서의 τ 분포 → 단측 p."""
    var, ac1 = ews(x, win)
    sl = slice(t_from, t_to)
    out = {}
    fano = var / np.maximum(pd.Series(x, dtype=float).rolling(win).mean().to_numpy(), 0.5)
    for nm, ind in (('분산', var), ('AC1', ac1), ('Fano', fano)):
        y = ind[sl]; ok = ~np.isnan(y)
        tau = stats.kendalltau(np.arange(ok.sum()), y[ok]).statistic
        out[nm] = tau
    xs = np.asarray(x[:t_to], float); mu, sd = xs.mean(), xs.std()
    r1 = pd.Series(xs).autocorr(1)
    sur = {'분산': [], 'AC1': [], 'Fano': []}
    for _ in range(nsur):
        e = rng.normal(0, sd * np.sqrt(1 - r1 ** 2), len(xs)); z = np.empty(len(xs)); z[0] = mu
        for i in range(1, len(xs)): z[i] = mu + r1 * (z[i - 1] - mu) + e[i]
        v, a = ews(z, win)
        fz = v / np.maximum(pd.Series(z).rolling(win).mean().to_numpy(), 0.5)
        for nm, ind in (('분산', v), ('AC1', a), ('Fano', fz)):
            y = ind[sl]; ok = ~np.isnan(y); sur[nm].append(stats.kendalltau(np.arange(ok.sum()), y[ok]).statistic)
    return {nm: (out[nm], float(np.mean(np.array(sur[nm]) >= out[nm]))) for nm in out}


def main():
    rng = np.random.default_rng(SEED)
    out = []; P = lambda *a: out.append(' '.join(str(x) for x in a))
    c = sqlite3.connect(DB)
    dc = load_dc(); yt = load_yt()
    lg = dc[dc.gall.isin(DC_LONG)]
    fk = dc[dc.gall == 'fkgjwks']
    ch = pd.read_sql("select item_id, ts, kind, text from chats", c); ch['ts'] = to_kst(ch.ts)
    live = pd.read_sql("select item_id, published_at from items where source_type='youtube_live'", c); live['ts'] = to_kst(live.published_at)

    ser = pd.DataFrame({
        '디시 장기 7갤': hourly(lg.ts),
        '디시 전용갤': hourly(fk.ts),
        '유튜브 업로드': hourly(yt.ts),
        '생방송 채팅': hourly(ch.ts),
        '생방송 개시': hourly(live.ts),
        '자해어 제목(7갤)': hourly(lg[lg.title.fillna('').str.contains(RWORD)].ts),
        '행방어 제목(7갤)': hourly(lg[lg.title.fillna('').str.contains(GONE)].ts),
        '연락두절 제목(디시 전체)': hourly(dc[dc.title.fillna('').str.contains(CONTACT)].ts),
        '자해어 채팅': hourly(ch[ch.text.fillna('').str.contains(RWORD)].ts),
    })
    act = ch.assign(h=ch.ts.dt.floor('h')).groupby('h').item_id.nunique().reindex(IDX, fill_value=0)
    ser['동시 생방송(채팅 있는)'] = act.to_numpy()
    iV, iM, iF = IDX.get_loc(VERIFY.floor('h')), IDX.get_loc(MISSING.floor('h')), IDX.get_loc(FOUND.floor('h'))
    P('## 시간당 지표: 11/19 00~13시 (07=검증 시작, 08=종료·실종, 13=발견)')
    P(ser.iloc[IDX.get_loc(T('2026-11-18 18:00')):iF + 2].to_string())
    P('\n제목 키워드 7갤 07:30 이전 합계: 자해어', int(lg[(lg.ts < VERIFY) & lg.title.fillna('').str.contains(RWORD)].shape[0]),
      '/ 행방어', int(lg[(lg.ts < VERIFY) & lg.title.fillna('').str.contains(GONE)].shape[0]))
    for _, r in lg[(lg.ts < VERIFY) & (lg.ts >= T('2026-11-17 00:00')) & lg.title.fillna('').str.contains(GONE + '|' + RWORD)].sort_values('ts').iterrows():
        P(f"  {r.ts:%m-%d %H:%M} {r.gall} | {str(r.title)[:50]}")

    # ---- (a) 임계 감속
    P('\n## (a) 임계 감속 지표: Kendall τ (11/15 00시 → 11/19 07시, 08:37 이전 데이터만) + AR(1) 대리 1,000개 단측 p')
    a, b = IDX.get_loc(T('2026-11-15 00:00')), iV + 1
    for col, win in (('디시 장기 7갤', 24), ('디시 장기 7갤', 12), ('유튜브 업로드', 24)):
        r = kendall_with_surrogates(ser[col].to_numpy(), win, a, b, rng)
        P(f"  {col} 창 {win}h: " + ', '.join(f"{k} τ={v[0]:+.2f} p={v[1]:.3f}" for k, v in r.items()))
    a2 = IDX.get_loc(T('2026-11-18 03:00'))
    r = kendall_with_surrogates(ser['디시 전용갤'].to_numpy(), 12, a2, b, rng)
    P(f"  디시 전용갤 창 12h (11/18 03시~): " + ', '.join(f"{k} τ={v[0]:+.2f} p={v[1]:.3f}" for k, v in r.items()))
    var24, ac24 = ews(ser['디시 장기 7갤'].to_numpy(), 24)

    # ---- (b) 이동창 Hawkes 분기비 (과거 24h 사건만)
    P('\n## (b) 이동창 Hawkes n (과거 24h, 2h 간격) — 디시 장기 7갤 / 전용갤(12h창)')
    t0 = S0
    tl = to_hours(lg.ts, t0, rng, ~lg.sec_prec.to_numpy())
    tf = to_hours(fk.ts, t0, rng, ~fk.sec_prec.to_numpy())
    roll = []
    for end in pd.date_range(T('2026-11-15 00:00'), T('2026-11-19 14:00'), freq='2h'):
        e = (end - t0).total_seconds() / 3600
        for nm, tt, w in (('7갤', tl, 24), ('전용갤', tf, 12)):
            sub = tt[(tt >= e - w - 6) & (tt < e)]
            if ((sub >= e - w)).sum() < 15: continue
            f = fit_window(sub, e - w, e)
            roll.append(dict(end=end, data=nm, N=f['k'], n=f['n'], lo=f['n_lo'], hi=f['n_hi'], mu=f['mu']))
    roll = pd.DataFrame(roll)
    P(roll.assign(end=roll.end.dt.strftime('%m-%d %H'), n=roll.n.round(2), lo=roll.lo.round(2), hi=roll.hi.round(2), mu=roll.mu.round(2)).to_string(index=False))

    # ---- (d) 코딩 표본
    rows = []
    for f in sorted(glob.glob('/Users/river/social-lab/data/raw/codes_haikuv2_*.jsonl')):
        rows += [json.loads(l) for l in open(f) if l.strip()]
    cd = pd.DataFrame(rows).drop_duplicates('target_id')
    cd = cd.merge(dc[['item_id', 'ts', 'gall']], left_on='target_id', right_on='item_id')
    bins = [('~11/13 (세무냥이)', S0 - pd.Timedelta(days=60), T('2026-11-14 00:00')), ('의혹 11/14~11/18 09', T('2026-11-14 00:00'), ACCUSE),
            ('고발 ~11/19 07:30', ACCUSE, VERIFY), ('검증·실종 07:30~13:12', VERIFY, FOUND), ('발견 이후', FOUND, E0)]
    P(f'\n## (d) 층화표본 코딩(haiku-v2) 중 디시 글 {len(cd)}건 — 국면별 비율과 Wilson 95% CI')
    drows = []
    for nm, a_, b_ in bins:
        g = cd[(cd.ts >= a_) & (cd.ts < b_)]; n = len(g)
        rel = g[g.stance != '무관']
        for lab, k, base in (('공격 stance(무관 제외)', (rel.stance == '공격').sum(), len(rel)),
                             ('R-flag', g['flags'].map(lambda f: 'R' in f).sum(), n), ('O-flag', g['flags'].map(lambda f: 'O' in f).sum(), n)):
            p, lo, hi = wilson(int(k), int(base))
            drows.append(dict(bin=nm, 지표=lab, k=int(k), n=int(base), p=p, lo=lo, hi=hi))
    dtab = pd.DataFrame(drows)
    P(dtab.assign(p=dtab.p.round(3), lo=dtab.lo.round(3), hi=dtab.hi.round(3)).to_string(index=False))
    rf = cd[cd['flags'].map(lambda f: 'R' in f or 'O' in f) & (cd.ts < VERIFY)].sort_values('ts')
    P('  07:30 이전 R/O flag 글:'); [P(f"   {r.ts:%m-%d %H:%M} {r.gall} {r['flags']}") for _, r in rf.iterrows()]

    # ---- 변화점: 오프라인 PELT
    P('\n## 변화점 (오프라인 PELT, 포아송 비용, 벌점 = 과분산 φ × 2 log n) — 사후 판단')
    w0 = IDX.get_loc(T('2026-11-14 00:00'))
    for col in ('디시 장기 7갤', '디시 전용갤', '유튜브 업로드', '생방송 채팅'):
        x = ser[col].to_numpy()[w0:iF + 6]
        st = 0 if col != '디시 전용갤' else IDX.get_loc(T('2026-11-17 14:00')) - w0
        x = x[st:]
        mu_ = pd.Series(x).rolling(6, center=True, min_periods=1).mean().to_numpy()
        phi = max(1.0, np.mean((x - mu_) ** 2 / np.maximum(mu_, 0.5)))
        cps = pelt(x, pen=phi * 2 * np.log(len(x)))
        P(f"  {col} (φ={phi:.1f}): " + ', '.join(f"{IDX[w0 + st + k]:%m-%d %H시}" for k in cps))

    # ---- 온라인 CUSUM
    P('\n## 온라인 CUSUM 경보 (과거 24h만 사용, k=0.5) — 11/14 00시 ~ 11/19 13시')
    alarm_rows = []
    for col in ('디시 장기 7갤', '디시 전용갤', '유튜브 업로드', '생방송 채팅', '생방송 개시', '행방어 제목(7갤)', '자해어 제목(7갤)', '연락두절 제목(디시 전체)', '자해어 채팅'):
        for h in (5.0, 10.0):
            x = ser[col].to_numpy().astype(float)
            al, _ = online_cusum(x, h=h)
            al = [i for i in al if w0 <= i <= iF]
            ts_ = [IDX[i] for i in al]
            pre = [t for t in ts_ if t < VERIFY.floor('h')]
            first_after_acc = [t for t in ts_ if t >= ACCUSE.floor('h')]
            alarm_rows.append(dict(series=col, h=h, n_alarms=len(ts_), before_0730=len(pre),
                                   last_before_0730=(pre[-1].strftime('%m-%d %H시') if pre else '-'),
                                   lead_to_0837=(f"{(MISSING - pre[-1]).total_seconds()/3600:.1f}h" if pre else '-'),
                                   alarms=' '.join(t.strftime('%d일%H') for t in ts_)))
    at = pd.DataFrame(alarm_rows); P(at.to_string(index=False))
    # 오경보율: 11/14~11/18 08시(실종 이전 ~4.4일) 동안 경보 수 / 일
    pre_days = (VERIFY - T('2026-11-14 00:00')).total_seconds() / 86400
    first = dc[(dc.ts < MISSING) & dc.title.fillna('').str.contains(CONTACT)].ts.min()
    P(f"  '첫 등장' 규칙(연락두절 계열 제목이 처음 나오면 경보): {first:%m-%d %H:%M} → 08:37까지 {(MISSING-first).total_seconds()/3600:.1f}h, 13:12까지 {(FOUND-first).total_seconds()/3600:.1f}h")
    rc = ch[(ch.ts < MISSING) & ch.text.fillna('').str.contains(RWORD)]
    P(f"  채팅 자해어 08:37 이전 {len(rc)}건 / 채팅 {int((ch.ts < MISSING).sum())}건, 첫 {rc.ts.min():%m-%d %H:%M}; 시간별:", rc.ts.dt.floor('h').dt.strftime('%d일%H').value_counts().sort_index().to_dict())
    P(f"  참고: 11/14 00시~11/19 07시 = {pre_days:.1f}일. 이 구간 경보는 '사망 위기' 기준으로는 모두 오경보 후보(주목 급증은 맞힐 수 있음).")

    # ---- 그림
    fig, ax = plt.subplots(5, 1, figsize=(13, 17), sharex=True)
    win = slice(IDX.get_loc(T('2026-11-14 00:00')), iF + 9)
    xi = IDX[win]
    def marks(a_):
        for t_, c_ in ((ACCUSE, '#888'), (VERIFY, 'k'), (MISSING, 'r'), (FOUND, 'r')):
            a_.axvline(t_, color=c_, ls='--', lw=.8)
    ax[0].plot(xi, ser['디시 장기 7갤'][win], label='디시 장기 7갤'); ax[0].plot(xi, ser['디시 전용갤'][win], label='디시 전용갤')
    ax[0].plot(xi, ser['유튜브 업로드'][win] * 10, label='유튜브 업로드 ×10')
    for col in ('디시 장기 7갤', '디시 전용갤'):
        al, _ = online_cusum(ser[col].to_numpy().astype(float), h=5.0)
        al = [IDX[i] for i in al if win.start <= i < win.stop]
        ax[0].plot(al, ser[col].loc[al], 'v', ms=7, label=f'온라인 경보 h=5 ({col})')
    ax[0].set_yscale('symlog'); ax[0].legend(fontsize=7); ax[0].set_title('(a) 시간당 글 수와 온라인 CUSUM 경보 (▼)'); marks(ax[0])
    ax[1].plot(xi, var24[win] / np.nanmax(var24[win]), label='이동 분산(24h, 정규화)'); ax[1].plot(xi, ac24[win], label='lag-1 자기상관(24h)')
    ax[1].legend(fontsize=8); ax[1].set_title('(a) 임계 감속 지표 — 디시 장기 7갤 (인과적 잔차)'); marks(ax[1])
    for nm, g in roll.groupby('data'):
        ax[2].plot(g.end, g.n, 'o-', ms=3, label=nm); ax[2].fill_between(g.end, g.lo.clip(upper=3), g.hi.clip(upper=3), alpha=.15)
    ax[2].axhline(1, color='r', ls=':'); ax[2].set_ylim(0, 2); ax[2].legend(fontsize=8); ax[2].set_title('(b) 이동창 Hawkes 분기비 (과거 창만 사용, 95% CI)'); marks(ax[2])
    ax[3].plot(xi, ser['생방송 채팅'][win], label='채팅/시간'); ax3 = ax[3].twinx()
    ax3.step(xi, ser['동시 생방송(채팅 있는)'][win], color='C1', where='post', label='채팅 있는 생방송 수'); ax3.bar(xi, ser['생방송 개시'][win], width=1 / 24, color='C2', alpha=.6, label='생방송 개시')
    ax[3].legend(loc='upper left', fontsize=8); ax3.legend(loc='upper center', fontsize=8); ax[3].set_title('(c) 생방송: 채팅 속도·동시 진행·개시'); marks(ax[3])
    for lab, cc in (('공격 stance(무관 제외)', 'C3'), ('R-flag', 'C0'), ('O-flag', 'C2')):
        g = dtab[dtab.지표 == lab]
        mids = [a_ + (min(b_, E0) - max(a_, T('2026-11-13 12:00'))) / 2 if a_ > T('2026-11-13') else T('2026-11-14 00:00') for _, a_, b_ in bins]
        ax[4].errorbar(mids, g.p, yerr=[g.p - g.lo, g.hi - g.p], fmt='o-', capsize=3, color=cc, label=lab)
    ax[4].legend(fontsize=8); ax[4].set_title('(d) 코딩 표본 비율 (국면 단위, Wilson 95% CI)'); marks(ax[4])
    ax[4].set_xlim(xi[0], xi[-1])
    fig.tight_layout(); fig.savefig(f'{FIND}/260119_RQ9_조기경보.png', dpi=120)
    at.to_csv(f'{FIND}/260119_RQ9_alarms.csv', index=False); roll.to_csv(f'{FIND}/260119_RQ9_rolling_n.csv', index=False)
    print('\n'.join(out))


if __name__ == '__main__':
    main()
