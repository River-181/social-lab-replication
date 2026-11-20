"""코더 간 일치도(Cohen κ)를 공개 변형 자료 codes_all.csv로 다시 계산한다.
usage: python3 scripts/analysis/reliability_public.py
파일럿 haikuA vs haikuB(같은 400건), 본 코딩 vs skeptic 독립 코딩(200건).
"""
import pandas as pd

c = pd.read_csv("data/derived/codes_all.csv", keep_default_na=False)


def kappa(a, b):
    cats = sorted(set(a) | set(b))
    n = len(a); po = (a == b).mean()
    pe = sum((a == k).mean() * (b == k).mean() for k in cats)
    return (po - pe) / (1 - pe), n


def pair(fa, fb, col, drop_unclear=False):
    A = c[c.file == fa].drop_duplicates("unit").set_index("unit")[col]
    B = c[c.file == fb].drop_duplicates("unit").set_index("unit")[col]
    j = pd.concat([A, B], axis=1, join="inner", keys=["a", "b"])
    if drop_unclear:
        j = j[(j.a != "unclear") & (j.b != "unclear")]
    return kappa(j.a, j.b)


# 파일럿(코드북 v0.1)에서 코더 A는 '기타', 코더 B는 'unclear'로 같은 뜻을 적었다. 보고한 κ=0.68은 둘을 같은 값으로 본 것이다.
k, n = pair("codes_haikuA_pilot", "codes_haikuB_pilot", "frame")
print(f"파일럿 A vs B  frame (원값)            κ={k:.2f} (n={n})")
c.loc[(c.file == "codes_haikuA_pilot") & (c.frame == "기타"), "frame"] = "unclear"
for col in ["frame", "target_of_blame", "stance"]:
    k, n = pair("codes_haikuA_pilot", "codes_haikuB_pilot", col)
    print(f"파일럿 A vs B  {col:16s} κ={k:.2f} (n={n})" + ("  ← '기타'=unclear (보고값 0.68)" if col == "frame" else "") + ("  ← v0.1엔 값 목록 없음(그래서 v0.2에서 닫음)" if col == "stance" else ""))
main = c[c.file.str.startswith("codes_haikuv2_")].drop_duplicates("unit").assign(file="main")
c = pd.concat([c, main])
for col in ["frame"]:
    k, n = pair("main", "codes_skeptic_drift", col)
    print(f"본 코딩 vs skeptic {col} κ={k:.2f} (n={n})")
