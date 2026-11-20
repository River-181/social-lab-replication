"""디시 글 상세 + 댓글 전체. 입력은 dc_search.jsonl(url 목록).
usage: python3 dc_post.py data/raw/dc_search.jsonl data/raw/dc_posts.jsonl data/raw/dc_comments.jsonl
글은 dc_posts에 1줄(삭제면 status=deleted), 댓글은 dc_comments에 댓글당 1줄(원형 JSON + post_url). 이미 받은 url은 건너뜀.
"""
import sys, json, re, time, html, datetime, pathlib, urllib.parse, urllib.request

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0 Safari/537.36"
TAG = re.compile(r"<[^>]+>")


def get(url, data=None, ref=None):
    h = {"User-Agent": UA}
    if data:
        h.update({"X-Requested-With": "XMLHttpRequest", "Referer": ref})
        data = urllib.parse.urlencode(data).encode()
    return urllib.request.urlopen(urllib.request.Request(url, data, h), timeout=20).read().decode("utf-8", "replace")


def one(rx, h, default=None):
    m = re.search(rx, h, re.S)
    return html.unescape(m.group(1)).strip() if m else default


def num(s):
    return int(re.sub(r"\D", "", s)) if s and re.search(r"\d", s) else None


def post(url):
    h = get(url)
    q = urllib.parse.parse_qs(urllib.parse.urlparse(url).query)
    gid, no = q["id"][0], q["no"][0]
    esno = one(r'id="e_s_n_o"[^>]*value="([^"]+)"', h)
    if not esno:  # 삭제·차단 글
        return {"url": url, "status": "deleted"}, []
    body = one(r'<div class="write_div"[^>]*>(.*?)<!--\s*본문 우측 광고', h, "")  # 본문 안 div 중첩 → 광고 주석까지
    body = re.sub(r"<script.*?</script>", "", body, flags=re.S)
    p = {"url": url, "status": "live", "gall_id": gid, "no": no,
         "title": one(r'<span class="title_subject">(.*?)</span>', h),
         "author": one(r'class="gall_writer[^"]*"[^>]*data-nick="([^"]*)"', h),
         "author_uid": one(r'class="gall_writer[^"]*"[^>]*data-uid="([^"]*)"', h),
         "author_ip": one(r'class="gall_writer[^"]*"[^>]*data-ip="([^"]*)"', h),
         "posted_at": one(r'class="gall_date" title="([^"]+)"', h),
         "views": num(one(r'class="gall_count">([^<]*)', h)),
         "up": num(one(rf'id="recommend_view_up_{no}">([^<]*)', h)),
         "down": num(one(rf'id="recommend_view_down_{no}">([^<]*)', h)),
         "body": TAG.sub(" ", html.unescape(body)).strip()}
    gtype = one(r'id="_GALLTYPE_" value="([^"]+)"', h, "G")
    comments, page = [], 1
    while True:
        r = json.loads(get("https://gall.dcinside.com/board/comment/", {
            "id": gid, "no": no, "cmt_id": gid, "cmt_no": no, "e_s_n_o": esno,
            "comment_page": page, "sort": "", "_GALLTYPE_": gtype}, url))
        cs = r.get("comments") or []
        comments += cs
        p["comment_total"] = r.get("total_cnt")
        if not cs or len(comments) >= (r.get("total_cnt") or 0):
            break
        page += 1
        time.sleep(1)
    return p, comments


if __name__ == "__main__":
    src, pout, cout = sys.argv[1], pathlib.Path(sys.argv[2]), sys.argv[3]
    urls = list(dict.fromkeys(json.loads(l)["url"] for l in open(src)))
    done = {json.loads(l)["url"] for l in open(pout)} if pout.exists() else set()
    fails = 0
    with open(pout, "a") as po, open(cout, "a") as co:
        for u in urls:
            if u in done:
                continue
            now = datetime.datetime.now(datetime.timezone.utc).isoformat()
            try:
                p, cs = post(u)
                fails = 0
            except Exception as e:
                fails += 1
                print("FAIL", u, e, file=sys.stderr)
                if fails >= 5:
                    sys.exit("5 consecutive failures: likely blocked, stop")  # 계속 두드리면 차단만 길어짐
                time.sleep(30)
                continue
            po.write(json.dumps({**p, "collected_at": now}, ensure_ascii=False) + "\n")
            for c in cs:
                co.write(json.dumps({**c, "memo": TAG.sub("", html.unescape(c.get("memo") or "")),
                                     "post_url": u, "collected_at": now}, ensure_ascii=False) + "\n")
            po.flush(); co.flush()
            time.sleep(1.5)
