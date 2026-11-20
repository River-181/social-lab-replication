"""생방송 다시보기 채팅 보존(슈퍼챗 금액 포함). 스냅샷에서 was_live/live인 영상만.
usage: python3 yt_livechat.py data/raw/yt_snapshots.jsonl
출력: data/raw/livechat/<id>.live_chat.json (yt-dlp 원형, 이미 있으면 건너뜀)
"""
import sys, json, pathlib, time
import yt_dlp

out = pathlib.Path(__file__).resolve().parent.parent / "data/raw/livechat"
out.mkdir(parents=True, exist_ok=True)
lives = {d["id"] for d in map(json.loads, open(sys.argv[1]))
         if d.get("was_live") or d.get("live_status") in ("was_live", "post_live")}
opts = {"quiet": True, "no_warnings": True, "skip_download": True, "writesubtitles": True,
        "subtitleslangs": ["live_chat"], "outtmpl": str(out / "%(id)s"), "sleep_interval_requests": 3}
for vid in sorted(lives):
    if (out / f"{vid}.live_chat.json").exists():
        continue
    try:
        with yt_dlp.YoutubeDL(opts) as y:
            y.download([f"https://www.youtube.com/watch?v={vid}"])
    except Exception as e:
        print("FAIL", vid, str(e)[:120], file=sys.stderr)
        if "429" in str(e) or "봇" in str(e) or "bot" in str(e):
            sys.exit("rate-limited: stop, retry later")
    time.sleep(5)
print(len(lives), "live videos;", len(list(out.glob("*.json"))), "chats saved")
