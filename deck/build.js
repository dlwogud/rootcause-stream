// RootCause Stream 발표자료 생성기 — v5 (2026-11-27, '연구 보고서형' 디자인 · academic-pptx 규칙)
//   이야기 순서: 날림은 숫자로 안 보인다 → 전문가는 가서 본다 + 연구 질문 → 묻는 AI → 실제 화면 → 영상 → 63초 →
//               들어간 것과 나온 것 → 기술 9가지 → 효과 → 진짜 사진을 보나 → 결론 | 부록 A~G
//   디자인: 흰 바탕 · 글꼴 하나(맑은 고딕) · 남색 제목 왼쪽 정렬 · 카드 상자 대신 선과 여백 · 표와 그림에 번호와 설명 ·
//           그림 위 직접 표시(노란 표시) · 장마다 출처 · 위쪽 위치 표시줄. 주황은 날림과 우리 결과에만.
//   수치는 numbers.json(← export_numbers.py)에서만, 시연은 data/demo_runs/e323-ko.json(한국어 실제 실행)에서만 읽는다.
//   실행: .venv/bin/python deck/export_numbers.py && NODE_PATH=deck/node_modules node deck/build.js
const path = require("path");
const fs = require("fs");
const pptxgen = require("pptxgenjs");
const APPLY_THEME = process.env.APPLY_THEME_JS;
const applyTheme = APPLY_THEME && fs.existsSync(APPLY_THEME)
  ? require(APPLY_THEME).applyTheme
  : async () => console.warn("APPLY_THEME_JS 없음 — 테마 색 적용을 건너뜀");

const ROOT = path.resolve(__dirname, "..");
const N = JSON.parse(fs.readFileSync(path.join(__dirname, "numbers.json"), "utf8"));
const F = N.facts;
const E = N.tier_e_final;                       // run #84 — 최종 설계
const RB = N.rule_baseline.tier_e;              // 규칙 · 지도학습 분류기
const PT = N.tier_e_paired.tests;               // 10장 짝 검정 (scripts/95_tier_e_paired.py)
const MC = N.model_comparison.tiers;            // sonnet 사진 없음 · 앞면 사진
const DEMO = JSON.parse(fs.readFileSync(path.join(ROOT, "data/demo_runs/e323-ko.json"), "utf8"));   // 한국어 실제 실행 기록
const OUT = process.env.DECK_OUT || path.join(__dirname, "RootCause_Stream_발표자료.pptx");
// 글꼴: 맑은 고딕 (2026-11-24). 윈도우 전부와 맥용 PowerPoint 에 들어 있다.
const FONT = "Malgun Gothic";
const PH = p => path.join(ROOT, "data/photos/tier_e", p);
const AS = p => path.join(__dirname, "assets", p);
const DEMO_URL = "rootcause-stream-demo.vercel.app";
const REPO_URL = "github.com/dlwogud/rootcause-stream";

// ── 색: academic-pptx 기본(남색 · 파랑 · 회색) + 강조 주황 하나 + 그림 표시용 노랑 ──────────────
const C = { bg: "FFFFFF", navy: "1F4E79", blue: "2E75B6", body: "2D2D2D", muted: "6F6F6F", rule: "C9CED6",
            band: "F0F4F8", hi: "FFF2CC", hiLine: "E0B400", hiText: "7A5200", spark: "D9480F", light: "9FB3C8", faint: "9AA3AE" };
const THEME = {
  name: "RootCause Report",
  headFontFace: FONT,
  bodyFontFace: FONT,
  colors: { dk1: C.body, lt1: C.bg, dk2: C.navy, lt2: C.band,
            accent1: C.spark, accent2: C.blue, accent3: C.navy, accent4: C.hiLine, accent5: C.muted, accent6: C.light,
            hlink: C.blue, folHlink: C.navy },
};
const pres = new pptxgen();
pres.layout = "LAYOUT_WIDE";                // 13.333 × 7.5
pres.theme = { headFontFace: FONT, bodyFontFace: FONT };
pres.title = "RootCause Stream — 모르면, 먼저 물어보는 AI";
pres.author = "이재형";
const W = 13.333, M = 0.6, CW = W - 2 * M;
const r0 = v => `${Math.round(v)}%`;
const pfmt = p => (p < 0.001 ? "p < 0.001" : `p = ${p.toFixed(p < 0.01 ? 3 : 2)}`);
const t0 = DEMO.events[0].t;
const at = type => DEMO.events.find(e => e.type === type);
const secs = e => Math.round(e.t - t0);
const SECTIONS = ["배경", "아이디어", "시스템", "결과", "결론", "부록"];

// ── 레이아웃 ──────────────────────────────────────────────────────────
pres.defineSlideMaster({ title: "COVER", background: { color: C.bg }, objects: [] });
pres.defineSlideMaster({
  title: "REPORT",
  background: { color: C.bg },
  margin: [0.4, M, 0.6, M],
  slideNumber: { x: W - M - 0.6, y: 7.05, w: 0.6, h: 0.3, fontSize: 11, color: C.muted, fontFace: FONT, align: "right" },
  objects: [
    { rect: { x: 0, y: 0, w: W, h: 0.34, fill: { color: C.band }, line: { type: "none" } } },
    { text: { text: "RootCause Stream", options: { x: M, y: 0, w: 4, h: 0.34, fontSize: 11, color: C.faint, fontFace: FONT, valign: "middle", margin: 0 } } },
    { placeholder: { options: { name: "title", type: "title", x: M, y: 0.62, w: CW, h: 0.7,
        fontSize: 26, bold: true, color: C.navy, fontFace: FONT, align: "left", valign: "middle", margin: 0 }, text: "" } },
    { line: { x: M, y: 1.42, w: CW, h: 0, line: { color: C.rule, width: 1 } } },
  ],
});

// ── 클릭할 때마다 나타나는 묶음 (7·8장) ─────────────────────────────────
// ANIM 에 묶음 번호를 넣어 두면 그동안 그린 도형 이름이 'anim-<묶음>-<n>' 이 되고, 파일을 만든 뒤 addAnimations 가
// 그 이름으로 PowerPoint 애니메이션을 넣는다 (pptxgenjs 는 애니메이션을 쓰지 못한다). 묶음 하나 = 클릭 한 번.
let ANIM = null, ANIM_N = 0;
const nm = () => (ANIM ? { objectName: `anim-${ANIM}-${ANIM_N++}` } : {});

// ── 공통 조각 ─────────────────────────────────────────────────────────
function t(s, text, o) { s.addText(text, { fontFace: FONT, color: C.body, margin: 0, valign: "top", isTextBox: true, ...o, ...nm() }); }
function rect(s, x, y, w, h, fill, line) {
  s.addShape(pres.shapes.RECTANGLE, { x, y, w, h, fill: fill ? { color: fill } : { type: "none" },
    line: line ? { color: line[0], width: line[1] || 1 } : { type: "none" }, ...nm() });
}
function hline(s, x, y, w, color = C.rule, width = 0.75) { s.addShape(pres.shapes.LINE, { x, y, w, h: 0, line: { color, width }, ...nm() }); }
function img(s, file, x, y, w, h, alt, border) {
  s.addImage({ path: file, x, y, w, h, altText: alt || "", ...nm() });
  if (border) rect(s, x, y, w, h, null, [border[0], border[1] || 0.75]);
}
function photo(s, file, x, y, d, border) { img(s, PH(file), x, y, d, d, file, border || [C.rule, 0.75]); }
// 노란 표시 — 그림 위에 직접 짚는다 (academic-pptx: 결과는 그림 위에 표시)
function mark(s, px, py, r, lx, ly, label, lw = 1.5) {
  s.addShape(pres.shapes.OVAL, { x: px - r, y: py - r, w: 2 * r, h: 2 * r, fill: { type: "none" }, line: { color: C.hiLine, width: 2.25 }, ...nm() });
  const ex = lx + lw / 2, ey = ly + 0.42;
  s.addShape(pres.shapes.LINE, { x: Math.min(ex, px), y: Math.min(ey, py - r * 0.7), w: Math.abs(px - ex) || 0.01, h: Math.abs(py - r * 0.7 - ey) || 0.01,
    flipH: px < ex, line: { color: C.hiLine, width: 1.5 }, ...nm() });
  rect(s, lx, ly, lw, 0.42, C.hi, [C.hiLine, 1]);
  t(s, label, { x: lx, y: ly, w: lw, h: 0.42, fontSize: 14, bold: true, color: C.hiText, align: "center", valign: "middle" });
}
const PHOTO_CREDIT = "사진: L. A. Dominguez Molina, Resistance Spot Welding Insights, Mendeley Data V3 (2025), CC BY 4.0";
function cite(s, text, y = 6.95) { t(s, text, { x: M, y, w: CW - 0.8, h: 0.35, fontSize: 11.5, color: C.muted }); }
// 논문식 표: 위·아래 굵은 선, 머리글 아래 선, 행 사이 얇은 선. 칸 상자를 쓰지 않는다.
function rtable(s, x, y, colW, rows, o = {}) {
  const rh = o.rowH || 0.46, w = colW.reduce((a, b) => a + b, 0);
  hline(s, x, y, w, C.navy, 1.5);
  rows.forEach((r, i) => {
    const yy = y + 0.04 + i * rh;
    let xx = x;
    r.forEach((cell, j) => {
      const c = cell && typeof cell === "object" && !Array.isArray(cell) ? cell : { text: String(cell) };
      t(s, c.text, { x: xx + 0.06, y: yy, w: colW[j] - 0.12, h: rh - 0.04, fontSize: i ? (o.size || 15) : (o.headSize || 13),
                     bold: !i || !!c.bold, color: !i ? C.muted : (c.color || C.body), align: (o.align || [])[j] || "left", valign: "middle" });
      xx += colW[j];
    });
    if (i < rows.length - 1) hline(s, x, yy + rh, w, i ? C.rule : C.navy, i ? 0.5 : 0.75);
  });
  const end = y + 0.04 + rows.length * rh + 0.02;
  hline(s, x, end, w, C.navy, 1.5);
  return end;
}
// 정의 목록: 왼쪽 이름표, 오른쪽 설명, 행 사이 얇은 선
function deflist(s, x, y, w, labelW, items, o = {}) {
  const rh = o.rowH || 0.9;
  items.forEach(([k, v, col], i) => {
    const yy = y + i * rh;
    t(s, k, { x, y: yy, w: labelW, h: rh, fontSize: o.labelSize || 16, bold: true, color: col || C.navy, valign: "middle" });
    t(s, v, { x: x + labelW, y: yy, w: w - labelW, h: rh, fontSize: o.size || 14, valign: "middle" });
    hline(s, x, yy + rh, w, C.rule, 0.5);
  });
  hline(s, x, y, w, C.navy, 1.5);
}
function frame(section, title) {
  const s = pres.addSlide({ masterName: "REPORT" });
  s.addText(title, { placeholder: "title" });
  const sw = 1.2;
  SECTIONS.forEach((name, i) => {
    const on = name === section, x = W - M - (SECTIONS.length - i) * sw;
    t(s, name, { x, y: 0, w: sw, h: 0.34, fontSize: 11, align: "center", valign: "middle", bold: on, color: on ? C.navy : C.faint });
    if (on) rect(s, x + 0.28, 0.3, sw - 0.56, 0.04, C.navy);
  });
  return s;
}
// 기술 꼬리표 — 어느 부분이 LLM·VLM·HITL 인지 (7장 타임라인). 테두리만 있는 작은 이름표
function tag(s, text, col, x, y) {
  const w = 0.3 + [...text].reduce((a, ch) => a + (/[가-힣]/.test(ch) ? 0.155 : 0.085), 0);
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: x - w / 2, y, w, h: 0.27, rectRadius: 0.13, fill: { color: C.bg }, line: { color: col, width: 1 }, ...nm() });
  t(s, text, { x: x - w / 2, y, w, h: 0.27, fontSize: 11, bold: true, color: col, align: "center", valign: "middle" });
}

async function build() {
  const req = at("photo_request"), reads = DEMO.events.filter(e => e.type === "photo_read"), fin = at("final");
  const inc = at("incident").summary, lg = inc.logged_during_weld, pop = inc.same_setpoint_population;
  const inBand = (v, d) => v >= d.p10 && v <= d.p90;
  const cnt = r => Math.round(r * E.photo.explode_n / 100);
  const fz = E.explode_funnel;

  // ══ 1. 표지 ═════════════════════════════════════════════════════════
  {
    const s = pres.addSlide({ masterName: "COVER" });
    rect(s, 0, 0, W, 0.34, C.band);
    t(s, "LLM 서비스 개발 프로젝트", { x: M, y: 0.95, w: 7, h: 0.4, fontSize: 15, color: C.muted });
    t(s, "모르면,\n먼저 물어보는 AI", { x: M, y: 1.45, w: 7.0, h: 2.1, fontSize: 46, bold: true, color: C.navy, lineSpacingMultiple: 1.05 });
    t(s, "공장 설비의 불량 원인을 찾다가, 기록만으로 모르면\n작업자에게 \"이걸 찍어 주세요\"라고 요청하는 진단 AI",
      { x: M, y: 3.75, w: 7.0, h: 1.0, fontSize: 19, lineSpacingMultiple: 1.25 });
    hline(s, M, 5.2, 6.4, C.rule, 1);
    t(s, [{ text: "이재형", options: { bold: true, breakLine: true } }, { text: "RootCause Stream · 2026년 11월", options: { color: C.muted, fontSize: 14 } }],
      { x: M, y: 5.35, w: 6.4, h: 0.8, fontSize: 17 });
    const px = 8.35, py = 0.85, pd = 4.2;
    photo(s, "RGB_323F.jpg", px, py, pd);
    rect(s, px, py + pd + 0.2, pd, 0.9, C.bg, [C.navy, 1.25]);
    t(s, [{ text: "AI의 촬영 요청", options: { fontSize: 12, bold: true, color: C.navy, breakLine: true } },
          { text: "\"이 용접, 뒷면도 찍어 주실 수 있나요?\"", options: { fontSize: 15.5, bold: true } }],
      { x: px + 0.2, y: py + pd + 0.2, w: pd - 0.3, h: 0.9, valign: "middle" });
    t(s, "그림. 실제 용접 사진 (날림 불량)", { x: px, y: py + pd + 1.2, w: pd, h: 0.3, fontSize: 12, color: C.muted, align: "right" });
    t(s, PHOTO_CREDIT, { x: M, y: 6.95, w: CW, h: 0.3, fontSize: 10, color: C.muted, align: "right" });
    s.addNotes(`안녕하세요. 제가 만든 건 '모르면 먼저 물어보는 AI'입니다. 공장에서 불량이 났을 때 AI가 원인을 찾다가, 기록만으로 모르겠으면 작업자에게 '이걸 찍어 주세요'라고 요청하고 그 사진으로 결론을 냅니다. 오늘은 이 아이디어가 실제로 효과가 있는지를 실제 용접 사진으로 확인한 결과를 말씀드리겠습니다.`);
  }

  // ══ 2. 배경 · 문제 ═════════════════════════════════════════════════
  {
    const s = frame("배경", "날림 불량은 숫자에는 안 잡히는데 사진에는 보인다");
    t(s, [{ text: "점용접", options: { bold: true, color: C.navy } }, { text: "  두 철판을 전기 열로 녹여 붙인 점. 차 한 대에 수천 개.", options: { breakLine: true } },
          { text: "날림", options: { bold: true, color: C.spark } }, { text: "  용접 중 녹은 쇳물이 밖으로 튀어나가는 불량." }],
      { x: M, y: 1.7, w: 7.0, h: 0.9, fontSize: 16, lineSpacingMultiple: 1.35 });
    t(s, `표 1. E-323 용접의 기록을 같은 설정 용접 ${pop.n_welds}회와 비교`, { x: M, y: 2.95, w: 7.0, h: 0.35, fontSize: 14, bold: true });
    const row = (k, v, d, unit) => {
      const ok = inBand(v, d);
      return [k, { text: `${Math.round(v).toLocaleString()} ${unit}`, bold: true }, `${Math.round(d.p10).toLocaleString()} ~ ${Math.round(d.p90).toLocaleString()} ${unit}`,
              { text: ok ? "보통" : "끝자락", color: ok ? C.body : C.spark, bold: !ok }];
    };
    rtable(s, M, 3.4, [1.6, 1.6, 2.55, 1.15], [
      ["항목", "이 용접", "같은 설정의 보통 범위", "판정"],
      row("최대 전류", lg.peak_current_A, pop.peak_current_A, "A"),
      row("평균 전류", lg.mean_current_A, pop.mean_current_A, "A"),
      row("누르는 힘", lg.peak_force_N, pop.peak_force_N, "N"),
    ], { rowH: 0.5, size: 16, align: ["left", "right", "right", "right"] });
    t(s, [{ text: `숫자만 보는 방법은 날림 ${E.photo.explode_n}개 중 ` }, { text: `규칙 ${cnt(RB.rule_peak_current_p90.explode_recall)}개, 학습 AI ${cnt(RB.supervised_rf_reference.explode_recall)}개`, options: { bold: true, color: C.spark } }, { text: "만 찾았다." }],
      { x: M, y: 5.75, w: 7.1, h: 0.45, fontSize: 16 });
    const px = 8.15, py = 1.75, pd = 4.4;
    photo(s, "RGB_323F.jpg", px, py, pd);
    mark(s, px + 0.41 * pd, py + 0.47 * pd, 0.28, px + 0.25, py + 0.5, "튄 쇳조각", 1.6);
    t(s, "그림 1. E-323 용접 앞면. 기록상으로는 보통이지만 실제로는 날림이다.", { x: px, y: py + pd + 0.1, w: pd, h: 0.55, fontSize: 12.5, color: C.muted });
    cite(s, PHOTO_CREDIT);
    s.addNotes(`점용접은 두 철판을 전기 열로 녹여 붙이는 방식이고, 자동차 한 대에 수천 개가 들어갑니다. 까다로운 불량 중 하나가 '날림'인데, 용접 중 녹은 쇳물이 밖으로 튀어나가는 현상입니다. 이 용접의 기록을 같은 설정의 다른 용접들과 비교하면 최대 전류와 누르는 힘은 보통 범위이고, 평균 전류만 범위 끝자락입니다. 숫자만 보면 알 수 없습니다. 실제로는 날림이었고, 사진에는 가운데 튀어나온 쇳조각이 보입니다. 숫자만 보는 규칙은 날림 ${E.photo.explode_n}개 중 ${cnt(RB.rule_peak_current_p90.explode_recall)}개, 정답 수백 개로 학습한 AI도 ${cnt(RB.supervised_rf_reference.explode_recall)}개밖에 못 찾습니다.`);
  }

  // ══ 3. 아이디어 ═══════════════════════════════════════════════════
  {
    const s = frame("아이디어", "전문가는 애매하면 직접 가서 본다");
    t(s, "표 2. 기록만으로 애매할 때 전문가가 하는 일", { x: M, y: 1.65, w: CW, h: 0.35, fontSize: 14, bold: true });
    rtable(s, M, 2.1, [2.4, 2.95, 3.2, 3.58], [
      ["누가", "상황", "하는 말", "그다음"],
      ["의사", "증상만으로는 애매하다", "\"엑스레이 찍어 보자\"", "사진을 읽고 진단"],
      ["숙련 엔지니어", "기록만으로는 애매하다", "\"가서 직접 보자\"", "눈으로 확인하고 원인 확정"],
      [{ text: "이 프로젝트의 AI", bold: true, color: C.spark }, "기록만으로는 애매하다", { text: "\"이 부분을 찍어 주세요\"", bold: true, color: C.spark }, "사진을 읽고 근거를 달아 결론"],
    ], { rowH: 0.66, size: 17 });
    rect(s, M, 5.0, CW, 1.35, C.band);
    t(s, "연구 질문", { x: M + 0.35, y: 5.15, w: 3, h: 0.35, fontSize: 14, bold: true, color: C.navy });
    t(s, "AI도 모를 때 사진을 요청하게 하면, 기록만 볼 때보다 불량을 더 잘 찾을까?", { x: M + 0.35, y: 5.5, w: CW - 0.7, h: 0.6, fontSize: 21, bold: true, valign: "middle" });
    s.addNotes("사람 전문가는 이럴 때 어떻게 할까요. 의사는 증상만으로 애매하면 엑스레이를 찍자고 합니다. 숙련 엔지니어도 기록만으로 애매하면 가서 직접 봅니다. 그래서 이 프로젝트의 질문은 하나입니다. AI도 모를 때 사진을 요청하게 하면, 기록만 볼 때보다 불량을 더 잘 찾을까?");
  }

  // ══ 4. 해결 ═══════════════════════════════════════════════════════
  {
    const s = frame("아이디어", "그래서 AI가 모르면 사진을 부탁하게 만들었다");
    const turns = [
      ["AI", "LLM 에이전트", C.navy, 0.72, "기록만으로는 정상인지 날림인지 갈리지 않아요."],
      ["AI", "LLM 에이전트", C.navy, 0.98, "용접 자국 앞면과 뒷면을 가까이 찍어 주세요.\n탄 고리나 튄 쇳조각이 보이면 날림이에요."],
      ["작업자", "HITL", C.blue, 1.22, null],
      ["AI", "VLM + 에이전트", C.navy, 0.98, "앞면에 정상 샘플에는 없는 쇳조각이 보여요.\n뒷면은 정상이지만 날림으로 판단합니다."],
    ];
    let y = 1.72;
    turns.forEach(([who, tech, col, h, msg]) => {
      t(s, [{ text: who, options: { bold: true, color: col, fontSize: 16, breakLine: true } }, { text: tech, options: { color: C.muted, fontSize: 11 } }],
        { x: M, y, w: 1.45, h, valign: "middle" });
      if (msg) {
        rect(s, M + 1.5, y, 5.5, h, C.band);
        t(s, msg, { x: M + 1.75, y, w: 5.1, h, fontSize: 15.5, valign: "middle", lineSpacingMultiple: 1.15 });
      } else {
        rect(s, M + 1.5, y, 5.5, h, null, [C.rule, 0.75]);
        img(s, PH("RGB_323F.jpg"), M + 1.65, y + 0.1, h - 0.2, h - 0.2, "앞면");
        img(s, PH("RGB_323B.jpg"), M + 1.75 + h - 0.2, y + 0.1, h - 0.2, h - 0.2, "뒷면");
        t(s, "앞면과 뒷면 사진을 올린다", { x: M + 1.95 + 2 * (h - 0.2), y, w: 2.6, h, fontSize: 14, color: C.muted, valign: "middle" });
      }
      y += h + 0.14;
    });
    t(s, "그림 2. 실제 실행 기록(E-323)의 요청과 판독을 대화로 줄여 적었다. 실제 화면은 5장.", { x: M, y: y + 0.02, w: 7.0, h: 0.4, fontSize: 12.5, color: C.muted });
    const pts = [
      ["무엇을 찍을지 스스로 정한다", "막히면 어떤 사진이 답을 가를지 골라서 요청한다"],
      ["보기 전에 기준부터 말한다", "'이게 보이면 날림'을 먼저 정해 둔다"],
      ["합격품 사진과 나란히 본다", "같은 설정의 정상품 사진을 옆에 놓고 읽는다"],
    ];
    const rx = 8.05, rw = W - M - rx;
    t(s, "설계의 세 가지", { x: rx, y: 1.7, w: rw, h: 0.4, fontSize: 20, bold: true, color: C.blue });
    hline(s, rx, 2.2, rw, C.navy, 1.5);
    pts.forEach(([h, d], i) => {
      const yy = 2.3 + i * 1.3;
      t(s, h, { x: rx, y: yy + 0.12, w: rw, h: 0.45, fontSize: 18, bold: true });
      t(s, d, { x: rx, y: yy + 0.58, w: rw, h: 0.6, fontSize: 15, color: C.muted });
      hline(s, rx, yy + 1.25, rw, C.rule, 0.5);
    });
    cite(s, PHOTO_CREDIT);
    s.addNotes("그래서 만든 서비스입니다. 대화로 보면 이렇습니다. AI가 기록만으로는 갈리지 않는다고 판단하면, 작업자에게 앞면과 뒷면을 찍어 달라고 요청합니다. 이때 사진을 보기 전에 '탄 고리나 튄 쇳조각이 보이면 날림'이라고 기준부터 말합니다. 작업자가 사진을 올리면, AI가 합격품 사진과 나란히 비교해 앞면에서 쇳조각을 찾고, 뒷면은 정상이지만 날림이라고 결론 냅니다. 실제 화면은 채팅이 아니고, 실제 실행 기록의 요청과 판독 내용을 대화처럼 줄여 적은 것입니다. 원문은 뒤에서 그대로 보여드립니다.");
  }

  // ══ 5. 실제 화면 ═════════════════════════════════════════════════
  {
    const s = frame("시스템", "관제 화면과 작업자 휴대폰으로 실제로 돌아간다");
    s.addImage({ path: AS("ui_overview.png"), x: M, y: 1.7, w: 7.2, h: 4.19, sizing: { type: "cover", w: 7.2, h: 4.19 }, altText: "관제 화면" });
    rect(s, M, 1.7, 7.2, 4.19, null, [C.rule, 0.75]);
    t(s, "그림 3. 관제 화면. AI의 가설과 점수, 촬영 요청, 실행 기록이 한 화면에 실시간으로 뜬다.", { x: M, y: 6.0, w: 7.2, h: 0.5, fontSize: 12.5, color: C.muted });
    s.addImage({ path: AS("ui_mobile.png"), x: 8.05, y: 1.7, w: 1.95, h: 4.19, sizing: { type: "cover", w: 1.95, h: 4.19 }, altText: "휴대폰 촬영 페이지" });
    rect(s, 8.05, 1.7, 1.95, 4.19, null, [C.rule, 0.75]);
    t(s, "그림 4. 휴대폰 촬영 페이지 (QR로 연다)", { x: 8.05, y: 6.0, w: 2.1, h: 0.5, fontSize: 12.5, color: C.muted });
    const rx = 10.4, rw = W - M - rx;
    const facts = [["자동 테스트", `${F.tests}개`], ["코드", "GitHub 공개"], ["시연 재생", "서버 없이 여는\nHTML 파일"], ["공개 시연", "링크로 누구나"]];
    hline(s, rx, 1.7, rw, C.navy, 1.5);
    facts.forEach(([k, v], i) => {
      const yy = 1.72 + i * 1.05;
      t(s, k, { x: rx, y: yy + 0.1, w: rw, h: 0.3, fontSize: 12, color: C.muted });
      t(s, v, { x: rx, y: yy + 0.38, w: rw, h: 0.62, fontSize: i ? 15 : 22, bold: true, color: C.navy });
      hline(s, rx, yy + 1.05, rw, C.rule, 0.5);
    });
    s.addNotes(`실제로 돌아가는 서비스입니다. 왼쪽이 관제 화면입니다. AI가 세운 가설과 점수가 실시간으로 바뀌고, 촬영이 필요하면 무엇을 왜 찍어야 하는지 요청이 뜹니다. 작업자는 QR 코드로 오른쪽 휴대폰 화면을 열어 바로 찍어 올립니다. 자동 테스트 ${F.tests}개와 함께 GitHub에 공개했습니다.`);
  }

  // ══ 6. 시연 영상 — deck/assets/demo.mp4 가 있을 때만 (deck/replay/demo.html 을 화면 녹화한 것) ══
  const VIDEO = AS("demo.mp4");
  if (fs.existsSync(VIDEO)) {
    const s = frame("시스템", "시연 영상: 실제 실행 기록을 시간만 줄여 재생");
    const vh = 4.75, vw = vh * 16 / 9, vx = (W - vw) / 2;     // 16:9 그대로 (녹화 1920×1080)
    s.addMedia({ type: "video", path: VIDEO, x: vx, y: 1.65, w: vw, h: vh,
                 cover: "image/png;base64," + fs.readFileSync(AS("ui_overview.png")).toString("base64") });
    t(s, `날림(E-323), 정상(E-357), 공장 데이터 순서. ${DEMO_URL} 에서 다시 볼 수 있다.`, { x: M, y: 6.5, w: CW, h: 0.35, fontSize: 12.5, color: C.muted, align: "center" });
    s.addNotes("시연 영상입니다. 실제 실행 기록을 시간만 줄여 재생한 것이고, 사건 세 개가 이어집니다. 첫 번째는 날림 용접입니다. AI가 기록만으로 애매하다고 판단해 앞면과 뒷면 촬영을 요청하고, 사진을 합격품과 비교해 날림으로 결론 냅니다. 두 번째는 정상 용접입니다. 똑같이 사진을 요청하지만, 이번에는 튄 쇳조각이 없어서 정상으로 결론 냅니다. 마지막은 실제 공장 데이터입니다. 사진 없이 기록만 보고, 설비 고장이 아니라 다른 날 기록이 그대로 복사돼 들어간 것이라고 찾아냅니다.");
  }

  // ══ 7. 실제 실행 63초 (클릭마다 한 단계) ═══════════════════════════════
  {
    const s = frame("시스템", `실제 실행에서는 ${Math.round(DEMO.meta.elapsed_s)}초 만에 날림을 찾았다`);
    const steps = [
      [0, "기록 확인", "숫자만으로는\n애매하다", C.faint, null, ["LLM 에이전트", C.navy]],
      [secs(req), "촬영 요청", "앞면과 뒷면을\n찍어 달라고 요청", C.blue, null, ["HITL", C.blue]],
      [secs(reads[0]), "앞면 판독", "정상 샘플에 없는\n쇳조각 발견", C.spark, "RGB_323F.jpg", ["VLM", C.blue]],
      [secs(reads[1]), "뒷면 판독", "특이점 없음", C.navy, "RGB_323B.jpg", ["VLM", C.blue]],
      [secs(fin), "결론: 날림", "뒷면이 정상이어도\n앞면 결함은 남는다", C.spark, null, ["선언 검사 + 에이전트", C.spark]],
    ];
    const x0 = M + 0.9, span = 9.9, y = 4.2;
    hline(s, x0, y + 0.2, span, C.rule, 2);
    rect(s, x0 - 0.75, 2.3, 2.5, 1.3, C.band);
    t(s, [{ text: "같은 설정 용접들과\n비교하면 ", options: {} }, { text: "거의 보통", options: { bold: true, color: C.muted } }],
      { x: x0 - 0.65, y: 2.3, w: 2.3, h: 1.3, fontSize: 14, align: "center", valign: "middle" });
    steps.forEach(([sec, title, d, col, ph, tg], i) => {
      const x = x0 + span * i / (steps.length - 1);
      ANIM = i ? i : null;
      tag(s, tg[0], tg[1], x, 3.84);
      s.addShape(pres.shapes.OVAL, { x: x - 0.17, y: y + 0.03, w: 0.34, h: 0.34, fill: { color: col }, line: { color: C.bg, width: 2 }, ...nm() });
      t(s, `${sec}초`, { x: x - 0.8, y: y + 0.5, w: 1.6, h: 0.4, fontSize: 15, bold: true, color: col, align: "center" });
      t(s, title, { x: x - 1.1, y: y + 0.9, w: 2.2, h: 0.45, fontSize: 18, bold: true, align: "center" });
      t(s, d, { x: x - 1.1, y: y + 1.38, w: 2.2, h: 0.75, fontSize: 14.5, color: C.muted, align: "center" });
      if (ph) photo(s, ph, x - 0.85, 2.05, 1.7, [col, 2]);
    });
    ANIM = steps.length - 1;                                   // '날림 · 정답과 같다'는 63초와 함께
    rect(s, x0 + span - 1.15, 2.3, 2.3, 1.3, C.bg, [C.spark, 1.5]);
    t(s, [{ text: "날림\n", options: { bold: true, fontSize: 28, color: C.spark } }, { text: "정답과 같다", options: { fontSize: 14, bold: true, color: C.navy } }],
      { x: x0 + span - 1.15, y: 2.3, w: 2.3, h: 1.3, align: "center", valign: "middle" });
    ANIM = null;
    t(s, "그림 5. E-323 실제 실행 기록의 시각별 진행. 시연 영상은 이 기록을 그대로 재생했다.", { x: M, y: 6.5, w: 9, h: 0.35, fontSize: 12.5, color: C.muted });
    cite(s, PHOTO_CREDIT);
    s.addNotes(`(클릭할 때마다 다음 시각이 하나씩 나타납니다.) 실제 실행 기록입니다. 0초에 기록을 확인했는데 숫자로는 애매합니다. ${secs(req)}초에 AI가 앞면과 뒷면 촬영을 요청합니다. ${secs(reads[0])}초에 앞면 사진에서 정상 샘플에 없는 쇳조각을 찾고, ${secs(reads[1])}초에 뒷면은 특이점이 없다고 읽습니다. 두 신호가 엇갈려 시스템이 한 번 되물었고, AI는 뒷면이 정상이어도 앞면 결함은 없어지지 않는다고 판단해 ${secs(fin)}초에 날림으로 결론 냈습니다. 정답입니다.`);
  }

  // ══ 8. 들어간 것과 나온 것 (E-323 실제 기록 발췌, 클릭마다 한 줄) ═══════════
  {
    const must = (ok, m) => { if (!ok) throw new Error(`8장: 실행 기록과 다름 — ${m}`); };
    const quote = (q, src) => { must(src.includes(q), q); return q; };
    const step1 = DEMO.events.find(e => e.type === "step" && e.step === 1);
    const H = Object.fromEntries(step1.hypotheses.map(h => [h.id, h]));
    must(H.H1.statement.startsWith("정상") && H.H2.statement.includes("날림") && H.H3.statement.includes("용입 부족")
         && H.H4.statement.includes("편심"), "가설 이름");
    must(step1.action === "request_photo", "1단계 행동");
    const r1 = req.requests[0];
    const declKey = Object.keys(r1.if_observed).find(k => k.includes("튄 금속 방울"));
    must(declKey && r1.if_observed[declKey].H2 === "support" && r1.if_observed[declKey].H1 === "weaken", "보기 전 선언");
    const front = reads[0].reading, back = reads[1].reading;
    must(front.fault_present === true && front.differs_from_reference === true && back.fault_present === false, "판독");
    must(front.checks.find(c => c.observation === declKey).visible === true, "체크 항목");
    must(fin.challenge && fin.challenge.conflicts.length > 0, "되묻기");
    const FH = Object.fromEntries(fin.hypotheses.map(h => [h.id, h]));
    const f2 = v => v.toFixed(2), n0 = v => Math.round(v).toLocaleString();

    const s = frame("시스템", `그 ${Math.round(DEMO.meta.elapsed_s)}초 동안 AI에 들어간 것과 나온 것`);
    const cols = [M, M + 2.75, M + 7.2], cw = [2.6, 4.25, CW - 7.2];
    ["단계", "들어간 것", "나온 것"].forEach((h, j) => t(s, h, { x: cols[j], y: 1.6, w: cw[j], h: 0.35, fontSize: 13.5, bold: true, color: C.muted }));
    hline(s, M, 1.98, CW, C.navy, 1.5);
    const R = (txt, o = {}) => ({ text: txt, options: { breakLine: true, ...o } });
    const rows = [
      [["LLM 에이전트", "Claude Sonnet 5.5"],
       [R(`용접 기록: 최대 전류 ${n0(lg.peak_current_A)} A`), R(`같은 설정 ${pop.n_welds}회 상위 10%는 ${n0(pop.peak_current_A.p90)} A`, { color: C.muted })],
       [R(`가설 4개: 정상 ${f2(H.H1.score)}, 날림 ${f2(H.H2.score)}`), R(`용입 부족 ${f2(H.H3.score)}, 편심 ${f2(H.H4.score)}`, { color: C.muted }), R("숫자로는 안 갈려서 촬영을 요청", { bold: true, color: C.navy })]],
      [["사람에게 요청", "Human-in-the-loop"],
       [R(`찍을 곳: ${quote("전극이 닿은 윗면", r1.target)}과 뒷면`), R("선언: 튄 금속이나 변색이 보이면 날림 쪽", { color: C.muted })],
       [R("작업자 휴대폰에 요청이 뜨고 진단은 멈춤"), R(`앞면과 뒷면 사진 ${reads.length}장이 오면 다시 진행`, { bold: true, color: C.navy })]],
      [["VLM 사진 판독", "Claude Haiku 5.5"],
       null,
       [R(`"${quote("왼쪽으로 뻗은 뾰족한 밝은 금속 돌기", front.observation)}"`), R("선언해 둔 '튄 금속, 변색'이 보인다", { bold: true, color: C.navy })]],
      [["검증과 결론", "코드 검사 + 에이전트"],
       [R("앞면은 이상 있음, 뒷면은 이상 없음"), R("뒷면은 '정상' 선언인데 초안은 날림", { color: C.muted })],
       [R(`결론: 날림 ${f2(FH.H2.score)}, 근거는 앞면과 뒷면`), R(`"${quote("뒷면이 정상이라는 사실은 이 앞면 결함을 없애지 못한다", fin.root_cause)}"`, { color: C.muted })]],
    ];
    const y0 = 2.08, rh = 1.12;
    rows.forEach(([[name, model], IN, OUT], i) => {
      const y = y0 + i * rh;
      ANIM = null;
      t(s, [R(name, { bold: true, color: C.navy }), { text: model, options: { color: C.muted, fontSize: 13 } }], { x: cols[0], y, w: cw[0], h: rh - 0.12, fontSize: 17, valign: "middle" });
      hline(s, M, y + rh - 0.04, CW, i === rows.length - 1 ? C.navy : C.rule, i === rows.length - 1 ? 1.5 : 0.75);
      ANIM = i + 1;
      if (IN) t(s, IN, { x: cols[1], y, w: cw[1], h: rh - 0.12, fontSize: 15.5, valign: "middle", lineSpacingMultiple: 1.15 });
      else {
        img(s, PH(reads[0].photo.split("tier_e/")[1]), cols[1], y + 0.12, 0.82, 0.82, "이 용접 앞면");
        img(s, PH(reads[0].reference.split("tier_e/")[1]), cols[1] + 0.92, y + 0.12, 0.82, 0.82, "합격품 앞면");
        t(s, [R("합격품 사진과 나란히"), R("+ 선언한 체크리스트", { color: C.muted })], { x: cols[1] + 1.9, y, w: cw[1] - 1.9, h: rh - 0.12, fontSize: 15.5, valign: "middle" });
      }
      t(s, OUT, { x: cols[2], y, w: cw[2], h: rh - 0.12, fontSize: 15.5, valign: "middle", lineSpacingMultiple: 1.15 });
    });
    ANIM = null;
    cite(s, `E-323 실제 실행 기록(data/demo_runs/e323-ko.json)에서 옮김. 처음부터 결론까지 ${Math.round(DEMO.meta.elapsed_s)}초.   사진: RSW Insights, CC BY 4.0`);
    s.addNotes(`(클릭할 때마다 한 줄씩 나타납니다. 왼쪽 단계 이름 네 개는 처음부터 보입니다.) 방금 본 63초 안에서 실제로 무엇이 들어가고 무엇이 나왔는지입니다. 먼저 LLM 에이전트에 용접 기록이 들어갑니다. 최대 전류가 같은 설정 용접들의 상위 10% 바로 아래라 애매하고, 에이전트는 가설 네 개에 점수를 매긴 뒤 숫자로는 안 갈린다며 촬영을 요청합니다. 이때 무엇을 어떻게 찍을지와 함께, 사진을 보기 전에 '튄 금속이나 변색이 보이면 날림 쪽'이라고 기준을 먼저 선언합니다. 요청은 작업자 휴대폰에 뜨고, 사진이 올 때까지 진단은 멈춥니다. 사진이 오면 VLM이 이 용접 사진과 같은 설정의 합격품 사진을 나란히 보고, 왼쪽으로 뻗은 금속 돌기를 찾아 선언한 항목이 보인다고 답합니다. 마지막으로 코드가 선언과 결론을 대조합니다. 뒷면은 정상 쪽이라고 선언했는데 결론이 날림이라 한 번 되묻고, 에이전트는 뒷면이 정상이어도 앞면 결함은 없어지지 않는다며 앞면과 뒷면을 근거로 날림을 확정합니다.`);
  }

  // ══ 9. 기술 ════════════════════════════════════════════════════════
  {
    const s = frame("시스템", "이 과정에 LLM과 VLM 기술 9가지를 엮었다");
    const cols = [
      ["생각하기", C.navy, [
        ["추론 루프 (Agent)", "가설과 점수를 고치며 다음 행동을 고른다"],
        ["도구 호출 (Tool Calling)", "기록, 매뉴얼, 도면, 과거 사례를 찾아본다"],
        ["매뉴얼·도면 검색 (RAG)", `매뉴얼 ${F.manual_pages}쪽과 도면 ${F.diagrams_described}장에서 찾는다`],
      ]],
      ["보고 묻기", C.blue, [
        ["사진 판독 (VLM)", "합격품 사진과 나란히 놓고 읽는다"],
        ["사람에게 요청 (HITL)", "사진이 올 때까지 멈췄다가 이어간다"],
      ]],
      ["믿을 수 있게", C.spark, [
        ["보기 전 선언과 되묻기", "기준과 다른 결론이면 되묻는다"],
        ["근거 인용 검증", "근거를 안 단 결론은 받지 않는다"],
        ["대화 이어 쓰기", `입력 토큰을 ${F.resume_tokens[0].toLocaleString()}개에서 ${F.resume_tokens[1]}개로`],
        ["AI 채점 (LLM-as-Judge)", "진단과 다른 모델(Opus)이 채점"],
      ]],
    ];
    const cw = 3.85, gx = (CW - 3 * cw) / 2;
    cols.forEach(([head, col, items], ci) => {
      const x = M + ci * (cw + gx);
      t(s, head, { x, y: 1.7, w: cw, h: 0.42, fontSize: 19, bold: true, color: col, valign: "middle" });
      hline(s, x, 2.18, cw, col, 1.75);
      items.forEach(([name, d], k) => {
        const y = 2.25 + k * 1.02;
        t(s, name, { x, y: y + 0.12, w: cw, h: 0.4, fontSize: 16, bold: true });
        t(s, d, { x, y: y + 0.5, w: cw, h: 0.45, fontSize: 14, color: C.muted });
        hline(s, x, y + 1.0, cw, C.rule, 0.5);
      });
    });
    cite(s, "모델: 진단 Claude Sonnet 5.5, 사진 판독 Claude Haiku 5.5, 채점 Claude Opus 5.5. 모두 Claude Code CLI로 호출 (eval/MODEL_VERSIONS.md)", 6.6);
    s.addNotes("기술적으로 보면 아홉 가지가 한 흐름으로 이어집니다. 생각하는 부분은 추론 루프, 도구 호출, 매뉴얼과 도면 검색입니다. 보고 묻는 부분은 사진 판독과 사람에게 요청하는 기능인데, 사진을 기다리는 동안 진단을 멈췄다가 사진이 오면 이어갑니다. 믿을 수 있게 하는 부분은 보기 전 선언과 되묻기, 근거 인용 검증, 대화 이어 쓰기, 그리고 다른 모델로 채점하는 것입니다.");
  }

  // ══ 10. 효과 ═══════════════════════════════════════════════════════
  {
    const s = frame("결과", `사진을 요청하게 하자 정답률이 ${r0(MC["E-none"].sonnet.pct)}에서 ${r0(E.photo.accuracy)}로 올랐다`);
    const bars = [["숫자 규칙", RB.rule_peak_current_p90.accuracy], ["학습 AI", RB.supervised_rf_reference.accuracy],
                  ["우리 AI\n사진 없이", MC["E-none"].sonnet.pct], ["우리 AI\n사진 요청", E.photo.accuracy]];
    const last = bars.length - 1;
    t(s, "그림 6. 같은 시험 58문제의 정답률 (날림·정상 반반, 찍으면 50%)", { x: M, y: 1.62, w: 7.2, h: 0.35, fontSize: 14, bold: true });
    s.addChart(pres.charts.BAR, [
      { name: "비교", labels: bars.map(b => b[0]), values: bars.map((b, i) => i === last ? 0 : Math.round(b[1])) },
      { name: "우리", labels: bars.map(b => b[0]), values: bars.map((b, i) => i === last ? Math.round(b[1]) : 0) },
    ], { x: M, y: 2.05, w: 7.2, h: 4.2, barDir: "col", barGrouping: "stacked", barGapWidthPct: 60,
         chartColors: [C.light, C.spark], showLegend: false,
         showValue: true, dataLabelPosition: "inEnd", dataLabelFormatCode: "0\"%\";;;", dataLabelColor: "FFFFFF",
         dataLabelFontSize: 16, dataLabelFontBold: true, dataLabelFontFace: "+mn-lt",
         catAxisLabelColor: C.body, catAxisLabelFontSize: 14, catAxisLabelFontFace: "+mn-lt",
         valAxisMaxVal: 100, valAxisMinVal: 0, valAxisLabelColor: C.muted, valAxisLabelFontSize: 11, valAxisLabelFontFace: "+mn-lt",
         valGridLine: { color: "E5E8EC", size: 0.5 }, catGridLine: { style: "none" } });
    rect(s, M + 4.9, 2.12, 2.2, 0.42, C.hi, [C.hiLine, 1]);
    t(s, `사진 없이보다 +${Math.round(E.photo.accuracy - MC["E-none"].sonnet.pct)}%p`, { x: M + 4.9, y: 2.12, w: 2.2, h: 0.42, fontSize: 13.5, bold: true, color: C.hiText, align: "center", valign: "middle" });
    // 학습 AI 와 정답률은 비슷(p = 0.18) — 차이는 준비물: 학습 AI 는 5-fold 마다 판정 라벨 394개(493건의 4/5)로 학습 (scripts/95 · 94 와 같은 설정)
    const RF_TRAIN = 394;
    const rx = 8.3, rw = W - M - rx;
    t(s, "읽는 법", { x: rx, y: 1.65, w: rw, h: 0.4, fontSize: 20, bold: true, color: C.blue });
    hline(s, rx, 2.12, rw, C.navy, 1.5);
    const nz = Math.round(MC["E-none"].sonnet.explode_recall * E.photo.explode_n / 100);
    t(s, [
      { text: `날림을 ${nz}개에서 ${E.photo.explode_hit}개 찾았다 (${E.photo.explode_n}개 중)`, options: { bullet: true, breakLine: true } },
      { text: `정상은 ${E.photo.good_n}개 중 ${E.photo.good_hit}개를 정상으로 봤다`, options: { bullet: true, breakLine: true } },
      { text: `학습 AI와는 비슷하다. 다만 학습 AI는 정답 ${RF_TRAIN}개로 배웠고, 우리 AI는 정답 없이 시작한다`, options: { bullet: true } },
    ], { x: rx, y: 2.3, w: rw, h: 3.6, fontSize: 17, paraSpaceAfter: 14, lineSpacingMultiple: 1.1 });
    const pv = x => (x < 0.001 ? "< 0.001" : x.toFixed(x < 0.01 ? 3 : 2));
    cite(s, `같은 문제끼리 비교한 McNemar 정확 검정 p값: 사진 없이 대비 ${pv(PT.photo_vs_none.p_two_sided)}, 숫자 규칙 대비 ${pv(PT.photo_vs_rule.p_two_sided)}, 학습 AI 대비 ${pv(PT.photo_vs_rf.p_two_sided)}. 원 자료 eval/results/tier_e_paired.json`);
    s.addNotes(`같은 시험 58문제로 비교했습니다. 날림과 정상이 반반이라 아무렇게나 찍으면 50%입니다. 숫자 규칙은 ${r0(RB.rule_peak_current_p90.accuracy)}, 정답 수백 개로 학습한 AI는 ${r0(RB.supervised_rf_reference.accuracy)}, 우리 AI도 사진 없이는 ${r0(MC["E-none"].sonnet.pct)}였습니다. 사진을 요청하게 하자 ${r0(E.photo.accuracy)}로 올랐습니다. 특히 날림은 사진 없이 하나도 못 찾았는데, 사진을 요청하자 ${E.photo.explode_n}개 중 ${E.photo.explode_hit}개를 찾았습니다. 같은 문제끼리 짝지어 비교하면, 사진 없이 할 때(${pfmt(PT.photo_vs_none.p_two_sided)})나 숫자 규칙(${pfmt(PT.photo_vs_rule.p_two_sided)})보다 나은 건 우연이 아닙니다. 학습 AI와는 비슷한 수준입니다(${pfmt(PT.photo_vs_rf.p_two_sided)}). 다만 학습 AI는 정답 ${RF_TRAIN}개를 보고 배웠고, 우리 AI는 정답을 하나도 보지 않은 채 무엇을 찍을지 스스로 정하고 근거를 달았습니다. 정답 라벨을 모으기 어려운 현장에서는 이 차이가 큽니다.`);
  }

  // ══ 11. 바꿔치기 ═════════════════════════════════════════════════════
  {
    const s = frame("결과", `사진을 다른 것으로 바꾸면 정답률이 ${r0(E.swap.accuracy)}로 떨어진다`);
    const half = [
      ["이 용접의 진짜 사진을 주면", "RGB_323F.jpg", r0(E.photo.accuracy), C.spark],
      ["다른 용접 사진으로 몰래 바꾸면", "RGB_310F.jpg", r0(E.swap.accuracy), C.faint],
    ];
    s.addShape(pres.shapes.LINE, { x: W / 2, y: 1.75, w: 0, h: 3.6, line: { color: C.rule, width: 0.75 } });
    half.forEach(([head, ph, v, col], i) => {
      const x = M + i * (CW / 2 + 0.25);
      t(s, head, { x, y: 1.7, w: 5.6, h: 0.45, fontSize: 18, bold: true });
      const pd = 2.75, py = 2.35;
      photo(s, ph, x, py, pd, [i ? C.rule : C.spark, i ? 0.75 : 2]);
      if (!i) mark(s, x + 0.41 * pd, py + 0.47 * pd, 0.2, x + 0.12, py + 0.15, "튄 쇳조각", 1.35);
      t(s, [{ text: v, options: { fontSize: 54, bold: true, color: col, breakLine: true } }, { text: "정답률", options: { fontSize: 15, color: C.muted } }],
        { x: x + pd + 0.35, y: 2.75, w: 2.4, h: 1.7, align: "center", valign: "middle" });
    });
    t(s, [{ text: "다른 환자의 엑스레이를 받은 의사가 오진하듯, 결론이 사진을 따라 바뀐다.", options: { bold: true, breakLine: true } },
          { text: `같은 문제끼리 비교: 진짜 사진에서만 맞힌 ${E.photo_vs_swap.only_photo_ref}문제, 바꿔치기에서만 맞힌 ${E.photo_vs_swap.only_swap_ref}문제 (${pfmt(E.photo_vs_swap.p_two_sided)})`, options: { color: C.muted, fontSize: 14.5 } }],
      { x: M, y: 5.65, w: CW, h: 0.95, fontSize: 17, lineSpacingMultiple: 1.2 });
    cite(s, PHOTO_CREDIT);
    s.addNotes(`AI가 정말 사진을 보는지, 그냥 그럴듯하게 말하는지 확인하려고 사진을 몰래 바꿔 봤습니다. 진짜 사진을 주면 ${r0(E.photo.accuracy)}, 다른 용접 사진으로 바꾸면 ${r0(E.swap.accuracy)}로 떨어집니다. 다른 환자의 엑스레이를 주면 의사가 오진하는 것과 같습니다. 결론이 사진 내용을 따라 바뀐다는 뜻입니다. 같은 문제끼리 보면 진짜 사진에서만 맞힌 문제가 ${E.photo_vs_swap.only_photo_ref}개, 바꿔치기에서만 맞힌 문제는 ${E.photo_vs_swap.only_swap_ref}개라 우연이 아닙니다.`);
  }

  // ══ 12. 결론 ═══════════════════════════════════════════════════════
  {
    const s = frame("결론", "AI가 모를 때 사진을 부탁하게 하니 불량을 더 잘 찾았다");
    const lw = 8.1;
    t(s, "결론", { x: M, y: 1.65, w: lw, h: 0.4, fontSize: 20, bold: true, color: C.blue });
    hline(s, M, 2.12, lw, C.navy, 1.5);
    t(s, [
      { text: "AI가 모르면 무엇을 찍을지 스스로 정해서 요청한다", options: { bullet: true, breakLine: true } },
      { text: "합격품 사진과 비교해 읽고, 근거를 달아 결론을 낸다", options: { bullet: true, breakLine: true } },
      { text: `날림을 ${E.photo.explode_hit}개 찾았고, 사진을 바꾸면 정답률이 ${r0(E.swap.accuracy)}로 떨어졌다`, options: { bullet: true } },
    ], { x: M, y: 2.3, w: lw, h: 2.1, fontSize: 17, paraSpaceAfter: 12 });
    t(s, "한계와 다음 단계", { x: M, y: 4.55, w: lw, h: 0.4, fontSize: 20, bold: true, color: C.blue });
    hline(s, M, 5.02, lw, C.navy, 1.5);
    t(s, `날림 ${fz.total}개 중 ${fz.total - E.photo.explode_hit}개는 아직 놓친다. 그중 ${fz.reader_saw_nothing}개는 사진에 흔적이 없었다. 현장에서 직접 찍은 사진으로 검증하는 것이 다음 단계다.`,
      { x: M, y: 5.15, w: lw, h: 1.1, fontSize: 16, lineSpacingMultiple: 1.2 });
    const qx = 9.2, qd = 2.35;
    img(s, AS("demo_qr.png"), qx + 0.4, 1.75, qd, qd, "시연 다시 보기 QR", [C.rule, 0.75]);
    t(s, [{ text: "시연 다시 보기", options: { bold: true, color: C.navy, breakLine: true } }, { text: DEMO_URL, options: { fontSize: 12.5, color: C.muted } }],
      { x: qx - 0.2, y: 4.2, w: 3.55, h: 0.75, fontSize: 16, align: "center" });
    hline(s, qx - 0.2, 5.1, 3.55, C.rule, 0.5);
    t(s, [{ text: "코드와 실험 자료", options: { bold: true, color: C.navy, breakLine: true } }, { text: REPO_URL, options: { fontSize: 12.5, color: C.muted } }],
      { x: qx - 0.2, y: 5.25, w: 3.55, h: 0.75, fontSize: 16, align: "center" });
    s.addNotes(`정리하겠습니다. 처음 질문, AI가 모를 때 사진을 요청하게 하면 더 잘 찾는가에 대한 답은 그렇다입니다. 사진 없이는 날림을 하나도 못 찾았는데 사진을 요청하자 ${E.photo.explode_hit}개를 찾았고, 사진을 바꿔치기하면 정답률이 ${r0(E.photo.accuracy)}에서 ${r0(E.swap.accuracy)}로 떨어져 AI가 실제로 사진을 보고 판단한다는 것도 확인했습니다. 다만 날림 ${fz.total}개 중 ${fz.total - E.photo.explode_hit}개는 아직 놓칩니다. 오른쪽 QR로 오늘 본 시연을 다시 볼 수 있습니다. 답하는 AI에서 묻는 AI로. 감사합니다.`);
  }

  // ══ 부록 A. 점용접 그림 ═══════════════════════════════════════════════
  {
    const s = frame("부록", "부록 A. 날림은 튄 쇳물 자국이 사진에 남는다");
    const cx = M + 2.0;
    rect(s, cx, 2.0, 1.1, 1.05, "B8733F");
    rect(s, M + 0.4, 3.1, 4.3, 0.32, "9CA3AF");
    rect(s, M + 0.4, 3.47, 4.3, 0.32, "C3C8CF");
    s.addShape(pres.shapes.OVAL, { x: cx + 0.05, y: 3.17, w: 1.0, h: 0.55, fill: { color: C.spark }, line: { type: "none" } });
    rect(s, cx, 3.85, 1.1, 1.05, "B8733F");
    t(s, "전극: 누르면서 전기를 흘림", { x: cx + 1.3, y: 2.3, w: 2.6, h: 0.45, fontSize: 14 });
    t(s, "철판 2장", { x: M + 4.8, y: 3.25, w: 1.2, h: 0.4, fontSize: 14 });
    t(s, "녹아 붙은 점", { x: cx + 1.3, y: 4.15, w: 2.3, h: 0.4, fontSize: 14, bold: true, color: C.spark });
    t(s, "그림 A1. 점용접은 전기 열로 두 철판을 점 하나로 붙인다. 자동차 한 대에 이런 점이 수천 개 들어간다.", { x: M, y: 5.2, w: 6.0, h: 0.65, fontSize: 12.5, color: C.muted });
    const x = 7.05, pd = 2.6;
    photo(s, "RGB_310F.jpg", x, 1.95, pd);
    photo(s, "RGB_323F.jpg", x + 2.95, 1.95, pd, [C.spark, 1.5]);
    t(s, "정상", { x, y: 1.95 + pd + 0.08, w: pd, h: 0.35, fontSize: 15, bold: true, align: "center" });
    t(s, "날림", { x: x + 2.95, y: 1.95 + pd + 0.08, w: pd, h: 0.35, fontSize: 15, bold: true, color: C.spark, align: "center" });
    t(s, "그림 A2. 같은 설정으로 용접한 정상과 날림. 날림은 용접 중 녹은 쇳물이 밖으로 튀어나가 자국이 남는다. 공정 기록으로는 잘 안 보여 현장에서는 용접 자국을 눈으로 본다.",
      { x, y: 5.05, w: 5.55, h: 0.9, fontSize: 12.5, color: C.muted });
    cite(s, PHOTO_CREDIT);
    s.addNotes("점용접 질문이 나오면 쓰는 부록입니다. 점용접은 두 철판을 전극으로 누르면서 전기를 흘려, 그 열로 점 하나를 녹여 붙이는 방식입니다. 자동차 한 대에 이런 점이 수천 개 들어갑니다. 가장 까다로운 불량 중 하나가 '날림'인데, 용접 중에 녹은 쇳물이 밖으로 튀어나가는 현상입니다. 오른쪽 두 사진은 같은 설정으로 용접한 정상과 날림입니다. 공정 기록으로는 잘 안 보여서, 현장에서는 용접 자국을 눈으로 봅니다.");
  }

  // ══ 부록 B. 사진과 정답 ═══════════════════════════════════════════════
  {
    const RC = N.rsw_classes;
    const s = frame("부록", "부록 B. 사진과 정답은 어디서 왔나");
    deflist(s, M, 1.75, 7.0, 1.1, [
      ["사진", "멕시코 케레타로 자치대학(UAQ)이 공개한 RSW Insights 데이터셋 (Mendeley Data, CC BY 4.0). 실험실 점용접 495회마다 용접 자국 앞·뒷면 사진, 열화상, 공정 기록이 있다."],
      ["정답", "데이터셋 제공자가 매긴 분류 (정상, 날림, 불량). 우리는 라벨을 만들거나 고치지 않았다."],
      ["주의", "분류 기준은 데이터셋에 적혀 있지 않다. 날림의 인장강도는 정상과 비슷해서, 강도 미달이 아니라 용접 중 금속이 튄 현상을 기록한 분류로 보인다.", C.spark],
    ], { rowH: 1.2, size: 14 });
    t(s, "표 B1. 제공자 분류별 용접 수와 시험 결과 평균", { x: 8.1, y: 1.4 + 0.3, w: 4.6, h: 0.35, fontSize: 13, bold: true });
    rtable(s, 8.1, 2.15, [1.55, 0.85, 1.15, 1.08], [
      ["제공자 분류", "용접 수", "인장강도\n평균", "너깃 지름\n평균"],
      ["정상 (Good)", String(RC.Good.n), `${RC.Good.pull_mean.toLocaleString()} N`, `${RC.Good.nugget_mean} mm`],
      [{ text: "날림 (Explode)", bold: true, color: C.spark }, String(RC.Explode.n), { text: `${RC.Explode.pull_mean.toLocaleString()} N`, bold: true, color: C.spark }, `${RC.Explode.nugget_mean} mm`],
      ["불량 (Bad)", String(RC.Bad.n), `${RC.Bad.pull_mean.toLocaleString()} N`, `${RC.Bad.nugget_mean} mm`],
    ], { rowH: 0.6, size: 13.5, headSize: 12, align: ["left", "right", "right", "right"] });
    t(s, "같은 설정끼리 짝지어 날림 29, 정상 29를 시험 문제로 썼다. 불량은 설정값만으로 구별돼 뺐다.", { x: 8.1, y: 4.75, w: 4.6, h: 0.75, fontSize: 13, color: C.muted });
    s.addNotes(`예상 질문: 사진은 어디서 났고 불량인지 어떻게 알았나. 답: 멕시코 케레타로 자치대학이 공개한 데이터셋이고, 용접마다 사진과 제공자의 분류가 있습니다. 정답은 그 분류를 그대로 썼고 우리가 만들지 않았습니다. 다만 분류 기준은 데이터셋에 적혀 있지 않습니다. 날림 용접의 인장강도가 정상과 비슷해서(${RC.Explode.pull_mean} N 대 ${RC.Good.pull_mean} N), 강도 미달이 아니라 용접 중 금속이 튄 현상을 기록한 분류로 보입니다. 이 점은 한계로 보고서에 적었습니다.`);
  }

  // ══ 부록 C. 개발 과정 ═════════════════════════════════════════════════
  {
    const s = frame("부록", "부록 C. 막힌 곳 4개를 차례로 풀었다");
    const st = [
      ["사진이 없으면\n날림을 못 찾는다", "사진 요청 기능", `날림 0 → ${r0(MC["E-photo"].sonnet.explode_recall)}`],
      ["AI가 미세한\n흔적을 못 본다", "합격품 사진과 비교", "구별력 3%p → 35%p"],
      ["사진을 보고도\n숫자를 더 믿는다", "보기 전 선언 지키기", "사진을 따르게 됨"],
      ["앞면에 흔적이\n없는 날림", "뒷면 촬영 허용", `날림 ${r0(E.front_only.explode_recall)} → ${r0(E.photo.explode_recall)}`],
    ];
    const w = 2.8, g = (CW - 4 * w) / 3, base = 6.45;
    st.forEach(([prob, fix, res], i) => {
      const x = M + i * (w + g), h = 1.45 + i * 0.72, y = base - h;
      const shade = ["DCE6F0", "B9CCE0", "7FA3C8", C.navy][i], dark = i === 3;
      rect(s, x, y, w, h, shade);
      t(s, `${i + 1}단계`, { x: x + 0.22, y: y + 0.15, w: w - 0.4, h: 0.35, fontSize: 13, bold: true, color: dark ? "DCE6F0" : C.navy });
      t(s, fix, { x: x + 0.22, y: y + 0.5, w: w - 0.4, h: 0.45, fontSize: 17, bold: true, color: dark ? "FFFFFF" : C.body });
      t(s, res, { x: x + 0.22, y: y + 0.95, w: w - 0.4, h: 0.4, fontSize: 14, bold: true, color: dark ? "FFD8C2" : C.spark });
      t(s, prob, { x, y: y - 0.82, w, h: 0.75, fontSize: 14, color: C.muted, valign: "bottom" });
    });
    t(s, `4단계에선 "어느 면이든 찍을 수 있다"고만 알렸는데,\nAI가 ${E.asked_back[1]}건 중 ${E.asked_back[0]}건에서 스스로 뒷면을 요청했다.`,
      { x: M, y: 1.7, w: 6.6, h: 0.8, fontSize: 15, bold: true, color: C.navy });
    s.addNotes(`한 번에 된 것은 아닙니다. 막힌 곳 네 개를 차례로 풀었습니다. 처음엔 사진이 없으면 날림을 못 찾아서 사진 요청 기능을 넣었습니다. 다음엔 AI가 미세한 흔적을 못 봐서 합격품 사진을 옆에 놓고 비교하게 했습니다. 그다음엔 사진을 보고도 숫자를 더 믿어서, 보기 전에 한 선언을 지키게 했습니다. 마지막으로 앞면에 흔적이 없는 날림이 남았는데, 어느 면이든 찍을 수 있다고만 알리자 AI가 거의 모든 경우에 스스로 뒷면을 요청했고 날림 발견이 두 배가 됐습니다.`);
  }

  // ══ 부록 D. 측정 이력 ═════════════════════════════════════════════════
  {
    const s = frame("부록", "부록 D. 측정 이력과 정정");
    t(s, "표 D1. 같은 58문제에서 조건별 결과 (진단 Sonnet 5.5, 판독 Haiku 5.5, 채점 Opus 5.5)", { x: M, y: 1.6, w: CW, h: 0.35, fontSize: 13, bold: true });
    const end = rtable(s, M, 2.0, [1.2, 7.33, 1.8, 1.8], [
      ["실행", "조건", "정답률", "날림"],
      ["—", "사진 없음", r0(MC["E-none"].sonnet.pct), r0(MC["E-none"].sonnet.explode_recall)],
      ["—", "앞면 사진", r0(MC["E-photo"].sonnet.pct), r0(MC["E-photo"].sonnet.explode_recall)],
      [`#${E.front_only.run}`, "앞면 + 합격품 비교 + 보기 전 선언", r0(E.front_only.accuracy), r0(E.front_only.explode_recall)],
      [{ text: `#${E.run}`, bold: true }, { text: "앞·뒷면 + 합격품 비교 + 보기 전 선언 (최종)", bold: true }, { text: r0(E.photo.accuracy), bold: true, color: C.spark }, { text: r0(E.photo.explode_recall), bold: true, color: C.spark }],
      [`#${E.run}`, "↳ 바꿔치기 사진", r0(E.swap.accuracy), r0(E.swap.explode_recall)],
      ["—", "숫자 규칙 (최대 전류 > 같은 설정 상위 10%)", r0(RB.rule_peak_current_p90.accuracy), r0(RB.rule_peak_current_p90.explode_recall)],
      ["—", "학습 AI (랜덤 포레스트, 판정 라벨로 학습)", r0(RB.supervised_rf_reference.accuracy), r0(RB.supervised_rf_reference.explode_recall)],
    ], { rowH: 0.42, size: 14, align: ["left", "left", "right", "right"] });
    const fixes = [
      ["증거 가림 버그", "한 단계에 증거가 여러 개면 마지막 것만 AI에게 보였다. 고치고 다시 측정했다."],
      ["정답 누출 2건", "사건 요약의 라벨 필드, 증거 요약의 파일 이름. 지우고 누출 검사 테스트를 추가했다."],
      ["정답지 정정", "공장 데이터의 정답 '원인 불명'을 '기록 재활용'으로 고치고 다시 측정했다."],
    ];
    fixes.forEach(([k, d], i) => {
      const y = end + 0.25 + i * 0.4;
      t(s, k, { x: M, y, w: 2.3, h: 0.36, fontSize: 13.5, bold: true, color: C.spark });
      t(s, d, { x: M + 2.4, y, w: CW - 2.4, h: 0.36, fontSize: 13.5 });
    });
    s.addNotes(`최종 대 앞면만: 최종에서만 맞힘 ${E.final_vs_front.only_final}, 앞면만에서만 ${E.final_vs_front.only_front}, ${pfmt(E.final_vs_front.p_two_sided)} (경계). 10장 짝 검정 — 사진 요청 대 학습 AI: ${PT.photo_vs_rf.only_photo} 대 ${PT.photo_vs_rf.only_rf}, ${pfmt(PT.photo_vs_rf.p_two_sided)} (날림만 ${PT.photo_vs_rf_explode.only_photo} 대 ${PT.photo_vs_rf_explode.only_rf}, ${pfmt(PT.photo_vs_rf_explode.p_two_sided)}). 대 숫자 규칙: ${PT.photo_vs_rule.only_photo} 대 ${PT.photo_vs_rule.only_rule}, ${pfmt(PT.photo_vs_rule.p_two_sided)}. 대 사진 없이: ${PT.photo_vs_none.only_photo} 대 ${PT.photo_vs_none.only_none}, ${pfmt(PT.photo_vs_none.p_two_sided)}.`);
  }

  // ══ 부록 E. 공장 데이터 ═══════════════════════════════════════════════
  {
    const au = F.audit, kb = N.rule_baseline.kamp;
    const s = frame("부록", "부록 E. 공장 데이터의 이상은 '기록 재활용'이었다");
    t(s, `${au.dup_index_pct}% → ${au.reused_pct}%`, { x: M, y: 1.75, w: 5.6, h: 0.85, fontSize: 38, bold: true, color: C.spark });
    t(s, `알려진 중복 비율에서, 실제로 다른 날 기록과 수백 줄씩 똑같은 비율로. 순서를 섞으면 최대 ${au.chance_longest}줄이라 우연이 아니다.`, { x: M, y: 2.7, w: 5.6, h: 1.0, fontSize: 15 });
    t(s, "표 E1. 사건 유형별 원인 정답률", { x: 6.9, y: 1.65, w: 5.8, h: 0.35, fontSize: 13, bold: true });
    rtable(s, 6.9, 2.05, [2.75, 1.9, 1.18], [
      ["사건 유형", "AI", "규칙 한 줄"],
      ["A 조용한 수준 이동", `${r0(MC.A.sonnet.pct)} (Sonnet)`, r0(kb.A.pct)],
      ["C 알람 폭주", `${r0(N.conditions.full.C.M1_match.mean)} (Haiku)`, r0(kb.C.pct)],
      ["B 주입 고장 (주 변수)", `${r0(N.conditions.full.B.M2_primary_variable.mean)} (Haiku)`, r0(kb.B.pct)],
    ], { rowH: 0.52, size: 14.5, align: ["left", "right", "right"] });
    rect(s, M, 4.55, CW, 1.6, C.band);
    t(s, [{ text: "정직한 위치  ", options: { bold: true, color: C.navy } },
          { text: "결정적 신호(다른 날과의 연속 일치 비율)는 사람이 설계했고, 그 신호가 있으면 규칙 한 줄도 AI만큼 맞힌다. 신호 없이 원본 기록과 SQL만 주자 AI는 스스로 찾지 못했다(Sonnet 0%). 그래서 AI만의 기여는 사진 실험으로 주장한다." }],
      { x: M + 0.35, y: 4.55, w: CW - 0.7, h: 1.6, fontSize: 15, valign: "middle", lineSpacingMultiple: 1.2 });
    cite(s, "KAMP 저항 점용접 공정 데이터 (재배포 권한 미확인으로 레포에는 받는 방법만). 분석: docs/14-data-reuse-finding.md");
    s.addNotes(`공장 데이터 질문이 나오면 쓰는 부록입니다. 실제 공장 데이터의 이상 신호를 따라가 보니, 기록의 ${au.reused_pct}%가 다른 날 기록과 수백 줄씩 똑같았습니다. 설비 고장이 아니라 기록이 재활용된 것입니다. 다만 이 신호는 제가 설계했고, 신호가 있으면 규칙 한 줄로도 맞힙니다. 그래서 공장 데이터에서는 AI가 규칙보다 낫다고 주장하지 않습니다. AI만의 기여는 사진을 요청해서 판단하는 부분이고, 그건 사진 실험으로 보여드렸습니다.`);
  }

  // ══ 부록 F. 남은 숙제 ═════════════════════════════════════════════════
  {
    const s = frame("부록", "부록 F. 날림의 절반 이상은 아직 놓친다");
    t(s, "그림 F1. 날림 29개가 걸러지는 단계", { x: M, y: 1.65, w: 6.2, h: 0.35, fontSize: 13, bold: true });
    const rows = [["날림 불량", fz.total, C.rule], ["사진에서 이상을 찾음", fz.reader_flagged, C.blue], ["날림이라고 결론", fz.flagged_and_concluded, C.spark]];
    rows.forEach(([l, v, col], i) => {
      const y = 2.1 + i * 0.95, w = 5.0 * v / fz.total;
      t(s, l, { x: M, y, w: 4, h: 0.35, fontSize: 15 });
      rect(s, M, y + 0.4, w, 0.4, col);
      t(s, `${v}개`, { x: M + w + 0.12, y: y + 0.4, w: 0.9, h: 0.4, fontSize: 16, bold: true, valign: "middle" });
    });
    rect(s, M, 5.05, 6.2, 1.25, C.band);
    t(s, [{ text: `${fz.reader_saw_nothing}개는 앞·뒷면 어디에서도 흔적을 못 찾았다.`, options: { bold: true, breakLine: true } },
          { text: "날림 분류 기준은 데이터에 적혀 있지 않다. 겉으로 흔적이 남지 않는 날림일 수 있다.", options: { color: C.muted } }],
      { x: M + 0.3, y: 5.05, w: 5.7, h: 1.25, fontSize: 14, valign: "middle", lineSpacingMultiple: 1.2 });
    const rx = 7.3, rw = W - M - rx;
    t(s, "그 밖의 한계", { x: rx, y: 1.65, w: rw, h: 0.4, fontSize: 18, bold: true, color: C.blue });
    hline(s, rx, 2.1, rw, C.navy, 1.5);
    const lims = [
      ["같은 시험 문제를 여러 번 썼다", "날림 사례가 31개뿐이라 개선은 여기서 멈췄다"],
      ["실행할 때마다 답이 조금 달라진다", "시연은 실제 실행 기록을 그대로 재생"],
      ["사진은 공개 데이터의 실제 사진", "현장에서 직접 찍는 검증은 다음 단계"],
    ];
    lims.forEach(([h, d], i) => {
      const y = 2.15 + i * 1.0;
      t(s, h, { x: rx, y: y + 0.1, w: rw, h: 0.4, fontSize: 16, bold: true });
      t(s, d, { x: rx, y: y + 0.52, w: rw, h: 0.4, fontSize: 13.5, color: C.muted });
      hline(s, rx, y + 0.98, rw, C.rule, 0.5);
    });
    t(s, [{ text: "다음 단계  ", options: { bold: true, color: C.spark } }, { text: "현장 검사 사진을 예시로 함께 보여주기" }],
      { x: rx, y: 5.4, w: rw, h: 0.5, fontSize: 15.5, valign: "middle" });
    s.addNotes(`한계도 말씀드립니다. 날림 ${fz.total}개 중 사진에서 이상을 찾은 건 ${fz.reader_flagged}개, 날림이라고 결론 낸 건 ${fz.flagged_and_concluded}개입니다. ${fz.reader_saw_nothing}개는 사진 어디에서도 흔적을 못 찾았는데, 날림을 어떤 기준으로 분류했는지 데이터에 적혀 있지 않아서, 겉으로 흔적이 남지 않는 날림일 수 있습니다. 또 날림 사례가 적어서 같은 시험 문제로 고치고 재기를 반복했습니다. 더 고치면 이 문제에만 맞춰질 수 있어서, 개선은 여기서 멈췄습니다.`);
  }

  // ══ 부록 G. 데이터와 출처 ═════════════════════════════════════════════
  {
    const s = frame("부록", "부록 G. 데이터와 출처");
    deflist(s, M, 1.7, CW, 2.1, [
      ["사진 실험", "RSW Insights: L. A. Dominguez Molina, Mendeley Data V3 (2025), CC BY 4.0. 용접 495회, 앞·뒷면 사진, 제공자 분류(기준 비공개)"],
      ["시험 문제", "날림 29 + 같은 설정의 정상 29 = 58건 (개발용 4건 제외). 같은 문제를 조건만 바꿔 비교"],
      ["사용 모델", "진단 Claude Sonnet 5.5, 사진 판독 Haiku 5.5, 채점 Opus 5.5 (진단과 다른 모델). Claude Code CLI로 실행. 측정별 버전은 eval/MODEL_VERSIONS.md"],
      ["공장 데이터", "KAMP 저항 점용접 공정 데이터. 재배포 권한이 확인되지 않아 레포에는 받는 방법만 적었다"],
      ["매뉴얼", `제조사 매뉴얼 ${F.manual_docs}종 ${F.manual_pages}쪽, 도면 ${F.diagrams_described}장. 레포에는 받는 방법만 적었다`],
      ["재현", `eval/run_tier_e.py (사진 실험), deck/export_numbers.py (발표 수치), deck/replay/demo.html (시연 재생, ${DEMO_URL})`],
    ], { rowH: 0.8, size: 14, labelSize: 15 });
    s.addNotes("데이터 출처 부록입니다. 모델 질문이 나오면: 진단은 Sonnet 5.5, 사진 판독은 Haiku 5.5, 채점은 진단과 다른 모델인 Opus 5.5입니다. 초기 시험 실행 몇 번은 버전이 바뀌기 전이라 옛 버전이었지만, 발표에 나온 숫자는 모두 5.5로 낸 것입니다.");
  }

  await pres.writeFile({ fileName: OUT });
  await applyTheme(OUT, THEME);
  await koreanFont(OUT);
  await addAnimations(OUT);
  console.log("→", OUT);
}

// 한글은 동아시아 글꼴(ea) 칸을 따른다. 테마의 ea 가 비어 있으면 윈도우가 아무 글꼴이나 고르므로 맑은 고딕으로 못 박는다.
async function koreanFont(file) {
  const JSZip = require("jszip");
  const zip = await JSZip.loadAsync(fs.readFileSync(file));
  for (const name of Object.keys(zip.files).filter(n => /^ppt\/(theme\/theme\d+|slides\/slide\d+|slideLayouts\/slideLayout\d+|slideMasters\/slideMaster\d+)\.xml$/.test(n))) {
    const x = await zip.file(name).async("string");
    const y = x.replace(/<a:ea typeface="(Courier New)?"/g, `<a:ea typeface="${FONT}"`);
    if (y !== x) zip.file(name, y);
  }
  for (const n of Object.keys(zip.files)) if (zip.files[n].dir) delete zip.files[n];   // zip.remove 는 안의 파일까지 지운다
  fs.writeFileSync(file, await zip.generateAsync({ type: "nodebuffer", compression: "DEFLATE" }));
}

// 'anim-<묶음>-<n>' 이름의 도형을 묶음별로 모아, 클릭할 때마다 한 묶음씩 서서히 나타나게 한다 (나타내기 · 페이드 0.3초).
// PowerPoint 가 직접 저장하는 <p:timing> 구조를 그대로 쓴다. 이 장들에는 다른 애니메이션이 없다.
async function addAnimations(file) {
  const JSZip = require("jszip");
  const zip = await JSZip.loadAsync(fs.readFileSync(file));
  for (const name of Object.keys(zip.files).filter(n => /^ppt\/slides\/slide\d+\.xml$/.test(n))) {
    let x = await zip.file(name).async("string");
    const groups = new Map();
    for (const m of x.matchAll(/<p:cNvPr\b[^>]*>/g)) {
      const id = (m[0].match(/\bid="(\d+)"/) || [])[1], nmv = (m[0].match(/\bname="anim-(\d+)-\d+"/) || [])[1];
      if (id && nmv) { if (!groups.has(+nmv)) groups.set(+nmv, []); groups.get(+nmv).push(id); }
    }
    if (!groups.size) continue;
    if (x.includes("<p:timing")) throw new Error(`${name}: 이미 애니메이션이 있다`);
    let n = 2;
    const clicks = [...groups.keys()].sort((a, b) => a - b).map(k => {
      const outer = ++n, inner = ++n;
      const effects = groups.get(k).map((spid, j) => {
        const e = ++n, set = ++n, fade = ++n;
        return `<p:par><p:cTn id="${e}" presetID="10" presetClass="entr" presetSubtype="0" fill="hold" nodeType="${j ? "withEffect" : "clickEffect"}">` +
          `<p:stCondLst><p:cond delay="0"/></p:stCondLst><p:childTnLst>` +
          `<p:set><p:cBhvr><p:cTn id="${set}" dur="1" fill="hold"><p:stCondLst><p:cond delay="0"/></p:stCondLst></p:cTn>` +
          `<p:tgtEl><p:spTgt spid="${spid}"/></p:tgtEl><p:attrNameLst><p:attrName>style.visibility</p:attrName></p:attrNameLst></p:cBhvr>` +
          `<p:to><p:strVal val="visible"/></p:to></p:set>` +
          `<p:animEffect transition="in" filter="fade"><p:cBhvr><p:cTn id="${fade}" dur="300"/><p:tgtEl><p:spTgt spid="${spid}"/></p:tgtEl></p:cBhvr></p:animEffect>` +
          `</p:childTnLst></p:cTn></p:par>`;
      }).join("");
      return `<p:par><p:cTn id="${outer}" fill="hold"><p:stCondLst><p:cond delay="indefinite"/></p:stCondLst><p:childTnLst>` +
        `<p:par><p:cTn id="${inner}" fill="hold"><p:stCondLst><p:cond delay="0"/></p:stCondLst><p:childTnLst>${effects}</p:childTnLst></p:cTn></p:par>` +
        `</p:childTnLst></p:cTn></p:par>`;
    }).join("");
    const timing = `<p:timing><p:tnLst><p:par><p:cTn id="1" dur="indefinite" restart="never" nodeType="tmRoot"><p:childTnLst>` +
      `<p:seq concurrent="1" nextAc="seek"><p:cTn id="2" dur="indefinite" nodeType="mainSeq"><p:childTnLst>${clicks}</p:childTnLst></p:cTn>` +
      `<p:prevCondLst><p:cond evt="onPrev" delay="0"><p:tgtEl><p:sldTgt/></p:tgtEl></p:cond></p:prevCondLst>` +
      `<p:nextCondLst><p:cond evt="onNext" delay="0"><p:tgtEl><p:sldTgt/></p:tgtEl></p:cond></p:nextCondLst></p:seq>` +
      `</p:childTnLst></p:cTn></p:par></p:tnLst></p:timing>`;
    const at = x.indexOf("<p:extLst") > x.indexOf("</p:clrMapOvr>") && x.indexOf("<p:extLst") > 0 ? x.indexOf("<p:extLst") : x.lastIndexOf("</p:sld>");
    x = x.slice(0, at) + timing + x.slice(at);
    zip.file(name, x);
    console.log(`  애니메이션 ${name}: 클릭 ${groups.size}번, 도형 ${[...groups.values()].flat().length}개`);
  }
  for (const k of Object.keys(zip.files)) if (zip.files[k].dir) delete zip.files[k];
  fs.writeFileSync(file, await zip.generateAsync({ type: "nodebuffer", compression: "DEFLATE" }));
}

build().catch(e => { console.error(e); process.exit(1); });
