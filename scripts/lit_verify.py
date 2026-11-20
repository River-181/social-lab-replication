"""서지 검증: 웹 Claude가 준 literature*.jsonl의 인용이 실재하는지 OpenAlex로 대조.
usage: python3 scripts/lit_verify.py out.jsonl data/raw/web_1119/literature*.jsonl
DOI가 있으면 DOI로 조회, 없으면 인용문 검색 상위 1건과 제목 유사도로 판정.
verdict: doi_match / title_match(유사도≥0.6) / weak(0.35~0.6, 사람 확인) / not_found / not_paper(사례 기사). 키 없이 무료 API.
"""
import os, sys, json, re, time, difflib, datetime, urllib.parse, urllib.request

API = "https://api.openalex.org/works"
DOI = re.compile(r"10\.\d{4,9}/[^\s\"'<>,;]+")


def get(url):
    if os.environ.get("OPENALEX_API_KEY"):  # 익명은 크레딧이 적어 429가 난다(11-20). 키는 환경변수로만
        url += ("&" if "?" in url else "?") + "api_key=" + os.environ["OPENALEX_API_KEY"]
    req = urllib.request.Request(url, headers={"User-Agent": "social-lab-litverify"})
    return json.loads(urllib.request.urlopen(req, timeout=30).read())


def norm(s):
    return re.sub(r"[^\w가-힣]+", " ", (s or "").lower()).strip()


def sim(title, citation):
    """OpenAlex 제목이 인용문 안에 얼마나 들어있나(인용문엔 저자·연도가 섞여 있어 부분 일치로 본다)."""
    t, c = norm(title), norm(citation)
    if not t:
        return 0.0
    m = difflib.SequenceMatcher(None, t, c).find_longest_match(0, len(t), 0, len(c))
    return max(m.size / len(t), difflib.SequenceMatcher(None, t, c).ratio())


def verify(d):
    cit = d.get("citation") or d.get("title") or ""
    doi = DOI.search(cit + " " + (d.get("url") or ""))
    if doi:
        try:
            w = get(f"{API}/doi:{urllib.parse.quote(doi.group(0).rstrip('.'))}")
            return "doi_match", w, 1.0
        except Exception:
            pass  # DOI가 틀렸을 수 있음 → 제목 검색으로
    if cit.startswith("[사례]"):
        return "not_paper", None, 0.0  # 사례 기사 묶음은 서지 검증 대상 아님
    t = re.search(r"\(\d{4}[a-z]?\)\.?\s*(.+?)(?:\.\s|\?\s|$)", cit)  # 저자 (연도). 제목. → 제목만
    q = (t.group(1) if t else cit)[:200]
    rs = get(f"{API}?filter=title.search:{urllib.parse.quote(q.replace(',', ' '))}&per-page=5").get("results", []) \
        or get(f"{API}?search={urllib.parse.quote(q)}&per-page=5").get("results", [])
    if not rs:
        return "not_found", None, 0.0
    best = max(rs, key=lambda w: sim(w.get("display_name"), cit))
    s = sim(best.get("display_name"), cit)
    return ("title_match" if s >= 0.6 else "weak" if s >= 0.35 else "not_found"), best, round(s, 2)


if __name__ == "__main__":
    out = open(sys.argv[1], "a")
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    for path in sys.argv[2:]:
        for line in open(path, encoding="utf-8"):
            if not line.strip():
                continue
            d = json.loads(line)
            try:
                v, w, s = verify(d)
            except Exception as e:
                v, w, s = "error", None, 0.0
                print("FAIL", d.get("id"), e, file=sys.stderr)
            out.write(json.dumps({"id": d.get("id"), "citation": d.get("citation"), "verdict": v, "similarity": s,
                                  "openalex_id": w and w.get("id"), "oa_title": w and w.get("display_name"),
                                  "oa_year": w and w.get("publication_year"), "oa_doi": w and w.get("doi"),
                                  "cited_by": w and w.get("cited_by_count"), "source_file": path.split("/")[-1],
                                  "collected_at": now}, ensure_ascii=False) + "\n")
            out.flush()
            time.sleep(0.3)  # OpenAlex 공손한 속도
    assert sim("Robust dynamic classes", "Crane & Sornette (2008) Robust dynamic classes revealed ...") > 0.9
