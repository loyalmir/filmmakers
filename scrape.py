#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
캐스팅 공고 수집기 — 원픽 / 플필
- GitHub Actions에서 주기적으로 실행 → notices.json 저장 → GitHub Pages가 읽음
- 로컬에 저장된 HTML(src/*.html)이 있으면 그걸 쓰고(=오프라인 테스트),
  없으면 실제 사이트를 fetch 한다.
"""
import os, re, json, html as H, datetime, sys

LOCAL = os.path.join(os.path.dirname(__file__), "src")  # 오프라인 테스트용

SOURCES = {
    "onepick": {"name": "원픽",  "type": "platform", "url": "https://www.myonepick.com/audi/list/"},
    "plfil":   {"name": "플필",  "type": "platform", "url": "https://plfil.com/casting"},
}

def get_html(key):
    p = os.path.join(LOCAL, f"{key}.html")
    if os.path.exists(p):
        return open(p, encoding="utf-8").read()
    import urllib.request
    req = urllib.request.Request(SOURCES[key]["url"], headers={"User-Agent": "Mozilla/5.0"})
    return urllib.request.urlopen(req, timeout=20).read().decode("utf-8", "replace")

def txt(s):
    return H.unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", s))).strip()

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
    m = re.search(r"(\d{1,2})\s*~\s*(\d{1,2})\s*세", s)
    if m: return int(m.group(1)), int(m.group(2))
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

def main():
    notices = []
    notices += parse_onepick(get_html("onepick"))
    notices += parse_plfil(get_html("plfil"))
    data = {
        "updatedAt": datetime.datetime.now().astimezone().isoformat(timespec="minutes"),
        "count": len(notices),
        "notices": notices,
    }
    out = os.path.join(os.path.dirname(__file__), "notices.json")
    json.dump(data, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"수집 완료: {len(notices)}건  → {out}")
    by = {}
    for n in notices: by[n["source"]] = by.get(n["source"], 0) + 1
    print("소스별:", by)

if __name__ == "__main__":
    main()
