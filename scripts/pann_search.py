"""네이트판 검색 목록 수집 → posts_pann.jsonl (ingest의 posts* 규칙으로 적재).
usage: python3 pann_search.py out.jsonl since 키워드...   (검색은 최신순이라 since보다 오래된 글이 나오면 그 키워드는 멈춘다)
shortcut: 목록 화면 필드만(제목·요약·게시판·작성자·시각·댓글수). 조회·추천은 글 페이지에 있으니 필요해지면 글 단위 수집을 붙인다.
"""
import sys, json, re, time, html, datetime, pathlib, urllib.parse, urllib.request

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0 Safari/537.36"
ITEM = re.compile(r'<a href="(/talk/\d+)"\s+title="([^"]*)" class="subject">.*?reple-num">\((\d+)\)</span>.*?<div class="txt">\s*<a[^>]*>(.*?)</a>'
                  r'.*?class="part"><a[^>]*>([^<]*)</a>.*?class="writer">([^<]*)</a>.*?class="date">([^<]+)</span>', re.S)

if __name__ == "__main__":
    out_path, since, kws = pathlib.Path(sys.argv[1]), sys.argv[2], sys.argv[3:]
    seen = {json.loads(l)["url"] for l in open(out_path)} if out_path.exists() else set()
    with open(out_path, "a") as out:
        for q in kws:
            n = new = 0
            while True:
                n += 1
                url = f"https://pann.nate.com/search/talk?q={urllib.parse.quote(q)}&page={n}"
                h = urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": UA}), timeout=20).read().decode("utf-8", "replace")
                items = ITEM.findall(h)
                if not items:
                    break
                now = datetime.datetime.now(datetime.timezone.utc).isoformat()
                for path, title, nrep, snip, board, writer, ts in items:
                    u = "https://pann.nate.com" + path
                    if u in seen:
                        continue
                    seen.add(u); new += 1
                    out.write(json.dumps({"url": u, "platform": "네이트판", "title": html.unescape(title), "author": html.unescape(writer),
                                          "published_at": datetime.datetime.strptime(ts.strip(), "%y.%m.%d %H:%M").isoformat() + "+09:00",
                                          "description": html.unescape(re.sub(r"<[^>]+>", "", snip)).strip(), "board": board,
                                          "replies": int(nrep), "keyword": q, "collected_at": now}, ensure_ascii=False) + "\n")
                out.flush(); time.sleep(1.5)
                if "20" + items[-1][6].strip()[:8].replace(".", "-") < since:
                    break
            print(q, "pages", n - 1, "new", new, file=sys.stderr)
