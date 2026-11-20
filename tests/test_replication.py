"""공개 집계만으로 결과가 재현되는지, 집계에 원문·식별 칸이 없는지 검사한다.
usage: python3 tests/test_replication.py   (CI: .github/workflows/replicate.yml)
"""
import os, subprocess, sys, pathlib, csv
import pandas as pd

R = pathlib.Path(__file__).resolve().parents[1]
os.chdir(R)
env = {**os.environ, "LAB_PUBLIC": "data/aggregates"}

# 1. 확증 H1~H7: 비공개 원자료로 낸 결과와 같은 출력(시드 고정)
out = subprocess.run([sys.executable, "scripts/analysis/confirm.py"], env=env, capture_output=True, text=True, check=True).stdout
exp = (R / "tests/expected/confirm_public.txt").read_text()
if out != exp:
    import difflib
    sys.exit("확증 출력이 기대값과 다르다:\n" + "\n".join(difflib.unified_diff(exp.splitlines(), out.splitlines(), "expected", "got", lineterm="")))
print("ok confirm H1-H7 identical")

# 2. 탐색 단계 대표 수치(findings 문서와 대조)
hv = pd.read_csv("data/aggregates/explore/hourly_volume.csv")
p = hv[hv.series == "dc_dedicated_gallery_post"].sort_values("n").iloc[-1]
assert (p.hour, p.n) == ("2026-11-19T13:00+0900", 237), p  # RQ1: 전용갤 정점 11/19 13시 237건
c = pd.read_csv("data/aggregates/explore/codes_explore_norecode.csv", keep_default_na=False)
a = (c[c.phase == "사망"].groupby("platform").stance.apply(lambda s: round(100 * (s == "공격").mean(), 1))).to_dict()
assert a == {"디시": 40.0, "유튜브": 36.5}, a  # RQ3 3절 표(재코딩 전)
print("ok explore RQ1 peak, RQ3 attack share")

# 3. 개인정보: 원문·제목·닉네임·URL 칸이 없고, 사람 칸은 익명 키뿐이다
import re
BAN = {"text", "title", "name", "nickname", "url", "description", "body", "memo", "note", "snippet", "author_id"}
KEY = re.compile(r"^((yu|du)_[0-9a-f]{12})?$")
for f in list(pathlib.Path("data/aggregates").rglob("*.csv")) + list(pathlib.Path("data/derived").glob("*.csv")):
    df = pd.read_csv(f, dtype=str, keep_default_na=False)
    bad = set(df.columns) & BAN - ({"author_id"} if f.name == "chat_rows.csv" else set())  # chat_rows의 author_id는 번호
    assert not bad, (f, bad)
    if "author" in df.columns and f.parent.name == "derived":
        assert df.author.map(lambda a: bool(KEY.match(a))).all(), f
print("ok no text/identity columns, authors are pseudonymous keys")

# 4. 변형 자료: 객체 키가 표 사이에서 이어진다
D = "data/derived/"
units = pd.read_csv(D + "codes_all.csv").unit
keys = set(pd.read_csv(D + "dc_comments.csv").comment) | set(pd.read_csv(D + "dc_posts.csv").post) | set(pd.read_csv(D + "yt_comments.csv").comment)
assert units.isin(keys).all(), "코딩 단위가 공개 행과 연결되지 않는다"
dcp = set(pd.read_csv(D + "dc_posts.csv").post)
assert pd.read_csv(D + "dc_comments.csv").post.isin(dcp).mean() > 0.9
ch = pd.read_csv(D + "yt_chats.csv")
assert len(ch) == 129476 and ch.groupby("author_int").author.nunique().max() == 1  # chat_rows 번호와 사람 키가 1:1
print("ok derived keys link across tables")

# 5. 신뢰도 보고값(κ)이 공개 자료로 재현된다
r = subprocess.run([sys.executable, "scripts/analysis/reliability_public.py"], capture_output=True, text=True, check=True).stdout
assert "κ=0.68" in r and "target_of_blame  κ=0.67" in r and "skeptic frame κ=0.52" in r, r
print("ok reliability kappas reproduce")
