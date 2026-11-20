"""RQ2 증폭: (a) 채널 조회 집중도 (b) 생방송·슈퍼챗 (c) 댓글러·채팅러 집중.
실행: python3 scripts/analysis/rq2_amplify.py  (work/lab_260119.db 사본 사용)"""
import sys, os, re, math
sys.path.insert(0, os.path.dirname(__file__))
import pandas as pd, numpy as np, matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from common import conn, yt_items
plt.rcParams['font.family'] = 'AppleGothic'; plt.rcParams['axes.unicode_minus'] = False
OUT = '/Users/river/social-lab/findings/260119_RQ2_증폭.png'
pd.set_option('display.width', 220); pd.set_option('display.max_colwidth', 40)
c = conn()

def gini(x):
    x = np.sort(np.asarray(x, float)); n = len(x)
    return float((2 * np.arange(1, n + 1) - n - 1).dot(x) / (n * x.sum()))
def lorenz(x):
    x = np.sort(np.asarray(x, float)); return np.insert(np.cumsum(x) / x.sum(), 0, 0)
def topshare(x, k): x = np.sort(np.asarray(x, float))[::-1]; return float(x[:k].sum() / x.sum())

yt = yt_items(c)
print('유튜브 전체', len(yt), '관련 통과', int(yt.rel.sum())); yt = yt[yt.rel].copy()
print('제외 기준: 제목·설명·태그·채널명에 사건 키워드 없음 -> 제외(common.py REL)')

# ---- 방송사/개인 분류 규칙
BC = re.compile(r'YTN|JTBC|MBC|SBS|KBS|채널A|OBS|연합뉴스TV|뉴스1|CHOSUN|MBN|KNN|TJB|CBS|서울신문|매일신문|엠빅뉴스|VIDEOMUG|iMBC|시교라')
yt['type'] = np.where(yt.author.fillna('').str.contains(BC), '기성 방송·언론사', '개인·독립채널')

# ============ (a)
print('\n## (a) 채널 집중도 (조회수 = 수집 시점 1회 스냅샷)')
ch = yt.groupby('author').agg(n=('item_id', 'count'), views=('views', 'sum'), type=('type', 'first')).sort_values('views', ascending=False)
V = ch.views.values
print('채널', len(ch), '영상', len(yt), '총조회', int(V.sum()))
print('Gini(채널 누적조회)', round(gini(V), 3), '| Gini(영상 단위)', round(gini(yt.views.values), 3))
for k in (1, 5, 10): print(f'상위 {k} 채널 점유율', round(topshare(V, k) * 100, 1), '%')
k15 = math.ceil(len(ch) * .015); print(f'채널 상위 1.5%(={k15}개) 점유', round(topshare(V, k15) * 100, 1), '%')
exI = ch.drop('REDACTED_CHANNEL_C'); print('REDACTED_CHANNEL_C 제외 시: Gini', round(gini(exI.views.values), 3), ' 상위1/5/10',
      [round(topshare(exI.views.values, k) * 100, 1) for k in (1, 5, 10)])
print(ch.head(12).assign(share=lambda d: (d.views / V.sum() * 100).round(1)).to_string())
t = yt.groupby('type').agg(채널=('author', 'nunique'), 영상=('item_id', 'count'), 조회=('views', 'sum'), 중앙값=('views', 'median'))
t['점유%'] = (t.조회 / t.조회.sum() * 100).round(1); print(t.to_string())
for tp in t.index:
    v = ch[ch.type == tp].views.values; print(f'{tp} 내부 Gini', round(gini(v), 3), '상위1 점유(유형 내)', round(topshare(v, 1) * 100, 1), '%')
print('방송·언론사로 분류된 채널:', sorted(ch[ch.type == '기성 방송·언론사'].index))
print('개인·독립 상위 8:', list(ch[ch.type == '개인·독립채널'].head(8).index))
print('개인·기타 중 라이브 보유 채널 목록은 (b) 참고')

# ============ (b)
print('\n## (b) 생방송')
lv = yt[yt.source_type == 'youtube_live'].copy()
chat = pd.read_sql("select item_id,author_id,kind,paid from chats", c)
chat = chat[chat.item_id.isin(lv.item_id)]
def parse(p):
    if p is None: return (None, None)
    m = re.match(r'^₩\s*([\d,\.]+)$', p)
    if m: return ('KRW', float(m.group(1).replace(',', '')))
    m = re.match(r'^([^\d\s]+|[A-Z]{2,3})\s*([\d,\.]+)$', p)
    return (m.group(1), float(m.group(2).replace(',', ''))) if m else ('?', p)
sc = chat[chat.kind == 'superchat'].copy(); sc[['cur', 'amt']] = sc.paid.apply(lambda p: pd.Series(parse(p)))
print('채팅 행', len(chat), '(생방송', chat.item_id.nunique(), '편) kind:', chat.kind.value_counts().to_dict())
print('슈퍼챗', len(sc), '통화별:', sc.groupby('cur').agg(건=('amt', 'size'), 합=('amt', 'sum')).to_string().replace('\n', ' | '))
print('파싱 실패', int((sc.cur == '?').sum()))
PAT = re.compile('찾음|찾아|추적|현장검증|대치|잠수|잠적|수색')
lv['pat'] = lv.title.fillna('').map(lambda s: '추적·검증류' if PAT.search(s) else '그 외')
agg = chat.groupby('item_id').size().rename('chats')
sck = sc[sc.cur == 'KRW'].groupby('item_id').agg(sc_n=('amt', 'size'), krw=('amt', 'sum'))
sca = sc.groupby('item_id').size().rename('sc_all')
lv = lv.join(agg, on='item_id').join(sck, on='item_id').join(sca, on='item_id')
for col in ('chats', 'sc_n', 'krw', 'sc_all'): lv[col] = lv[col].fillna(0)
lv['has_chat'] = lv.chats > 0
print('생방송', len(lv), '/ 채팅 수집분', int(lv.has_chat.sum()))
print('추적·검증류 패턴 제목:'); print(lv[lv.pat == '추적·검증류'][['author', 'title', 'type', 'views', 'chats', 'sc_all', 'krw']].to_string(index=False))
cp = lv.groupby('author').agg(생방=('item_id', 'count'), 조회=('views', 'sum'), 채팅=('chats', 'sum'), 슈챗건=('sc_all', 'sum'), 원화=('krw', 'sum'), type=('type', 'first')).sort_values('조회', ascending=False)
print('\n채널별 생방송 (상위 15 + 슈퍼챗 보유 채널)'); print(pd.concat([cp.head(15), cp[(cp.슈챗건 > 0) & ~cp.index.isin(cp.head(15).index)]]).to_string())
def cmp(keys):
    g = lv.groupby(keys).agg(생방=('item_id', 'count'), 조회합=('views', 'sum'), 조회중앙=('views', 'median'), 채팅수집편=('has_chat', 'sum'),
                          채팅=('chats', 'sum'), 슈챗건=('sc_all', 'sum'), 원화=('krw', 'sum'))
    g['슈챗/천채팅'] = (g.슈챗건 / g.채팅.replace(0, np.nan) * 1000).round(2); return g
print('\n패턴별'); print(cmp('pat').to_string()); print('\n패턴 x 유형'); print(cmp(['pat', 'type']).to_string())
tot_sc = lv.krw.sum(); print('생방 조회 합', int(lv.views.sum()), '추적·검증류 조회 비중', round(lv[lv.pat=='추적·검증류'].views.sum()/lv.views.sum()*100,1), '% | 채팅 비중', round(lv[lv.pat=='추적·검증류'].chats.sum()/lv.chats.sum()*100,1), '%')
print('원화 슈퍼챗 합계', int(tot_sc), '/ 추적류 비중', round(lv[lv.pat == '추적·검증류'].krw.sum() / tot_sc * 100, 1), '%')
print('전체 슈퍼챗 건수 중 추적·검증류 비중:', round(lv[lv.pat == '추적·검증류'].sc_all.sum() / lv.sc_all.sum() * 100, 1), '%')
print('슈퍼챗 보낸 계정 수', sc.author_id.nunique(), ' 상위 3 금액 점유(KRW)', round(sc[sc.cur == 'KRW'].groupby('author_id').amt.sum().nlargest(3).sum() / tot_sc * 100, 1), '%')
print('통화 외:', sc[sc.cur != 'KRW'][['cur', 'amt', 'paid']].to_string(index=False))
print('슈퍼챗 보유 생방별:'); print(lv[lv.sc_all > 0][['author', 'pat', 'views', 'chats', 'sc_all', 'krw']].sort_values('krw', ascending=False).to_string(index=False))

# ============ (c)
print('\n## (c) 댓글러·채팅러 집중')
cm = pd.read_sql("select comment_id,item_id,parent_id,author_id from comments", c)
cm = cm[cm.item_id.isin(yt.item_id)]
def conc(df, label):
    n = df.groupby('author_id').size(); N = len(n); k = math.ceil(N * .015)
    top = n.sort_values(ascending=False)
    vids = df.groupby('author_id').item_id.nunique()
    r = dict(label=label, 행=len(df), 작성자=N, 영상수=df.item_id.nunique(), Gini=round(gini(n.values), 3), 상위1_5pct_인원=k,
             상위1_5pct_점유=round(top.iloc[:k].sum() / len(df) * 100, 1), 상위1pct점유=round(top.iloc[:math.ceil(N * .01)].sum() / len(df) * 100, 1),
             상위10pct점유=round(top.iloc[:math.ceil(N * .1)].sum() / len(df) * 100, 1), 최다1인=int(top.iloc[0]),
             s1=int((n == 1).sum()), s2=int((n == 2).sum()), s3_5=int(n.between(3, 5).sum()), s6=int((n >= 6).sum()),
             s1_점유=round((n == 1).sum() / len(df) * 100, 1), v2=int((vids >= 2).sum()), v3=int((vids >= 3).sum()), v5=int((vids >= 5).sum()), v10=int((vids >= 10).sum()))
    # 다작+다영상: 영상 3개 이상 또 댓글 5건 이상
    r['다작·다영상(영상>=3 & 5건+)'] = int(((vids >= 3) & (n >= 5)).sum())
    r['다영상 작성자의 댓글 점유%'] = round(n[vids >= 3].sum() / len(df) * 100, 1)
    return r, n
host = dict(zip(yt.item_id, yt.author_id))
cm['host'] = cm.item_id.map(host); chat['host'] = chat.item_id.map(host)
print('채널 주인(영상 업로더) 본인 행: 댓글', int((cm.author_id == cm.host).sum()), '채팅', int((chat.author_id == chat.host).sum()))
rows = []; ns = {}
for lab, df in [('댓글(전체 대댓글 포함)', cm), ('댓글(최상위만)', cm[cm.parent_id.isna()]), ('생방 채팅(전체 행)', chat[chat.author_id.notna()]),
                ('생방 채팅(text만)', chat[(chat.kind == 'text') & chat.author_id.notna()]),
                ('댓글(최상위, 주인 제외)', cm[cm.parent_id.isna() & (cm.author_id != cm.host)]), ('생방 채팅(text, 주인 제외)', chat[(chat.kind == 'text') & chat.author_id.notna() & (chat.author_id != chat.host)])]:
    r, n = conc(df, lab); rows.append(r); ns[lab] = n
print(pd.DataFrame(rows).set_index('label').T.to_string())
print('댓글 있는 영상', cm.item_id.nunique(), '/ 관련 영상 284 | 최상위', int(cm.parent_id.isna().sum()), '대댓글', int(cm.parent_id.notna().sum()))
print('영상당 최대 댓글 행', cm.groupby('item_id').size().max())
# 소수 작성자의 영상 간 이동: 댓글러가 방송·언론사 영상과 개인채널 영상 양쪽에 쓴 수
cmt = cm.merge(yt[['item_id', 'type']], on='item_id'); both = cmt.groupby('author_id').type.nunique()
print('댓글러 중 방송·언론+개인채널 양쪽에 쓴 수', int((both == 2).sum()), '/', len(both))
cht = chat.merge(yt[['item_id', 'type']], on='item_id'); cht = cht[cht.author_id.notna()]
print('채팅러 중 생방 2편+ 참여', int((cht.groupby('author_id').item_id.nunique() >= 2).sum()), '/', cht.author_id.nunique())
# 댓글러 ↔ 채팅러 겹침
ov = set(cm.author_id) & set(cht.author_id); print('댓글러∩채팅러', len(ov))

# ============ 그림
fig, axs = plt.subplots(2, 3, figsize=(19, 10.5))
ax = axs[0, 0]; top = ch.head(15)[::-1]
ax.barh(top.index, top.views / 1e6, color=['#d62728' if t == '개인·독립채널' else '#1f77b4' for t in top.type])
ax.set_title('(a) 채널 누적 조회 상위 15 (파랑=기성 방송·언론, 빨강=개인·독립)'); ax.set_xlabel('백만 회')
ax = axs[0, 1]
for lab, v, cc in [('채널 조회', V, 'k'), ('영상 조회', yt.views.values, 'gray')]:
    L = lorenz(v); ax.plot(np.linspace(0, 1, len(L)), L, label=f'{lab} Gini={gini(v):.2f}', color=cc)
ax.plot([0, 1], [0, 1], 'k:', lw=.5); ax.legend(); ax.set_title('(a) 로렌츠 곡선: 조회수')
ax = axs[0, 2]
g = lv.groupby('pat').agg(krw=('krw', 'sum'), n=('sc_all', 'sum'), live=('item_id', 'count'))
ax.bar(g.index, g.krw, color=['#d62728', '#999']); [ax.text(i, v, f'₩{int(v):,}\n{int(g.n.iloc[i])}건/{int(g.live.iloc[i])}편', ha='center', va='bottom') for i, v in enumerate(g.krw)]
ax.set_title('(b) 슈퍼챗 원화 합계: 추적·검증류 vs 그 외'); ax.set_ylim(0, g.krw.max() * 1.25)
ax = axs[1, 0]
for lab, cc in [('댓글(최상위만)', 'k'), ('생방 채팅(text만)', 'tab:orange')]:
    L = lorenz(ns[lab].values); r = [x for x in rows if x['label'] == lab][0]
    ax.plot(np.linspace(0, 1, len(L)), L, color=cc, label=f"{lab} Gini={r['Gini']}, 상위1.5% {r['상위1_5pct_점유']}%")
ax.plot([0, 1], [0, 1], 'k:', lw=.5); ax.axvline(.985, color='r', ls=':', lw=.8); ax.legend(fontsize=8); ax.set_title('(c) 작성자 로렌츠 (빨간선=상위 1.5% 경계)')
ax = axs[1, 1]
for lab, cc in [('댓글(최상위만)', 'k'), ('생방 채팅(text만)', 'tab:orange')]:
    d = ns[lab].value_counts().sort_index(); ax.loglog(d.index, d.values, 'o', ms=4, color=cc, label=lab)
ax.set_xlabel('작성자당 글 수'); ax.set_ylabel('작성자 수'); ax.legend(); ax.set_title('(c) 작성자당 글 수 분포 (log-log)')
ax = axs[1, 2]
s = lv[lv.has_chat].sort_values('views')
ax.scatter(s.views, s.sc_all, c=['#d62728' if p == '추적·검증류' else '#1f77b4' for p in s.pat], s=np.maximum(s.chats / 40, 8))
ax.set_xscale('log'); ax.set_xlabel('조회수'); ax.set_ylabel('슈퍼챗 건수'); ax.set_title('(b) 생방(채팅 수집분): 조회 vs 슈퍼챗 (빨강=추적·검증류, 크기=채팅수)')
plt.tight_layout(); plt.savefig(OUT, dpi=120); print('\nsaved', OUT)
