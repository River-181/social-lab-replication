import random,sqlite3,json,subprocess
random.seed(260119)
out=[];rows=[]
db=sqlite3.connect('work/lab_260119b.db')
for b in ['aa','ab','ac','ad']:
    ids=[l.strip() for l in open(f'work/main_batch_{b}') if l.strip()]
    for i in random.sample(ids,50):
        out.append(f'{b}\t{i}')
open('work/skeptic_ids.txt','w').write('\n'.join(out)+'\n')
def text(i):
    r=db.execute('select text from comments where comment_id=?',(i,)).fetchone()
    if r: return r[0]
    r=db.execute('select title,description from items where item_id=?',(i,)).fetchone()
    return (r[0] or '')+' || '+(r[1] or '') if r else None
import sys
with open('work/skeptic_texts.tsv','w') as f:
    for n,l in enumerate(out):
        b,i=l.split('\t'); t=text(i)
        f.write(f"{n}|{i[:12]}|{(t or 'NONE')[:350]!r}\n")
