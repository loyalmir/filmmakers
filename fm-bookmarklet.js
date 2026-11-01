/* 필름메이커스 → 캐스팅 슬레이트 가져오기 (북마클릿 원본)
 * - 사용자가 직접 열어둔 필름메이커스 화면에 보이는 공고만 읽어서 앱으로 넘긴다 (자동 수집 아님)
 * - 목록 페이지: 화면의 공고 카드 전부 / 상세 페이지: 그 공고 1건 + 보이는 메일 주소
 * - 상세 페이지 메일은 "연락처 보기"를 눌러 화면에 보일 때만 잡힌다
 * - index.html의 FM_BOOKMARKLET은 이 파일을 한 줄로 줄인 것
 */
(function () {
  var APP = "https://loyalmir.github.io/filmmakers/";
  if (!/filmmakers\.co\.kr/.test(location.host)) { alert("필름메이커스 배우모집 화면에서 눌러주세요"); return; }
  function T(el) { return el ? el.textContent.replace(/\s+/g, " ").trim() : ""; }
  function fields(box) {
    var o = {};
    box.querySelectorAll("div").forEach(function (d) {
      var k = d.children;
      if (k.length === 2 && !k[0].children.length && !k[1].children.length) {
        var key = T(k[0]); if (key && key.length <= 6 && !(key in o)) o[key] = T(k[1]);
      }
    });
    return o;
  }
  function ymd(s) { /* '11월 14일' → 2026-11-14 */
    var q = (s || "").match(/(\d{1,2})\s*월\s*(\d{1,2})\s*일/); if (!q) return (s || "").trim();
    var now = new Date(), y = now.getFullYear(); if (+q[1] < now.getMonth() + 1 - 1) y++;
    return y + "-" + ("0" + q[1]).slice(-2) + "-" + ("0" + q[2]).slice(-2);
  }
  var out = [], m = location.pathname.match(/^\/([A-Za-z]+)\/(\d+)/);
  if (m) {
    var main = document.querySelector("main") || document.body, txt = main.innerText;
    var mails = [];
    document.querySelectorAll('a[href^="mailto:"]').forEach(function (a) { mails.push(a.getAttribute("href").slice(7).split("?")[0]); });
    mails = mails.concat(txt.match(/[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}/g) || [])
      .filter(function (e) { return !/filmmakers\.co\.kr/i.test(e); });
    var g = txt.match(/성별\s*([^\n국]+?)(?:국적|\n)/), a = txt.match(/연령\s*([^\n인]+?)(?:인원|\n)/), due = txt.match(/모집 마감일[\s~]*([^\n(]+)/);
    out.push({ id: m[2], board: m[1], url: location.href.split("#")[0], title: document.title.replace(/\s*-\s*필름메이커스\s*$/, ""),
      gender: g ? g[1].trim() : "", age: a ? a[1].trim() : "", due: due ? ymd(due[1]) : "",
      email: mails[0] || "", detail: 1 });
  } else {
    document.querySelectorAll("h2 a[href]").forEach(function (a) {
      var mm = a.getAttribute("href").match(/\/([A-Za-z]+)\/(\d+)$/); if (!mm) return;
      var card = a.closest("h2").parentElement, f = fields(card), spans = card.querySelectorAll("span");
      out.push({ id: mm[2], board: mm[1], url: a.href, title: T(a), cat: T(spans[0]),
        prod: f["제작"] || "", work: f["제목"] || "", gender: f["성별"] || "", age: f["연령"] || "",
        pay: f["출연료"] || "", due: f["마감"] || "" });
    });
  }
  if (!out.length) { alert("가져올 공고를 못 찾았어요. 배우모집 목록이나 공고 상세 화면에서 눌러주세요."); return; }
  var data = btoa(unescape(encodeURIComponent(JSON.stringify(out)))).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
  location.href = APP + "#fm=" + data;
})();
