"""확증 가설을 '다른 통계 방법'으로 다시 본다. 의심하는 사람이 바로 돌려 볼 수 있게, 공개 집계만 쓴다.
usage: python3 scripts/analysis/alt_checks.py [data/aggregates]
사전등록 판정은 confirm.py가 정본이다. 여기 결과는 견고성 점검(탐색)이다.
"""
import sys, math, pathlib
import numpy as np, pandas as pd
from scipy.stats import fisher_exact, chi2_contingency, spearmanr, pearsonr, kendalltau, norm

A = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else "data/aggregates")
EDGES = [("전사", "2026-11-14"), ("의혹", "2026-11-18T09:00"), ("고발", "2026-11-19T07:30"),
         ("검증실종", "2026-11-19T13:12"), ("사망", "2026-11-20"), ("사후", "9999")]  # confirm.py와 같은 경계
phase = lambda ts: next(n for n, e in EDGES if ts < e)


def newcombe(k1, n1, k2, n2, z=1.96):
    """두 비율 차(p2−p1)의 Newcombe(윌슨 하이브리드) 95% CI."""
    def wilson(k, n):
        p = k / n; d = 1 + z * z / n; c = p + z * z / (2 * n); h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
        return (c - h) / d, (c + h) / d
    p1, p2 = k1 / n1, k2 / n2; l1, u1 = wilson(k1, n1); l2, u2 = wilson(k2, n2)
    return p2 - p1 - math.sqrt((p2 - l2) ** 2 + (u1 - p1) ** 2), p2 - p1 + math.sqrt((u2 - p2) ** 2 + (p1 - l1) ** 2)


def top_share(c, q):
    c = np.sort(c)[::-1]; return c[:max(1, math.ceil(len(c) * q))].sum() / c.sum()


for name in ["codes_confirm.csv", "codes_confirm_norecode.csv"]:
    d = pd.read_csv(A / name, keep_default_na=False); d["phase"] = d.published_at.map(phase)
    att = d[d.stance != "무관"]
    v, m = att[att.phase == "검증실종"], att[att.phase == "사망"]
    k1, n1, k2, n2 = (v.stance == "공격").sum(), len(v), (m.stance == "공격").sum(), len(m)
    _, pf = fisher_exact([[k2, n2 - k2], [k1, n1 - k1]], alternative="less")  # H0 기각 = 사망 국면이 더 낮다
    lo, hi = newcombe(k1, n1, k2, n2)
    print(f"[{name}] H1 대안: Fisher 단측 p(사망<검증실종)={pf:.3f}, Newcombe 차 95% CI [{lo:+.1%}, {hi:+.1%}]")
    # 갤러리 구성 교란 점검: 갤러리를 층으로 둔 Mantel-Haenszel 대신, 국면 간 공통 갤러리만 남겨 다시 본다
    common = set(v.gall) & set(m.gall)
    vc, mc = v[v.gall.isin(common)], m[m.gall.isin(common)]
    print(f"   공통 갤러리 {len(common)}곳만: 검증실종 {(vc.stance=='공격').mean():.1%} (n={len(vc)}) → 사망 {(mc.stance=='공격').mean():.1%} (n={len(mc)})")
    # H2·H6 보류 사유(구성 교란) 확인표: 국면별 상위 갤러리 비중
    tab = d.groupby("phase").gall.agg(lambda s: f"{s.value_counts().index[0]} {s.value_counts(normalize=True).iloc[0]:.0%}")
    print("   국면별 최다 갤러리:", tab.to_dict())

chat = pd.read_csv(A / "chat_rows.csv")
c = chat.groupby("author_id").size().values
print("H3 대안: 상위 q% 점유", {f"{q:.1%}": f"{top_share(c, q):.1%}" for q in (0.01, 0.015, 0.02, 0.05, 0.10)})
per_video = chat.groupby("item_id").author_id.apply(lambda s: top_share(s.value_counts().values, 0.015))
big = chat.item_id.value_counts()
print(f"   영상별 상위1.5% 점유 중앙값 {per_video.median():.1%} (채팅 500개 이상 영상 {int((big>=500).sum())}편: {per_video[big[big>=500].index].median():.1%})")
top_item = big.index[0]
print(f"   채팅 최다 영상 1편 제외: {top_share(chat[chat.item_id!=top_item].groupby('author_id').size().values, 0.015):.1%}")

g = pd.read_csv(A / "dc_gallery_posts.csv")
g["h"] = pd.to_datetime(g.published_at).dt.tz_convert("Asia/Seoul").dt.floor("h")
idx = pd.date_range("2026-11-17 14:00", "2026-11-20 13:00", freq="h", tz="Asia/Seoul")
a = g[g.gall_id == "fkgjwks"].groupby("h").size().reindex(idx, fill_value=0)
b = g[g.gall_id != "fkgjwks"].groupby("h").size().reindex(idx, fill_value=0)
print(f"H4 대안: Spearman {spearmanr(a,b)[0]:.2f}, Kendall {kendalltau(a,b)[0]:.2f}, Pearson(log1p) {pearsonr(np.log1p(a),np.log1p(b))[0]:.2f}, "
      f"1차 차분 Spearman {spearmanr(a.diff().dropna(), b.diff().dropna())[0]:.2f}")
