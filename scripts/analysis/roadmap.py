"""연구실 로드맵 그림: poster/roadmap.json → findings/_roadmap.png (DESIGN.md 스타일).
usage: python3 scripts/analysis/roadmap.py
상태는 색만이 아니라 채움 방식으로도 구분한다(완료=먹색 채움, 진행=강조색 채움, 예정=테두리만, River 몫=빗금).
"""
import json, pathlib, datetime as dt
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.patches import Patch
import lab_style as S

ROOT = pathlib.Path(__file__).resolve().parents[2]
R = json.load(open(ROOT / "poster/roadmap.json"))
d = lambda s: dt.datetime.fromisoformat(s)
STYLE = {  # (facecolor, edgecolor, hatch, 범례 이름)
    "done": (S.TEXT, S.TEXT, None, "완료"),
    "doing": (S.ACCENT, S.ACCENT, None, "진행 중"),
    "next": ("none", S.ACCENT, None, "예정"),
    "river": ("none", S.INK, "////", "River 몫"),
}

S.use()
rows = [(t["name"], it) for t in R["tracks"] for it in t["items"]]
fig, ax = plt.subplots(figsize=(11, 0.32 * len(rows) + 2.2))
y, yticks, ylabels, groups = 0, [], [], []
for ti, t in enumerate(R["tracks"]):
    top = y
    for it in t["items"]:
        a, b = d(it["start"]), d(it["end"]) + dt.timedelta(days=1)  # 끝날 포함
        fc, ec, hatch, _ = STYLE[it["status"]]
        ax.barh(y, b - a, left=a, height=0.62, color=fc, edgecolor=ec, hatch=hatch, linewidth=1.0)
        yticks.append(y); ylabels.append(it["label"])
        y += 1
    groups.append((t["name"], top, y - 1))
    y += 0.6  # 트랙 사이 숨
ax.set_yticks(yticks, ylabels, fontsize=8.5)
ax.invert_yaxis()
for name, a, b in groups:  # 트랙 이름은 왼쪽 바깥, 굵게
    ax.text(-0.40, (a + b) / 2, name, transform=ax.get_yaxis_transform(), ha="right", va="center",
            fontsize=10, fontweight="semibold", color=S.INK)

today = d(R["today"])
ax.axvline(today, color=S.INK, lw=1.0)
ax.text(today, -0.9, " 오늘", ha="left", va="bottom", fontsize=8.5, color=S.INK)
for i, m in enumerate(R["milestones"]):
    x = d(m["date"]) + dt.timedelta(hours=12)
    ax.axvline(x, color=S.MUTED, lw=0.6, ls=(0, (2, 3)))
    right = x > d("2026-12-10")  # 오른쪽 끝 라벨은 왼쪽으로 펼쳐 잘림 방지
    ax.text(x, 1.01 + 0.03 * (i % 3), f"{m['date'][5:].replace('-', '/')} {m['label']} " if right else f" {m['date'][5:].replace('-', '/')} {m['label']}",
            transform=ax.get_xaxis_transform(), ha="right" if right else "left", va="bottom", fontsize=7.8, color=S.TEXT)

ax.xaxis.set_major_locator(mdates.WeekdayLocator(byweekday=mdates.MO))
ax.xaxis.set_minor_locator(mdates.DayLocator())
ax.xaxis.set_major_formatter(mdates.DateFormatter("%m/%d"))
ax.set_xlim(d("2026-11-18"), d("2026-12-22"))
ax.grid(axis="x", which="major", color=S.GRID, lw=0.6)
ax.grid(axis="y", visible=False)
ax.tick_params(axis="y", length=0)
ax.legend(handles=[Patch(facecolor=fc, edgecolor=ec, hatch=h, label=n) for fc, ec, h, n in STYLE.values()],
          loc="lower right", ncol=4, fontsize=8.5)
ax.set_title("연구실 로드맵 — 1차 보고 마감, 다음은 11/27 정식 검정·12/19 평가", pad=88)
S.annotate_scope(fig, "계획 날짜는 추정이며 수집 완료 시점에 따라 밀린다. 확증 분석은 PREREG.md에 등록된 가설만.",
                 status="계획", limits="River 사람 코딩·수집 완료 시점이 일정을 좌우한다.", source="poster/roadmap.json → scripts/analysis/roadmap.py")
out = ROOT / "findings/_roadmap.png"
S.check(fig)
fig.savefig(out)
assert out.stat().st_size > 10_000
print(out)
