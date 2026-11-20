"""YouTube 메타데이터 스냅샷. 같은 영상을 여러 번 찍어 collected_at별 확산 곡선을 만든다.
usage: python3 yt_meta.py ids.txt out.jsonl
"""
import sys, json, datetime
import yt_dlp

KEYS = ["id", "title", "channel", "channel_id", "channel_follower_count", "upload_date",
        "timestamp", "release_timestamp", "duration", "view_count", "like_count",
        "comment_count", "live_status", "was_live", "description", "tags", "availability"]
OPTS = {"quiet": True, "sleep_interval_requests": 3, "no_warnings": True, "skip_download": True,
        "extractor_args": {"youtube": {"lang": ["ko"]}}}


def fetch(vid):
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    try:
        with yt_dlp.YoutubeDL(OPTS) as y:
            d = y.extract_info(f"https://www.youtube.com/watch?v={vid}", download=False)
        return {**{k: d.get(k) for k in KEYS}, "status": "live", "collected_at": now}
    except Exception as e:  # 삭제·비공개 자체가 데이터
        msg = str(e)
        if "429" in msg or "봇" in msg or "bot" in msg:
            raise SystemExit("rate-limited: stop, retry later")  # 계속 두드리면 차단만 길어짐
        st = "private" if "rivate" in msg else "deleted" if ("unavailable" in msg or "removed" in msg) else "error"
        return {"id": vid, "status": st, "error": msg[:200], "collected_at": now}


if __name__ == "__main__":
    ids = [l.strip() for l in open(sys.argv[1]) if l.strip()]
    # 병렬 8개는 429·봇검사로 IP 차단됨(11-19) → 직렬 + 요청 간 휴식
    with open(sys.argv[2], "a") as out:
        for vid in ids:
            out.write(json.dumps(fetch(vid), ensure_ascii=False) + "\n")
            out.flush()
