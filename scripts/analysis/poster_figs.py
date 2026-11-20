"""포스터용 그림 4장 (DESIGN v2). 수치 계산은 rq1·rq2·rq4·rq9·ext_benchmark의 로직을 그대로 가져오고, 그리는 부분만 새로 썼다.
실행: python3 scripts/analysis/poster_figs.py [1 2 3 4]   (인자 없으면 4장 모두. 동결 DB work/lab_final.db, 읽기 전용)
저장: findings/poster_fig1_확산.png, poster_fig2_증폭.png, poster_fig3_조기경보.png, poster_fig4_제도시계.png
스타일: lab_style.use('poster') — A0 기준 2.2배 글자. figsize 폭 19in — 포스터 2×2 칸(385mm≈15.2in)에 0.8배로 붙어 23pt가 ≈18pt로 인쇄된다(DESIGN 18pt 하한, 11-20 PI).
  paper로 그려 확대하면 선 굵기·점 크기도 같이 커져 거칠어지고 확대 배율마다 글자 크기가 달라진다. 그래서 poster로 그린다."""
import sys, os, re, json, math, sqlite3
sys.path.insert(0, os.path.dirname(__file__))
import numpy as np, pandas as pd, matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.lines import Line2D
import lab_style as ls
from lab_style import PHASE_COLORS, INK, TEXT, MUTED, GRID, NODATA, ACCENT, PAPER
import common, rq7_hawkes as r7
from rq9_earlywarning import online_cusum, hourly as hourly9, GONE, CONTACT, IDX as IDX9
from common import to_kst, yt_items, KST

ROOT = '/Users/river/social-lab'
FINAL = f'{ROOT}/work/lab_final.db'
FIND = f'{ROOT}/findings'
r7.DB = FINAL                       # rq7.load_dc가 읽는 DB를 동결본으로 바꾼다
OKABE_ORANGE = '#E69F00'            # DESIGN §3.2 (외부 기준 계열)
T = lambda s: pd.Timestamp(s, tz=KST)
HELP = '자살예방 상담전화 109, SNS상담 마들랜'   # 보도준칙 문구의 ☎ 기호는 lab_style.check의 이모지 검사에 걸려 뺐다

PHASES = [('세무냥이', '2026-10-28 00:00', '2026-11-15 12:00'), ('의혹', '2026-11-15 12:00', '2026-11-18 09:00'),
          ('고발', '2026-11-18 09:00', '2026-11-19 07:30'), ('검증', '2026-11-19 07:30', '2026-11-19 08:37'),
          ('실종', '2026-11-19 08:37', '2026-11-19 13:12'), ('사망', '2026-11-19 13:12', '2026-11-20 00:00')]
SCOPE = '2026-11 사태 중 공개된 디시 글(전용 갤러리 전수, 관련 갤러리는 키워드 검색)과 구글 검색. 여론 전체가 아니며 수집 전 삭제분은 알 수 없다.'


def setup():
    ls.use('poster')
    plt.rcParams['font.size'] = 23              # annotate_scope 글자(0.8배)가 18pt 이상이 되게
    plt.rcParams['axes.titlesize'] = 30
    plt.rcParams['axes.labelsize'] = 22
    plt.rcParams['xtick.labelsize'] = 20
    plt.rcParams['ytick.labelsize'] = 20
    plt.rcParams['lines.linewidth'] = 3.2


def spans(lo, hi):
    out = []
    for p, a, b in PHASES:
        a, b = max(T(a), lo), min(T(b), hi)
        if a < b:
            out.append((p, a, b))
    return out


def title(ax, text, bands_rows=2):
    """phase_bands 국면명이 위로 쌓이는 높이만큼 제목을 띄운다."""
    h_in = ax.get_figure().get_size_inches()[1] * ax.get_position().height
    ax.set_title(text, pad=(0.055 * bands_rows + 0.07) * h_in * 72 + 20)


def hatch(ax, a, b, label=None, rot=0, fs=19, y=0.5, x=None):
    ax.axvspan(a, b, facecolor='none', edgecolor=NODATA, hatch='///', lw=0, zorder=1)
    if label:
        ax.text(x if x is not None else a + (b - a) / 2, y, label, transform=ax.get_xaxis_transform(), ha='center', va='center', rotation=rot,
                fontsize=fs, color=TEXT, zorder=6, bbox=dict(fc=PAPER, ec='none', pad=4, alpha=.92))


def fmt_time(ax, step_h=24, fmt='%m/%d'):
    ax.xaxis.set_major_locator(mdates.HourLocator(byhour=range(0, 24, step_h), tz=KST))
    ax.xaxis.set_major_formatter(mdates.DateFormatter(fmt, tz=KST))


def save(fig, name):
    ls.check(fig)
    path = f'{FIND}/{name}'
    fig.savefig(path)
    plt.close(fig)
    print('saved', path)


def dc_hourly():
    """rq1·rq9와 같은 정의: 전용갤 fkgjwks, 관련갤 = 장기 수집 7갤 중 전용갤 아닌 것(통합검색 C 제외)."""
    dc = r7.load_dc()
    fk = dc[dc.gall == 'fkgjwks']
    rel = dc[dc.gall.isin(r7.DC_LONG) & (dc.gall != 'fkgjwks')]
    return dc, fk, rel


# ───────────────────────── 그림 1 ─────────────────────────
def fig1():
    _, fk, _ = dc_hourly()
    lo, hi = T('2026-11-14 00:00'), T('2026-11-20 00:00')
    idx = pd.date_range(lo, hi, freq='h', inclusive='left')
    t = pd.DataFrame([json.loads(l) for l in open(f'{ROOT}/data/raw/web_1120/search_interest.jsonl')])
    t = t[(t.source == 'google_trends') & t.source_url.str.contains('2026-11-13T15') & (t.keyword == '리트냥이')]   # ext_benchmark와 같은 창
    t['h'] = pd.to_datetime(t.ts).dt.tz_convert(KST).dt.floor('h')
    tr = t.groupby('h').value.mean().reindex(idx)
    tr_i = tr / tr.max() * 100
    open_t, end_t = T('2026-11-17 14:00'), T('2026-11-19 21:00')   # 전용갤 14:08 첫 글, 21:50 수집 끝(21시 칸은 부분)
    dcs = fk.ts.dt.floor('h').value_counts().reindex(idx, fill_value=0).sort_index()
    dcs = dcs.where((idx >= open_t) & (idx < end_t))                # 결손은 NaN(0이 아니다)
    dc_i = dcs / dcs.max() * 100

    fig, ax = plt.subplots(figsize=(19, 8.6))
    ax.set_xlim(lo, hi); ax.set_ylim(0, 108)
    ls.phase_bands(ax, spans(lo, hi))
    hatch(ax, lo, open_t, '디시 전용갤 개설 전(11/17 14:08) — 결손이며 0이 아님', y=0.62)
    hatch(ax, end_t, hi, '수집 종료 후(결손)', rot=90, fs=18)
    ax.step(idx, tr_i, where='post', color=OKABE_ORANGE, lw=3.4, zorder=4)
    ax.step(idx, dc_i, where='post', color=ACCENT, lw=3.4, zorder=5)
    ax.set_ylabel('시간당 양 (각 계열 최대 = 100)')
    fmt_time(ax)
    ax.tick_params(axis='x', length=8)
    ax.set_yticks([0, 25, 50, 75, 100])
    pk = tr_i.idxmax()
    ax.annotate('구글 검색 관심 (일반 대중, 외부 기준)\n정점 11/19 13시', (pk, 100), xytext=(T('2026-11-17 02:00'), 93), fontsize=21, color='#8A5A00',
                ha='left', va='center', arrowprops=dict(arrowstyle='-', color=MUTED, lw=1.5, shrinkB=4))
    ax.annotate('디시 전용 갤러리 (글/시간, 정점 237건)', (T('2026-11-19 10:00'), dc_i[T('2026-11-19 10:00')]), xytext=(T('2026-11-16 20:00'), 34), fontsize=21, color=ACCENT,
                ha='left', va='center', arrowprops=dict(arrowstyle='-', color=MUTED, lw=1.5, shrinkB=4))
    # 핵심 사건: 한 줄씩 높이를 달리해 왼쪽으로 뺀다
    for tt, txt, yy in ((T('2026-11-19 07:30'), '공개검증 생중계 시작 07:30', 74), (T('2026-11-19 08:37'), '검증 종료 선언·실종 08:37', 62), (T('2026-11-19 13:12'), '발견 13:12', 86)):
        ax.plot([tt, tt], [0, yy], color=MUTED, lw=1.4, zorder=3)
        ax.text(tt - pd.Timedelta(minutes=50), yy, txt, ha='right', va='center', fontsize=21, color=INK, zorder=7,
                bbox=dict(fc=PAPER, ec='none', pad=3, alpha=.9)) if tt < T('2026-11-19 13:00') else \
            ax.text(tt - pd.Timedelta(minutes=50), yy, txt, ha='right', va='center', fontsize=21, color=INK, zorder=7,
                    bbox=dict(fc=PAPER, ec='none', pad=3, alpha=.9))
    title(ax, '구글 검색과 디시 글은 11/19 아침 공개검증 생중계와 함께 한꺼번에 치솟았다')
    ls.annotate_scope(fig, f'{SCOPE} 구글 트렌드는 시간 단위 상대지수(키워드 4개 동시 비교 창)를 최대=100으로 다시 맞췄다.', grade='A/B', status='탐색',
                      limits='전용갤은 11/17 14:08 개설이라 그 전은 비교 불가. 두 계열은 척도가 달라 높이가 아니라 시점만 비교한다. 선후 관계가 인과를 뜻하지 않는다.',
                      source='scripts/analysis/poster_figs.py (rq1_curve·ext_benchmark 로직) · 도움: ' + HELP)
    save(fig, 'poster_fig1_확산.png')


# ───────────────────────── 그림 2 ─────────────────────────
def boot_top_share(counts, frac=0.015, n=2000, seed=260120):
    rng = np.random.default_rng(seed)
    c = np.asarray(counts, float)
    k = math.ceil(len(c) * frac)
    top = lambda x: np.sort(x)[::-1][:max(1, math.ceil(len(x) * frac))].sum() / x.sum()
    bs = [top(rng.choice(c, len(c), replace=True)) for _ in range(n)]
    return top(c), np.percentile(bs, 2.5), np.percentile(bs, 97.5), k, len(c)


def boot_group_share(df, val, n=2000, seed=260120):
    """생방송 편 단위로 재표집해 추적·검증류 점유의 95% 구간. df: 편당 1행(pat, val)."""
    rng = np.random.default_rng(seed)
    d = df[['pat', val]].to_numpy()
    f = lambda a: a[a[:, 0] == '추적·검증류', 1].astype(float).sum() / max(a[:, 1].astype(float).sum(), 1e-9)
    bs = [f(d[rng.integers(0, len(d), len(d))]) for _ in range(n)]
    return f(d), np.percentile(bs, 2.5), np.percentile(bs, 97.5)


def fig2():
    c = sqlite3.connect(FINAL)
    yt = yt_items(c); yt = yt[yt.rel].copy()
    lv = yt[yt.source_type == 'youtube_live'].copy()
    chat = pd.read_sql('select item_id,author_id,kind,paid from chats', c)
    chat_lv = chat[chat.item_id.isin(lv.item_id)]
    sc = chat_lv[chat_lv.kind == 'superchat'].copy()
    sc['krw'] = sc.paid.fillna('').str.extract(r'^₩\s*([\d,\.]+)$')[0].str.replace(',', '').astype(float)
    PAT = re.compile('찾음|찾아|추적|현장검증|대치|잠수|잠적|수색')
    lv['pat'] = lv.title.fillna('').map(lambda s: '추적·검증류' if PAT.search(s) else '그 외')
    lv = lv.join(chat_lv.groupby('item_id').size().rename('chats'), on='item_id').join(sc.groupby('item_id').krw.sum().rename('krw'), on='item_id')
    lv[['chats', 'krw']] = lv[['chats', 'krw']].fillna(0); lv['views'] = lv.views.fillna(0)
    n_tr, n_all = int((lv.pat == '추적·검증류').sum()), len(lv)
    n_chat_streams = int((lv.chats > 0).sum())
    # 좌: 작성자 상위 1.5%
    cm = pd.read_sql('select item_id,parent_id,author_id from comments', c)
    cm = cm[cm.item_id.isin(yt.item_id) & cm.parent_id.isna()]
    tx = chat[(chat.kind == 'text') & chat.author_id.notna() & chat.item_id.isin(lv.item_id)]
    L = [('생방송 채팅', *boot_top_share(tx.groupby('author_id').size().values)), ('영상 댓글(최상위)', *boot_top_share(cm.groupby('author_id').size().values))]
    # 우: 세 점유
    R = [('생방송 조회', *boot_group_share(lv, 'views')), ('채팅', *boot_group_share(lv[lv.chats > 0], 'chats')), ('슈퍼챗 금액(원화)', *boot_group_share(lv, 'krw'))]
    print('fig2 L', [(a, round(b, 3), round(lo_, 3), round(hi_, 3), k, n) for a, b, lo_, hi_, k, n in L])
    print('fig2 R', [(a, round(b, 3), round(lo_, 3), round(hi_, 3)) for a, b, lo_, hi_ in R], 'streams', n_tr, n_all, n_chat_streams)

    fig, (a1, a2) = plt.subplots(1, 2, figsize=(19, 7.6), gridspec_kw={'width_ratios': [1, 1.25], 'wspace': 0.52})
    # (a) 상위 1.5%
    for i, (nm, p, lo_, hi_, k, n) in enumerate(L):
        y = len(L) - 1 - i
        a1.errorbar(p * 100, y, xerr=[[(p - lo_) * 100], [(hi_ - p) * 100]], fmt='o', ms=20, color=ACCENT, ecolor=ACCENT, elinewidth=4, capsize=9, zorder=4)
        a1.text(p * 100, y + 0.27, f'{p * 100:.0f}%', ha='center', va='bottom', fontsize=24, color=INK, fontweight='semibold')
        a1.text(2.5, y - 0.3, f'작성자 {n:,}명 중 상위 {k}명', fontsize=19, color=MUTED, va='top')
    a1.axvline(1.5, color=INK, lw=2, ls=(0, (4, 3)))
    a1.annotate('모두 같은 양을 썼다면 1.5%', (1.5, 1.4), xytext=(4, 1.5), fontsize=19, color=TEXT, va='center', arrowprops=dict(arrowstyle='-', color=MUTED, lw=1.5))
    a1.set_yticks(range(len(L))); a1.set_yticklabels([x[0] for x in L][::-1])
    a1.set_xlim(0, 50); a1.set_ylim(-0.75, 1.9); a1.set_xlabel('상위 1.5% 작성자가 쓴 글의 비율 (%)')
    a1.grid(axis='x', color=GRID); a1.grid(axis='y', visible=False)
    a1.set_title('글은 소수 작성자가 썼다')
    # (b) 점유
    for i, (nm, p, lo_, hi_) in enumerate(R):
        y = len(R) - 1 - i
        a2.plot([lo_ * 100, hi_ * 100], [y + .12] * 2, color=ACCENT, lw=4, zorder=3)
        a2.plot(p * 100, y + .12, 'o', ms=20, color=ACCENT, zorder=4)
        a2.plot([(1 - hi_) * 100, (1 - lo_) * 100], [y - .12] * 2, color=MUTED, lw=4, zorder=3)
        a2.plot((1 - p) * 100, y - .12, 'o', ms=20, color=MUTED, zorder=4)
        a2.text(p * 100, y + .12 + .17, f'{p * 100:.0f}%', ha='center', va='bottom', fontsize=21, color=ACCENT, fontweight='semibold')
        a2.text((1 - p) * 100, y - .12 - .17, f'{(1 - p) * 100:.0f}%', ha='center', va='top', fontsize=21, color=TEXT)
    ref = n_tr / n_all * 100
    a2.axvline(ref, color=INK, lw=2, ls=(0, (4, 3)))
    a2.annotate(f'생방송 편수 비중 {ref:.0f}% ({n_tr}/{n_all}편)', (ref, 2.62), xytext=(ref + 5, 2.68), fontsize=19, color=TEXT, va='center', arrowprops=dict(arrowstyle='-', color=MUTED, lw=1.5))
    a2.text(R[0][3] * 100 + 2, 2.12, '추적·검증류', color=ACCENT, fontsize=21, ha='left', va='center')
    a2.text((1 - R[0][3]) * 100 - 2, 1.88, '그 외', color=TEXT, fontsize=21, ha='right', va='center')
    a2.set_yticks(range(len(R))); a2.set_yticklabels([x[0] for x in R][::-1])
    a2.set_xlim(0, 100); a2.set_ylim(-0.6, 2.85); a2.set_xlabel('점유 (%)')
    a2.grid(axis='x', color=GRID); a2.grid(axis='y', visible=False)
    a2.set_title('추적·검증류 생방송은 조회보다 채팅·후원에서 컸다')
    fig.suptitle('조회는 적어도, 채팅과 후원은 소수 작성자와 추적·검증류 방송에 몰렸다', x=0.06, ha='left', fontsize=32, fontweight='semibold', color=INK, y=1.04)
    ls.annotate_scope(fig, '2026-11 사태 중 수집한 유튜브 생방송 %d편(채팅 다시보기가 남은 %d편의 채팅 %s건)과 관련 영상 댓글. 점=관측값, 선=95%% 구간(작성자·방송 편을 다시 뽑는 부트스트랩).' %
                      (n_all, n_chat_streams, f'{len(chat_lv):,}'), grade='A', status='탐색',
                      limits=f'추적·검증류는 제목 키워드로 가른 {n_tr}편이라 구간이 넓다. 한 방송이 채팅의 상당 부분을 차지한다. 삭제된 방송은 빠졌다.',
                      source='scripts/analysis/poster_figs.py (rq2_amplify 로직) · 도움: ' + HELP)
    save(fig, 'poster_fig2_증폭.png')


# ───────────────────────── 그림 3 ─────────────────────────
def fig3():
    dc, fk, rel = dc_hourly()
    lg = dc[dc.gall.isin(r7.DC_LONG)]
    lo, hi = T('2026-11-15 00:00'), T('2026-11-19 13:00')
    idx = pd.date_range(lo, hi, freq='h', inclusive='left')
    open_t = T('2026-11-17 14:00')
    hs = lambda s: s.dt.floor('h').value_counts().reindex(idx, fill_value=0).sort_index()
    f_, r_ = hs(fk.ts), hs(rel.ts)
    f_ = f_.where(idx >= open_t)                               # 개설 전은 결손
    gone = hs(lg[lg.title.fillna('').str.contains(GONE)].ts)
    # 경보: rq9와 같은 온라인 CUSUM(과거 24h만, k=0.5, h=5). 계열은 전체 구간(IDX9)에서 계산한 뒤 창으로 자른다.
    ser7 = hourly9(lg.ts, IDX9).to_numpy().astype(float)
    serf = hourly9(fk.ts, IDX9).to_numpy().astype(float)
    al7 = [IDX9[i] for i in online_cusum(ser7, h=5.0)[0] if lo <= IDX9[i] < hi]
    alf = [IDX9[i] for i in online_cusum(serf, h=5.0)[0] if lo <= IDX9[i] < hi]
    print('fig3 alarms 7갤', [a.strftime('%d일%H') for a in al7], '전용갤', [a.strftime('%d일%H') for a in alf])
    ct = dc[dc.title.fillna('').str.contains(CONTACT) & (dc.ts >= lo) & (dc.ts < T('2026-11-19 07:30'))].sort_values('ts')
    print('fig3 연락두절 제목', [(t.strftime('%d일%H:%M'), g) for t, g in zip(ct.ts, ct.gall)])
    ct_t = [t for t in ct.ts if T('2026-11-18 20:00') <= t < T('2026-11-18 21:00')]

    fig, axs = plt.subplots(3, 1, figsize=(19, 12), sharex=True, gridspec_kw={'height_ratios': [3.2, 1.25, 1.35], 'hspace': 0.22})
    a, b, c_ = axs
    for ax in axs:
        ax.set_xlim(lo, hi)
    ls.phase_bands(a, spans(lo, hi))
    for ax in (b, c_):
        ls.phase_bands(ax, spans(lo, hi), label=False)
    hatch(a, lo, open_t, '전용갤 개설 전 — 결손이며 0이 아님', y=0.55, fs=20)
    a.step(idx, r_, where='post', color=OKABE_ORANGE, lw=3.4, zorder=4)
    a.step(idx, f_, where='post', color=ACCENT, lw=3.4, zorder=5)
    a.set_ylabel('글 수 (건/시간)')
    a.text(T('2026-11-15 04:00'), r_[idx == T('2026-11-15 10:00')].iloc[0] + 8, '관련 갤러리 6곳 (키워드 검색)', color='#8A5A00', fontsize=21, ha='left', va='bottom')
    a.text(T('2026-11-18 21:30'), f_.max() * 0.55, '디시 전용 갤러리', color=ACCENT, fontsize=21, ha='right', va='bottom') if False else None
    a.annotate('디시 전용 갤러리 (11/17 14:08 개설)', (T('2026-11-18 14:00'), f_[idx == T('2026-11-18 14:00')].iloc[0]), xytext=(T('2026-11-17 16:00'), 92), fontsize=21, color=ACCENT,
               ha='left', va='center', arrowprops=dict(arrowstyle='-', color=MUTED, lw=1.5, shrinkB=3))
    b.bar(idx, gone, width=1 / 24, align='edge', color=MUTED, zorder=3)
    b.set_ylabel('건/시간'); b.set_title('같은 때 올라온 "잠수·런·도망" 류 예측 글 (7개 갤러리 제목 키워드)', fontsize=22, pad=8, color=TEXT, fontweight='normal')
    b.set_ylim(0, max(gone.max() * 1.2, 5))
    # 신호 줄 — 같은 표기 규칙: ▼ = 신호 시각. 속이 찬 것은 기계 경보, 속이 빈 것은 기계는 울리지 않은 내용 신호
    c_.set_ylim(0, 3.5); c_.set_yticks([]); c_.grid(visible=False)
    c_.spines['left'].set_visible(False)
    for ts_, y in [(al7, 2.2), (alf, 1.1)]:
        c_.plot(ts_, [y] * len(ts_), 'v', ms=24, color=INK, zorder=5)
    c_.text(lo - pd.Timedelta(hours=1.2), 2.2, '7개 갤러리\n합계', ha='right', va='center', fontsize=19, color=TEXT)
    c_.text(lo - pd.Timedelta(hours=1.2), 1.1, '전용 갤러리', ha='right', va='center', fontsize=19, color=TEXT)
    ct0 = T('2026-11-18 20:45')
    c_.plot([ct0], [0.3], 'v', ms=24, mfc=PAPER, mec=INK, mew=3.5, zorder=5)
    c_.text(ct0 - pd.Timedelta(minutes=70), 0.3, '"연락두절" 제목 3건 (20:41~49, 서로 다른 갤러리) — 기계 경보 없음', ha='right', va='center', fontsize=19, color=INK)
    # 오경보·첫 경보 설명(직접 글)
    fa = [t for t in al7 if t.day == 15]
    if fa:
        c_.annotate('11/15 경보: 자수 보도로 글이 몰렸을 뿐 위험 신호 아님 (오경보)', (fa[len(fa) // 2], 2.2), xytext=(T('2026-11-15 05:00'), 3.05), fontsize=19, color=INK, ha='left', va='center',
                    arrowprops=dict(arrowstyle='-', color=MUTED, lw=1.5, shrinkB=6))
    pre = [t for t in alf + al7 if t >= T('2026-11-18 12:00')]
    if pre:
        first = min(pre)
        c_.annotate('11/18 저녁 경보 (실종 10~16시간 전)', (first, 1.1 if first in alf else 2.2), xytext=(T('2026-11-16 06:00'), 1.65), fontsize=19, color=INK, ha='left', va='center',
                    arrowprops=dict(arrowstyle='-', color=MUTED, lw=1.5, shrinkB=8))
    for ax, yy, txt in ((a, 0.9, '07:30 공개검증 시작'),):
        pass
    for ax in axs:
        ax.axvline(T('2026-11-19 07:30'), color=MUTED, lw=1.3, zorder=2)
        ax.axvline(T('2026-11-19 08:37'), color=MUTED, lw=1.3, zorder=2)
    fmt_time(c_, 12, '%m/%d %H시')
    for ax in (a, b):
        ax.tick_params(axis='x', labelbottom=False)
    c_.tick_params(axis='x', length=8)
    a.set_title('신호는 있었지만, 조롱 섞인 예측 속에 묻혔다', pad=(0.055 * 2 + 0.07) * 15 * 0.5 * 72 * 0.9 + 14)
    ls.annotate_scope(fig, f'{SCOPE.replace("과 구글 검색", "")} 경보는 매 시각 그 시점까지의 글(과거 24시간 평균·분산)만 써서 낸 온라인 CUSUM(h=5)이다.', grade='A/B', status='탐색',
                      limits='사례가 하나라 적중률·민감도는 추정할 수 없고 오경보만 센다. 키워드는 조잡한 대리지표이고, 같은 키워드 글이 다른 시각에도 있어 맥락 확인이 필요하다. 사후에 고쳐진 제목이 섞일 수 있다.',
                      source='scripts/analysis/poster_figs.py (rq9_earlywarning 로직) · 도움: ' + HELP)
    save(fig, 'poster_fig3_조기경보.png')


# ───────────────────────── 그림 4 ─────────────────────────
def fig4():
    _, fk, rel = dc_hourly()
    c = sqlite3.connect(FINAL)
    lo, hi = T('2026-11-14 00:00'), T('2026-11-20 00:00')
    idx = pd.date_range(lo, hi, freq='h', inclusive='left')
    open_t, end_t = T('2026-11-17 14:00'), T('2026-11-19 21:00')
    hs = lambda s: s.dt.floor('h').value_counts().reindex(idx, fill_value=0).sort_index()
    f_ = hs(fk.ts).where((idx >= open_t) & (idx < end_t))
    r_ = hs(rel.ts)
    # 제도 사건: events_web.jsonl의 kind(정부·경찰·기관)만. 시각 있는 것은 점, 날짜만 있는 것은 그날 전체를 덮는 띠(시각 미상)
    kind = {d['event']: d['kind'] for d in map(json.loads, open(f'{ROOT}/data/raw/web_1119/events_web.jsonl'))}
    ev = pd.read_sql('select ts,event from events', c)
    ev['kind'] = ev.event.map(kind)
    ev = ev[ev.kind.isin(['government', 'police', 'institution'])].copy()
    ev['t'] = ev.ts.map(lambda s: T(s)); ev['minute'] = ev.ts.str.len() > 10
    LANES = [('government', '정부·국회'), ('police', '경찰·수사'), ('institution', '기관')]

    fig, (a, b) = plt.subplots(2, 1, figsize=(19, 9.8), sharex=True, gridspec_kw={'height_ratios': [2.5, 1.6], 'hspace': 0.12})
    for ax in (a, b):
        ax.set_xlim(lo, hi)
    ls.phase_bands(a, spans(lo, hi))
    ls.phase_bands(b, spans(lo, hi), label=False)
    hatch(a, lo, open_t, '전용갤 개설 전\n결손이며 0이 아님', y=0.62, fs=20, x=lo + pd.Timedelta(hours=14))
    hatch(a, end_t, hi, '수집 종료 후', rot=90, fs=17)
    a.step(idx, r_, where='post', color=OKABE_ORANGE, lw=3.4, zorder=4)
    a.step(idx, f_, where='post', color=ACCENT, lw=3.4, zorder=5)
    a.set_ylabel('글 수 (건/시간)')
    a.annotate('디시 전용 갤러리', (T('2026-11-19 13:00'), f_.max() - 6), xytext=(T('2026-11-18 03:00'), 205), fontsize=22, color=ACCENT, ha='left', va='center',
               arrowprops=dict(arrowstyle='-', color=MUTED, lw=1.5, shrinkB=4))
    a.annotate('관련 갤러리 6곳 (키워드 검색)', (T('2026-11-15 10:00'), r_[idx == T('2026-11-15 10:00')].iloc[0]), xytext=(T('2026-11-14 04:00'), 95), fontsize=22, color='#8A5A00', ha='left', va='center',
               arrowprops=dict(arrowstyle='-', color=MUTED, lw=1.5, shrinkB=4))
    a.annotate('군중 급증: 생방송 개시 직후\n(전용갤 글의 91%가 11/19 08시 이후)', (T('2026-11-19 08:00'), 62), xytext=(T('2026-11-17 22:00'), 150), fontsize=21, color=INK, ha='left', va='center',
               arrowprops=dict(arrowstyle='-', color=MUTED, lw=1.5, shrinkB=4))
    # 제도 줄
    b.set_ylim(-0.6, len(LANES) - 0.4); b.set_yticks(range(len(LANES))); b.set_yticklabels([n for _, n in LANES][::-1]); b.grid(visible=False)
    for i, (k, nm) in enumerate(LANES):
        y = len(LANES) - 1 - i
        d = ev[ev.kind == k]
        for _, e in d[~d.minute].iterrows():
            b.barh(y, pd.Timedelta(days=1), left=e.t, height=0.14, color=MUTED, alpha=.55, align='center', zorder=3)
        dm = d[d.minute]
        b.plot(dm.t, [y] * len(dm), 'D', ms=17, color=INK, zorder=5)
    b.plot([], [])
    b.text(T('2026-11-14 02:00'), 2.62, '', fontsize=1)
    # 제도 쪽 직접 주석
    b.annotate('11/15 공단 사과·정부 회의 (시각 미상, 회색 띠)', (T('2026-11-15 12:00'), 2), xytext=(T('2026-11-14 03:00'), 2.4), fontsize=19, color=TEXT, ha='left', va='center',
               arrowprops=dict(arrowstyle='-', color=MUTED, lw=1.5, shrinkB=5))
    b.annotate('11/18 고발장 접수·수사 배당 (시각 미상)', (T('2026-11-18 12:00'), 1), xytext=(T('2026-11-14 12:00'), 0.5), fontsize=19, color=TEXT, ha='left', va='center',
               arrowprops=dict(arrowstyle='-', color=MUTED, lw=1.5, shrinkB=5))
    jp = ev[ev.event.str.contains('공소권 없음 종결 전망')]
    if len(jp):
        t0 = jp.t.iloc[0]
        b.annotate('14:12 "공소권 없음 종결 전망" 보도\n= 법 절차의 결말에 관한 첫 보도(사후)', (t0, 1), xytext=(T('2026-11-17 15:00'), 0.5), fontsize=19, color=INK, ha='left', va='center',
                   arrowprops=dict(arrowstyle='-', color=MUTED, lw=1.5, shrinkB=6))
    b.annotate('08:42 신변 우려 신고 — 첫 공식 접수는 군중 급증 뒤', (T('2026-11-19 08:42'), 1), xytext=(T('2026-11-17 02:00'), 1.5), fontsize=19, color=INK, ha='left', va='center',
               arrowprops=dict(arrowstyle='-', color=MUTED, lw=1.5, shrinkB=6))
    fmt_time(b)
    b.tick_params(axis='x', length=8); a.tick_params(axis='x', labelbottom=False)
    b.set_xlabel('◆ 시각이 보도된 사건      회색 띠 = 날짜만 알려진 사건(그날 전체)', labelpad=10, fontsize=19, loc='left')
    a.set_title('군중은 먼저 몰렸고, 법 절차의 판단은 사건이 끝난 뒤에 왔다', pad=(0.055 * 2 + 0.07) * 15 * 0.55 * 72 * 0.9 + 20)
    ls.annotate_scope(fig, f'{SCOPE.replace("과 구글 검색", "")} 제도 사건은 보도에 나온 정부·경찰·기관 조치만(언론·플랫폼 사건 제외, events_web 분류).', grade='A/B', status='탐색',
                      limits='선후만 본 것이며 인과가 아니다. 시각이 보도 기준이라 실제 행위 시각과 다를 수 있다. 판단이 없었다는 뜻이 아니라 공개 보도에 없었다는 뜻이다.',
                      source='scripts/analysis/poster_figs.py (rq4_safety 로직) · 도움: ' + HELP)
    save(fig, 'poster_fig4_제도시계.png')


if __name__ == '__main__':
    setup()
    which = sys.argv[1:] or ['1', '2', '3', '4']
    for k in which:
        {'1': fig1, '2': fig2, '3': fig3, '4': fig4}[k]()
        setup()
