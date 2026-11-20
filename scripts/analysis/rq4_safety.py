"""RQ4 안전장치: 제도 시계 vs 군중 시계, 언론(보도준칙) 레이어, 플랫폼(생방송) 레이어.
사본 DB(work/lab_260120.db)와 raw 읽기 전용. 출력: findings/260120_RQ4_*.png, work/rq4_safety.out(stdout 복사본은 호출자가).
탐색(exploratory) 분석. 인과 주장 없음 — 시간적 선후와 크기만.
실행: cd /Users/river/social-lab && python3 scripts/analysis/rq4_safety.py
"""
import json, os, re, sqlite3, sys
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

sys.path.insert(0, os.path.dirname(__file__))
plt.rcParams['font.family'] = 'AppleGothic'
plt.rcParams['axes.unicode_minus'] = False

ROOT = '/Users/river/social-lab'
DB = f'{ROOT}/work/lab_260120.db'
OUT = f'{ROOT}/findings/260120_RQ4'
KST = 'Asia/Seoul'
rng = np.random.default_rng(20260120)


def T(s):
    t = pd.Timestamp(s)
    return t.tz_localize(KST) if t.tzinfo is None else t.tz_convert(KST)


def jl(p):
    return [json.loads(l) for l in open(p)]


c = sqlite3.connect(DB)
FOUND = T('2026-11-19T13:12')      # 발견(사망 전 심정지 상태 발견 보도 기준 사건 시각)
CONFIRM = T('2026-11-19T14:01')    # 민감도용: 사망 확인 보도 방송 개시 시각(JTBC 라이브 release)

# ---------------------------------------------------------------- 사건
ev = pd.read_sql('select ts,phase,event,source_url from events', c)
kind = {d['event']: d['kind'] for d in jl(f'{ROOT}/data/raw/web_1119/events_web.jsonl')}
ev['kind'] = ev.event.map(kind).fillna('subject')  # 맥 수집 1건(자수 영상 공개)은 jsonl에 없음 → subject
ev['minute'] = ev.ts.str.len() > 10
ev['t'] = ev.ts.map(T)
ev = ev.sort_values('t').reset_index(drop=True)
print('events', len(ev), ev.kind.value_counts().to_dict(), 'minute-level', int(ev.minute.sum()))

# ---------------------------------------------------------------- 군중 지표
g = pd.read_sql("select published_at from items where json_extract(extra,'$.gall_id')='fkgjwks'", c)
G = pd.Series(sorted(T(x) for x in g.published_at))              # A등급: 전용갤 전수
G_COV = (T('2026-11-17T14:08'), T('2026-11-19T21:50'))           # 첫 글 ~ 수집 시각
b = {}
for d in jl(f'{ROOT}/data/raw/dc_search_gall.jsonl'):            # B등급: 관련 갤러리 키워드 검색(통합검색 C 제외)
    if d['gall_id'] != 'fkgjwks':
        b[d['url']] = T(d['published_at'])
B = pd.Series(sorted(b.values()))
B_COV = (T('2026-11-13T00:00'), T('2026-11-19T22:24'))
snap = jl(f'{ROOT}/data/raw/yt_snapshots.jsonl')
REL = re.compile('냥이|리트|LEET|세무사|REDACTED_SUBJECT|만점|공개검증|AI ?안경|부정행위|고인|명복|IDA|시험지')
ytrows = []
for r in snap:
    txt = ' '.join([r['channel'] or '', r['title'] or '', r['description'] or '', ' '.join(r['tags'] or [])])
    if not REL.search(txt):
        continue
    live = r['live_status'] != 'not_live'
    ts = r['release_timestamp'] or r['timestamp'] if live else r['timestamp']
    ytrows.append(dict(id=r['id'], channel=r['channel'], title=r['title'], live=live, status=r['live_status'],
                       start=pd.Timestamp(ts, unit='s', tz='UTC').tz_convert(KST), dur=r['duration'],
                       views=r['view_count'], up=pd.Timestamp(r['timestamp'], unit='s', tz='UTC').tz_convert(KST)))
Y = pd.DataFrame(ytrows)
U = pd.Series(sorted(Y.start))                                    # A등급: 검색 노출 영상 업로드·방송 개시
U_COV = (T('2026-11-12T00:00'), T('2026-11-19T18:34'))
print('crowd n: G', len(G), 'B', len(B), 'U', len(U), '(yt relevant', len(Y), '/', len(snap), ')')


def cnt(S, a, b_, cov):
    lo, hi = max(a, cov[0]), min(b_, cov[1])
    h = max((hi - lo).total_seconds() / 3600, 0)
    return int(((S >= lo) & (S < hi)).sum()), h


def ratio(S, t, w, cov, min_cov=0.5):
    n0, h0 = cnt(S, t - pd.Timedelta(hours=w), t, cov)
    n1, h1 = cnt(S, t, t + pd.Timedelta(hours=w), cov)
    if h0 < w * min_cov or h1 < w * min_cov:
        return None
    r = ((n1 + 0.5) / h1) / ((n0 + 0.5) / h0)   # 0.5 가산(0건 창 방지)
    return dict(n0=n0, h0=h0, n1=n1, h1=h1, r0=n0 / h0, r1=n1 / h1, ratio=r)


def baseline(S, w, cov, step_min=30):
    t = cov[0] + pd.Timedelta(hours=w)
    out = []
    while t <= cov[1] - pd.Timedelta(hours=w):
        x = ratio(S, t, w, cov)
        if x:
            out.append(x['ratio'])
        t += pd.Timedelta(minutes=step_min)
    return np.array(out)


IDX = {'G(전용갤·A)': (G, G_COV), 'B(관련갤·B)': (B, B_COV), 'U(유튜브 업로드·A)': (U, U_COV)}
BASE = {(k, w): baseline(S, w, cov) for k, (S, cov) in IDX.items() for w in (3, 6, 12)}
for k in IDX:
    for w in (3, 6, 12):
        bs = BASE[(k, w)]
        print(f'baseline {k} ±{w}h: windows={len(bs)} median ratio={np.median(bs):.2f} P(ratio>=2)={np.mean(bs >= 2):.2f} P(ratio<=0.5)={np.mean(bs <= 0.5):.2f}')

rows = []
for _, e in ev[ev.minute].iterrows():
    row = dict(t=e.t, kind=e.kind, event=e.event)
    for k, (S, cov) in IDX.items():
        for w in (3, 6, 12):
            x = ratio(S, e.t, w, cov)
            row[f'{k}|{w}'] = x['ratio'] if x else np.nan
            if w == 6:
                row[f'{k}|n'] = f"{x['n0']}→{x['n1']}" if x else ''
                row[f'{k}|pct'] = float((BASE[(k, 6)] <= x['ratio']).mean()) if x else np.nan
    rows.append(row)
R = pd.DataFrame(rows)
pd.set_option('display.width', 250, 'display.max_colwidth', 40)
print('\n[분 단위 사건 ±6h, 전용갤 G 평가 가능분]')
rg = R[R['G(전용갤·A)|6'].notna()]
print(rg[['t', 'kind', 'event', 'G(전용갤·A)|n', 'G(전용갤·A)|6', 'G(전용갤·A)|pct', 'G(전용갤·A)|3', 'G(전용갤·A)|12']].round(2).to_string())
print('\n[분 단위 사건 ±6h, 관련갤 B 평가 가능분]')
rb = R[R['B(관련갤·B)|6'].notna()]
print(rb[['t', 'kind', 'event', 'B(관련갤·B)|n', 'B(관련갤·B)|6', 'B(관련갤·B)|pct', 'B(관련갤·B)|3', 'B(관련갤·B)|12']].round(2).to_string())


def cls(x):
    return np.nan if pd.isna(x) else (1 if x >= 2 else (-1 if x <= 0.5 else 0))


print('\n[사건 종류별 ±6h 비율 요약 (탐색)]')
for k in IDX:
    col = f'{k}|6'
    s = R[R[col].notna()]
    print(k, 'n=', len(s), '중앙값', round(s[col].median(), 2), '≥2:', int((s[col] >= 2).sum()), '≤0.5:', int((s[col] <= 0.5).sum()),
          '| 무작위 창 P(≥2)=', round(float(np.mean(BASE[(k, 6)] >= 2)), 2))
    print(s.groupby('kind')[col].agg(['count', 'median', 'min', 'max']).round(2).to_string())
print('\n[창 폭 민감도: 방향 일치(≥2/≤0.5/그 사이) 사건 수]')
for k in IDX:
    s = R[R[f'{k}|6'].notna()]
    same = sum(len({cls(r[f'{k}|3']), cls(r[f'{k}|6']), cls(r[f'{k}|12'])} - {np.nan}) == 1 for _, r in s.iterrows()
               if not pd.isna(r[f'{k}|3']) and not pd.isna(r[f'{k}|12']))
    tot = sum((not pd.isna(r[f'{k}|3'])) and (not pd.isna(r[f'{k}|12'])) for _, r in s.iterrows())
    print(k, f'3·6·12h 모두 평가 가능 {tot}건 중 분류 일치 {same}건')

# 발견 시각 기준 민감도(13:12 vs 14:01)
print('\n[기준 시각 민감도: 발견 13:12 vs 사망 확인 보도 14:01]')
for k, (S, cov) in IDX.items():
    for lab, t0 in (('13:12', FOUND), ('14:01', CONFIRM)):
        x = ratio(S, t0, 6, cov)
        if x:
            print(k, lab, f"±6h {x['n0']}→{x['n1']}건 ({x['r0']:.1f}→{x['r1']:.1f}/h) ratio={x['ratio']:.1f} 무작위창 백분위={(BASE[(k, 6)] <= x['ratio']).mean():.2f}")

# 날짜만 있는 사건: 일 단위 비교
print('\n[날짜만 있는 사건(일 단위, 시각 불명)]')
dd = ev[~ev.minute].copy()
dd['d'] = dd.ts
for d0, grp in dd.groupby('d'):
    day = T(d0)
    out = [f"{d0} 사건 {len(grp)}건({','.join(grp.kind.value_counts().index)})"]
    for k, (S, cov) in IDX.items():
        n1, h1 = cnt(S, day, day + pd.Timedelta(days=1), cov)
        n0, h0 = cnt(S, day - pd.Timedelta(days=1), day, cov)
        if h0 >= 12 and h1 >= 12:
            out.append(f"{k[0]} 전일 {n0}/{h0:.0f}h→당일 {n1}/{h1:.0f}h ({(n1 / h1) / max(n0 / h0, 1e-9):.2f}x)")
    print(' | '.join(out))
print('날짜 사건 목록(kind): ', dd.groupby('ts').apply(lambda x: ','.join(x.kind)).to_dict())

# ---------------------------------------------------------------- 그림1: 한 타임라인
fig, ax = plt.subplots(3, 1, figsize=(15, 10), sharex=True)
x0, x1 = T('2026-11-14'), T('2026-11-20')
hrs = pd.date_range(x0, x1, freq='h', tz=KST)
for a, (S, lab, col) in zip(ax, [(B, '관련 갤러리 검색분 시간당 글(B)', '#888'), (G, '전용갤(fkgjwks) 시간당 글(A) — 개설 11-17 14:08 이후', '#c0392b'),
                                 (U, '유튜브 업로드·방송 개시 시간당(A, 검색 노출 영상)', '#2c3e50')]):
    cts = pd.Series(S.values).value_counts() if False else pd.Series(1, index=pd.DatetimeIndex(S)).resample('h').sum().reindex(hrs, fill_value=0)
    a.bar(cts.index, cts.values, width=1 / 24, color=col, align='edge')
    a.set_ylabel(lab, fontsize=8)
    a.set_yscale('symlog', linthresh=10)
kc = {'police': '#1f77b4', 'institution': '#2ca02c', 'government': '#9467bd', 'media': '#ff7f0e', 'platform': '#d62728', 'subject': '#000', 'community': '#8c564b'}
for _, e in ev.iterrows():
    for a in ax:
        if e.minute:
            a.axvline(e.t, color=kc[e.kind], lw=.7, alpha=.6)
        else:
            a.axvspan(e.t, e.t + pd.Timedelta(days=1), color=kc[e.kind], alpha=.015)
for a in ax:
    a.axvline(FOUND, color='k', lw=2.2)
ax[0].text(FOUND, ax[0].get_ylim()[1], ' 발견 13:12', va='top', fontsize=9)
ax[0].set_title('제도 사건(세로선=분 단위, 옅은 띠=날짜만 있는 사건) vs 군중 지표  [탐색적 · 인과 주장 없음]')
ax[0].legend(handles=[plt.Line2D([0], [0], color=v, lw=2, label=k) for k, v in kc.items()], ncol=7, fontsize=8, loc='upper left')
ax[2].xaxis.set_major_formatter(matplotlib.dates.DateFormatter('%m-%d %H', tz=KST))
plt.tight_layout(); plt.savefig(OUT + '_타임라인.png', dpi=130); plt.close()

# ---------------------------------------------------------------- 그림2: 사건별 ±6h 비율
fig, axs = plt.subplots(1, 2, figsize=(15, 8))
for a, k in zip(axs, ['G(전용갤·A)', 'B(관련갤·B)']):
    s = R[R[f'{k}|6'].notna()].copy()
    ypos = np.arange(len(s))[::-1]
    a.barh(ypos, np.log2(s[f'{k}|6'].values), color=[kc[x] for x in s.kind])
    bs = BASE[(k, 6)]
    a.axvspan(np.log2(np.percentile(bs, 5)), np.log2(np.percentile(bs, 95)), color='#ddd', alpha=.7, label='무작위 시점 창 5~95%')
    a.axvline(0, color='k', lw=.8)
    a.set_yticks(ypos); a.set_yticklabels([f"{r.t.strftime('%d %H:%M')} {r.event[:22]}" for r in s.itertuples()], fontsize=7)
    a.set_xlabel('log2(사건 후 6h 시간당 글 / 사건 전 6h)'); a.set_title(k + ' ±6h'); a.legend(fontsize=8)
plt.suptitle('사건 전후 군중 볼륨 비 (회색 띠 = 사건과 무관한 임의 시점의 분포; 둘 다 증가 추세 위에 있음)', fontsize=11)
plt.tight_layout(); plt.savefig(OUT + '_사건전후.png', dpi=130); plt.close()

# ---------------------------------------------------------------- 언론
print('\n\n===== 언론 레이어 (질적 보조 자료 기준) =====')
nw = pd.read_sql("select item_id,published_at,phase,title,description,author,extra from items where source_type='news'", c)
nw['x'] = nw.extra.map(json.loads)
nw['prec'] = nw.x.map(lambda x: x.get('ts_precision'))
nw['sm'] = nw.x.map(lambda x: x.get('safe_messaging'))
nw['basis'] = nw.sm.map(lambda s: s.get('basis') if s else None)
PH = ['세무냥이', '의혹', '고발', '검증', '실종', '사망']
print('n=', len(nw)); print('국면별:', nw.phase.value_counts().reindex(PH).to_dict())
print('시각 정밀도:', nw.prec.value_counts().to_dict())
print('판정(safe_messaging 객체) 있음:', int(nw.sm.notna().sum()), '/ 없음(null):', int(nw.sm.isna().sum()))
print('판정 있는 건의 국면:', nw[nw.sm.notna()].phase.value_counts().to_dict(), '| basis:', nw.basis.value_counts().to_dict())
print('국면×판정유무:\n', pd.crosstab(nw.phase, nw.sm.notna()).reindex(PH).to_string())
FL = ['location', 'method_tool', 'note_content', 'cctv', 'extreme_choice_term', 'helpline']
j = nw[nw.sm.notna()]
tab = pd.DataFrame({f: j.groupby('phase').apply(lambda x: int(x.sm.map(lambda s: s.get(f) is True).sum())) for f in FL}).reindex(PH).fillna(0).astype(int)
tab['판정건수'] = j.groupby('phase').size().reindex(PH).fillna(0).astype(int)
print('판정 건 중 플래그 true 수 (질적 보조):\n', tab.to_string())
print('helpline 판정 가능(non-null):', int(j.sm.map(lambda s: s.get('helpline') is not None).sum()))
dth = nw[nw.phase == '사망']
print('사망 국면 기사:', len(dth), '판정 있음', int(dth.sm.notna().sum()), '없음', int(dth.sm.isna().sum()))
# 제목+스니펫 수준 자체 키워드 점검(개수만; 내용은 옮기지 않는다)
txt = (dth.title.fillna('') + ' ' + dth.description.fillna(''))
pats = {'위치(동·역·업소유형)': '천호|강동|모텔|역 인근', '유서·메모 언급': '유서|메모', '극단적 선택 표현': '극단적 선택', '자살 단어': '자살', 'CCTV': 'CCTV'}
print('사망 국면 제목+스니펫 자체 키워드 점검 (n=%d):' % len(dth), {k: int(txt.str.contains(v).sum()) for k, v in pats.items()})
tt = dth.title
print('  제목만:', {k: int(tt.str.contains(v).sum()) for k, v in pats.items()})
sm_pat = {k: int(dth.sm.map(lambda s: bool(s and s.get(k) is True)).sum()) for k in FL}
print('  1차 판정(웹 Claude) 사망 국면 true 수:', sm_pat)
both = sum(bool(re.search(pats['유서·메모 언급'], a)) for a in txt)
print('  유서·메모 언급 키워드 건 중 1차 판정 note_content true:', int(dth[txt.str.contains(pats['유서·메모 언급'])].sm.map(lambda s: bool(s and s.get('note_content') is True)).sum()), '/', both)
# 같은 판정이 판정 대상 외 사망 국면 기사 중 키워드만 있고 판정 null인 경우
miss = dth[dth.sm.isna() & txt.str.contains('|'.join(pats.values()))]
print('  사망 국면 중 판정 null인데 자체 키워드 걸린 건:', len(miss))
# 사망 전 국면 위치 보도(수색)
pre = nw[(nw.phase.isin(['검증', '실종']))]
print('검증·실종 국면 기사 %d건 중 판정 있음 %d, location true %d' % (len(pre), int(pre.sm.notna().sum()), int(pre.sm.map(lambda s: bool(s and s.get('location') is True)).sum())))
# 기사 게시 시각 vs 발견
nm = nw[nw.prec.isin(['minute', 'second', 'minute_modified'])].copy()
nm['t'] = nm.published_at.map(T)
print('시각 확정(분·초 단위) 기사', len(nm), '| 발견 13:12 이후:', int((nm.t >= FOUND).sum()), '| 이전:', int((nm.t < FOUND).sum()))
print('사망 국면 기사 중 날짜만:', int((dth.prec.isin(['date', 'date_inferred'])).sum()))

# 언론 그림
fig, axs = plt.subplots(1, 2, figsize=(14, 5))
cnts = nw.phase.value_counts().reindex(PH)
axs[0].bar(PH, cnts.values, color='#ff7f0e')
axs[0].bar(PH, nw[nw.sm.notna()].phase.value_counts().reindex(PH).fillna(0).values, color='#333', label='safe_messaging 1차 판정 있음')
axs[0].set_title('기사 66건 국면별(주황) · 1차 판정 있는 건(검정) [질적 보조]'); axs[0].legend()
tab[FL[:5]].plot.bar(ax=axs[1], rot=0); axs[1].set_title('판정 건 중 플래그 true (스니펫 기준, 질적 보조)')
axs[1].legend(fontsize=7)
plt.tight_layout(); plt.savefig(OUT + '_언론.png', dpi=130); plt.close()

# ---------------------------------------------------------------- 플랫폼
print('\n\n===== 플랫폼 레이어 (생방송) =====')
L = Y[Y.live].copy()
snap_end = T('2026-11-19T18:34')
L['end'] = L.apply(lambda r: r.start + pd.Timedelta(seconds=r.dur) if pd.notna(r.dur) else pd.NaT, axis=1)
BROAD = re.compile('News|NEWS|뉴스|MBC|YTN|JTBC|SBS|KBS|연합|TV ?CHOSUN|조선|채널A|MBN|매일신문|라디오')
L['cls'] = L.channel.map(lambda ch: '방송·언론' if BROAD.search(ch or '') else ('IDA(검증 주관)' if 'IDA' in (ch or '') else '개인·기타'))
TRK = re.compile('추적|찾음|현장|검증|잠적|행방|연락두절|불참|수색|대치|천호|심정지|사망|유서|실종')
L['trk'] = L.title.map(lambda t: bool(TRK.search(t or '')))
d19 = L[(L.start >= T('2026-11-19T00:00'))]
print('생방송 %d편(유튜브 검색 노출·관련성 필터 후), 11-19 개시 %d편' % (len(L), len(d19)))
print('상태:', L.status.value_counts().to_dict())
print('분류:', L.cls.value_counts().to_dict(), '| 제목에 추적·검증·사건어 포함:', int(L.trk.sum()))
def phase_of_t(t):
    for lab, a, b_ in [('의혹·고발 전', None, T('2026-11-18T09:00')), ('고발', T('2026-11-18T09:00'), T('2026-11-19T07:30')),
                       ('검증·실종', T('2026-11-19T07:30'), FOUND), ('사망', FOUND, T('2026-11-20'))]:
        if (a is None or t >= a) and t < b_:
            return lab
L['phase'] = L.start.map(phase_of_t)
print('개시 국면별 편수 (전체 / 개인·기타 / 추적·검증어 포함):')
print(pd.DataFrame({'전체': L.phase.value_counts(), '개인·기타': L[L.cls == '개인·기타'].phase.value_counts(), '추적·검증어': L[L.trk].phase.value_counts()}).reindex(['의혹·고발 전', '고발', '검증·실종', '사망']).fillna(0).astype(int).to_string())
# 사망(발견) 이후에도 이어진 방송
fin = L[L.status != 'is_live']
span = fin[(fin.start < FOUND) & (fin.end > FOUND)]
after = L[L.start >= FOUND]
print('\n발견 13:12 기준: 개시가 이후 %d편 (그중 is_live 상태 %d) | 이전 개시·종료 추정이 이후(걸침) %d편 (개인·기타 %d)' % (len(after), int((after.status == 'is_live').sum()), len(span), int((span.cls == '개인·기타').sum())))
cf = L[L.start >= CONFIRM]
span2 = fin[(fin.start < CONFIRM) & (fin.end > CONFIRM)]
print('민감도 14:01 기준: 개시 이후 %d편, 걸침 %d편(개인·기타 %d)' % (len(cf), len(span2), int((span2.cls == '개인·기타').sum())))
cols = ['cls', 'start', 'end', 'dur', 'views', 'trk', 'status']
print('\n걸침·이후 개시 방송 (개인·기타만 상세, 제목 생략):')
x = pd.concat([span, after]).drop_duplicates('id')
x = x.sort_values('start')
x['id2'] = x.cls.map(lambda s: s[:2]) + pd.Series(range(len(x)), index=x.index).astype(str)
print(x[x.cls == '개인·기타'][['id2'] + cols].to_string())
print('방송·언론 걸침/이후:', int((x.cls == '방송·언론').sum()), '편, 조회수 합', int(x[x.cls == '방송·언론'].views.sum()))
print('개인·기타 걸침/이후 조회수 합', int(x[x.cls == '개인·기타'].views.sum()), '/ 개인·기타 11-19 전체 조회수 합', int(d19[d19.cls == '개인·기타'].views.sum()))
# 방송 채팅: 발견 이후 채팅·슈퍼챗(재생 가능한 29편)
ch = pd.read_sql("select c.item_id,c.ts,c.paid,c.kind from chats c", c)
ch['t'] = ch.ts.map(T)
ids = pd.Series(L.id.values, index='yt_' + L.id).to_dict()
ch['cls'] = ch.item_id.map(lambda i: L.set_index('id').cls.get(i.replace('yt_', '')))
post = ch[ch.t >= FOUND]
print('\n채팅 다시보기 있는 %d편 중 발견 이후 채팅이 있는 방송: %d편, 채팅 %d건 / 전체 %d건, 슈퍼챗(paid) 발견 이후 %d건 / 전체 %d건' % (
    ch.item_id.nunique(), post.item_id.nunique(), len(post), len(ch), int((post.kind == 'superchat').sum()), int((ch.kind == 'superchat').sum())))
print('발견 이후 채팅 분류별 방송 수:', post.groupby('cls').item_id.nunique().to_dict(), '채팅 수:', post.groupby('cls').size().to_dict())
lastc = post.groupby('item_id').t.max()
print('발견 이후 채팅 마지막 시각 분포:', lastc.min().strftime('%H:%M'), '~', lastc.max().strftime('%H:%M'))
# 발견 후 업로드(일반 영상)
vid = Y[~Y.live & (Y.up >= FOUND)]
vtxt = vid.title.fillna('')
print('\n발견 이후 업로드 일반 영상(검색 노출·관련성 필터) %d편, 조회수 합 %d; 제목 키워드: 유서·메모 %d, CCTV %d, 극단적 선택·자살 %d' % (
    len(vid), vid.views.sum(), int(vtxt.str.contains('유서|메모').sum()), int(vtxt.str.contains('CCTV').sum()), int(vtxt.str.contains('극단적 선택|자살').sum())))
print('같은 기간 업로드 비교 — 발견 이전 6h 업로드: ', int(((Y.up >= FOUND - pd.Timedelta(hours=6)) & (Y.up < FOUND) & ~Y.live).sum()), '편')
print('이벤트 기록: 16:53 "추적 생방송 12개·253만 집계, REDACTED_HOST_A·백지연 출연 영상 내림" (웹 Claude, 날짜 확인 필요, 맥락 자료)')
ib = L[(L.status == 'is_live')]
print('수집 시점 방송 중(is_live) %d편: 개시 시각이 제목 갱신으로 부정확할 수 있음(24h 채널 재사용) → 개시 국면표에서 이들을 빼면:' % len(ib))
L2 = L[L.status != 'is_live']
print(L2.phase.value_counts().reindex(['의혹·고발 전', '고발', '검증·실종', '사망']).fillna(0).astype(int).to_dict())

# 플랫폼 그림: 11-19 간트
fig, a = plt.subplots(figsize=(14, 8))
g19 = L[(L.end > T('2026-11-19T05:00')) | (L.start >= T('2026-11-19T05:00'))].sort_values('start')
cc = {'방송·언론': '#7f8c8d', '개인·기타': '#e67e22', 'IDA(검증 주관)': '#2980b9'}
for i, r in enumerate(g19.itertuples()):
    e_ = r.end if pd.notna(r.end) else snap_end
    a.barh(i, (e_ - r.start).total_seconds() / 86400, left=matplotlib.dates.date2num(r.start), color=cc[r.cls], alpha=.85 if r.trk else .4, height=.7)
a.axvline(matplotlib.dates.date2num(FOUND), color='k', lw=2); a.text(matplotlib.dates.date2num(FOUND), len(g19), ' 발견', fontsize=9)
a.set_xlim(matplotlib.dates.date2num(T('2026-11-19T05:00')), matplotlib.dates.date2num(T('2026-11-19T19:00')))
a.xaxis_date(tz=KST); a.xaxis.set_major_formatter(matplotlib.dates.DateFormatter('%H:%M', tz=KST)); a.set_yticks([])
a.set_title('11-19 생방송 개시~추정 종료(release+duration; 방송 중이던 건 수집 시각까지) — 짙음=제목에 추적·검증·사건어')
a.legend(handles=[plt.Rectangle((0, 0), 1, 1, color=v, label=k) for k, v in cc.items()], loc='upper left')
plt.tight_layout(); plt.savefig(OUT + '_생방송.png', dpi=130); plt.close()

# ---------------------------------------------------------------- 군중 내용(코딩) 전후: 디시 표본, 단일 국면 안에서만 비교
print('\n\n===== 코딩 표본(디시) 발견 전후 stance — 탐색, 표본 층화 때문에 국면 내 비율만 =====')
import lab_codes as LC
for lab, env in (('sonnet 재코딩 덮어쓰기(기본)', None), ('민감도: haiku 원값만', '1')):
    if env:
        os.environ['LAB_NO_RECODE'] = env
    else:
        os.environ.pop('LAB_NO_RECODE', None)
    d = LC.load()
    d = d[d.platform == '디시']
    pre_ = d[(d.ts >= T('2026-11-19T07:30')) & (d.ts < FOUND)]
    post_ = d[(d.ts >= FOUND) & (d.ts < FOUND + pd.Timedelta(hours=6))]
    print(lab, 'n pre/post =', len(pre_), len(post_))
    for st in ['공격', '의심', '애도', '옹호', '중립', '무관']:
        p0, p1 = (pre_.stance == st).mean(), (post_.stance == st).mean()
        bs = [((rng.choice(post_.stance.values, len(post_)) == st).mean() - (rng.choice(pre_.stance.values, len(pre_)) == st).mean()) for _ in range(2000)]
        print(f'  {st}: 전 {p0:.2f} → 후 {p1:.2f}  차 {p1 - p0:+.2f} (95% CI {np.percentile(bs, 2.5):+.2f}~{np.percentile(bs, 97.5):+.2f})')
os.environ.pop('LAB_NO_RECODE', None)
print('\n[끝] 스크립트: scripts/analysis/rq4_safety.py')
