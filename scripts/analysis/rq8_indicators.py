"""RQ8 선행지표 계산. 실행: python3 scripts/analysis/rq8_indicators.py [DB경로]  (기본 work/lab_260120.db 사본, 읽기 전용)
출력: 표준출력 + findings/260120_RQ8_indicators.json. 매주 사본 DB만 바꿔 다시 돌린다. 고인의 유죄 여부는 다루지 않는다."""
import sys, os, re, json, sqlite3
import numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(__file__))
from common import to_kst

DB = sys.argv[1] if len(sys.argv) > 1 else '/Users/river/social-lab/work/lab_260120.db'
OUT = '/Users/river/social-lab/findings/260120_RQ8_indicators.json'
DEATH = pd.Timestamp('2026-11-19 13:12', tz='Asia/Seoul')
KNOWN = {'세무', '리트', '리트냥이', '세무냥이'}
THEMES = {  # 축별 키워드: 제목(유튜브·기사·디시) 기준 일별 점유율
    'A_수사종결': r'공소권|수사 ?종결|불송치|내사 ?종결',
    'B_입법': r'방지법|법안|개정안|입법|특별법|처벌 ?강화|사이버 ?렉카.*(?:법|규제)',
    'C_시험제도': r'전파탐지|금속탐지|반입|전수조사|감독관|물리적 검색|응시제한|합격 ?취소|국가시험',
    'D_책임공방': r'렉카|슈퍼챗|수익화|수익 ?정지|광고 ?정지|언론 ?책임|추적 ?방송|추적 ?라이브|주관사|공개검증',
}
c = sqlite3.connect(f'file:{DB}?mode=ro', uri=True)
R = {'db': DB}

# I1 영상 삭제·비공개율 (최신 스냅샷)
sn = pd.read_sql("select item_id,collected_at,status from snapshots", c)
last = sn.sort_values('collected_at').groupby('item_id').tail(1)
R['I1'] = dict(n_items=len(last), rounds=int(sn.collected_at.str[:13].nunique()), gone=int((last.status != 'live').sum()),
               gone_rate=float((last.status != 'live').mean()), last_round=sn.collected_at.max())

# I2 생방송·슈퍼챗 (수익화 신호)
ch = pd.read_sql("select ts,paid,item_id from chats", c); ch['t'] = to_kst(ch.ts)
def won(p):
    if p is None: return np.nan
    m = re.search(r'([₩$])\s*([\d,\.]+)', p)
    if not m: return np.nan
    v = float(m.group(2).replace(',', ''))
    return v if m.group(1) == '₩' else np.nan  # 외화는 합계에서 제외(건수만)
sc = ch[ch.paid.notna()].copy(); sc['krw'] = sc.paid.map(won)
lv = pd.read_sql("select item_id,published_at,title,author from items where source_type='youtube_live'", c); lv['t'] = to_kst(lv.published_at)
R['I2'] = dict(live_n=len(lv), live_after_death=int((lv.t >= DEATH).sum()), superchat_n=len(sc), superchat_krw=float(sc.krw.sum()),
               superchat_foreign_n=int(sc.krw.isna().sum()), superchat_after_death_n=int((sc.t >= DEATH).sum()),
               chat_last_ts=str(ch.t.max()), lives_by_day=lv.t.dt.strftime('%m-%d').value_counts().sort_index().to_dict())

# I3 전용갤(fkgjwks) 일별·시간별, 감쇠 반감기
g = pd.read_sql("select published_at from items where json_extract(extra,'$.gall_id')='fkgjwks'", c); g['t'] = to_kst(g.published_at)
daily = g.t.dt.strftime('%m-%d').value_counts().sort_index()
hr = g.t.dt.floor('h').value_counts().sort_index()
hr = hr.reindex(pd.date_range(hr.index.min(), hr.index.max(), freq='h'), fill_value=0)
pk = hr.idxmax(); post = hr[hr.index >= pk]
def half_life(h):
    """피크 이후 시간당 글수에 log-선형 적합(0은 +1 보정). 피크 이후 12시간 미만이면 None(미관측)."""
    if len(h) < 6: return None
    s = np.polyfit(np.arange(len(h)), np.log(h.values + 1), 1)[0]
    return float(np.log(2) / -s) if s < 0 else float('inf')
R['I3'] = dict(daily=daily.to_dict(), peak_hour=str(pk), peak_n=int(hr.max()), last_obs=str(hr.index.max()),
               hours_after_peak=len(post) - 1, last6h=int(hr.iloc[-6:].sum()), half_life_h=half_life(post), half_life_confirmed=len(post) >= 12)  # 12시간 미만이면 잠정

# I4 기사 수 (제목에 날짜만 있는 건 포함)
nw = pd.read_sql("select published_at,platform from items where source_type='news'", c)
nw['d'] = nw.published_at.fillna('').str[:10].replace('', 'unknown')
R['I4'] = dict(by_day=nw.d.value_counts().sort_index().to_dict(), n=len(nw), outlets=int(nw.platform.nunique()))

# I5 '냥이' 호칭 (제목·채팅·유튜브댓글)
RX = re.compile(r'([가-힣A-Za-z0-9]{1,6}?)냥이')
it = pd.read_sql("select title,published_at from items", c).rename(columns={'title': 'x', 'published_at': 'p'})
cm = pd.read_sql("select text x, published_at p from comments", c)
txt = pd.read_sql("select text x, ts p from chats", c)
rows = []
for name, df in [('title', it), ('ytcomment', cm), ('chat', txt)]:
    for x, p in zip(df.x.fillna(''), df.p):
        for m in RX.findall(x): rows.append((name, m + '냥이', p))
tk = pd.DataFrame(rows, columns=['src', 'tok', 'p'])
tk['tok'] = tk.tok.str.replace(r'^(이|가|은|는|의|와|과)(?=.{2,})', '', regex=True)
tk['tok'] = tk.tok.replace({'릿냥이': '리트냥이', '트냥이': '리트냥이'})
tk = tk[~tk.tok.isin({'승냥이'})]  # 승냥이=늑대류 일반어
tk['d'] = to_kst(tk.p.where(tk.p.str.len() >= 16)).dt.strftime('%m-%d')  # 날짜만 있는 값은 첫 등장 계산에서 제외
new = tk[~tk.tok.isin(KNOWN)]
first = new.dropna(subset=['d']).groupby('tok').d.min()
top = new.tok.value_counts()
dd = pd.concat([to_kst(it.p.where(it.p.fillna('').str.len() >= 16)), to_kst(txt.p)]).dt.strftime('%m-%d').value_counts().sort_index()
nb = first[top[top >= 3].index.intersection(first.index)].value_counts().sort_index()
R['I5'] = dict(docs_by_day=dd.to_dict(), new_per_1000_docs={k: round(v / dd[k] * 1000, 2) for k, v in nb.items() if k in dd.index},
               total_mentions=len(tk), known_share=float(1 - len(new) / max(len(tk), 1)), distinct_new=int(top.size),
               distinct_new_ge3=int((top >= 3).sum()), top_new=top.head(15).to_dict(), first_seen={k: first.get(k) for k in top.head(15).index}, new_tokens_first_seen_by_day=first[top[top >= 3].index.intersection(first.index)].value_counts().sort_index().to_dict())

# I6 주제 키워드 일별 점유율(유튜브·기사·디시 제목)
t = pd.read_sql("select title,published_at,source_type from items where published_at is not null and length(published_at)>=10", c)
t['d'] = t.published_at.str[:10]; t = t[t.d >= '2026-11-12']
R['I6'] = {}
for k, rx in THEMES.items():
    m = t.title.fillna('').str.contains(rx, regex=True)
    byd = t.assign(m=m).groupby('d').m.agg(['sum', 'mean'])
    R['I6'][k] = {d: [int(a), round(float(b), 4)] for d, (a, b) in byd.iterrows() if d >= '2026-11-17'}

# I7 사망 국면 비난 대상(코딩 표본, B등급·층화) — 제도·메타·주변인 점유
try:
    from lab_codes import load
    d = load(); s = d[(d.phase == '사망') & (d.target_of_blame != '없음')]
    sh = s.target_of_blame.replace({'세무냥이': '당사자', '리트냥이': '당사자'}).value_counts(normalize=True).round(3)
    R['I7'] = dict(n=len(s), share=sh.to_dict(), flag_R_share=float(s.f_R.mean()))
except Exception as e:
    R['I7'] = dict(error=str(e))

json.dump(R, open(OUT, 'w'), ensure_ascii=False, indent=1, default=str)
print(json.dumps(R, ensure_ascii=False, indent=1, default=str))
