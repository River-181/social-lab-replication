"""YouTube 댓글 수집(답글 포함). 영상당 상한 N개(인기순).
usage: python3 yt_comments.py ids.txt out.jsonl [max=1000]
이미 받은 영상은 건너뛴다 → 중단 후 재실행해도 안전.
"""
import sys, json, datetime, time, pathlib
import yt_dlp

ids_path, out_path = sys.argv[1], pathlib.Path(sys.argv[2])
cap = sys.argv[3] if len(sys.argv) > 3 else "1000"
done = {json.loads(l)["video_id"] for l in open(out_path)} if out_path.exists() else set()
opts = {"quiet": True, "no_warnings": True, "skip_download": True, "getcomments": True,
        "sleep_interval_requests": 3,  # 병렬·무휴식은 429 차단됨(11-19)
        "extractor_args": {"youtube": {"max_comments": [cap, "all", "all", "50"], "comment_sort": ["top"]}}}

with open(out_path, "a") as out:
    for vid in (l.strip() for l in open(ids_path)):
        if not vid or vid in done:
            continue
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        try:
            with yt_dlp.YoutubeDL(opts) as y:
                info = y.extract_info(f"https://www.youtube.com/watch?v={vid}", download=False)
        except Exception as e:
            print("FAIL", vid, str(e)[:120], file=sys.stderr)
            if "429" in str(e) or "봇" in str(e) or "bot" in str(e):
                sys.exit("rate-limited: stop, retry later")  # 계속 두드리면 차단만 길어짐
            continue
        for c in info.get("comments") or []:
            keep = {k: c.get(k) for k in ("id", "parent", "author", "author_id", "text", "like_count", "timestamp")}
            out.write(json.dumps({**keep, "video_id": vid, "collected_at": now}, ensure_ascii=False) + "\n")
        out.flush()
        time.sleep(5)
