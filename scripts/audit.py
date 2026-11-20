"""수집 범위 감사 → findings/_coverage.md + data/MANIFEST.sha256 (둘 다 파생물, 매번 덮어씀).
사람이 쓴 방법 설명(METHODS.md)이 아니라 원자료가 스스로 보여주는 범위·결손을 기록한다. 스냅샷마다 실행.
usage: python3 scripts/audit.py
"""
import json, sqlite3, hashlib, pathlib, collections, datetime

ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW, DB = ROOT / "data/raw", ROOT / "data/lab.db"


def jl(name):
    p = RAW / name
    return [json.loads(l) for l in open(p) if l.strip()] if p.exists() else []


def manifest():
    lines = []
    for p in sorted(RAW.rglob("*")):
        if p.is_file() and p.name != ".DS_Store":
            lines.append(f"{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.relative_to(ROOT)}")
    (ROOT / "data/MANIFEST.sha256").write_text("\n".join(lines) + "\n")
    return len(lines)


def span(xs):
    xs = sorted(x for x in xs if x)
    return f"{xs[0][:16]} ~ {xs[-1][:16]}" if xs else "-"


def main():
    out, w = [], lambda s="": out.append(s)
    now = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9))).isoformat()[:16]
    w(f"# 수집 범위 감사 (자동 생성 {now} KST — `scripts/audit.py`, 손으로 고치지 말 것)\n")
    w("원자료에서 직접 계산한 범위와 결손. 주장의 범위는 여기 적힌 것을 넘을 수 없다.\n")

    # 유튜브
    snaps = jl("yt_snapshots.jsonl")
    latest = {}
    for s in snaps:
        latest[s["id"]] = s
    by_status = collections.Counter(s.get("status") for s in latest.values())
    rounds = sorted({s["collected_at"][:13] for s in snaps})
    hits = jl("search_hits.jsonl")
    lives = [s for s in latest.values() if s.get("was_live") or s.get("live_status") in ("is_live", "was_live", "post_live")]  # ingest와 같은 정의
    chat_dir = RAW / "livechat"
    chats = {p.name.split(".")[0] for p in chat_dir.glob("*.live_chat.json")} if chat_dir.exists() else set()
    cm = collections.Counter(c["video_id"] for c in jl("yt_comments.jsonl"))
    capped = sum(1 for v, n in cm.items() if n >= 1000)
    under = sum(1 for v, n in cm.items() if latest.get(v, {}).get("comment_count") and n < 0.5 * latest[v]["comment_count"])
    w("## 유튜브")
    w(f"- 표집 틀: 유튜브 검색(관련도·최신 각 상위 50) — 검색어 {len({h['q'] for h in hits})}개. 모집단 전체가 아니라 **검색 알고리즘이 노출한 영상**이다.")
    w(f"- 영상 {len(latest)}편, 상태 {dict(by_status)}, 메타 스냅샷 회차 {len(rounds)} ({rounds[0] if rounds else '-'} ~ {rounds[-1] if rounds else '-'} UTC)")
    w(f"- 업로드 시각 범위: {span(str(s.get('upload_date')) for s in latest.values())}")
    w(f"- 생방송 {len(lives)}편(그중 수집 시점 방송 중 {sum(s.get('live_status') == 'is_live' for s in lives)}편 — 다시보기 생기면 다음 스냅샷에서 채팅 수집) 중 채팅 다시보기 확보 {len(chats & {s['id'] for s in lives})}편 ({len(lives) - len(chats & {s['id'] for s in lives})}편 결손: 다시보기 비활성·삭제)")
    w(f"- 댓글: 영상 {len(cm)}편 / {sum(cm.values())}개. 인기순 상한 1000 도달 {capped}편, 공개 댓글 수의 절반 미만만 받은 영상 {under}편 → **인기 댓글 편향**")
    w()

    # 디시
    srch, gall = jl("dc_search.jsonl"), jl("dc_search_gall.jsonl")
    w("## 디시인사이드")
    w(f"- 통합검색(최신순, 120쪽 상한): {len(srch)}건, 게시 시각 {span(r['published_at'] for r in srch)} — 상한 때문에 **최근 수 시간치만** 덮는다")
    g = collections.defaultdict(list)
    for r in gall:
        g[(r["gall_id"], r["keyword"])].append(r["published_at"])
    w(f"- 갤러리 단위: {len(gall)}건")
    w("\n| 갤러리 | 방식/키워드 | 건수 | 게시 시각 범위 |\n|---|---|---|---|")
    for (gid, kw), ts in sorted(g.items(), key=lambda x: -len(x[1])):
        w(f"| {gid} | {kw} | {len(ts)} | {span(ts)} |")
    posts = jl("dc_posts.jsonl")
    if posts:
        st = collections.Counter(p["status"] for p in posts)
        w(f"\n- 본문 수집: {len(posts)}건 {dict(st)} — deleted는 **수집 시점에 이미 삭제된 글**(생존 편향의 하한 추정치)")
    w()

    # 기타
    pann = jl("posts_pann.jsonl")
    w("## 네이트판")
    w(f"- 검색 목록 {len(pann)}건 중 연구 기간(2026-10-01~) {sum(p['published_at'] >= '2026-10-01' for p in pann)}건. 나머지는 동명이인 등 잡음(ingest에서 제외)")
    w()
    w("## 웹 Claude 수집분 (질적 보조 자료 — 수치 주장에 쓰지 않는다)")
    for p in sorted((RAW).glob("web_*/*.jsonl")):
        w(f"- {p.parent.name}/{p.name}: {sum(1 for l in open(p) if l.strip())}행")
    w()

    # 코딩
    if DB.exists():
        con = sqlite3.connect(DB)
        w("## 코딩")
        for coder, n in con.execute("select coder, count(*) from codes group by coder"):
            w(f"- {coder}: {n}")
        w("- 신뢰도 기록: findings/260119_RQ3_coding_review.md (사람 기준 코딩 없음 — 미결)")
    w()
    w(f"## 무결성\n- `data/MANIFEST.sha256`: 원자료 {manifest()}개 파일 SHA-256. git 이력과 함께 수집 후 변조가 없음을 보인다.")
    (ROOT / "findings/_coverage.md").write_text("\n".join(out) + "\n")


if __name__ == "__main__":
    main()
    print((ROOT / "findings/_coverage.md").read_text()[:1500])
