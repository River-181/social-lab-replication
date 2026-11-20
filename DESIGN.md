# 디자인 철학과 시스템 (DESIGN.md) — v2 (2026-11-20)

> social-lab의 모든 시각 산출물(findings 그림, 포스터, 로드맵, 볼트 노트 도판)이 따르는 기준. 코드판은 `scripts/analysis/lab_style.py`.
> 레퍼런스 표(§6)의 URL은 2026-11-20에 실제로 열어 내용을 확인한 것만 올렸다. 열지 못한 것은 §6.3에 따로 적었다.

## 0. 출발점 — 지금 그림의 문제 (2026-11-20 점검)

findings 그림 4장(RQ1 확산곡선, RQ3 히트맵 등)을 보고 확인한 것.

- **사망 국면이 가장 붉고 가장 어둡다.** RQ1 배경 띠는 사망 구간이 진한 분홍~회색이고, RQ3 히트맵(YlOrRd)은 사망 행의 F04 칸이 가장 붉다. 결과적으로 사람이 죽은 자리가 그림에서 제일 '뜨거운' 지점으로 읽힌다.
- **범위 문장·자료 등급이 그림 밖(md)에만 있다.** 그림만 떼어 포스터나 볼트에 붙이면 "공개 온라인 담론에 한정"이라는 단서가 사라진다.
- **제목이 설명문이다**("시간별(KST 1h) 게시량 — symlog축, 점선=…"). 주장이 없고 범례 설명이 제목에 들어가 있다.
- **결손 구간이 데이터 0과 같은 모양이다.** RQ1에서 "디시 14시 이전 통합검색분 없음"이 부제로만 적혀 있고, 그림에서는 낮은 막대와 구별되지 않는다.
- 폰트는 AppleGothic, 기본 matplotlib 색(tab10)과 흰 바탕, 사방 테두리를 썼다.

## 1. 디자인 철학 — 7원칙

각 원칙 끝의 [R#]은 §6 레퍼런스 번호.

**P1. 사람이 죽었다. 그림은 그 사실 앞에서 조용해야 한다.**
사망은 경고색(빨강)이나 가장 진한 면적, 폭발 아이콘, 카운트다운으로 그리지 않는다. 먹색 얇은 선과 빈 띠로 표시하고, 그 시점부터는 그림의 소리를 낮춘다. 보도준칙 4.0은 "자살 사건과 관련한 시각 자료 사용을 자제"하고 "자살 장소, 방법, 도구 … 자살을 암시하는 자료 등은 사용하지 않"는다고 정하고, 블로그·SNS 같은 1인 미디어에도 같은 기준을 요구한다. 우리 산출물도 그 범위에 든다. [R10, R11, R12]

**P2. 고인을 점 하나로 환원하지 않는다. 숫자는 사람들의 행동을 센 것이다.**
우리가 세는 것은 군중의 글·영상·채팅이지 고인이 아니다. 고인을 그래프의 표적(과녁, 중심 노드, 빨간 점)으로 그리지 않는다. 네트워크 그림에서 고인 노드는 빼거나 이름 없는 빈 원으로 둔다. 경향신문 「1748번의 죽음의 기록」과 Periscopic의 'stolen years'는 반대 방향, 곧 개인을 하나하나 기억하는 방식의 예다. 우리 연구는 당사자가 한 명이라 그 방식을 쓰지 않는다. 대신 숫자 뒤에 있는 것이 사람의 행동이라는 점을 주석으로 드러낸다. [R7, R17, R16]

**P3. 주석이 본문이다.**
그림 하나만 떼어 가도 거짓말이 되지 않아야 한다. 모든 그림은 ①주장형 제목 ②범위 문장 요지 ③자료 등급 ④탐색/확증 ⑤재현 스크립트 ⑥**한계 한 줄**(v2: `annotate_scope(…, limits=…)`, Anthropic 해석가능성 논문이 본문에 한계를 반복 적는 방식 [AI-a2])을 그림 안에 담는다(`annotate_scope`). 포스터와 findings에는 "그림 언어: DESIGN.md vN · 결정: 누구"를 기여 명세에 적는다 [AI-a7]. 핵심 사건은 범례 번호가 아니라 그 자리에 직접 글로 단다. OWID는 "모든 차트에 데이터 출처를 분명히 표시하고, 원자료를 바꾼 경우 그 사실도 표시한다". Wilke는 제목이 그림의 주장을 말해야 한다고 쓴다. [R4, R14, R5]

**P4. 불확실성은 숨기지 않고 그린다.**
점추정만 그리지 않는다. 비율에는 부트스트랩 95% 띠나 구간을 붙이고, 무엇의 구간인지 밝힌다. 결손은 0이 아니라 빗금으로 칠한다. 코더 일치도(κ)가 낮은 축에는 그 값을 축 옆에 적는다. v2: 결과가 뒤집히는 민감도 조건은 **우선해서** 작은 그림으로 함께 싣는다. Google은 다수 선호와 반대인 "강한 소수"의 결과도 본문에 남겼다 [AI-g7]. NYT 니들 팀의 말대로 흔들림을 끄면 "불확실성을 숨길 뿐 사라지게 하지는 않는다". Lupi의 원칙도 "데이터는 불완전하다는 것을 기억하라"다. [R2, R19, R7]

**P5. 지각 정확도가 높은 인코딩을 먼저 쓴다.**
공통 축 위의 위치 > 길이 > 각도·면적 > 색 농도. 국면별 비율 비교는 히트맵(색 농도)보다 점 그림(dot plot)과 구간 막대로 그린다. 히트맵은 전체 패턴을 훑어보는 보조 그림으로만 쓴다. v2: 색(국면색 포함)이 혼자 의미를 지지 않게 하고, 늘 직접 레이블을 함께 쓴다. 표지만으로는 무엇을 하는지 전달되지 않았다는 Google 스파클 아이콘 연구가 근거다 [AI-g8]. 차트 종류는 FT Visual Vocabulary의 관계 분류(시간 변화·분포·순위·흐름)로 고른다. [R1, R18]

**P6. 데이터 잉크는 줄이되, 읽기 쉬움은 줄이지 않는다.**
테두리, 사방 격자, 3D, 그림자를 지운다. 다만 축 레이블과 단위, 직접 레이블처럼 읽기를 돕는 잉크는 남긴다. ScienceUX가 말하는 '골디락스' 균형이다. 흑백으로 바꿔 봐도 읽혀야 한다. [R15, R3]

**P8. 규칙은 문장이 아니라 검사로 지킨다.** *(v2 신설)*
금지 목록은 읽고 지키는 문서로 두면 언젠가 어긋난다. 그래서 `lab_style.check(fig)`가 저장 직전에 다음을 막는다: 빨강 마크, 금지 색표, 범위 문장 누락, 이중 축, 이모지, 카운트다운 문구, 사망 국면 면 채우기. 사람 눈 검수(라벨 충돌·맥락)는 그대로 남는다. 근거: AI 연구소 4곳이 모두 디자인 판단을 채점 기준과 평가로 형식화한다. Anthropic은 디자인 시스템을 모델이 읽고 검사하게 만든다. [AI-a4, AI-a8, AI-o7, AI-g6]

**P7. 포스터는 발견 하나, 방법은 투명하게.**
포스터 가운데에는 쉬운 말로 쓴 주 발견 한 문장을 둔다(#betterposter). 양옆 막대에는 방법·범위·한계를 그대로 싣는다. 한계(VALIDITY의 ❌·🟡)를 작게 줄이지 않는다. 무거운 주제라 장식, 사진, 캐릭터, 밈 이미지는 쓰지 않는다. [R8, R9, R20]

## 2. 금지 목록

1. 고인의 사진·얼굴·실루엣·방송 캡처·유서·발견 장소를 연상시키는 이미지 (보도준칙 4.0 원칙 2-3)
2. 사망 시점을 빨강·경고 아이콘·해골·십자가·불꽃·폭발 기호로 표시하는 것
3. "죽음까지 N시간" 같은 카운트다운형 시각화 (실종→사망 구간을 서스펜스로 만든다)
4. 고인을 네트워크 중심 노드·과녁·빨간 점으로 그리는 것. 비난 대상 그림에서 고인은 회색 레이블로만 둔다
5. 혐오 댓글 원문을 큰 글씨로 인용해 장식으로 쓰는 것(인용은 작게, 필요한 만큼, 출처 등급과 함께)
6. 레인보우·jet 색표, 빨강-초록 대비, 8개를 넘는 범주 색 (§3)
7. 결손 구간을 0이나 빈칸으로 두는 것 (빗금 `NODATA`로 칠한다)
8. 범위 문장 없는 그림 반출, C등급·질적 자료로 그린 수치 그래프
9. 3D, 그림자, 그라디언트 막대, 이중 y축(불가피하면 두 패널로 나눈다)
10. 이모지

**도움 정보**: 볼트 공개 노트와 포스터 하단에는 보도준칙 4.0 원칙 4의 도움 정보 한 줄을 넣는다. "자살예방 상담전화 ☎109, SNS상담 마들랜" (문구는 [R10] 원문 그대로).

## 3. 색

### 3.1 국면 7색 (`PHASE_COLORS`)

| 국면 | 색 | HEX | 의도 |
|---|---|---|---|
| 세무냥이 | 슬레이트 | `#A3AEBA` | 전사(前史). 차갑고 옅게 |
| 의혹 | 황토 | `#D9A441` | 주목이 데워진다 |
| 고발 | 번트 오렌지 | `#B8693A` | 열이 오른다(빨강까지 가지 않음) |
| 검증 | 자두 | `#8E4D7D` | 생중계 스펙터클. 분노와 구경이 섞인 탁한 보라 |
| 실종 | 인디고 | `#4F5A99` | 차가워짐, 불안 |
| 사망 | 먹 | `#2B2B2B` | **애도·정지. 면을 칠하지 않고 경계 먹선만** |
| 사후 | 세이지 | `#6E8B74` | 가라앉음, 책임 공방 |

- **사망을 빨강으로 소비하지 않는 방법**: (기본) 먹색 경계선 두 줄 + 빈 띠. `phase_bands()`가 자동으로 이렇게 그린다. (대안 A) 사망 이후 모든 계열의 채도를 40%로 낮추는 '소등' 처리. 포스터 큰 그림에 쓴다. (대안 B) 사망 시점에 세로선 하나와 작은 글자 "11/19 13:12 발견"만 둔다. 타임라인·로드맵에 쓴다. 빨강 계열(`#C00`~`#F44` 근방)은 팔레트에 아예 없다.
- **배경 띠 농도**: `BAND_ALPHA = 0.14`. 데이터 선보다 항상 옅게 둔다.
- **색각이상 검증값** (Machado 2009 시뮬레이션, severity 1.0, 7색 중 가장 가까운 쌍의 CIE76 ΔE, `python3 scripts/analysis/lab_style.py`로 재현):

| 시각 | 최소 ΔE | 가장 가까운 쌍 |
|---|---|---|
| 정상 | 26.4 | 세무냥이–사후 |
| 적색맹(protan) | 14.9 | 검증–실종 |
| 녹색맹(deutan) | 22.2 | 세무냥이–사후 |
| 청색맹(tritan) | 16.9 | 세무냥이–사후 |

기준은 ΔE ≥ 10(작은 선에서도 구분되는 보수적 하한)이며 스크립트가 assert로 막는다. 가장 가까운 쌍인 세무냥이–사후는 시간상 양 끝이라 서로 붙어 나올 일이 없다. 검증–실종은 붙어 있으므로 두 국면 사이에는 늘 경계선이나 직접 레이블을 둔다. 처음 고른 세무냥이 `#8C9BAB`는 청색맹에서 ΔE 9.7로 기준을 넘지 못해 밝게 바꿨다.

### 3.2 중립·기능색

| 이름 | HEX | 용도 |
|---|---|---|
| PAPER | `#FAF9F6` | 바탕. 따뜻한 미색(순백보다 눈부심이 덜하다) |
| INK | `#1F1F1F` | 제목, 핵심 숫자 |
| TEXT | `#4A4A4A` | 축 레이블, 본문 |
| MUTED | `#8A8A8A` | 범위 문장, 출처, 보조 주석 |
| GRID | `#E4E2DD` | 격자(축 글자보다 옅게. Datawrapper 회색 위계) |
| NODATA | `#C9C6BF` | 결손 빗금 `///` |
| ACCENT | `#2F5D8A` | 국면과 무관한 단일 계열 강조 1색 |

- 연속값(히트맵)은 단색 순차 팔레트(`Greys` 또는 `Blues`)를 쓴다. `YlOrRd`처럼 빨강으로 끝나는 팔레트는 금지다.
- 발산값(증감)은 `PuOr`. 빨강-초록 대비를 피한다(Wilke). [R3]
- 플랫폼 계열(유튜브·디시·판·기사)을 색으로 나눠야 하면 Okabe-Ito의 하위 집합(`#0072B2` 파랑, `#E69F00` 주황, `#009E73` 청록, `#CC79A7` 자주)을 쓴다. 빨간 주홍 `#D55E00`은 뺀다. 4개를 넘으면 직접 레이블로 나눈다. [R3, R22]

## 4. 타이포그래피

`fc-list :lang=ko family`와 `~/Library/Fonts`로 확인한 결과 (2026-11-20):

| 폰트 | 설치 | 판정 |
|---|---|---|
| **Pretendard** (Thin~Black 9굵기, `~/Library/Fonts`) | 있음, matplotlib 인식 | **기본.** 숫자가 또렷하고 굵기가 많다 |
| Apple SD Gothic Neo | 시스템 | 대체 1순위(Pretendard가 없는 기계) |
| AppleGothic | 시스템 | 대체 2순위. 기존 그림이 쓰던 폰트. 굵기가 하나뿐이라 위계를 만들 수 없다 |
| AppleMyungjo | 시스템 | 본문용 아님. 포스터 인용구에만 쓸 수 있다 |
| Noto Sans KR, 나눔 | 없음 | — |

`lab_style.use()`가 Pretendard → Apple SD Gothic Neo → AppleGothic 순으로 자동 선택한다.

**위계 (paper 기준 pt. poster는 2.2배)**

| 요소 | 크기 | 굵기 | 색 |
|---|---|---|---|
| 제목(주장 한 문장) | 12 | SemiBold | INK, 왼쪽 정렬 |
| 축 레이블 | 9.5 | Regular | TEXT |
| 눈금 | 9 | Regular | TEXT |
| 직접 주석 | 8.5 | Regular | TEXT |
| 범위 문장·출처 | 8 | Regular | MUTED |
| 국면 이름 | 8 | Regular | 국면색 |

Thin·Light 굵기는 쓰지 않는다(작은 크기에서 흐려진다, [R6]). 강조는 굵기와 INK색으로 하고 색을 늘려 강조하지 않는다.

## 5. 규격과 차트 규칙

### 5.1 그림 규격

| 용도 | 크기 | 비고 |
|---|---|---|
| findings·볼트 단일 그림 | 7.2 × 3.6~4.5 in, 200 dpi | 볼트에서 폭 100%로 읽힌다 |
| findings 2단 비교 | 7.2 × 6 in (2행) | 패널마다 제목, 범위 문장은 그림 전체에 1번 |
| 포스터 | **A0 세로 841 × 1189 mm** | ICWSM 2026 보드는 30×40 in(762×1016 mm). 그 학회에 내면 그 크기에 맞춘다 [R20] |
| 포스터 그림 폭 | 1단 그림 ≈ 250 mm, 중앙 큰 그림 ≈ 760 mm | `use('poster')` 후 그 폭에 맞춰 figsize를 잡는다 |
| 포스터 최소 글자 | 본문 24 pt, 그림 안 글자 ≥ 18 pt, 주 발견 ≥ 90 pt | 2 m 거리에서 읽히는 하한 |

**포스터 배치** (#betterposter 세로판 변형): 위쪽 1/3에 주 발견 한 문장(쉬운 말), 그 아래 중앙에 핵심 그림 1장(RQ1 확산 + 국면 띠), 아래쪽 2단에 방법·결과 ②~④·한계, 맨 아래에 QR(저장소), 범위 문장, 도움 정보 한 줄. 칸 내용은 `poster/outline.md`를 따른다. [R8, R9]

### 5.2 차트 규칙

- **축**: 위·오른쪽 테두리를 없애고 y 격자만 둔다. 단위를 반드시 적는다(건/시간, %). 로그·symlog 축은 축 레이블에 "(로그)"를 적는다.
- **시간 축**: KST 표기. 국면 띠는 `phase_bands()`로 그리고, 커뮤니티 기준 의혹 시작(11/14 00:00)처럼 국면 정의가 둘인 곳은 점선 + 직접 레이블로 표시한다.
- **주석**: 핵심 사건 3~6개만 직접 글로 단다. 나머지 사건은 옅은 회색 틱으로 남기고 개수를 범위 문장에 적는다. 범례는 직접 레이블이 불가능할 때만 쓴다.
- **범위 문장 위치**: 그림 아래 왼쪽(`annotate_scope`). 형식은 `[탐색|확증 | 자료 A·B] 범위 요지. / 재현: 스크립트 경로`.
- **자료 등급**: 범위 문장 앞 대괄호에 둔다. 계열마다 등급이 다르면 범례나 직접 레이블 끝에 `(A)`, `(B)`를 붙인다. C등급은 그림에 수치 축을 그리지 않는다.
- **불확실성 띠**: 계열색 alpha 0.18, 테두리 없음. 범례에 "95% 부트스트랩 구간"처럼 무엇의 구간인지 적는다. 비율 비교는 점 + 오차막대로 그린다(Wilke: 겹침으로 차이를 판단하지 말 것. 차이의 CI를 따로 계산한다). [R2]
- **결손**: `NODATA` 빗금 + "수집 전(결손)" 같은 글. 0과 구별돼야 한다.
- **κ 표기**: 코딩 기반 그림(RQ3·RQ10)은 축 옆이나 부제에 "frame κ=0.52(skeptic 대비)"를 적는다.
- **민감도**: 본 그림 옆에 작은 그림(small multiple)으로 둔다. unclear 포함/제외처럼 둘 다 보여 준다.
- **크기 비교**: 면적·원 크기 대신 길이를 쓴다. Hawkes 같은 모형 그림에는 적합선과 실측을 같은 축에 둔다. [R18]

## 6. 레퍼런스

### 6.1 표 (열어서 확인한 것: 22건)

| # | 레퍼런스 | URL | 배울 기법 | 적용처 |
|---|---|---|---|---|
| R1 | FT Visual Vocabulary (chart-doctor) | https://github.com/Financial-Times/chart-doctor/tree/main/visual-vocabulary | 관계 9분류로 차트를 고른다(시간 변화, 분포, 순위, 흐름…) | 모든 findings 그림의 차트 선택 |
| R2 | Wilke, *Fundamentals of Data Visualization* — Visualizing uncertainty | https://clauswilke.com/dataviz/visualizing-uncertainty.html | 구간이 무엇인지 반드시 명시. 단계형 오차막대. 겹침으로 차이를 판단하지 않는다 | RQ3·RQ10 비율 그림, RQ7 적합 띠 |
| R3 | Wilke — Common pitfalls of color use | https://clauswilke.com/dataviz/color-pitfalls.html | Okabe-Ito 8색. 8범주를 넘으면 직접 레이블. 레인보우 금지. CVD 시뮬레이션 | 팔레트 §3 |
| R4 | Wilke — Titles, captions, and tables | https://clauswilke.com/dataviz/figure-titles-captions.html | 제목은 주장 한 문장. 캡션 끝에 출처. 단위를 적는다 | 제목 규칙, `annotate_scope` |
| R5 | Datawrapper — Colors for data vis style guides | https://www.datawrapper.de/blog/colors-for-data-vis-style-guides | 회색이 가장 중요한 색. 격자 < 축 글자 < 제목 순의 회색 위계. 강조색 1개 | GRID·TEXT·INK 위계, ACCENT |
| R6 | Datawrapper — Fonts for data visualization | https://www.datawrapper.de/blog/fonts-for-data-visualization | 고정폭(tabular) 숫자. 12px 미만 금지. 얇은 굵기 금지. 굵게는 제목과 핵심 숫자만 | 타이포 §4 |
| R7 | Giorgia Lupi, Data Humanism manifesto | http://giorgialupi.com/data-humanism-my-manifesto-for-a-new-data-world | "데이터는 불완전하다", 불확실성을 보여라, 맥락을 끼워 넣어라, 숫자 뒤 사람 | P2·P4, 볼트 노트 도판 |
| R8 | betterposter.org (포스터 생성기) | https://www.betterposter.org/ | 중앙 패널 + 좌우 사이드바 + QR 구성, 중앙/측면 비율 | 포스터 배치 |
| R9 | s-ink, Betterposter template | https://s-ink.org/betterposter-poster-template | 쉬운 말 주 발견을 큰 글씨로. CVD·흑백 대응 템플릿 | 포스터 상단 1/3 |
| R10 | 한국기자협회, 자살예방 보도준칙 4.0 | https://www.journalist.or.kr/news/section4.html?p_num=12 | 시각 자료 자제(원칙 2-3 ㉮㉯), 1인 미디어 적용, 도움 정보 문구 | P1, 금지 1~3, 도움 정보 줄 |
| R11 | 한국언론진흥재단, 자살예방 보도준칙 4.0 | https://www.kpf.or.kr/front/board/boardContentsView.do?board_id=291&contents_id=00022D741E6939F8807EFED72CD46BA3 | 원칙 3: 고인의 인격을 "살아있는 사람처럼 보호", 유서 미보도 | P2, 금지 1·4 |
| R12 | WHO, *Preventing suicide: a resource for media professionals* (2023 update) 소개 페이지 | https://www.who.int/publications/i/item/9789240076846 | 사진·영상 제작자도 대상. 위기를 극복한 이야기를 앞세우라 | P1 근거(세부 시각 조항은 PDF 접근 실패, §6.3) |
| R13 | The Pudding — How to make dope shit, part 3 | https://pudding.cool/process/how-to-make-dope-shit-part-3/ | 구체적 앵커 하나로 시작. 쉬운 핵심은 먼저 말한다. 섹션당 그림 하나 | 볼트 노트 구성, 포스터 결과 칸 |
| R14 | Our World in Data FAQ | https://ourworldindata.org/faqs | 모든 차트에 출처와 원자료 변형(합산·환산) 여부를 표시 | `annotate_scope`의 재현 줄 |
| R15 | ScienceUX — Minimalist data viz aren't necessarily ideal | https://scienceux.org/articles/data-ink-ideal-vs-minimal | 데이터 잉크의 골디락스 균형. 흑백 변환으로 점검 | P6 |
| R16 | Periscopic, U.S. Gun Deaths | https://guns.periscopic.com/ | 개인을 생애 호로 그리는 'stolen years', 출처·방법 링크 | P2의 대조 사례(우리는 쓰지 않는 방식) |
| R17 | 경향신문, 매일 김용균이 있었다 — 1748번의 죽음의 기록 | https://www.khan.co.kr/kh_storytelling/2019/labordeath/ | 사망자를 아이콘 하나씩, 가명 처리, 출처·기간·제외 범위(질병사·미신고)를 본문에 명시 | P2·P3, 범위 문장 작성법 |
| R18 | Cleveland & McGill (1984), Graphical Perception, JASA 79 | https://math.pku.edu.cn/teachers/xirb/Courses/biostatistics/Biostatistics2016/GraphicalPerception_Jasa1984.pdf | 기초 지각 과제 10종, 위치 > 길이 > 각도·면적 > 색. 점 그림 대안 | P5, 히트맵을 점 그림으로 바꾸기 |
| R19 | Reuters Institute — How NYT guided readers through an uncertain election | https://reutersinstitute.politics.ox.ac.uk/news/moving-needle-how-new-york-times-aims-guide-readers-through-americas-most-uncertain-election | 그래픽 옆에 기자 해설 모듈을 둔다. 확신이 설 때만 추정치를 게시 | P4, RQ9 조기경보 그림(사후 vs 실시간 구분) |
| R20 | ICWSM 2026 Presenter Guidelines | https://www.icwsm.org/2026/presenter-guidelines.html | 보드 30×40 in, 가로·세로 자유 | 포스터 규격 |
| R21 | 뉴스타파 데이터 저널리즘 프로젝트 | https://newstapa.org/projects/data | 원자료 공개(데이터포털), 건수·제외 기준을 기사 첫머리에 적는다 | 재현 줄, GitHub 공개 칸 |
| R22 | Okabe & Ito, Color Universal Design (jfly) | https://jfly.uni-koeln.de/color/ | 주홍·청록·자주·하늘색 등 색각이상 배리어프리 팔레트의 원 출처 | §3.2 플랫폼 색 |

참고(확인함, 표 밖): Tufte 데이터 잉크 정의와 5원칙 요약 https://jtr13.github.io/cc19/tuftes-principles-of-data-ink.html (2차 요약이므로 인용은 원서로 한다). Reuters Graphics style 저장소 https://github.com/reuters-graphics/style 는 2024-12 보관 처리됐고 페이지에 색·폰트 규정이 보이지 않아 기법 출처로 쓰지 않았다.

### 6.2 우리 산출물별 적용 요약

| 산출물 | 핵심 레퍼런스 | 바꿀 것 |
|---|---|---|
| RQ1 확산곡선 | R1, R4, R5, R2 | 주장형 제목, 사망 띠 비움, 결손 빗금, 사건 직접 주석 |
| RQ3 프레임 히트맵 | R18, R3, R2 | YlOrRd → 국면 내 비율 점 그림 + CI(히트맵은 Greys 보조) |
| RQ9 조기경보 | R19, R2 | "사후 판정 vs 실시간 가능"을 두 패널로 분리, 문턱값 불확실성 |
| RQ10 비난 이동 | P2, R11 | 고인을 중심 노드에서 빼고 회색 레이블로 |
| 포스터 | R8, R9, R20, R10 | 주 발견 1문장, 한계 칸 축소 금지, 도움 정보 줄 |
| 로드맵·타임라인 | R17, P1 대안 B | 사망은 세로선 하나 + 작은 글자 |
| 볼트 노트 | R13, R7 | 섹션당 그림 하나, 그림 아래 범위 문장 |

### 6.3 찾았지만 확인하지 못한 것 (근거로 쓰지 않음)

- WHO 2023 지침 PDF 본문(iris.who.int, 403). 시각 요소의 세부 Do/Don't는 원문을 확인한 뒤에 추가한다.
- *Data Feminism* 3장의 Periscopic 논쟁(감정 vs 중립, MIT Press 403). 검색 요약만 봤다.
- NYT 니들 원문과 FlowingData 해설(403). "끄면 불확실성을 숨길 뿐"이라는 인용은 검색 요약을 통해서만 봤으므로 P4에서는 보조 근거다.
- Mike Morrison 원 템플릿(OSF ef53g / g6xsm)과 Astrobites 해설(403).
- 일본: NHK クローズアップ現代+ 「ネット炎上追跡500日」(nhk.or.jp 접근 차단), 朝日新聞 데이터 기사. 확인한 일본 시각화 레퍼런스는 **0건**이다. 다음 리서치 과제로 남긴다.
- 한겨레 데이터 기사: 이번 검색에서 해당 작업을 찾지 못했다.
- ICWSM·IC2S2 실제 포스터 PDF: 수상작 제목(IC2S2 2024 "Big Tech dominance despite global mistrust")만 확인했다. 포스터 파일은 Zenodo·OSF에서 다시 찾아야 한다.
- Paul Tol 팔레트 페이지(DNS 실패).


## 7. AI 연구소에서 가져온 것 (v2, 2026-11-20)

Google·OpenAI·Anthropic·xAI가 디자인 철학을 프론트엔드(보이는 것)·백엔드(시스템·조직)·과정(결정·검수)에서 어떻게 지키는지 조사했다. 근거는 1차 출처 45건(검증 39건, skeptic 10건 표본 재확인 오류 1건 강등) + Grok(X 발언) 교차. 전문: `poster/design_research/claude_report.md`, `refs.jsonl`(번호 [AI-xN]이 refs의 약칭), `skeptic_check.md`, 볼트 「2026-11-20 AI 연구소 디자인 철학 연구」.

| 가져온 것 | 우리 원칙 | 근거 연구소 |
|---|---|---|
| 디자인 규칙을 자동 검사로 | P8 신설 | Anthropic(시스템을 모델이 읽고 검사, 미감 채점), OpenAI(content designer eval), Google(Model UX) |
| 그림마다 한계 한 줄 | P3 ⑥ | Anthropic 해석가능성 논문 |
| 그림 디자인 언어의 기여 명세 | P3 | Anthropic 논문 저자 기여 절 |
| 뒤집히는 결과 우선 공개 | P4 | Google M3 Expressive 연구 |
| 색만으로 의미 전달 금지, 직접 레이블 | P5 | Google 스파클 아이콘 연구, OpenAI "의미 보존" |

| 덜어내기 — 여러 안을 만들고 하나만 낸다 | P6 | OpenAI 제품 디자인(Lenny's Podcast "Just do less", 부분 확인) |
| 포스터·그림은 시안보다 실제 데이터 렌더로 먼저 | P7 | Anthropic 제품 디자인 책임자 IDEO 인터뷰 "code-first, prototype-first" |
| 에이전트로 탐색 폭을 넓히고 마감은 사람이 | 과정 | xAI 「Designing Grok Bot with Grok Bot」 — 우리 생성 → skeptic 검수 구조와 같은 방향 |

**가져오지 않은 것**: 대규모 사용자 연구로 디자인 결정(Google)은 우리 규모에 맞지 않는다. 경쟁 수치 중심의 발표 문법(xAI)은 민감 주제와 맞지 않는다.

## 변경 기록

- v1 (2026-11-20): 원칙 7·레퍼런스 22(데이터 저널리즘·보도준칙).
- v2 (2026-11-20): P8 신설(`lab_style.check`), P3 한계 슬롯·기여 명세, P4 뒤집히는 결과 우선, P5 직접 레이블 의무화, §7 추가. 근거 AI 연구소 4곳 조사(Claude 1차 출처 + Grok 교차, Grok 새 주장 9건 중 확인 2·부분 7).
