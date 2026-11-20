"""문서용 도식 2장: 방법론 흐름(docs/fig_method.png), 시스템 구조(docs/fig_system.png).
usage: python3 scripts/analysis/docs_figs.py   — 숫자는 확정 문서(METHODS·확증검정·provenance.json)에서 옮겼다.
"""
import json, pathlib, sys
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
sys.path.insert(0, str(pathlib.Path(__file__).parent))
from lab_style import use, annotate_scope, check, INK, TEXT, MUTED, ACCENT, GRID, PAPER

ROOT = pathlib.Path(__file__).resolve().parents[2]
OUT = ROOT / "docs"
PV = json.load(open(OUT / "provenance.json"))
use()
GATE = "#6E8B74"  # 품질 관문(세이지). 빨강 금지


def box(ax, x, y, w, h, title, lines=(), edge=TEXT, fill=PAPER, title_color=INK, size=10.5):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.008,rounding_size=0.012", fc=fill, ec=edge, lw=1.4))
    ax.text(x + 0.012, y + h - 0.022, title, ha="left", va="top", fontsize=size + 1, color=title_color, weight="bold")
    for i, l in enumerate(lines):
        ax.text(x + 0.012, y + h - 0.062 - i * 0.034, l, ha="left", va="top", fontsize=size - 1, color=TEXT)


def arrow(ax, a, b, color=MUTED, style="-|>", ls="-"):
    ax.add_patch(FancyArrowPatch(a, b, arrowstyle=style, mutation_scale=14, color=color, lw=1.4, linestyle=ls))


def canvas(title):
    fig, ax = plt.subplots(figsize=(15, 8.4))
    ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis("off")
    ax.set_title(title, loc="left")
    return fig, ax


# ── 1. 방법론 흐름 ─────────────────────────────────────
fig, ax = canvas("방법론 — 모으고, 재고, 미리 등록하고, 새 표본으로 확인한다")
ax.set_ylim(0.24, 1); fig.set_size_inches(15, 6.6)
W, H, Y = 0.152, 0.34, 0.56
stages = [
    ("① 수집", ["유튜브 영상 287", "생방송 채팅 129,476", "디시 전용갤 전수 1,212", "관련갤 키워드 11,104", "본문 6,935·댓글 18,910", "네이트판·기사 66(질적)"]),
    ("② 적재·감사", ["원자료 JSONL은 추가만", "→ SQLite 통째 재생성", "_coverage.md 결손 자동 계산", "MANIFEST SHA-256", "스냅샷 하루 3회(launchd)"]),
    ("③ 측정", ["코드북 v0.2.1(닫힌 값 목록)", "국면별 층화 무작위 표본", "Haiku 코더 4 병렬", "Sonnet skeptic 드리프트 검사", "unclear는 Sonnet 재코딩"]),
    ("④ 탐색 → 등록", ["RQ1~10 탐색(1,800건)", "결과 보기 전 PREREG", "H1~H4 11/19 22:53", "H5~H7 11/20 00:35", "탐색 결과는 '탐색' 표시"]),
    ("⑤ 확증", ["데이터 동결 11/20 14:35", "새 표본 디시 댓글 1,706", "부트스트랩·CA 검정·Holm", "민감도 S1~S4", "지지 H1·H3·H4 / 보류 H2·H6"]),
    ("⑥ 공개", ["보고서·포스터·요약", "집계 CSV로 확증 재현", "(비공개 결과와 diff 일치)", "대안 검정 alt_checks", "원자료는 비공개"]),
]
xs = [0.012 + i * (W + 0.013) for i in range(6)]
for x, (t, ls) in zip(xs, stages):
    box(ax, x, Y, W, H, t, ls, edge=ACCENT if t.startswith("⑤") else TEXT)
for x in xs[:-1]:
    arrow(ax, (x + W, Y + H / 2), (x + W + 0.013, Y + H / 2))
gates = [
    "직렬 수집·쪽 상한\n(유튜브 429 교훈)", "테스트 → ingest\n자료 등급 A/B/C/질적", "κ 0.68(코더 간)\nκ 0.52(독립 검증)",
    "등록 = 커밋 시각\n바꾸면 탐색으로 강등", "다른 통계로 재확인\n(Fisher·차분·층)", "실명·개인 채널 가림\n공개 전 diff 대조"]
for x, g in zip(xs, gates):
    ax.add_patch(FancyBboxPatch((x, 0.38), W, 0.11, boxstyle="round,pad=0.006,rounding_size=0.01", fc="#EEF2EE", ec=GATE, lw=1.1, ls="--"))
    ax.text(x + W / 2, 0.435, g, ha="center", va="center", fontsize=9.5, color=GATE)
    arrow(ax, (x + W / 2, Y), (x + W / 2, 0.49), color=GATE, style="-")
ax.text(0.012, 0.335, "점선 상자 = 품질 관문. 매 단계 skeptic(Sonnet)이 검토하고, PI가 핵심 수치를 다시 계산해 재현한다.", fontsize=10, color=GATE)
arrow(ax, (xs[4] + W / 2, Y + H + 0.01), (xs[3] + W / 2, Y + H + 0.01), color=MUTED, style="-|>", ls=":")
ax.text((xs[3] + xs[4] + W) / 2, Y + H + 0.03, "확증 실패(H2)는 '탐색'으로 남기고 다시 등록", ha="center", fontsize=9.5, color=MUTED)
ax.text(0.012, 0.275, "외부 기준: 구글 트렌드와 시간당 순위상관 ρ=0.69(정점 11/19 13시 일치)   ·   서지 30/30 실재 확인(OpenAlex)   ·   주장 범위: 공개 온라인 담론, 여론 전체 아님",
        fontsize=10, color=TEXT)
annotate_scope(fig, "범위: 2026-11 리트냥이 사태, 공개적으로 보이던 유튜브·디시·네이트판 담론. 인과와 고인의 유무죄는 다루지 않는다.",
               status="방법", limits="사람 기준 코딩 없음, 단일 사례, 사망 후 관측창 하루(H5·H7 잠정).", source="METHODS.md · PREREG.md · VALIDITY.md")
check(fig)
fig.savefig(OUT / "fig_method.png", dpi=160, bbox_inches="tight")

# ── 2. 시스템 구조 ─────────────────────────────────────
fig, ax = canvas("시스템 구조 — 사람 1명, AI 연구실 1개, 자동화와 저장소")
sub = PV["subagents"]["by_role"]
role_line = lambda rs: " · ".join(f"{r} {sub[r]['runs']}" for r in rs if r in sub)
box(ax, 0.38, 0.84, 0.24, 0.12, "River (사람)", ["질문·범위·윤리 결정, 공유 판단"], edge=INK)
box(ax, 0.30, 0.58, 0.40, 0.20, "PI — Claude Code · Opus 5.5", [
    f"조율·수치 재현·문서화 (응답 {PV['pi']['responses']}회)", f"도구 Bash {PV['pi']['tool_calls'].get('Bash', 0)} · Chrome {PV['pi']['tool_calls'].get('claude-in-chrome', 0)} · Agent {PV['pi']['tool_calls'].get('Agent', 0)}",
    "플랜 모드 · 백그라운드 서브에이전트"], edge=ACCENT, title_color=ACCENT)
box(ax, 0.02, 0.30, 0.30, 0.20, "연구원 — Haiku 5.5", [role_line(["coder"]), "층화 표본 코딩(배치 병렬)"], edge="#8A96A3")
box(ax, 0.35, 0.30, 0.30, 0.20, "연구원 — Sonnet 5.5", [role_line(["analyst", "skeptic", "recoder"]), role_line(["designer", "forecaster"])], edge=ACCENT)
box(ax, 0.68, 0.30, 0.30, 0.20, "연구원 — Opus 5.5", [role_line(["modeler", "lens", "researcher"]), "모형·종합·1차 출처 조사"], edge=INK)
box(ax, 0.74, 0.62, 0.24, 0.30, "외부 AI (웹)", ["claude.ai: 기사 66·서지 30", "  매일 20:46 사후 기사", "Grok: X 발언 교차조사", "Gemini 딥리서치: 3회 실패", "Feynman CLI: 문헌"], edge=MUTED)
box(ax, 0.02, 0.62, 0.24, 0.30, "자동화·하네스", ["launchd 스냅샷 9·15·21시", "tmux `lab` 장시간 수집", "yt-dlp(직렬)·디시 크롤러", "Zotero·OpenAlex 서지", f"동시 실행 최대 {PV['subagents']['peak_concurrency']}"], edge=MUTED)
box(ax, 0.02, 0.04, 0.96, 0.18, "자료 흐름", [
    "원자료 JSONL(추가만, SHA-256)  →  SQLite DB(통째 재생성)  →  동결 DB(14:35)  →  findings/ 문서·그림  →  포스터·요약",
    "비공개 저장소 social-lab(원문 포함)  → 집계 CSV·가린 코드 →  공개 저장소 social-lab-replication(재현·검증)"], edge=TEXT)
arrow(ax, (0.5, 0.84), (0.5, 0.78), color=INK)
for x in (0.17, 0.50, 0.83):
    arrow(ax, (0.5, 0.58), (x, 0.50), color=ACCENT)
arrow(ax, (0.70, 0.70), (0.74, 0.74), color=MUTED, style="<|-|>", ls=":")
arrow(ax, (0.26, 0.74), (0.30, 0.70), color=MUTED, style="<|-|>", ls=":")
for x in (0.17, 0.50, 0.83):
    arrow(ax, (x, 0.30), (x, 0.22), color=MUTED)
annotate_scope(fig, "범위: 이 연구의 실제 구성(2026-11-19~20). 숫자는 docs/provenance.json에서 읽는다.",
               status="기록", limits="웹 AI의 토큰·내부 동작은 계측 불가.", source="scripts/analysis/docs_figs.py")
check(fig)
fig.savefig(OUT / "fig_system.png", dpi=160, bbox_inches="tight")
print("ok")
