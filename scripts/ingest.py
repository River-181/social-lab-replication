"""data/raw/*.jsonl → data/lab.db 재적재. 몇 번 돌려도 같은 결과(멱등).
usage: python3 ingest.py            # 기본 경로 전체
원자료 종류는 파일명 접두어로 구분:
  yt_snapshots*.jsonl  (yt_meta.py)      → items + snapshots
  yt_comments*.jsonl   (yt_comments.py)  → comments
  news*.jsonl / posts*.jsonl (웹 Claude 산출, 필드: url,title,platform|매체,published_at,phase,...) → items
  events*.jsonl        (ts,phase,event,source_url) → events
  codes*.jsonl         (target_id,coder,frame,...) → codes
"""
import json, sqlite3, hashlib, datetime, pathlib, sys, urllib.parse

ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW, DB = ROOT / "data/raw", ROOT / "data/lab.db"
STUDY_START = "2026-10-01"
KST = datetime.timezone(datetime.timedelta(hours=9))


def kst(ts):
    return datetime.datetime.fromtimestamp(ts, KST).isoformat() if ts else None


def rows(pattern):
    for p in sorted(RAW.glob(pattern)):
        for line in open(p, encoding="utf-8"):
            if line.strip():
                yield json.loads(line)


def sha(s):
    return hashlib.sha1(s.encode()).hexdigest()[:12]


def dcid(url):
    q = urllib.parse.parse_qs(urllib.parse.urlparse(url).query)
    return f"dc_{q['id'][0]}_{q['no'][0]}"


def dc_time(s, collected_at):
    """디시 댓글 시각 'MM.DD HH:MM:SS'(올해) 또는 'YY.MM.DD HH:MM:SS' → KST ISO."""
    if not s:
        return None
    parts = s.split()
    d = parts[0].split(".")
    y = "20" + d[0] if len(d) == 3 else collected_at[:4]
    return f"{y}-{d[-2]}-{d[-1]}T{parts[1]}+09:00"


CHAT_KINDS = {"liveChatTextMessageRenderer": "text", "liveChatPaidMessageRenderer": "superchat",
              "liveChatPaidStickerRenderer": "sticker", "liveChatMembershipItemRenderer": "membership"}


def load_chat(con, iid, path):
    for line in open(path, encoding="utf-8"):
        r = json.loads(line).get("replayChatItemAction", {})
        for a in r.get("actions", []):
            for k, it in a.get("addChatItemAction", {}).get("item", {}).items():
                if k not in CHAT_KINDS:
                    continue
                runs = (it.get("message") or it.get("headerSubtext") or {}).get("runs", [])
                text = "".join(x.get("text") or (x.get("emoji", {}).get("shortcuts") or [""])[0] for x in runs)
                paid = (it.get("purchaseAmountText") or {}).get("simpleText")
                con.execute("INSERT OR REPLACE INTO chats VALUES (?,?,?,?,?,?,?,?,?)",
                            (it.get("id"), iid, kst(int(it.get("timestampUsec", 0)) / 1e6), int(r.get("videoOffsetTimeMsec", 0)),
                             (it.get("authorName") or {}).get("simpleText"), it.get("authorExternalChannelId"),
                             text, CHAT_KINDS[k], paid))


def load(con):
    con.executescript(open(ROOT / "scripts/schema.sql").read())
    for d in rows("yt_snapshots*.jsonl"):
        iid = "yt_" + d["id"]
        if d.get("status") == "live":
            st = "youtube_live" if d.get("was_live") or d.get("live_status") in ("is_live", "was_live") else \
                 "shorts" if (d.get("duration") or 999) <= 60 else "youtube_video"
            # 최신 스냅샷 메타로 덮어씀(제목 변경도 반영)
            con.execute("INSERT OR REPLACE INTO items VALUES (?,?,?,?,?,?,?,?,coalesce((SELECT phase FROM items WHERE item_id=?),NULL),?,?)",
                        (iid, st, "youtube", f"https://www.youtube.com/watch?v={d['id']}", d.get("title"),
                         d.get("channel"), d.get("channel_id"), kst(d.get("release_timestamp") or d.get("timestamp")),
                         iid, d.get("description"),
                         json.dumps({k: d.get(k) for k in ("duration", "tags", "live_status", "upload_date")}, ensure_ascii=False)))
        con.execute("INSERT OR REPLACE INTO snapshots VALUES (?,?,?,?,?,?,?)",
                    (iid, d["collected_at"], d.get("view_count"), d.get("like_count"), d.get("comment_count"),
                     d.get("channel_follower_count"), d.get("status")))
    for c in rows("yt_comments*.jsonl"):
        con.execute("INSERT OR REPLACE INTO comments VALUES (?,?,?,?,?,?,?,?,?)",
                    (c["id"], "yt_" + c["video_id"], None if c.get("parent") == "root" else c.get("parent"),
                     c.get("author"), c.get("author_id"), c.get("text"), c.get("like_count"),
                     kst(c.get("timestamp")), c.get("collected_at")))
    for kind, pats in (("news", ("news*.jsonl", "web_*/articles*.jsonl")),
                       ("community_post", ("posts*.jsonl", "web_*/community_posts*.jsonl"))):
        for d in (d for p in pats for d in rows(p)):
            if d.get("platform") == "네이트판" and d["published_at"] < STUDY_START:  # 동명이인 옛 글 잡음(raw엔 남김). 웹 전사 글은 살린다
                continue
            con.execute("INSERT OR REPLACE INTO items (item_id,source_type,platform,url,title,author,published_at,phase,description,extra) VALUES (?,?,?,?,?,?,?,?,?,?)",
                        (f"{'news' if kind == 'news' else 'post'}_{sha(d['url'])}", kind,
                         d.get("platform") or d.get("outlet") or d.get("매체"), d["url"], d.get("title") or d.get("제목"),
                         d.get("author"), d.get("published_at") or d.get("published_at_kst") or d.get("posted_at_kst") or d.get("게시시각"),
                         d.get("phase"),
                         d.get("description"), json.dumps(d, ensure_ascii=False)))
    for d in rows("dc_search*.jsonl"):
        con.execute("INSERT OR IGNORE INTO items (item_id,source_type,platform,url,title,author,published_at,description,extra) VALUES (?,?,?,?,?,?,?,?,?)",
                    (dcid(d["url"]), "community_post", "dcinside", d["url"], d["title"], None, d["published_at"], d["snippet"],
                     json.dumps({"gall_id": d["gall_id"], "gall_name": d["gall_name"], "keyword": d["keyword"]}, ensure_ascii=False)))
    for d in rows("dc_posts*.jsonl"):
        iid = dcid(d["url"])
        if d.get("status") == "live":
            con.execute("UPDATE items SET author=?, author_id=?, description=?, title=coalesce(?,title) WHERE item_id=?",
                        (d["author"], d.get("author_uid") or d.get("author_ip"), d["body"], d["title"], iid))
        con.execute("INSERT OR REPLACE INTO snapshots VALUES (?,?,?,?,?,?,?)",
                    (iid, d["collected_at"], d.get("views"), d.get("up"), d.get("comment_total"), None, d["status"]))
    for c in rows("dc_comments*.jsonl"):
        if c.get("nicktype") == "COMMENT_BOY":  # 댓글돌이(광고) 제외
            continue
        iid = dcid(c["post_url"])
        con.execute("INSERT OR REPLACE INTO comments VALUES (?,?,?,?,?,?,?,?,?)",
                    (f"{iid}_{c['no']}", iid, f"{iid}_{c['c_no']}" if str(c.get("depth")) != "0" and c.get("c_no") else None,
                     c.get("name"), c.get("user_id") or c.get("ip"), c.get("memo"), None,
                     dc_time(c.get("reg_date"), c["collected_at"]), c["collected_at"]))
    for f in sorted((RAW / "livechat").glob("*.live_chat.json")):
        load_chat(con, "yt_" + f.name.split(".")[0], f)
    for e in (e for p in ("events*.jsonl", "web_*/events*.jsonl") for e in rows(p)):
        con.execute("INSERT INTO events VALUES (?,?,?,?)", (e["ts"], e.get("phase"), e["event"], e.get("source_url")))
    for c in rows("codes*.jsonl"):
        con.execute("INSERT OR REPLACE INTO codes VALUES (?,?,?,?,?,?,?,?)",
                    (c["target_id"], c["coder"], c.get("frame"), c.get("stance"), c.get("emotion"),
                     c.get("target_of_blame"), c.get("note"), c.get("coded_at")))


if __name__ == "__main__":
    DB.unlink(missing_ok=True)  # 파생물이라 통째 재생성(원자료는 raw/에 그대로)
    con = sqlite3.connect(DB)
    load(con)
    con.commit()
    for t in ("items", "snapshots", "comments", "chats", "codes", "events"):
        print(t, con.execute(f"SELECT count(*) FROM {t}").fetchone()[0])
