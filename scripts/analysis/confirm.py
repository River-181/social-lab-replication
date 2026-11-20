"""PREREG.md 확증 검정 H1~H7을 등록 문구 그대로 계산. 동결 DB(work/lab_final.db) + 확증 코딩(codes_confirm_*).
usage: python3 scripts/analysis/confirm.py  → findings/260120_확증검정.md 용 표를 stdout으로
시드 20261119, 부트스트랩 10,000회. H1~H4는 확증 가족(Holm 보정), H5~H7은 '관측창 1일' 잠정(River 11-20 결정).
"""
import glob, json, math, re, sqlite3, pathlib, os
import numpy as np, pandas as pd
from scipy.stats import norm, spearmanr

ROOT = pathlib.Path(__file__).resolve().parents[2]
DB = ROOT / "work/lab_final.db"
PUB = os.environ.get("LAB_PUBLIC")  # 공개 집계 폴더(원자료 없이 재현). 설정되면 DB·원자료 대신 CSV를 읽는다
EXP = os.environ.get("LAB_EXPORT")  # 이 폴더에 익명 집계 CSV를 쓴다(비공개 저장소에서만)


def pub(name):
    return pd.read_csv(pathlib.Path(PUB) / name, keep_default_na=False)


def export(df, name):
    if EXP:
        pathlib.Path(EXP).mkdir(parents=True, exist_ok=True)
        df.to_csv(pathlib.Path(EXP) / name, index=False)
RNG = np.random.default_rng(20261119)
B = 10_000
EDGES = [("전사", "2026-11-14"), ("의혹", "2026-11-18T09:00"), ("고발", "2026-11-19T07:30"),
         ("검증실종", "2026-11-19T13:12"), ("사망", "2026-11-20"), ("사후", "9999")]
con = None if PUB else sqlite3.connect(DB)


def phase(ts):
    return next(n for n, e in EDGES if ts < e)


def codes():
    if PUB:
        d = pub("codes_confirm_norecode.csv" if os.environ.get("LAB_NO_RECODE") else "codes_confirm.csv")
        d["flags"] = d.R.map(lambda r: ["R"] if r else [])
        d["phase"] = d.published_at.map(phase)
        d["R"] = d.R.astype(bool)
        return d
    rows = [json.loads(l) for f in sorted(glob.glob(str(ROOT / "data/raw/codes_confirm_[a-d].jsonl"))) for l in open(f)]
    d = pd.DataFrame(rows).set_index("target_id")
    rc = [json.loads(l) for f in glob.glob(str(ROOT / "data/raw/codes_confirm_recode*.jsonl")) for l in open(f)]
    if rc and not os.environ.get("LAB_NO_RECODE"):  # unclear 재코딩 덮어쓰기(1차와 같은 규칙)
        d.update(pd.DataFrame(rc).set_index("target_id")[["frame", "stance", "emotion", "target_of_blame", "flags", "coder"]])
    d = d.reset_index()
    ts = pd.read_sql("select comment_id as target_id, published_at from comments where item_id like 'dc_%'", con)
    d = d.merge(ts, on="target_id", how="left")
    assert d.published_at.notna().all()
    if os.environ.get("LAB_ONLY_FKG"):  # 민감도 S4: 전용갤(전수) 댓글만
        d = d[d.target_id.str.startswith("dc_fkgjwks_")]
    d["phase"] = d.published_at.map(phase)
    d["R"] = d["flags"].map(lambda x: "R" in (x or []))
    export(pd.DataFrame({"gall": d.target_id.str.split("_").str[1], "published_at": d.published_at, "frame": d.frame,
                         "stance": d.stance, "target_of_blame": d.target_of_blame, "R": d.R.astype(int)}),
           "codes_confirm_norecode.csv" if os.environ.get("LAB_NO_RECODE") else "codes_confirm.csv")
    return d


def boot_diff(a, b):
    """비율 차(b−a)의 부트스트랩 분포. a,b는 0/1 배열."""
    a, b = np.asarray(a, float), np.asarray(b, float)
    ia, ib = RNG.integers(0, len(a), (B, len(a))), RNG.integers(0, len(b), (B, len(b)))
    return b[ib].mean(1) - a[ia].mean(1)


def ca_z(k, n):
    k, n, sc = np.asarray(k, float), np.asarray(n, float), np.arange(len(k))
    N, pb = n.sum(), k.sum() / n.sum()
    t = (sc * (k - n * pb)).sum()
    v = pb * (1 - pb) * ((n * sc ** 2).sum() - (n * sc).sum() ** 2 / N)
    return t / math.sqrt(v)


def top_share(counts, q=0.015):
    c = np.sort(np.asarray(counts, float))[::-1]
    k = max(1, math.ceil(len(c) * q))
    return c[:k].sum() / c.sum()


R = []  # (가설, 값, 판정, p 또는 None, 메모)

# ---------- H3·H7: 생방송 채팅 (코딩 불필요)
if PUB:
    chat = pub("chat_rows.csv")
else:
    chat = pd.read_sql("select item_id, author_id, kind, paid from chats", con)
    vid = {v: f"v{i:03d}" for i, v in enumerate(sorted(chat.item_id.unique()))}
    aid = {a: i for i, a in enumerate(sorted(chat.author_id.unique()))}  # 정렬 순서 보존 → 부트스트랩 동일
    export(pd.DataFrame({"item_id": chat.item_id.map(vid), "author_id": chat.author_id.map(aid), "kind": chat.kind}), "chat_rows.csv")
per_author = chat.groupby("author_id").size().values
share = top_share(per_author)
bs = np.array([top_share(RNG.choice(per_author, len(per_author))) for _ in range(2000)])  # shortcut: 2,000회(작성자 수 많아 느림)
lo = np.quantile(bs, 0.025)
R.append(("H3 채팅 상위1.5% 점유 ≥30%", f"{share:.1%} (95% CI 하한 {lo:.1%}, 작성자 {len(per_author):,}, 채팅 {len(chat):,})",
          "지지" if lo >= 0.30 else "기각", None, "확증"))

if PUB:
    lv = pub("live_items.csv")
    lv["track"] = lv.track.astype(bool)
else:
    yt = pd.read_sql("select item_id, author, title, source_type from items where item_id like 'yt_%'", con)
    BC = re.compile(r'YTN|JTBC|MBC|SBS|KBS|채널A|OBS|연합뉴스TV|뉴스1|CHOSUN|MBN|KNN|TJB|CBS|서울신문|매일신문|엠빅뉴스|VIDEOMUG|iMBC|시교라')  # rq2_amplify.py와 같은 규칙
    PAT = re.compile('찾음|찾아|추적|현장검증|대치|잠수|잠적|수색')
    lv = yt[(yt.source_type == "youtube_live") & ~yt.author.fillna("").str.contains(BC)].copy()
    lv["track"] = lv.title.fillna("").str.contains(PAT)
    lv["excluded_channel"] = lv.author.fillna("").str.contains("REDACTED_CHANNEL_A")  # 공개본에서는 이름 대신 이 플래그
    export(pd.DataFrame({"item_id": lv.item_id.map(vid), "track": lv.track.astype(int), "excluded_channel": lv.excluded_channel.astype(int)}), "live_items.csv")
if PUB:
    c = chat[chat.item_id.isin(lv.item_id)].merge(lv[["item_id", "track", "excluded_channel"]], on="item_id")
    c["excluded_channel"] = c.excluded_channel.astype(bool)
else:
    c = chat[chat.item_id.isin(lv.item_id)].merge(lv[["item_id", "track", "excluded_channel"]], on="item_id")
def per1k(df):
    return 1000 * (df.kind == "superchat").sum() / max(1, (df.kind == "text").sum())
t1, t0 = per1k(c[c.track]), per1k(c[~c.track])
ex = c[~c.excluded_channel]
t1x, t0x = per1k(ex[ex.track]), per1k(ex[~ex.track])
h7 = share >= 0.30 and t1 <= t0 and t1x <= t0x
R.append(("H7 주목 집중·수익 아님(잠정)", f"상위1.5% {share:.1%}; 천 채팅당 슈퍼챗 추적 {t1:.2f} vs 비추적 개인 {t0:.2f}; REDACTED_CHANNEL_A 제외 {t1x:.2f} vs {t0x:.2f}",
          "지지(잠정)" if h7 else "기각(잠정)", None, "잠정"))

# ---------- H4: 키워드 표본(B) vs 전용갤 전수(A) 시간당 순위상관
if PUB:
    g = pub("dc_gallery_posts.csv")
else:
    g = pd.DataFrame([json.loads(l) for l in open(ROOT / "data/raw/dc_search_gall.jsonl")]).drop_duplicates("url")
    export(g[["gall_id", "published_at"]], "dc_gallery_posts.csv")
g["h"] = pd.to_datetime(g.published_at).dt.tz_convert("Asia/Seoul").dt.floor("h")
idx = pd.date_range("2026-11-17 14:00", "2026-11-20 13:00", freq="h", tz="Asia/Seoul")  # 전용갤 개설~동결
A = g[g.gall_id == "fkgjwks"].groupby("h").size().reindex(idx, fill_value=0)
Bk = g[g.gall_id != "fkgjwks"].groupby("h").size().reindex(idx, fill_value=0)
rho, p4 = spearmanr(A, Bk)
R.append(("H4 키워드표본↔전용갤 ρ≥0.5", f"ρ={rho:.2f} (시간 {len(idx)}개)", "지지" if rho >= 0.5 else "기각", p4, "확증"))

# ---------- 코딩 기반 H1·H2·H5·H6
if PUB or glob.glob(str(ROOT / "data/raw/codes_confirm_*.jsonl")):
    d = codes()
    att = d[d.stance != "무관"]
    a_v = (att[att.phase == "검증실종"].stance == "공격").values
    a_d = (att[att.phase == "사망"].stance == "공격").values
    diff = boot_diff(a_v, a_d)
    p1 = float((diff >= 0).mean())  # 단측: '낮다'의 증거 = diff<0 비율이 클 때 → p = P(diff≥0)
    R.append(("H1 사망 공격 ≥ 검증·실종", f"검증실종 {a_v.mean():.1%} (n={len(a_v)}) → 사망 {a_d.mean():.1%} (n={len(a_d)}), 차 {a_d.mean()-a_v.mean():+.1%}, 95% CI [{np.quantile(diff,.025):+.1%}, {np.quantile(diff,.975):+.1%}]",
              "지지" if p1 >= 0.05 else "기각", p1, "확증"))

    P3 = ["전사", "의혹", "고발"]
    k = [int(d[d.phase == q].R.sum()) for q in P3]; n = [int((d.phase == q).sum()) for q in P3]
    z = ca_z(k, n); p2 = 1 - norm.cdf(z)
    R.append(("H2 R-flag 전사→의혹→고발 증가", f"{dict(zip(P3, zip(k, n)))} z={z:.2f}", "지지" if p2 < 0.05 else "기각", p2, "확증"))

    sv = d[d.phase == "사후"]
    att_s = (sv[sv.stance != "무관"].stance == "공격").mean()
    bl = sv[sv.target_of_blame != "없음"]
    own = bl.target_of_blame.isin(["리트냥이", "세무냥이"]).mean()
    R.append(("H5 사후 비해소(잠정, 관측창 11/20 00~13시)", f"공격 {att_s:.1%} (기준 >34%), 당사자 비난 {own:.1%} (기준 ≥73%), n={len(sv)}",
              "지지(잠정)" if att_s > 0.34 and own >= 0.73 else "기각(잠정)", None, "잠정"))

    f = lambda s: s.frame.isin(["F03", "F09"]).values
    pre, post = f(d[d.phase.isin(["전사", "의혹"])]), f(d[d.phase == "고발"])
    dd = boot_diff(pre, post)
    lo6, hi6 = np.quantile(dd, [0.025, 0.975])
    R.append(("H6 제도 대체(고발 후 F03+F09 안 오름)", f"고발 전 {pre.mean():.1%} (n={len(pre)}) → 고발~검증 {post.mean():.1%} (n={len(post)}), 차 95% CI [{lo6:+.1%}, {hi6:+.1%}]",
              "지지" if lo6 <= 0 else "기각", None, "확증(새 표본)"))
    print("코딩:", len(d), "건, 국면별", d.phase.value_counts().to_dict(), "| unclear", f"{(d.frame=='unclear').mean():.1%}")

# ---------- Holm (확증 가족 중 p가 있는 것)
fam = [(i, r[3]) for i, r in enumerate(R) if r[4].startswith("확증") and r[3] is not None]
for rank, (i, p) in enumerate(sorted(fam, key=lambda x: x[1])):
    adj = min(1.0, p * (len(fam) - rank))
    R[i] = R[i][:3] + (adj,) + (R[i][4] + f" (Holm p={adj:.3g})",)

print("| 가설 | 값 | 판정 | 구분 |\n|---|---|---|---|")
for h, v, j, p, kind in sorted(R):
    print(f"| {h} | {v} | {j} | {kind} |")
