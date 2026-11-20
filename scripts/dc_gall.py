"""디시 갤러리 단위 수집 — 통합검색은 120쪽(약 3시간치)에서 막혀서 과거 글은 이걸로 받는다.
usage: python3 dc_gall.py out.jsonl since 갤러리[:종류] [키워드]
  종류: g(일반) m(마이너, 기본) mini
  키워드 없으면 그 갤러리 글 전체(전용 갤), 있으면 갤러리 내 제목+내용 검색을 search_pos 블록(1만 글)씩 거슬러 올라간다.
출력은 dc_search.jsonl과 같은 필드라 ingest가 그대로 먹는다(dc_search*로 시작하는 파일명). 이미 받은 url은 건너뜀.
"""
import sys, json, re, time, html, datetime, pathlib, urllib.parse, urllib.request

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0 Safari/537.36"
BASE = {"g": "board", "m": "mgallery/board", "mini": "mini/board"}
ROW = re.compile(r'<tr class="ub-content us-post" data-no="(\d+)".*?<td class="gall_tit[^>]*>\s*<a\s+href="[^"]*"[^>]*>(.*?)</a>'
                 r'.*?class="gall_date" title="([^"]+)"', re.S)
TAG = re.compile(r"<[^>]+>")


def get(url):
    return urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": UA}), timeout=20).read().decode("utf-8", "replace")


def rows(h, gid, kind):
    for no, title, ts in ROW.findall(h):
        yield {"url": f"https://gall.dcinside.com/{BASE[kind]}/view/?id={gid}&no={no}", "no": int(no),
               "title": html.unescape(TAG.sub("", title)).strip(), "published_at": ts.replace(" ", "T") + "+09:00"}


def crawl(gid, kind, kw, since):
    """(행 목록, 블록 끝 여부)를 쪽마다 낸다. 키워드면 search_pos 블록을 이어 붙인다."""
    pos = ""
    while True:
        page, prev = 1, None
        while True:
            q = {"id": gid, "page": page}
            if kw:
                q.update({"search_pos": pos, "s_type": "search_subject_memo", "s_keyword": kw})
            h = get(f"https://gall.dcinside.com/{BASE[kind]}/lists/?" + urllib.parse.urlencode(q))
            rs = list(rows(h, gid, kind))
            if not rs or rs[0]["url"] == prev:  # 끝 쪽을 넘기면 같은 쪽이 되돌아옴
                break
            prev = rs[0]["url"]
            yield rs
            if rs[-1]["published_at"][:10] < since:
                return
            page += 1
            time.sleep(1.5)
        if not kw:
            return
        # 다음 검색 블록: 현재보다 오래된(절대값 작은) search_pos 중 가장 가까운 것
        cur = abs(int(pos)) if pos else 10**12
        nxt = [int(p) for p in re.findall(r"search_pos=(-\d+)", h) if abs(int(p)) < cur]
        if not nxt:
            return
        pos = str(max(nxt, key=abs))
        time.sleep(1.5)


if __name__ == "__main__":
    out_path, since, gk = pathlib.Path(sys.argv[1]), sys.argv[2], sys.argv[3]
    kw = sys.argv[4] if len(sys.argv) > 4 else None
    gid, kind = (gk.split(":") + ["m"])[:2]
    seen = {json.loads(l)["url"] for l in open(out_path)} if out_path.exists() else set()
    new = pages = 0
    with open(out_path, "a") as out:
        for rs in crawl(gid, kind, kw, since):
            pages += 1
            now = datetime.datetime.now(datetime.timezone.utc).isoformat()
            for r in rs:
                if r["url"] in seen or r["published_at"][:10] < since:
                    continue
                seen.add(r["url"]); new += 1
                out.write(json.dumps({"url": r["url"], "gall_id": gid, "gall_name": gid, "title": r["title"], "snippet": "",
                                      "published_at": r["published_at"], "keyword": kw or "(전체)",
                                      "collected_at": now}, ensure_ascii=False) + "\n")
            out.flush()
    print(gid, kw, "pages", pages, "new", new, file=sys.stderr)
