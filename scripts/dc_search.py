"""디시 통합검색(전 갤러리) 최신순 수집 → 갤러리 간 확산 시계열의 원자료.
usage: python3 dc_search.py out.jsonl 2026-11-01 키워드1 키워드2 ...
since 날짜보다 오래된 글이 나오면 그 키워드는 멈춘다. 이미 받은 url은 건너뜀(재실행 안전).
"""
import sys, json, re, time, html, datetime, pathlib, urllib.parse, urllib.request

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0 Safari/537.36"
ITEM = re.compile(r'<li>\s*<a href="([^"]+)"[^>]*class="tit_txt">(.*?)</a>\s*<p class="link_dsc_txt">(.*?)</p>'
                  r'.*?class="sub_txt">(.*?)</a><span class="date_time">([^<]+)</span>', re.S)
TAG = re.compile(r"<[^>]+>")


def text(s):
    return html.unescape(TAG.sub("", s)).strip()


def page(q, n):
    url = f"https://search.dcinside.com/post/p/{n}/sort/latest/q/{urllib.parse.quote(q)}"
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    return urllib.request.urlopen(req, timeout=20).read().decode("utf-8", "replace")


def parse(h):
    for url, title, snip, gall, ts in ITEM.findall(h):
        gid = re.search(r"[?&]id=([^&]+)", url)
        yield {"url": html.unescape(url), "gall_id": gid and gid.group(1), "gall_name": text(gall),
               "title": text(title), "snippet": text(snip),
               "published_at": datetime.datetime.strptime(ts.strip(), "%Y.%m.%d %H:%M").isoformat() + "+09:00"}


if __name__ == "__main__":
    out_path, since, kws = pathlib.Path(sys.argv[1]), sys.argv[2], sys.argv[3:]
    seen = {json.loads(l)["url"] for l in open(out_path)} if out_path.exists() else set()
    with open(out_path, "a") as out:
        for q in kws:
            n, new = 1, 0
            while True:
                try:
                    rows = list(parse(page(q, n)))
                except Exception as e:
                    print("FAIL", q, n, e, file=sys.stderr); time.sleep(30); continue
                if not rows:
                    break
                now = datetime.datetime.now(datetime.timezone.utc).isoformat()
                for r in rows:
                    if r["url"] not in seen:
                        seen.add(r["url"]); new += 1
                        out.write(json.dumps({**r, "keyword": q, "collected_at": now}, ensure_ascii=False) + "\n")
                out.flush()
                if rows[-1]["published_at"][:10] < since or n >= 120:  # 통합검색은 120쪽까지만 주고 그 뒤론 같은 쪽 반복
                    break
                n += 1
                time.sleep(1.5)
            print(q, "pages", n, "new", new, file=sys.stderr)
