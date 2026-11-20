"""rq1·rq2 공용: 사본 DB 로드, KST 시각 파싱, 유튜브 관련성 필터."""
import re, json, sqlite3
import pandas as pd

DB = '/Users/river/social-lab/work/lab_260119.db'
KST = 'Asia/Seoul'
# 제외 기준: 제목·설명·태그 어디에도 아래 키워드가 없으면 무관 영상으로 본다
REL = re.compile('냥이|리트|LEET|세무사|REDACTED_SUBJECT|만점|공개검증|AI ?안경|부정행위|고인|명복|IDA|시험지')

def conn():
    return sqlite3.connect(DB)

def to_kst(s):
    """문자열 시각 -> KST tz-aware. 시각 없는(날짜만) 값은 NaT. 오프셋 없으면 KST로 간주."""
    out = []
    for v in s:
        if v is None or (isinstance(v, str) and len(v) < 16):
            out.append(pd.NaT); continue
        t = pd.Timestamp(v)
        out.append(t.tz_localize(KST) if t.tzinfo is None else t.tz_convert(KST))
    return pd.Series(pd.to_datetime(out, utc=True), index=s.index).dt.tz_convert(KST)

def yt_items(c):
    d = pd.read_sql("""select i.item_id,i.source_type,i.author,i.author_id,i.title,i.description,i.published_at,i.extra,
        s.views,s.likes,s.comment_count from items i left join snapshots s on s.item_id=i.item_id
        where i.source_type in ('youtube_video','youtube_live','shorts')""", c)
    def txt(r):
        tags = ' '.join(json.loads(r.extra).get('tags', [])) if r.extra else ''
        return f"{r.author or ''} {r.title or ''} {r.description or ''} {tags}"
    d['rel'] = d.apply(lambda r: bool(REL.search(txt(r))), axis=1)
    d['author'] = d.author.str.strip()
    d['ts'] = to_kst(d.published_at)
    return d
