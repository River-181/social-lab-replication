"""social-lab 그림 스타일 — DESIGN.md의 코드판.

쓰는 법:
    from lab_style import use, PHASE_COLORS, annotate_scope, phase_bands
    use()                      # rcParams 적용 (Pretendard, 회색 위계)
    ...
    annotate_scope(fig, '범위: 공개 온라인 담론(유튜브·디시·판), 11-19부터 수집. 여론 전체 아님.', grade='A/B')

자체 검사: python3 scripts/analysis/lab_style.py  → 국면색 CVD 거리표 출력 + assert
"""
import numpy as np
import re
import colorsys
import matplotlib as mpl
import matplotlib.pyplot as plt
import matplotlib.dates
from matplotlib import font_manager

# ── 색 ────────────────────────────────────────────────
INK = '#1F1F1F'        # 제목·핵심 숫자
TEXT = '#4A4A4A'       # 본문·축 레이블
MUTED = '#8A8A8A'      # 보조 주석·출처
GRID = '#E4E2DD'       # 격자(축 글자보다 옅게)
PAPER = '#FAF9F6'      # 바탕(따뜻한 미색, 순백 아님)
NODATA = '#C9C6BF'     # 결손·수집 전 구간(빗금과 함께)
ACCENT = '#2F5D8A'     # 단일 계열 강조 1색(국면과 무관한 그림에서만)

# 국면 7색. 사망은 경고색(빨강)이 아니라 먹색 — 애도·정지의 의미. DESIGN.md §3.1
PHASE_COLORS = {
    '세무냥이': '#A3AEBA',  # 슬레이트
    '의혹':     '#D9A441',  # 황토
    '고발':     '#B8693A',  # 번트 오렌지
    '검증':     '#8E4D7D',  # 자두(생중계 스펙터클)
    '실종':     '#4F5A99',  # 인디고
    '사망':     '#2B2B2B',  # 먹
    '사후':     '#6E8B74',  # 세이지
}
PHASE_ORDER = list(PHASE_COLORS)
BAND_ALPHA = 0.14          # 배경 띠는 옅게. 사망 국면은 phase_bands가 면을 칠하지 않고 경계선만 그림

# 자료 등급 표기(METHODS §1)
GRADE_LABEL = {'A': '자료 A', 'B': '자료 B', 'C': '자료 C(탐색)', 'Q': '질적 보조'}


def _font():
    names = {f.name for f in font_manager.fontManager.ttflist}
    for n in ('Pretendard', 'Apple SD Gothic Neo', 'AppleGothic'):
        if n in names:
            return n
    return 'sans-serif'


def use(context='paper'):
    """rcParams 적용. context='paper'(findings·볼트) | 'poster'(A0, 글자 2.2배)."""
    k = 2.2 if context == 'poster' else 1.0
    mpl.rcParams.update({
        'font.family': _font(),
        'axes.unicode_minus': False,
        'font.size': 10 * k,
        'axes.titlesize': 12 * k, 'axes.titleweight': 'semibold', 'axes.titlelocation': 'left',
        'axes.titlecolor': INK, 'axes.labelsize': 9.5 * k, 'axes.labelcolor': TEXT,
        'xtick.labelsize': 9 * k, 'ytick.labelsize': 9 * k,
        'xtick.color': TEXT, 'ytick.color': TEXT,
        'axes.edgecolor': MUTED, 'axes.linewidth': 0.6,
        'axes.spines.top': False, 'axes.spines.right': False,
        'axes.grid': True, 'axes.grid.axis': 'y', 'grid.color': GRID, 'grid.linewidth': 0.6,
        'axes.facecolor': PAPER, 'figure.facecolor': PAPER, 'savefig.facecolor': PAPER,
        'axes.prop_cycle': mpl.cycler(color=[ACCENT, '#B8693A', '#6E8B74', '#8E4D7D', MUTED]),
        'lines.linewidth': 1.6,
        'legend.frameon': False, 'legend.fontsize': 9 * k,
        'figure.dpi': 110, 'savefig.dpi': 200, 'savefig.bbox': 'tight',
    })


def annotate_scope(fig, text, grade=None, status='탐색', source=None, limits=None):
    """그림 아래 왼쪽에 범위 문장 + 자료 등급 + 탐색/확증 + 출처를 붙인다(주석이 본문이다).
    grade: 'A' | 'B' | 'C' | 'Q' 또는 'A/B' 같은 조합."""
    tags = [status]
    if grade:
        tags.append(' · '.join(GRADE_LABEL.get(g, g) for g in grade.split('/')))
    line = f"[{' | '.join(tags)}] {text}"
    if limits:  # v2: 한계 한 줄(DESIGN P3 ⑥)
        line += f"\n한계: {limits}"
    if source:
        line += f"\n재현: {source}"
    fig.text(0.01, -0.02, line, ha='left', va='top', fontsize=mpl.rcParams['font.size'] * 0.8,
             color=MUTED, wrap=True)


def phase_bands(ax, spans, label=True):
    """spans: [(phase, start, end), ...]. 국면 배경 띠 + 위쪽 작은 국면명.
    사망 국면은 채우지 않고(빈 띠) 양 끝 얇은 먹선만 — 붉은 경고 면적으로 소비하지 않는다.
    shortcut: x축이 날짜(datetime)라고 가정. 숫자 축이면 date2num 줄을 바꿀 것."""
    row = 0
    total = mpl.dates.date2num(spans[-1][2]) - mpl.dates.date2num(spans[0][1])
    for ph, a, b in spans:
        c = PHASE_COLORS[ph]
        if ph == '사망':
            for x in (a, b):
                ax.axvline(x, color=c, lw=0.8)
        else:
            ax.axvspan(a, b, color=c, alpha=BAND_ALPHA, lw=0)
        if label:
            # 좁은 국면(검증 67분 등)은 이름이 겹치므로 한 줄씩 위로 올린다
            row = row + 1 if (mpl.dates.date2num(b) - mpl.dates.date2num(a)) / total < 0.06 else 0
            ax.text(a, 1.0 + 0.055 * row, f' {ph}', transform=ax.get_xaxis_transform(), ha='left',
                    va='bottom', fontsize=mpl.rcParams['font.size'] * 0.8, color=c if ph != '사망' else INK)


# ── 색각이상 검사 (Machado et al. 2009, severity 1.0; ΔE = CIE76) ──────────────
_CVD = {
    'protan': [[0.152286, 1.052583, -0.204868], [0.114503, 0.786281, 0.099216], [-0.003882, -0.048116, 1.051998]],
    'deutan': [[0.367322, 0.860646, -0.227968], [0.280085, 0.672501, 0.047413], [-0.011820, 0.042940, 0.968881]],
    'tritan': [[1.255528, -0.076749, -0.178779], [-0.078411, 0.930809, 0.147602], [0.004733, 0.691367, 0.303900]],
}


def _lin(h):
    c = np.array([int(h[i:i + 2], 16) / 255 for i in (1, 3, 5)])
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def _lab(lin):
    xyz = np.array([[0.4124, 0.3576, 0.1805], [0.2126, 0.7152, 0.0722], [0.0193, 0.1192, 0.9505]]) @ np.clip(lin, 0, 1)
    xyz = xyz / np.array([0.95047, 1.0, 1.08883])
    f = np.where(xyz > 0.008856, np.cbrt(xyz), 7.787 * xyz + 16 / 116)
    return np.array([116 * f[1] - 16, 500 * (f[0] - f[1]), 200 * (f[1] - f[2])])


def cvd_min_distances(colors=PHASE_COLORS):
    """시각 유형별(정상·적색·녹색·청색맹) 국면색 쌍 중 최소 ΔE와 그 쌍."""
    out = {}
    names = list(colors)
    for kind in ['normal'] + list(_CVD):
        M = np.eye(3) if kind == 'normal' else np.array(_CVD[kind])
        labs = {n: _lab(M @ _lin(colors[n])) for n in names}
        best = min(((np.linalg.norm(labs[a] - labs[b]), a, b) for i, a in enumerate(names) for b in names[i + 1:]))
        out[kind] = best
    return out

# ── 금지 목록 자동 검사 (DESIGN.md §2 → 코드). AI 연구소들이 디자인 판단을 채점 기준·평가로 바꾸는 방식을 따른다(2026-11-20).
BANNED_CMAPS = {'jet', 'rainbow', 'hsv', 'gist_rainbow', 'turbo', 'nipy_spectral', 'YlOrRd', 'OrRd', 'Reds', 'RdYlGn', 'RdYlGn_r', 'autumn', 'hot'}
_EMOJI = re.compile('[\U0001F300-\U0001FAFF☀-➿\U0001F000-\U0001F2FF]')
_COUNTDOWN = re.compile(r'(사망|죽음)\s*까지\s*\d')


def _is_red(rgba):
    r, g, b = rgba[:3]
    h, s, v = colorsys.rgb_to_hsv(r, g, b)
    return (h < 0.04 or h > 0.96) and s > 0.45 and v > 0.35 and (len(rgba) < 4 or rgba[3] > 0.2)


def check(fig):
    """그림을 저장하기 전에 부른다. 금지 목록 위반을 모아 AssertionError로 막는다(사람 눈 검수를 대신하지 않는다).
    자동으로 보는 것: 빨강 마크(§2-2·P1), 금지 색표(§2-6), 범위 문장 유무(§2-8), 이중 y축(§2-9), 이모지(§2-10), 카운트다운 문구(§2-3), 사망 국면 면 채우기(P1)."""
    bad, texts = [], [t.get_text() for t in fig.texts]
    for ax in fig.axes:
        texts += [ax.get_title(loc) for loc in ('left', 'center', 'right')] + [ax.get_xlabel(), ax.get_ylabel()] + [t.get_text() for t in ax.texts]
        texts += [t.get_text() for t in ax.get_xticklabels() + ax.get_yticklabels()]
        for art in ax.patches + ax.lines + ax.collections:
            cols = []
            for getter in ('get_facecolor', 'get_edgecolor', 'get_color'):
                try:
                    c = mpl.colors.to_rgba_array(getattr(art, getter)())
                    cols += [tuple(x) for x in c]
                except (AttributeError, ValueError, TypeError):
                    pass
            if any(_is_red(c) for c in cols):
                bad.append(f'빨강 마크: {type(art).__name__}')
            if isinstance(art, mpl.patches.Polygon) and art.get_fill() and \
                    mpl.colors.to_hex(art.get_facecolor()[:3]) == PHASE_COLORS['사망'].lower():
                bad.append('사망 국면을 면으로 칠함(선만 허용)')
        for im in ax.images:
            if im.get_cmap().name in BANNED_CMAPS:
                bad.append(f'금지 색표 {im.get_cmap().name}')
    pos = [tuple(round(v, 3) for v in ax.get_position().bounds) for ax in fig.axes]
    if len(pos) != len(set(pos)):
        bad.append('이중 축(같은 자리에 축 두 개)')
    if not any(t.lstrip().startswith('[') for t in (x.get_text() for x in fig.texts)):
        bad.append('범위 문장 없음(annotate_scope 미호출)')
    joined = '\n'.join(texts)
    if _EMOJI.search(joined.replace('☎', '')):  # ☎는 보도준칙 도움 정보 원문 기호라 허용
        bad.append('이모지')
    if _COUNTDOWN.search(joined):
        bad.append('카운트다운 문구')
    assert not bad, '디자인 검사 실패: ' + '; '.join(dict.fromkeys(bad))
    return True


if __name__ == '__main__':
    res = cvd_min_distances()
    for k, (d, a, b) in res.items():
        print(f'{k:7s} 최소 ΔE76 = {d:5.1f}  ({a} vs {b})')
    # 인접 국면이 시뮬레이션에서도 구별돼야 한다. 기준 ΔE76 ≥ 10 (작은 면적·선에서도 구분되는 하한, 보수적)
    assert all(d >= 10 for d, _, _ in res.values()), res
    print('ok')
    # check() 자체 검사: 나쁜 그림은 막고 좋은 그림은 통과
    use()
    f, a = plt.subplots(); a.plot([0, 1], [0, 1], color='#D62728'); a.set_title('사망까지 3시간')
    try:
        check(f); raise SystemExit('check()가 나쁜 그림을 통과시킴')
    except AssertionError as e:
        assert '빨강' in str(e) and '범위 문장' in str(e) and '카운트다운' in str(e), e
    g, b = plt.subplots(); b.plot([0, 1], [0, 1]); annotate_scope(g, '테스트')
    assert check(g)
    print('check ok')
