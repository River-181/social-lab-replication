"""RQ3·RQ10 공용: haiku-v2 코딩 1,800건 + 게시시각 + phase_platform. 사본 DB(lab_260119b)만 사용."""
import glob, json, os, sqlite3
import pandas as pd

DB = '/Users/river/social-lab/work/lab_260119b.db'
RAW = '/Users/river/social-lab/data/raw/codes_haikuv2_*.jsonl'
PHASES = ['전사', '의혹', '고발', '검증·실종', '사망']
# phase_platform 경계(KST, 반열린 구간)
EDGES = ['2026-11-14T00:00:00+09:00', '2026-11-18T09:00:00+09:00', '2026-11-19T07:30:00+09:00',
         '2026-11-19T13:12:00+09:00', '2026-11-20T00:00:00+09:00']

def phase_of(ts):
    e = [pd.Timestamp(x) for x in EDGES]
    for i, b in enumerate(e):
        if ts < b:
            return PHASES[i]
    return '사후'

def load():
    d = pd.DataFrame([dict(json.loads(l), batch=f[-8:-6]) for f in sorted(glob.glob(RAW)) for l in open(f)])
    d = d[d.coder == 'haiku-v2'].copy()
    # unclear 재코딩(sonnet-v2r, skeptic 권고)이 있으면 그 값으로 덮는다. LAB_NO_RECODE=1이면 원래 haiku 값
    rc = [json.loads(l) for f in glob.glob(RAW.replace('codes_haikuv2_*', 'codes_sonnet_unclear_recode*')) for l in open(f)]
    if rc and not os.environ.get('LAB_NO_RECODE'):
        cols = ['frame', 'stance', 'emotion', 'target_of_blame', 'flags', 'note', 'coder']
        r = pd.DataFrame(rc).set_index('target_id')[cols]
        d = d.set_index('target_id'); d.update(r); d = d.reset_index()
    c = sqlite3.connect(DB)
    it = pd.read_sql("select item_id target_id, published_at from items where item_id like 'dc_%'", c)
    cm = pd.read_sql("select comment_id target_id, published_at from comments", c)
    d = d.merge(pd.concat([it, cm]), on='target_id', how='left')
    assert d.published_at.notna().all(), 'published_at 결손'
    d['ts'] = d.published_at.map(pd.Timestamp)
    d['platform'] = d.target_id.str.startswith('dc_').map({True: '디시', False: '유튜브'})
    d['phase'] = d.ts.map(phase_of)
    d['flg'] = d['flags'].map(lambda x: x or [])
    for f in 'LROE':
        d['f_' + f] = d['flg'].map(lambda x: f in x)
    return d

if __name__ == '__main__':
    d = load()
    print(pd.crosstab(d.platform, d.phase)[[p for p in PHASES + ['사후'] if p in set(d.phase)]])
    print(d.groupby('platform').ts.agg(['min', 'max']))
    print(d[['f_L', 'f_R', 'f_O', 'f_E']].sum())

def md(df, index=True):
    """tabulate 없이 마크다운 표."""
    df = df.reset_index() if index else df
    h = '| ' + ' | '.join(map(str, df.columns)) + ' |\n|' + '---|' * len(df.columns) + '\n'
    return h + '\n'.join('| ' + ' | '.join(str(v) for v in r) + ' |' for r in df.values)
