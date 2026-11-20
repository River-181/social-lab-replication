"""확증 표본: 동결 DB에서 1차 코딩과 겹치지 않는 디시 댓글을 국면별 무작위 추출(PREREG H1·H2·H5·H6용).
usage: python3 scripts/analysis/confirm_sample.py → work/confirm_ids.txt, work/confirm_batch_*
"""
import random, sqlite3, pathlib
ROOT = pathlib.Path(__file__).resolve().parents[2]
PH = [("전사", None, "2026-11-14"), ("의혹", "2026-11-14", "2026-11-18T09:00"), ("고발", "2026-11-18T09:00", "2026-11-19T07:30"),
      ("검증실종", "2026-11-19T07:30", "2026-11-19T13:12"), ("사망", "2026-11-19T13:12", "2026-11-20"), ("사후", "2026-11-20", None)]
N = 300
con = sqlite3.connect(ROOT / "work/lab_final.db")
coded = {r[0] for r in con.execute("select target_id from codes")}
rng, out = random.Random(20261119), []
for name, a, b in PH:
    q = "select comment_id from comments where item_id like 'dc_%' and length(text) between 5 and 300"
    q += f" and published_at >= '{a}'" if a else ""
    q += f" and published_at < '{b}'" if b else ""
    ids = sorted(r[0] for r in con.execute(q) if r[0] not in coded)
    pick = rng.sample(ids, min(N, len(ids)))
    out += pick
    print(name, len(ids), "→", len(pick))
assert not set(out) & coded and len(out) == len(set(out))
rng.shuffle(out)
(ROOT / "work/confirm_ids.txt").write_text("\n".join(out) + "\n")
for i in range(4):
    (ROOT / f"work/confirm_batch_{'abcd'[i]}").write_text("\n".join(out[i::4]) + "\n")
print("total", len(out))
