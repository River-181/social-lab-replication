"""ingest 자체 점검: 가짜 raw로 적재 → 행 수·분류 확인. python3 tests/test_ingest.py"""
import json, sqlite3, sys, tempfile, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent / "scripts"))
import ingest

tmp = pathlib.Path(tempfile.mkdtemp())
w = lambda n, rs: (tmp / n).write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rs))
w("yt_snapshots_a.jsonl", [
    {"id": "v1", "title": "t", "channel": "c", "timestamp": 1763500000, "duration": 40, "view_count": 10, "status": "live", "collected_at": "T1"},
    {"id": "v1", "title": "t2", "channel": "c", "timestamp": 1763500000, "duration": 40, "view_count": 50, "status": "live", "collected_at": "T2"},
    {"id": "v2", "status": "deleted", "collected_at": "T2"}])
w("yt_comments_a.jsonl", [{"id": "c1", "parent": "root", "video_id": "v1", "text": "x", "timestamp": 1763500100},
                          {"id": "c1.r", "parent": "c1", "video_id": "v1", "text": "y"}])
w("news_a.jsonl", [{"url": "https://n/1", "제목": "기사", "매체": "A", "phase": "사망"}])
ingest.RAW = tmp
con = sqlite3.connect(":memory:")
ingest.load(con)
q = lambda s: con.execute(s).fetchall()
assert q("SELECT source_type,title FROM items WHERE item_id='yt_v1'") == [("shorts", "t2")]
assert q("SELECT count(*) FROM snapshots") == [(3,)]
assert q("SELECT status FROM snapshots WHERE item_id='yt_v2'") == [("deleted",)]
assert q("SELECT parent_id FROM comments ORDER BY comment_id") == [(None,), ("c1",)]
assert q("SELECT source_type,platform,phase FROM items WHERE item_id LIKE 'news_%'") == [("news", "A", "사망")]
print("ok")

# 디시 3종
assert ingest.dc_time("11.19 17:30:44", "2026-11-19T09:00") == "2026-11-19T17:30:44+09:00"
assert ingest.dc_time("25.12.31 01:02:03", "2026-11-19") == "2025-12-31T01:02:03+09:00"
u = "https://gall.dcinside.com/board/view/?id=g1&no=5"
w("dc_search_a.jsonl", [{"url": u, "gall_id": "g1", "gall_name": "G", "title": "t", "snippet": "s", "published_at": "2026-11-19T17:30:00+09:00", "keyword": "k"}])
w("dc_posts_a.jsonl", [{"url": u, "status": "live", "author": "nick", "author_uid": "", "author_ip": "1.2", "title": "t", "body": "b", "views": 42, "up": 1, "comment_total": 2, "collected_at": "T3"}])
w("dc_comments_a.jsonl", [{"no": "1", "c_no": "1", "depth": 0, "name": "a", "ip": "3.4", "memo": "m", "reg_date": "11.19 17:31:00", "post_url": u, "collected_at": "2026-11-19T10:00"},
                          {"no": "2", "c_no": "1", "depth": 1, "name": "b", "memo": "r", "reg_date": "11.19 17:32:00", "post_url": u, "collected_at": "2026-11-19T10:00"},
                          {"no": "3", "nicktype": "COMMENT_BOY", "memo": "ad", "post_url": u, "collected_at": "x"}])
con = sqlite3.connect(":memory:")
ingest.load(con)
assert q("SELECT author,author_id,description FROM items WHERE item_id='dc_g1_5'") == [("nick", "1.2", "b")]
assert q("SELECT views FROM snapshots WHERE item_id='dc_g1_5'") == [(42,)]
assert q("SELECT comment_id,parent_id FROM comments WHERE item_id='dc_g1_5' ORDER BY comment_id") == [("dc_g1_5_1", None), ("dc_g1_5_2", "dc_g1_5_1")]
print("ok dc")

# 생방송 채팅
(tmp / "livechat").mkdir()
act = lambda off, k, it: json.dumps({"replayChatItemAction": {"videoOffsetTimeMsec": off, "actions": [{"addChatItemAction": {"item": {k: it}}}]}})
(tmp / "livechat" / "v1.live_chat.json").write_text("\n".join([
    act("100", "liveChatTextMessageRenderer", {"id": "m1", "timestampUsec": "1763500000000000", "message": {"runs": [{"text": "a"}, {"emoji": {"shortcuts": [":x:"]}}]}, "authorName": {"simpleText": "@u"}}),
    act("200", "liveChatPaidMessageRenderer", {"id": "m2", "timestampUsec": "1763500001000000", "purchaseAmountText": {"simpleText": "₩10,000"}}),
    act("300", "liveChatPlaceholderItemRenderer", {"id": "m3"})]))
con = sqlite3.connect(":memory:")
ingest.load(con)
assert q("SELECT chat_id,offset_ms,text,kind,paid FROM chats ORDER BY chat_id") == [("m1", 100, "a:x:", "text", None), ("m2", 200, "", "superchat", "₩10,000")]
print("ok chat")
