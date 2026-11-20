#!/bin/zsh
# 주기 스냅샷(launchd com.river.sociallab.snapshot): 메타 재수집 → 적재 → git push
cd ~/social-lab || exit 1
PY=/Library/Frameworks/Python.framework/Versions/3.13/bin/python3
find .lock -maxdepth 0 -mmin +720 -exec rmdir {} \; 2>/dev/null  # 세션이 죽어 남은 12시간 넘은 잠금은 버린다(11-19 사고)
if mkdir .lock 2>/dev/null; then
  trap 'rmdir .lock' EXIT
else
  # 긴 유튜브 수집(댓글·검색)이 잠금을 쥐고 있으면 스냅샷 동안만 일시정지했다가 이어 간다(11-20: 댓글이 하루 종일 스냅샷을 막음)
  P=$(pgrep -f "^[^ ]*[Pp]ython[^ ]* scripts/yt_(comments|search)\.py" | head -1)  # 감싼 zsh가 아니라 python 본체
  [ -n "$P" ] || { echo "$(date) skip: already running"; exit 0; }
  kill -STOP $P && trap "kill -CONT $P" EXIT && echo "$(date) paused pid $P for snapshot"
fi
echo "== $(date)"
$PY scripts/yt_meta.py data/raw/ids_all.txt data/raw/yt_snapshots.jsonl
$PY scripts/yt_livechat.py data/raw/yt_snapshots.jsonl
$PY scripts/ingest.py
$PY scripts/audit.py >/dev/null
git add data/raw data/MANIFEST.sha256 findings/_coverage.md && git commit -qm "data: snapshot $(date +%y%m%d-%H%M)" && git push -q
