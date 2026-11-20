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

# 3. 개인정보: 집계에 원문·작성자·제목 칸이 없다
BAN = {"text", "author", "author_id_raw", "title", "nickname", "comment_id", "url", "description"}
for f in pathlib.Path("data/aggregates").rglob("*.csv"):
    cols = set(next(csv.reader(open(f))))
    assert not cols & BAN, (f, cols & BAN)
print("ok no text/identity columns")
