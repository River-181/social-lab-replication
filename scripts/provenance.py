"""연구 생산 기록(provenance): 이 연구를 만든 AI 세션의 모델·토큰·동시성·도구를 집계한다.

usage: python3 scripts/provenance.py <세션.jsonl>   → docs/provenance.json, docs/fig_agent_timeline.png, stdout에 표
대화 내용·프롬프트는 읽기만 하고 내보내지 않는다. 숫자와 역할명만 남긴다.
"""
import json, glob, os, sys, re, subprocess, collections, pathlib, datetime as dt

ROOT = pathlib.Path(__file__).resolve().parents[1]
SESSION = pathlib.Path(sys.argv[1])
SUBDIR = SESSION.with_suffix("") / "subagents"
OUT = ROOT / "docs"
KST = dt.timezone(dt.timedelta(hours=9))

# API 정가(USD/MTok, claude-api 스킬 2026-11-03 캐시 기준). 참고 환산일 뿐 실제 청구액이 아니다(구독 사용).
# 캐시 쓰기는 5분 TTL(1.25×)로 가정. 1시간 TTL(2×)이면 쓰기 비용이 1.6배가 된다.
RATE = {"claude-opus-5-5": (4.00, 20.00, 0.20), "claude-sonnet-5-5": (2.00, 10.00, 0.10), "claude-haiku-5-5": (0.10, 0.50, 0.01)}  # Haiku 캐시 읽기는 문서에 명시 없음 → 일반 0.1× 가정
ROLE = [("Confirm coder", "coder"), ("Coder", "coder"), ("Recode", "recoder"), ("Skeptic", "skeptic"), ("Verify", "skeptic"),
        ("Analyst", "analyst"), ("Modeler", "modeler"), ("Lens", "lens"), ("Forecaster", "forecaster"),
        ("Designer", "designer"), ("Design research", "researcher"), ("Primary-source", "researcher")]
KEYS = ["input_tokens", "cache_creation_input_tokens", "cache_read_input_tokens", "output_tokens"]


def scan(path):
    """같은 message.id는 한 번만 센다(스트리밍으로 여러 줄에 나뉘어 기록됨)."""
    u, models, tools, seen, ts = collections.Counter(), collections.Counter(), collections.Counter(), set(), []
    for line in open(path):
        try:
            d = json.loads(line)
        except ValueError:
            continue
        if d.get("timestamp"):
            ts.append(d["timestamp"])
        m = d.get("message")
        if d.get("type") != "assistant" or not isinstance(m, dict) or m.get("model") == "<synthetic>":
            continue
        for c in m.get("content") or []:
            if isinstance(c, dict) and c.get("type") == "tool_use":
                n = c["name"]
                tools[n.split("__")[1] if n.startswith("mcp__") else n] += 1
        if m.get("id") in seen:
            continue
        seen.add(m.get("id"))
        models[m["model"]] += 1
        for k in KEYS:
            u[(m["model"], k)] += (m.get("usage") or {}).get(k, 0)
    t = sorted(ts)
    return u, models, tools, t[0], t[-1]


def cost(u):
    c = 0.0
    for (model, k), v in u.items():
        i, o, r = RATE[model]
        c += v / 1e6 * {"input_tokens": i, "cache_creation_input_tokens": i * 1.25, "cache_read_input_tokens": r, "output_tokens": o}[k]
    return c


def ver(cmd):
    try:
        return subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=20).stdout.strip().splitlines()[0]
    except Exception:
        return "?"


main_u, main_m, main_tools, t0, t1 = scan(SESSION)
agents = []
for meta in sorted(glob.glob(str(SUBDIR / "*.meta.json"))):
    mj = json.load(open(meta))
    u, m, tools, a, b = scan(meta.replace(".meta.json", ".jsonl"))
    role = next((r for p, r in ROLE if mj["description"].startswith(p)), "other")
    agents.append({"role": role, "task": mj["description"], "model": next(iter(m)), "start": a, "end": b,
                   "responses": sum(m.values()), "tokens": {k: sum(v for (_, kk), v in u.items() if kk == k) for k in KEYS},
                   "tool_calls": sum(tools.values()), "_u": u})
    assert len(m) == 1 and next(iter(m)).split("-")[1] == mj["model"], (meta, m, mj["model"])  # meta 모델 = 실제 응답 모델
assert len(agents) == 27, len(agents)

# 최대 동시 실행 수(서브에이전트 구간 겹침)
ev = sorted([(a["start"], 1) for a in agents] + [(a["end"], -1) for a in agents], key=lambda x: (x[0], x[1]))
cur = peak = 0
peak_at = None
for t, d in ev:
    cur += d
    if cur > peak:
        peak, peak_at = cur, t

allu = main_u + sum((a["_u"] for a in agents), collections.Counter())
by_model = {}
for (model, k), v in allu.items():
    by_model.setdefault(model, {kk: 0 for kk in KEYS})[k] += v
for a in agents:
    a.pop("_u")
roles = collections.defaultdict(lambda: {"runs": 0, "model": set(), "output_tokens": 0, "hours": 0.0})
for a in agents:
    r = roles[a["role"]]
    r["runs"] += 1; r["model"].add(a["model"]); r["output_tokens"] += a["tokens"]["output_tokens"]
    r["hours"] += (dt.datetime.fromisoformat(a["end"].replace("Z", "+00:00")) - dt.datetime.fromisoformat(a["start"].replace("Z", "+00:00"))).total_seconds() / 3600
k = lambda s: dt.datetime.fromisoformat(s.replace("Z", "+00:00")).astimezone(KST).strftime("%Y-%m-%d %H:%M")
P = {
    "note": "상한값: PI 세션에는 연구 외 요청(브리핑, 메시지 전송 등)이 일부 섞여 있다. 웹 claude.ai·Gemini·Grok·Feynman 토큰은 계측 불가로 제외.",
    "session_span_kst": [k(t0), k(t1)],
    "pi": {"model": dict(main_m), "responses": sum(main_m.values()), "tokens": {kk: sum(v for (_, x), v in main_u.items() if x == kk) for kk in KEYS},
           "tool_calls": dict(main_tools.most_common())},
    "subagents": {"runs": len(agents), "peak_concurrency": peak, "peak_at_kst": k(peak_at),
                  "by_role": {r: {**v, "model": sorted(v["model"]), "hours": round(v["hours"], 2)} for r, v in sorted(roles.items())},
                  "runs_detail": [{**a, "start": k(a["start"]), "end": k(a["end"])} for a in agents]},
    "by_model": by_model,
    "api_list_price_usd_estimate": round(cost(allu), 2),
    "software": {"claude_code": ver("claude --version"), "python": ver("python3 -V"),
                 "numpy/pandas/scipy": ver("python3 -c \"import numpy,pandas,scipy;print(numpy.__version__,pandas.__version__,scipy.__version__)\""),
                 "matplotlib": ver("python3 -c 'import matplotlib;print(matplotlib.__version__)'"), "yt-dlp": ver("yt-dlp --version"),
                 "sqlite": ver("sqlite3 --version").split()[0], "tmux": ver("tmux -V"), "feynman": ver("feynman --version"),
                 "poppler(pdftoppm)": ver("pdftoppm -v 2>&1"), "os": ver("sw_vers -productVersion")},
}
OUT.mkdir(exist_ok=True)
json.dump(P, open(OUT / "provenance.json", "w"), ensure_ascii=False, indent=1)

# 그림: 서브에이전트 실행 타임라인(역할 행, 모델 색)
sys.path.insert(0, str(ROOT / "scripts/analysis"))
from lab_style import use, annotate_scope, check, INK, MUTED, ACCENT  # noqa: E402
import matplotlib.pyplot as plt, matplotlib.dates as md  # noqa: E402
use()
MC = {"claude-haiku-5-5": "#A3AEBA", "claude-sonnet-5-5": ACCENT, "claude-opus-5-5": INK}
order = ["coder", "recoder", "skeptic", "analyst", "modeler", "lens", "forecaster", "designer", "researcher"]
# 실행이 몰린 세 창만 그린다. 사이의 빈 시간은 생략(실행 0개)
T = lambda d, h, m: dt.datetime(2026, 11, d, h, m, tzinfo=KST)
W = [(T(19, 22, 15), T(20, 1, 15)), (T(20, 8, 15), T(20, 8, 30)), (T(20, 14, 25), T(20, 14, 55))]  # 실행이 있던 세 창
fig, axes = plt.subplots(1, 3, figsize=(13, 5.6), sharey=True, gridspec_kw={"width_ratios": [3, 0.5, 1.3], "wspace": 0.05})
for ax, (w0, w1) in zip(axes, W):
    for a in agents:
        y = order.index(a["role"])
        s, e = (dt.datetime.fromisoformat(x.replace("Z", "+00:00")).astimezone(KST) for x in (a["start"], a["end"]))
        ax.barh(y, max(e - s, dt.timedelta(minutes=1)), left=s, height=0.62, color=MC[a["model"]], edgecolor="#FAF9F6", linewidth=1)
    ax.set_xlim(w0, w1)
    ax.xaxis.set_major_locator(md.MinuteLocator(byminute=[0, 30] if w1 - w0 > dt.timedelta(hours=1) else [15, 30, 45], tz=KST))
    ax.xaxis.set_major_formatter(md.DateFormatter("%H:%M", tz=KST))
    ax.set_xlabel(w0.strftime("%m/%d"), color=MUTED)
starts = [dt.datetime.fromisoformat(a["start"].replace("Z", "+00:00")) for a in agents]
assert all(any(w0 <= t <= w1 for w0, w1 in W) for t in starts), "창 밖 실행"
for ax in axes[1:]:
    ax.spines["left"].set_visible(False); ax.tick_params(left=False)
axes[0].set_yticks(range(len(order)), [f"{r} ({roles[r]['runs']})" for r in order])
axes[0].invert_yaxis()
axes[0].set_title(f"연구원 에이전트 27회 실행 — 동시에 최대 {peak}개", loc="left")
for i, (mname, lab) in enumerate([("claude-opus-5-5", "Opus 5.5 (모형·종합·조사)"), ("claude-sonnet-5-5", "Sonnet 5.5 (분석·검증·디자인)"), ("claude-haiku-5-5", "Haiku 5.5 (코딩)")]):
    fig.text(0.90 - i * 0.2, 0.955, "■ " + lab, ha="right", color=MC[mname] if mname != "claude-haiku-5-5" else "#6F7A86", fontsize=10)
annotate_scope(fig, "범위: 맥 Claude Code PI 세션의 서브에이전트만(웹 claude.ai·Gemini·Grok 제외). 막대 = 첫~마지막 기록 시각.",
               status="기록", limits="대기 시간 포함, 실제 연산 시간보다 길다.", source="scripts/provenance.py")
check(fig)
fig.savefig(OUT / "fig_agent_timeline.png", dpi=160, bbox_inches="tight")

# 표(stdout)
M = lambda n: f"{n/1e6:.2f}M"
print(f"세션 {P['session_span_kst'][0]} ~ {P['session_span_kst'][1]} KST | 최대 동시 {peak} ({P['subagents']['peak_at_kst']}) | API 정가 환산 ${P['api_list_price_usd_estimate']}")
print("| 모델 | 입력 | 캐시 쓰기 | 캐시 읽기 | 출력 |")
for model, t in sorted(by_model.items()):
    print(f"| {model} | {M(t['input_tokens'])} | {M(t['cache_creation_input_tokens'])} | {M(t['cache_read_input_tokens'])} | {M(t['output_tokens'])} |")
for r, v in P["subagents"]["by_role"].items():
    print(r, v)
print("PI 도구", P["pi"]["tool_calls"])
