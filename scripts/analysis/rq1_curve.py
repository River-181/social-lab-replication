"""RQ1 확산곡선: 시간별(KST 1h) 유튜브 업로드·디시 글(전용갤 fkgjwks vs 그 외)·기사 수 + events.
실행: python3 scripts/analysis/rq1_curve.py  (work/lab_260119.db 사본 사용)"""
import sys, os, re, json
sys.path.insert(0, os.path.dirname(__file__))
import pandas as pd, numpy as np, matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from common import conn, to_kst, yt_items, KST
plt.rcParams['font.family'] = 'AppleGothic'; plt.rcParams['axes.unicode_minus'] = False
OUT = '/Users/river/social-lab/findings/260119_RQ1_확산곡선.png'
T = lambda s: pd.Timestamp(s, tz=KST)
c = conn()

yt = yt_items(c)
print('## 유튜브 전체', len(yt), '/ 관련 키워드 통과', int(yt.rel.sum()))
print('제외:', yt[~yt.rel][['item_id','author','title']].to_string(index=False))
yt = yt[yt.rel].copy()

it = pd.read_sql("select * from items where source_type in ('community_post','news')", c)
it['ts'] = to_kst(it.published_at)
it['x'] = it.extra.map(lambda s: json.loads(s) if s else {})
dc = it[it.item_id.str.startswith('dc_')].copy()
dc['gall'] = dc.x.map(lambda x: x.get('gall_id')); dc['gname'] = dc.x.map(lambda x: x.get('gall_name'))
print('\n## 디시', len(dc), '시각 있음', int(dc.ts.notna().sum()), '날짜만/없음', int(dc.ts.isna().sum()))
print(dc.groupby('gall').gname.first().loc[['fkgjwks']])
dc['grp'] = np.where(dc.gall == 'fkgjwks', '디시 전용갤(fkgjwks)', '디시 그 외 갤')
news = it[it.source_type == 'news'].copy()
print('기사', len(news), '시각 있음', int(news.ts.notna().sum()), '정밀도:', news.x.map(lambda x: x.get('ts_precision')).value_counts().to_dict())
web = it[(it.source_type == 'community_post') & ~it.item_id.str.startswith('dc_')]
print('웹수집 커뮤니티 글', len(web), '시각 있음', int(web.ts.notna().sum()))

# ---- 관련성: 디시 글은 제목에 사건 키워드가 있는 것만 별도 집계(전체도 병기)
KW = re.compile('냥이|리트|LEET|세무사|REDACTED_SUBJECT|만점|공개검증|AI ?안경')
dc['rel'] = dc.title.fillna('').map(lambda t: bool(KW.search(t)))
print('디시 제목 키워드 통과', int(dc.rel.sum()), '전용갤 전체 대비', int(dc[dc.gall=='fkgjwks'].rel.sum()), '/', int((dc.gall=='fkgjwks').sum()))

S, E = T('2026-11-11 00:00'), T('2026-11-20 00:00')
idx = pd.date_range(S, E, freq='h', inclusive='left')
def hourly(df):
    d = df[df.ts.notna() & (df.ts >= S) & (df.ts < E)]
    return d.ts.dt.floor('h').value_counts().reindex(idx, fill_value=0).sort_index()
series = {
 '유튜브 업로드': hourly(yt),
 '디시 전용갤': hourly(dc[dc.grp.str.startswith('디시 전용')]),
 '디시 그 외 갤': hourly(dc[~dc.grp.str.startswith('디시 전용')]),
 '기사': hourly(news),
}
tot = pd.DataFrame(series)
print('\n## 윈도 11/11~11/19 시각 있는 건수 합계'); print(tot.sum().to_string())
print('윈도 밖/시각없음:', {'유튜브': int((~yt.ts.between(S,E,inclusive='left')).sum()),
  '디시': int(len(dc) - tot[['디시 전용갤','디시 그 외 갤']].sum().sum()), '기사': int(len(news)-tot['기사'].sum())})
print('\n## 일별 합계'); print(tot.groupby(tot.index.date).sum().to_string())

# ---- onset (플랫폼별 첫 등장)
R = re.compile('리트|LEET|REDACTED_SUBJECT')   # 리트냥이 건 (세무냥이와 구분)
def txt(r): return f"{r.title or ''} {r.description or ''}" if 'description' in r else (r.title or '')
yt['r'] = yt.apply(lambda r: bool(R.search(txt(r))), axis=1)
yt['r'] = yt.r
dc['r'] = dc.title.fillna('').map(lambda t: bool(R.search(t)))
news['r'] = news.apply(lambda r: bool(R.search(f"{r.title or ''}")), axis=1)
print('\n## onset (KST)')
S0 = T('2026-11-11')
def onset(df):
    d = df[df.ts.notna()].sort_values('ts')
    d11 = d[d.ts >= S0]
    return dict(first_all=d.ts.iloc[0], first_1111=d11.ts.iloc[0], n5=d11.ts.iloc[4] if len(d11) > 4 else None,
                n20=d11.ts.iloc[19] if len(d11) > 19 else None, n=len(d11))
groups = {'유튜브': yt, '디시(전체)': dc, '디시(제목 키워드)': dc[dc.rel], '디시 전용갤': dc[dc.grp.str.startswith('디시 전용')], '기사(시각 정밀분)': news}
print('-- 전체 주제'); res = {}
for nm, df in groups.items():
    res[nm] = onset(df); print(nm, {k: str(v) for k, v in res[nm].items()})
print('-- 리트/REDACTED_SUBJECT 언급(제목[+유튜브 설명]) 건'); resr = {}
for nm, df in groups.items():
    resr[nm] = onset(df[df.r]); print(nm, {k: str(v) for k, v in resr[nm].items()})
for nm in ['유튜브', '기사(시각 정밀분)']:
    print(f'리트 첫 등장(11/11~) 차이 {nm} - 디시(제목 키워드): {resr[nm]["first_1111"]-resr["디시(제목 키워드)"]["first_1111"]}')
    print(f'리트 5건째 차이 {nm} - 디시(제목 키워드): {resr[nm]["n5"]-resr["디시(제목 키워드)"]["n5"]}')
print('11/11 이후 리트 첫 3건')
print(yt[yt.r].sort_values('ts')[['ts','author','title']].head(3).to_string(index=False))
print(dc[dc.r&(dc.ts>=S0)].sort_values('ts')[['ts','gall','title']].head(3).to_string(index=False))
print(news[news.r&news.ts.notna()].sort_values('ts')[['ts','title']].head(3).to_string(index=False))
print('11/11 이전 디시 리트 키워드 글:'); print(dc[dc.r&(dc.ts<S0)][['ts','gall','title']].to_string(index=False))
print('디시 11/11 이전 전체', int((dc.ts<S0).sum()))
print('디시 키워드(리트/REDACTED_SUBJECT) 11/14 00:00 이전(11/11~):', int((dc[dc.r].ts.between(S0, T('2026-11-14'))).sum()))
print('기사 날짜만/미정밀 포함 일별:'); print(news.assign(d=news.published_at.str[:10]).d.value_counts().sort_index().to_string())

# ---- 사망 발견 전후
D = T('2026-11-19 13:12')
print('\n## 사망 발견(13:12) 전후')
ends = {'유튜브': yt.ts.max(), '디시 전용갤': dc[dc.grp.str.startswith('디시 전용')].ts.max(),
        '디시 그 외 갤': dc[~dc.grp.str.startswith('디시 전용')].ts.max(), '기사': news.ts.max()}
dfs = {'유튜브': yt, '디시 전용갤': dc[dc.grp.str.startswith('디시 전용')], '디시 그 외 갤': dc[~dc.grp.str.startswith('디시 전용')], '기사': news}
# 하루 일반 속도: 11/15 00:00~11/18 23:59 평균 시간당
base = {}
for k, df in dfs.items():
    L = ends[k] - D
    post = int(((df.ts >= D) & (df.ts <= ends[k])).sum()); pre = int(((df.ts >= D - L) & (df.ts < D)).sum())
    h = L.total_seconds() / 3600
    b = int(((df.ts >= T('2026-11-15')) & (df.ts < T('2026-11-19'))).sum()) / 96
    print(f'{k}: 관측끝={ends[k]:%m-%d %H:%M} 창길이={h:.1f}h 직전={pre} 직후={post} 비(직후/직전)={post/max(pre,1):.2f} 직후 시간당={post/h:.1f} 11/15~18 시간당={b:.1f}')
# 검증 개시(07:30) 이후 ~ 발견 전 구간 (고발~검증)
print('\n## 11/19 시간대별')
print(tot.loc[T('2026-11-19 00:00'):].to_string())
print('피크 시각:', {k: (tot[k].idxmax(), int(tot[k].max())) for k in tot})

# ---- 그림
ev = pd.read_sql('select ts,phase,event from events', c)
ev['t'] = to_kst(ev.ts)
key = {'2026-11-15T09:00:15': '자수 영상 공개', '2026-11-18T10:55': '고발 보도', '2026-11-18T18:30': '귀가 안함',
       '2026-11-19T07:30': '검증 시작', '2026-11-19T08:37': '검증 종료', '2026-11-19T13:12': '발견'}
phases = [('세무냥이', '2026-10-28 00:00', '2026-11-15 12:00', '#eee'), ('의혹', '2026-11-15 12:00', '2026-11-18 09:00', '#fde9c8'),
          ('고발', '2026-11-18 09:00', '2026-11-19 07:30', '#f8c9c9'), ('검증', '2026-11-19 07:30', '2026-11-19 08:37', '#d9a0a0'),
          ('실종', '2026-11-19 08:37', '2026-11-19 13:12', '#c07070'), ('사망', '2026-11-19 13:12', '2026-11-20 00:00', '#777')]
fig, axs = plt.subplots(2, 1, figsize=(15, 10), gridspec_kw={'height_ratios': [3, 2]})
col = {'유튜브 업로드': '#d62728', '디시 전용갤': '#1f77b4', '디시 그 외 갤': '#9ecae1', '기사': '#2ca02c'}
for ax, (lo, hi, sym) in zip(axs, [(S, E, True), (T('2026-11-19 00:00'), E, False)]):
    for nm, a, b, cc in phases:
        ax.axvspan(max(T(a), lo), min(T(b), hi), color=cc, alpha=.45, lw=0) if T(b) > lo and T(a) < hi else None
    for k in tot:
        ax.step(tot.index, tot[k], where='post', color=col[k], label=k, lw=1.6)
    ax.axvline(T('2026-11-14'), color='k', ls=':', lw=1)
    for e in ev.itertuples():
        if pd.notna(e.t) and lo <= e.t < hi and len(e.ts) >= 16:
            ax.axvline(e.t, color='gray', lw=.4, alpha=.6)
            if e.ts[:16] in key:
                ax.axvline(e.t, color='k', lw=1)
                ax.annotate(key[e.ts[:16]], (e.t, 1), xycoords=('data', 'axes fraction'), rotation=90, va='top', ha='right', fontsize=9)
    ax.set_xlim(lo, hi)
    if sym: ax.set_yscale('symlog', linthresh=10); ax.set_ylim(0, 1500); ax.set_title('시간별(KST 1h) 게시량 — symlog축, 점선=커뮤니티·유튜브 의혹 onset 11/14 00:00, 배경=국면(codebook A)')
    else: ax.set_title('11/19 확대(선형축). 디시는 14시 이전 통합검색분 없음·갤러리별 수집 진행 중(부분 데이터)')
    ax.set_ylabel('건/시간'); ax.legend(loc='upper left', fontsize=9)
    ax.xaxis.set_major_formatter(matplotlib.dates.DateFormatter('%m/%d %H', tz=KST))
plt.tight_layout(); plt.savefig(OUT, dpi=130)
print('\nsaved', OUT)
