#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
캐스팅 공고 수집기 — 원픽 / 플필
- GitHub Actions에서 주기적으로 실행 → notices.json 저장 → GitHub Pages가 읽음
- 로컬에 저장된 HTML(src/*.html)이 있으면 그걸 쓰고(=오프라인 테스트),
  없으면 실제 사이트를 fetch 한다.
"""
import os, re, json, html as H, datetime, sys, time

LOCAL = os.path.join(os.path.dirname(__file__), "src")  # 오프라인 테스트용

SOURCES = {
    "onepick": {"name": "원픽",  "type": "platform", "url": "https://www.myonepick.com/audi/list/"},
    "plfil":   {"name": "플필",  "type": "platform", "url": "https://plfil.com/casting"},
}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "ko-KR,ko;q=0.9,en;q=0.8",
}

def get_html(key):
    p = os.path.join(LOCAL, f"{key}.html")
    if os.path.exists(p):
        return open(p, encoding="utf-8").read()
    import urllib.request
    req = urllib.request.Request(SOURCES[key]["url"], headers=HEADERS)
    return urllib.request.urlopen(req, timeout=20).read().decode("utf-8", "replace")

def txt(s):
    return H.unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", s))).strip()

# ---- 마감 지난 공고 거르기 ----
def is_open(due):
    """due 문자열(YYYY-MM-DD)이 오늘 이후면 True. 날짜 못 읽으면 일단 살림."""
    m = re.search(r"(\d{4})-(\d{1,2})-(\d{1,2})", due or "")
    if not m:
        return True
    d = datetime.date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    return d >= datetime.date.today()

# ---- 성별/나이 해석 (공통) ----
def parse_gender(s):
    if "여성" in s or "여자" in s or "여배우" in s: g = "female"
    elif "남성" in s or "남자" in s or "남배우" in s: g = "male"
    else: g = "any"
    # '남녀' / '남자,여자' → any
    if ("남" in s and "여" in s): g = "any"
    return g

def parse_age(s):
    m = re.search(r"(\d{1,2})\s*~\s*(\d{1,2})\s*대", s)
    if m: return int(m.group(1)), int(m.group(2)) + 9
    m = re.search(r"(\d{1,2})\s*대", s)
    if m: lo = int(m.group(1)); return lo, lo + 9
    m = re.search(r"(\d{1,2})\s*세?\s*~\s*(\d{1,2})\s*세", s)   # 21세 ~ 27세 / 21 ~ 27세
    if m: return int(m.group(1)), int(m.group(2))
    m = re.search(r"(\d{1,2})\s*세", s)                          # 단일 'NN세'
    if m: lo = int(m.group(1)); return lo, lo
    return None, None  # 무관/미표기

# ---- 원픽 ----
def parse_onepick(html):
    out = []
    for box in re.findall(r'<div class="audiListBox"[^>]*data-num="(\d+)".*?</div>\s*</div>\s*</div>', html, re.S):
        pass
    for m in re.finditer(r'<div class="audiListBox"[^>]*data-num="(\d+)"(.*?)(?=<div class="audiListBox"|</div>\s*</div>\s*</div>\s*$)', html, re.S):
        num, body = m.group(1), m.group(2)
        title = txt((re.search(r'class="lTitle[^"]*">(.*?)</div>', body, re.S) or [None, ""])[1])
        appels = re.findall(r'class="lAppel[^"]*">(.*?)</div>', body, re.S)
        genre = txt(appels[0]) if appels else ""
        detail = txt(appels[1]) if len(appels) > 1 else ""
        end = txt((re.search(r'class="endDate">(.*?)</div>', body, re.S) or [None, ""])[1])
        if not title:
            continue
        gender = parse_gender(detail + " " + title)
        lo, hi = parse_age(detail)
        out.append({
            "id": f"onepick-{num}", "source": "원픽", "sourceType": "platform",
            "cat": genre.split("|")[-1].strip() if "|" in genre else genre,
            "title": title, "role": detail or genre,
            "gender": gender, "ageMin": lo, "ageMax": hi, "ageText": detail,
            "due": end, "url": f"https://www.myonepick.com/audi/list/",  # 상세경로 라이브 확정 예정
            "email": None, "specials": [],
        })
    return out

# ---- 플필 ----
def parse_plfil(html):
    out = []
    cards = list(re.finditer(r'<a href="(/casting/(\d+))"(.*?)</a>', html, re.S))
    for c in cards:
        url, num, body = c.group(1), c.group(2), c.group(3)
        t = txt(body)
        # 형태: 장르 | 진행중 | 제목 | 페이 : ... | D-x | / | YYYY-MM-DD | 마감 ...
        parts = [p.strip() for p in t.split("|")] if "|" in t else t.split()
        flat = txt(body)
        genre = ""
        for g in ["뮤지컬", "TV/OTT", "영화", "드라마", "연극", "기타", "광고"]:
            if flat.startswith(g) or (" "+g+" ") in (" "+flat[:20]+" "):
                genre = g; break
        title_m = re.search(r"(진행중|마감임박|마감)\s*(.+?)\s*페이", flat)
        title = title_m.group(2).strip() if title_m else ""
        pay_m = re.search(r"페이\s*:\s*([0-9,]+만원(?:\s*~\s*[0-9,]+만원)?)", flat)
        pay = pay_m.group(1) if pay_m else ""
        date_m = re.search(r"(\d{4}-\d{2}-\d{2})", flat)
        due = date_m.group(1) if date_m else ""
        if not title:
            continue
        out.append({
            "id": f"plfil-{num}", "source": "플필", "sourceType": "platform",
            "cat": genre, "title": title, "role": "",
            "gender": parse_gender(title), "ageMin": None, "ageMax": None, "ageText": "",
            "due": due, "url": f"https://plfil.com{url}",
            "email": None, "specials": [], "pay": pay,
        })
    # 중복 제거(같은 num)
    seen = {}; 
    for n in out: seen[n["id"]] = n
    return list(seen.values())

def get_detail(url, num):
    """상세 HTML 가져오기. 오프라인이면 src/plfil_detail_<num>.html 사용."""
    p = os.path.join(LOCAL, f"plfil_detail_{num}.html")
    if os.path.exists(p):
        return open(p, encoding="utf-8").read()
    import urllib.request
    req = urllib.request.Request(url, headers=HEADERS)
    return urllib.request.urlopen(req, timeout=20).read().decode("utf-8", "replace")

def parse_plfil_detail(html):
    """상세페이지에서 배역별 (성별, 나이) 목록 추출."""
    genders = re.findall(r'>성별</p><p[^>]*>(.*?)</p>', html, re.S)
    ages    = re.findall(r'>모집 나이</p><p[^>]*>(.*?)</p>', html, re.S)
    roles = []
    for i in range(max(len(genders), len(ages))):
        g = txt(genders[i]) if i < len(genders) else ""
        a = txt(ages[i]) if i < len(ages) else ""
        lo, hi = parse_age(a)
        roles.append({"gender": parse_gender(g), "ageMin": lo, "ageMax": hi, "ageText": (g + " · " + a).strip(" ·")})
    return roles

def enrich_plfil(notices):
    """플필 공고에 상세페이지 성별·나이를 채워 정확도 향상."""
    for n in notices:
        if n.get("source") != "플필":
            continue
        num = n["id"].split("-")[-1]
        try:
            roles = parse_plfil_detail(get_detail(n["url"], num))
        except Exception as e:
            print(f"  상세 보강 실패 {num}: {e}"); continue
        if not roles:
            continue
        non_female = [r for r in roles if r["gender"] != "female"]
        pick = (non_female or roles)[0]
        n["gender"]  = pick["gender"]
        n["ageMin"]  = pick["ageMin"]
        n["ageMax"]  = pick["ageMax"]
        n["ageText"] = pick["ageText"]
        if len(roles) > 1:
            n["ageText"] += f" 외 {len(roles)-1}개 배역"
        time.sleep(0.4)
    return notices

def main():
    raw = []
    raw += parse_onepick(get_html("onepick"))
    raw += parse_plfil(get_html("plfil"))
    raw = enrich_plfil(raw)            # 플필 상세에서 성별·나이 정확히 보강
    # 마감 지난 공고 제외
    notices = [n for n in raw if is_open(n.get("due", ""))]
    dropped = len(raw) - len(notices)
    data = {
        "updatedAt": datetime.datetime.now().astimezone().isoformat(timespec="minutes"),
        "count": len(notices),
        "notices": notices,
    }
    out = os.path.join(os.path.dirname(__file__), "notices.json")
    json.dump(data, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"수집 완료: {len(notices)}건 (마감 제외 {dropped}건)  → {out}")
    by = {}
    for n in notices: by[n["source"]] = by.get(n["source"], 0) + 1
    print("소스별:", by)

if __name__ == "__main__":
    main()
