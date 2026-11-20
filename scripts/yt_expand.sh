#!/bin/zsh
# 유튜브 확장 1회: 웹 검색어 33 + 비교사례 검색어 → 새 id 메타·댓글. 다른 유튜브 작업(.lock)이 끝나길 기다렸다 직렬로.
cd "$(dirname $0)/.."
until mkdir .lock 2>/dev/null; do find .lock -maxdepth 0 -mmin +720 -exec rmdir {} \; 2>/dev/null; sleep 60; done; trap 'rmdir .lock' EXIT
R=data/raw; L=logs/yt.log
cp $R/ids_all.txt /tmp/ids_before.txt 2>/dev/null; touch $R/ids_compare.txt; cp $R/ids_compare.txt /tmp/idc_before.txt
python3 scripts/yt_search.py $R/search_hits.jsonl $R/ids_all.txt @$R/web_1119/youtube_queries.jsonl 2>>$L || exit 1
python3 scripts/yt_search.py $R/search_hits_compare.jsonl $R/ids_compare.txt @$R/compare_queries.jsonl 2>>$L || exit 1
comm -13 <(sort /tmp/ids_before.txt) <(sort $R/ids_all.txt) > /tmp/ids_new.txt
comm -13 <(sort /tmp/idc_before.txt) <(sort $R/ids_compare.txt) > /tmp/idc_new.txt
python3 scripts/yt_meta.py /tmp/ids_new.txt $R/yt_snapshots.jsonl 2>>$L || exit 1
python3 scripts/yt_meta.py /tmp/idc_new.txt $R/cmp_yt_snapshots.jsonl 2>>$L || exit 1
python3 scripts/yt_comments.py /tmp/ids_new.txt $R/yt_comments.jsonl 1000 2>>$L || exit 1
python3 scripts/yt_comments.py /tmp/idc_new.txt $R/cmp_yt_comments.jsonl 300 2>>$L
wc -l /tmp/ids_new.txt /tmp/idc_new.txt
