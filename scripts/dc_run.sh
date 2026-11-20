#!/bin/zsh
# 디시 1회 수집 묶음: 전용 갤 전체 → 관련 갤 키워드 검색 → 통합검색(최근 120쪽) 나머지 키워드 → 글·댓글 본문
cd "$(dirname $0)/.."
O=data/raw/dc_search_gall.jsonl; S=2026-10-01; L=logs/dc_gall.log
grep -q "^fkgjwks None" $L 2>/dev/null || python3 scripts/dc_gall.py $O $S fkgjwks 2>>$L
for g in leetkorea cta ctaexam ctastudy lawschool lawschoolroom lawip mimiminu mimiu cpacta csatlecture singlebungle1472 chzzk exam_new2:g comic_new6:g; do
  for k in 리트냥이 세무냥이 REDACTED_SUBJECT; do grep -q "^${g%%:*} $k pages" $L 2>/dev/null || python3 scripts/dc_gall.py $O $S $g $k 2>>$L; done  # 로그에 끝난 조합은 건너뜀(재시작용)
done
python3 scripts/dc_search.py data/raw/dc_search.jsonl $S 세무냥이 "REDACTED_SUBJECT 리트" "리트 만점" "세무사 만점" "공개검증" "리트 부정행위" 2>>logs/dc_search.log
cat data/raw/dc_search*.jsonl > /tmp/dc_all_urls.jsonl
python3 scripts/dc_post.py /tmp/dc_all_urls.jsonl data/raw/dc_posts.jsonl data/raw/dc_comments.jsonl 2>>logs/dc_post.log
