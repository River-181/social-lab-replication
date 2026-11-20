"""탐색 단계(RQ1·RQ2·RQ3·RQ10) 핵심 수치를 공개 집계만으로 다시 계산하는 출발점.
usage: python3 scripts/analysis/explore_public.py [data/aggregates/explore]
원래 분석은 비공개 DB의 그날 사본으로 했다(findings 각 문서 머리말). 동결 DB 기준이라 수집이 더 된 만큼 일부 수치가 다를 수 있다.
"""
import sys, pathlib
import pandas as pd

A = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else "data/aggregates/explore")
pct = lambda s: (100 * s).round(1)

# RQ1 과정: 출처별 시간당 정점
hv = pd.read_csv(A / "hourly_volume.csv")
peak = hv.loc[hv.groupby("series").n.idxmax()].set_index("series")
print("RQ1 출처별 시간당 정점\n", peak.to_string(), "\n")

# RQ2 증폭: 채널 유형별 조회 점유, 추적·검증류 생방송의 채팅·슈퍼챗 몫
v = pd.read_csv(A / "yt_videos.csv")
print("RQ2 조회 점유(방송사 vs 개인·독립)\n", pct(v.groupby("channel_type").views.sum() / v.views.sum()).to_string(), "\n")
lv = v[v.source_type == "youtube_live"]
t = lv.groupby("track_title")[["views", "n_chat", "n_superchat", "superchat_krw"]].sum()
print("RQ2 생방송: 추적·검증류(1) vs 그 외(0) 점유 %\n", pct(t / t.sum()).to_string(), "\n")

# RQ3·RQ10 담론: 플랫폼 × 국면 입장·감정·비난 대상(전체 분모)
# 주의: findings/260119_RQ3_프레임이동.md 3절 표는 '재코딩 전' 값이다(codes_explore_norecode.csv로 그대로 재현된다).
order = ["전사", "의혹", "고발", "검증·실종", "사망"]
for fname, col in [("codes_explore_norecode.csv", "stance"), ("codes_explore.csv", "stance"), ("codes_explore.csv", "emotion"), ("codes_explore.csv", "target_of_blame")]:
    c = pd.read_csv(A / fname, keep_default_na=False)
    tab = pd.crosstab([c.platform, c[col]], c.phase, normalize=False)
    tot = c.groupby(["platform", "phase"]).size().unstack()
    share = (tab / tot.reindex(tab.index.get_level_values(0)).set_axis(tab.index)).mul(100).round(1)
    print(f"RQ3 {col} % (플랫폼 × 국면, {fname})\n", share[[p for p in order if p in share.columns]].to_string(), "\n")
