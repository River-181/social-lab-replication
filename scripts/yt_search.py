"""유튜브 검색(관련도·최신 각 50) → hits jsonl 추가 + 새 id를 ids 파일 끝에 붙임. 직렬, 차단되면 멈춤.
usage: python3 yt_search.py hits.jsonl ids.txt 검색어1 검색어2 ...   (검색어 자리에 @파일 = 한 줄 한 검색어 또는 jsonl의 query)
"""
import sys, json, time, pathlib, yt_dlp

OPTS = {"quiet": True, "extract_flat": True, "skip_download": True, "sleep_interval_requests": 3,
        "extractor_args": {"youtube": {"lang": ["ko"]}}}


def queries(args):
    for a in args:
        if a.startswith("@"):
            for l in open(a[1:], encoding="utf-8"):
                l = l.strip()
                if l:
                    yield json.loads(l)["query"] if l.startswith("{") else l
        else:
            yield a


if __name__ == "__main__":
    hits, ids_path = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2])
    ids = ids_path.read_text().split() if ids_path.exists() else []
    seen, done = set(ids), {json.loads(l)["q"] for l in open(hits)} if hits.exists() else set()
    with open(hits, "a") as h, open(ids_path, "a") as fi, yt_dlp.YoutubeDL(OPTS) as y:
        for q in queries(sys.argv[3:]):
            if q in done:
                continue
            for prefix in ("ytsearch50:", "ytsearchdate50:"):
                try:
                    es = y.extract_info(prefix + q, download=False).get("entries") or []
                except Exception as e:
                    if any(k in str(e) for k in ("429", "bot", "봇")):
                        sys.exit(f"rate-limited at {q}")
                    print("FAIL", q, e, file=sys.stderr); continue
                for e in es:
                    h.write(json.dumps({"id": e["id"], "title": e.get("title"), "channel": e.get("channel"), "q": q}, ensure_ascii=False) + "\n")
                    if e["id"] not in seen:
                        seen.add(e["id"]); fi.write(e["id"] + "\n")
                h.flush(); fi.flush()
                time.sleep(3)
            print(q, len(seen), file=sys.stderr)
