"""외부 기준 대조: 구글 트렌드(일반 대중의 검색 관심, 시간 단위) vs 우리 수집 자료의 시간당 양.
usage: python3 scripts/analysis/ext_benchmark.py [db]  (기본 work/lab_260120.db)
트렌드는 창마다 0~100 상대지수라 창 하나(11/14~20, 시간 단위)만 쓴다. 순위상관이라 척도 차이는 무관.
"""
import sys, json, sqlite3, pathlib
import pandas as pd
from scipy.stats import spearmanr

ROOT = pathlib.Path(__file__).resolve().parents[2]
db = sys.argv[1] if len(sys.argv) > 1 else ROOT / "work/lab_260120.db"
t = pd.DataFrame([json.loads(l) for l in open(ROOT / "data/raw/web_1120/search_interest.jsonl")])
t = t[(t.source == "google_trends") & t.source_url.str.contains("2026-11-13T15") & (t.keyword == "리트냥이")]  # 11/14~20 시간 단위 창
t["h"] = pd.to_datetime(t.ts).dt.tz_convert("Asia/Seoul").dt.floor("h")
trend = t.groupby("h").value.mean()

con = sqlite3.connect(db)
def hourly(sql):
    s = pd.read_sql(sql, con)
    s["h"] = pd.to_datetime(s.published_at, utc=True).dt.tz_convert("Asia/Seoul").dt.floor("h")
    return s.groupby("h").size().reindex(trend.index, fill_value=0)

ours = {
    "디시 전용갤(A, 11/17~)": hourly("select published_at from items where item_id like 'dc_fkgjwks_%'"),
    # B는 갤러리 단위 수집 원자료에서 직접(DB items엔 통합검색 C등급이 섞여 출처 구분 불가)
    "디시 관련갤 키워드(B)": (lambda g: g[g.gall_id != "fkgjwks"].assign(h=lambda x: pd.to_datetime(x.published_at).dt.tz_convert("Asia/Seoul").dt.floor("h"))
                              .drop_duplicates("url").groupby("h").size().reindex(trend.index, fill_value=0))(
        pd.DataFrame([json.loads(l) for l in open(ROOT / "data/raw/dc_search_gall.jsonl")])),
    "유튜브 업로드": hourly("select published_at from items where item_id like 'yt_%' and published_at is not null"),
    "생방송 채팅": hourly("select ts as published_at from chats"),
}
print(f"트렌드 시간 수 {len(trend)} ({trend.index.min()} ~ {trend.index.max()})")
for name, s in ours.items():
    rho, p = spearmanr(trend.values, s.values)
    m = s.index >= pd.Timestamp("2026-11-17T14:00", tz="Asia/Seoul")
    rho2, p2 = spearmanr(trend[m].values, s[m].values)
    print(f"{name}: 전체 ρ={rho:.2f} (p={p:.1e}) | 11/17 14시 이후 ρ={rho2:.2f} (p={p2:.1e}) | 우리 자료 총 {int(s.sum())}")
peak = lambda s: s.idxmax().strftime("%m-%d %H시")
print("정점: 트렌드", peak(trend), "|", " | ".join(f"{k} {peak(v)}" for k, v in ours.items()))
