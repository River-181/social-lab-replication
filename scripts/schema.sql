-- 연구실 단일 DB. 원자료는 data/raw/*.jsonl(불변), DB는 언제든 재적재 가능한 파생물.
CREATE TABLE IF NOT EXISTS items (          -- 영상·기사·커뮤니티 글 한 건
  item_id TEXT PRIMARY KEY,                 -- yt_<id> | news_<sha1> | post_<sha1>
  source_type TEXT,                         -- youtube_video | youtube_live | shorts | news | community_post
  platform TEXT, url TEXT, title TEXT, author TEXT, author_id TEXT,
  published_at TEXT,                        -- KST ISO
  phase TEXT,                               -- 세무냥이|의혹|고발|검증|실종|사망|사후 (codebook.md)
  description TEXT, extra TEXT              -- extra = JSON
);
CREATE TABLE IF NOT EXISTS snapshots (      -- 같은 item을 여러 번 찍은 수치 → 확산 곡선
  item_id TEXT, collected_at TEXT, views INT, likes INT, comment_count INT,
  followers INT, status TEXT,               -- live | deleted | private | error
  PRIMARY KEY (item_id, collected_at)
);
CREATE TABLE IF NOT EXISTS comments (
  comment_id TEXT PRIMARY KEY, item_id TEXT, parent_id TEXT,
  author TEXT, author_id TEXT, text TEXT, likes INT,
  published_at TEXT, collected_at TEXT
);
CREATE TABLE IF NOT EXISTS codes (          -- 코더 에이전트·사람의 라벨. 여러 코더 병존(신뢰도 측정)
  target_id TEXT, coder TEXT, frame TEXT, stance TEXT, emotion TEXT,
  target_of_blame TEXT, note TEXT, coded_at TEXT,
  PRIMARY KEY (target_id, coder)
);
CREATE TABLE IF NOT EXISTS events (         -- 사건 타임라인(사실 단위)
  ts TEXT, phase TEXT, event TEXT, source_url TEXT
);

-- 생방송 다시보기 채팅(슈퍼챗 포함). paid = 표시 금액 원문('₩10,000'), 없으면 NULL
CREATE TABLE IF NOT EXISTS chats (
  chat_id TEXT PRIMARY KEY, item_id TEXT, ts TEXT, offset_ms INTEGER,
  author TEXT, author_id TEXT, text TEXT, kind TEXT, paid TEXT
);
