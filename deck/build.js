// RootCause Stream 발표자료 생성기 — v4 (2026-11-23, academic-pptx 점검 반영: 본문 11장 · 질문 슬라이드 · 지표 통일 · 사진 출처)
//   이야기 순서: 날림은 숫자로 안 보인다 → 전문가는 가서 본다 + 질문 → 묻는 AI → 실제 화면 → 영상 → 63초 →
//               기술 → 효과 → 진짜 사진을 보나 → 결론(질문의 답 · 남은 숙제) | 부록 A~G
//   디자인: 장마다 메시지 하나 · 결론형 제목 · 큰 숫자 · 칸 나눈 배치 · 강조색 하나(불꽃 주황)
//   수치는 numbers.json(← export_numbers.py)에서만, 시연은 data/demo_runs/e323-ko.json(한국어 실제 실행)에서만 읽는다.
//   실행: .venv/bin/python deck/export_numbers.py && NODE_PATH=deck/node_modules node deck/build.js
const path = require("path");
const fs = require("fs");
const pptxgen = require("pptxgenjs");
const React = require("react");
const { renderToStaticMarkup } = require("react-dom/server");
const sharp = require("sharp");
const FA = require("react-icons/fa6");
const APPLY_THEME = process.env.APPLY_THEME_JS;
const applyTheme = APPLY_THEME && fs.existsSync(APPLY_THEME)
  ? require(APPLY_THEME).applyTheme
  : async () => console.warn("APPLY_THEME_JS 없음 — 테마 색 적용을 건너뜀");

const ROOT = path.resolve(__dirname, "..");
const N = JSON.parse(fs.readFileSync(path.join(__dirname, "numbers.json"), "utf8"));
const F = N.facts;
const E = N.tier_e_final;                       // run #84 — 최종 설계
const RB = N.rule_baseline.tier_e;
const PT = N.tier_e_paired.tests;           // 10장 짝 검정 (scripts/95_tier_e_paired.py)              // 규칙 · 지도학습 분류기
const MC = N.model_comparison.tiers;            // sonnet 사진 없음 · 앞면 사진
const DEMO = JSON.parse(fs.readFileSync(path.join(ROOT, "data/demo_runs/e323-ko.json"), "utf8"));   // 한국어 실제 실행 기록
const OUT = process.env.DECK_OUT || path.join(__dirname, "RootCause_Stream_발표자료.pptx");
// 글꼴: 맑은 고딕 (2026-11-24). Apple SD Gothic Neo 는 맥에만 있어, 윈도우에서 열면 다른 글꼴로 바뀌며
// 글자 폭이 13~15% 넓어져 줄이 넘친다. 맑은 고딕은 윈도우 전부와 맥용 PowerPoint 에 들어 있다.
const FONT = "Malgun Gothic";
const PH = p => path.join(ROOT, "data/photos/tier_e", p);
const AS = p => path.join(__dirname, "assets", p);

// ── 테마: 차콜 + 용접 불꽃 주황 하나. 보라는 '사람·사진'에만 아껴 쓴다 ────────────
const THEME = {
  name: "RootCause Spark",
  headFontFace: FONT,
  bodyFontFace: FONT,
  colors: {
    // 어두운 발표자료 (2026-11-22, 시연 화면과 한 세트): dk1 = 글자(밝음), lt1 = 바탕(어두움), lt2 = 카드
    dk1: "E6E8EB", lt1: "0E1116", dk2: "0B0D11", lt2: "161A21",
    accent1: "FF6A2B", accent2: "19C2A8", accent3: "FF5A5A",
    accent4: "F5B547", accent5: "8A93A0", accent6: "8B7CFF",
    hlink: "0F9D8A", folHlink: "6D5DF6",
  },
};
const HEX = THEME.colors;
const pres = new pptxgen();
pres.layout = "LAYOUT_WIDE";                // 13.333 × 7.5
pres.theme = { headFontFace: THEME.headFontFace, bodyFontFace: THEME.bodyFontFace };
pres.title = "RootCause Stream — 모르면, 먼저 물어보는 AI";
pres.author = "이재형";
const C = pres.SchemeColor;
const M = 0.7;
const r0 = v => `${Math.round(v)}%`;
const pfmt = p => (p < 0.001 ? "p < 0.001" : `p = ${p.toFixed(p < 0.01 ? 3 : 2)}`);
const t0 = DEMO.events[0].t;
const at = type => DEMO.events.find(e => e.type === type);
const secs = e => Math.round(e.t - t0);
const SUB = "B4BAC3";                          // 읽어야 하는 보조 글씨 (프로젝터에서 C.accent5 는 흐리다)
const soft = () => ({ type: "outer", blur: 10, offset: 3, angle: 90, color: "000000", opacity: 0.12 });

// ── 아이콘: react-icons → PNG (색을 입혀 미리 그린다) ───────────────────
const ICON = {};
async function icon(name, color) {
  const key = `${name}-${color}`;
  if (!ICON[key]) {
    const svg = renderToStaticMarkup(React.createElement(FA[name], { color: `#${color}`, size: 256 }));
    ICON[key] = "image/png;base64," + (await sharp(Buffer.from(svg)).png().toBuffer()).toString("base64");
  }
  return ICON[key];
}
const NEED = [
  ["FaCamera", HEX.accent1], ["FaCamera", HEX.accent6], ["FaCamera", "FFFFFF"], ["FaRobot", "FFFFFF"], ["FaRobot", HEX.accent1],
  ["FaHelmetSafety", "FFFFFF"], ["FaHelmetSafety", HEX.accent6], ["FaUserDoctor", HEX.accent5], ["FaXRay", HEX.accent6],
  ["FaStethoscope", HEX.accent5], ["FaIndustry", HEX.accent5], ["FaMagnifyingGlass", HEX.accent2], ["FaBookOpen", HEX.accent2],
  ["FaScrewdriverWrench", HEX.accent2], ["FaImage", HEX.accent6], ["FaCircleCheck", HEX.accent2], ["FaTriangleExclamation", HEX.accent4],
  ["FaCircleXmark", HEX.accent3], ["FaBolt", HEX.accent4], ["FaCarSide", HEX.accent5], ["FaMobileScreenButton", HEX.accent6],
  ["FaDesktop", HEX.accent2], ["FaListCheck", HEX.accent1], ["FaComments", HEX.accent6], ["FaGavel", HEX.accent1],
  ["FaShuffle", HEX.accent6], ["FaBrain", HEX.accent2], ["FaEye", HEX.accent6], ["FaShieldHalved", HEX.accent1],
  ["FaLink", HEX.accent1], ["FaQuoteLeft", HEX.accent1], ["FaClockRotateLeft", HEX.accent1], ["FaGithub", "8A9099"],
  ["FaLayerGroup", HEX.accent2], ["FaRotate", HEX.accent1], ["FaMicroscope", HEX.accent3], ["FaCircleQuestion", HEX.accent4],
  ["FaImage", HEX.accent1], ["FaUserDoctor", HEX.accent6],
];

// ── 레이아웃 ──────────────────────────────────────────────────────────
// 2026-11-26: 격자·빛 번짐 배경과 사방 테두리를 뺐다 (템플릿 티) — 단색 바탕 + 꼬리말 선 하나
pres.defineSlideMaster({ title: "DARK", background: { color: "0E1116" }, objects: [] });
pres.defineSlideMaster({
  title: "LIGHT",
  background: { color: "0E1116" },
  margin: [0.4, 0.7, 0.6, 0.7],
  slideNumber: { x: 12.3, y: 7.0, w: 0.5, h: 0.3, fontSize: 10, color: C.accent5, align: "right" },
  objects: [
    { line: { x: M, y: 6.93, w: 13.333 - 2 * M, h: 0, line: { color: "232933", width: 0.75 } } },
    { placeholder: { options: { name: "title", type: "title", x: M, y: 0.8, w: 11.9, h: 0.85,
        fontSize: 32, bold: true, color: C.text1, valign: "middle", margin: 0 }, text: "" } },
    { text: { text: "RootCause Stream", options: { x: M, y: 7.0, w: 4, h: 0.3, fontSize: 10, color: C.accent5, margin: 0 } } },
  ],
});

// ── 공통 조각 ─────────────────────────────────────────────────────────
function box(s, x, y, w, h, fill, opt = {}) {
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w, h, rectRadius: opt.r ?? 0.14, fill: { color: fill },
    line: opt.line ? { color: opt.line, width: opt.lineW || 1.5 } : { type: "none" }, shadow: opt.shadow ? soft() : undefined });
}
function dot(s, x, y, d, fill) { s.addShape(pres.shapes.OVAL, { x, y, w: d, h: d, fill: { color: fill }, line: { type: "none" } }); }
// 맑은 고딕은 같은 크기에서 Apple SD Gothic Neo 보다 글자가 크고 13~15% 넓다 → 글자 크기를 8% 줄여 같은 배치를 지킨다
const FS = 0.92;
const sc = v => (v ? Math.round(v * FS * 2) / 2 : v);
function txt(s, runs, o) {
  if (Array.isArray(runs)) runs = runs.map(r => (r && r.options && r.options.fontSize
    ? { ...r, options: { ...r.options, fontSize: sc(r.options.fontSize) } } : r));
  s.addText(runs, { isTextBox: true, margin: 0, valign: "top", ...o, ...(o && o.fontSize ? { fontSize: sc(o.fontSize) } : {}) });
}
// 큰 숫자 · 핵심 그림 뒤에 까는 빛 (Behance Cybersecurity · Keel 참고)
function glowAt(s, cx, cy, d, purple) {
  s.addImage({ path: AS(purple ? "glow_purple.png" : "glow_orange.png"), x: cx - d / 2, y: cy - d / 2, w: d, h: d, altText: "" });
}
function ico(s, name, color, x, y, d) {
  const data = ICON[`${name}-${color}`];
  if (!data) throw new Error(`아이콘 ${name}-${color} 을 NEED 에 추가하라`);
  s.addImage({ data, x, y, w: d, h: d, altText: name });
}
function iconDot(s, name, color, bg, x, y, d) { dot(s, x, y, d, bg); ico(s, name, color, x + d * 0.24, y + d * 0.24, d * 0.52); }
function arrow(s, x, y, w = 0.45, h = 0.38, color = "3A424E") {
  s.addShape(pres.shapes.RIGHT_ARROW, { x, y, w, h, fill: { color }, line: { type: "none" } });
}
function photo(s, file, x, y, d, cap, capColor = C.accent5, line) {
  if (line) s.addShape(pres.shapes.RECTANGLE, { x: x - 0.05, y: y - 0.05, w: d + 0.1, h: d + 0.1, fill: { color: line }, line: { type: "none" } });
  s.addImage({ path: PH(file), x, y, w: d, h: d, altText: cap || file });
  if (cap) txt(s, cap, { x: x - 0.2, y: y + d + 0.1, w: d + 0.4, h: 0.3, fontSize: 13, color: capColor, align: "center", bold: true });
}
// 참고 디자인 (Behance, 2026-11-22): ORYN 의 '■ 01 표식 · 얇은 격자선', Tensora 의 '회색 + 진한 두 톤 제목'
function twoTone(title, dim = "6B7280", strong = C.text1) {
  const [a, b] = title.includes("|") ? title.split("|") : ["", title];
  return [a ? { text: a, options: { color: dim } } : null, { text: b, options: { color: strong } }].filter(Boolean);
}
let SECTION = 0;
function light(kicker, title) {
  const s = pres.addSlide({ masterName: "LIGHT" });
  // 2026-11-26: 상단 '■ 01 라벨'과 회색·흰색 두 톤 제목을 뺐다 (템플릿 티). 부록만 제목 앞에 표시
  s.addText(kicker.startsWith("부록") ? `${kicker}. ${title}` : title, { placeholder: "title" });
  return s;
}
// 사진 출처 (CC BY 4.0 — 사진을 쓴 장마다 표기)
function credit(s, x = 6.4, y = 7.0, w = 5.8) {
  txt(s, "사진: RSW Insights (Dominguez Molina, 2025) · CC BY 4.0", { x, y, w, h: 0.28, fontSize: 10, color: "6B7280", align: "right" });
}
// 기술 꼬리표 — 어느 부분이 LLM·VLM·HITL 인지 (4장 대화 · 7장 타임라인)
function tag(s, text, col, x, y, align = "left") {
  const w = 0.3 + [...text].reduce((a, ch) => a + (/[가-힣]/.test(ch) ? 0.155 : 0.085), 0);
  const bx = align === "center" ? x - w / 2 : align === "right-edge" ? x - w : x;
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: bx, y, w, h: 0.27, rectRadius: 0.13, fill: { color: "1D222B" }, line: { color: col, width: 1 } });
  txt(s, text, { x: bx, y, w, h: 0.27, fontSize: 11.5, bold: true, color: col, align: "center", valign: "middle" });
}
// 채팅 말풍선 (who: 'ai' | 'human')
function bubble(s, who, x, y, w, h, text, size = 15) {
  const ai = who === "ai";
  iconDot(s, ai ? "FaRobot" : "FaHelmetSafety", "FFFFFF", ai ? HEX.accent1 : HEX.accent6, ai ? x : x + w + 0.15, y, 0.55);
  const bx = ai ? x + 0.7 : x;
  box(s, bx, y, w - 0.7 + (ai ? 0 : 0.7) - (ai ? 0 : 0.7), h, ai ? "1D222B" : "241F45", { r: 0.18 });
  if (text) txt(s, text, { x: bx + 0.22, y: y + 0.14, w: w - 0.7 - 0.44, h: h - 0.24, fontSize: size, color: C.text1, valign: "middle" });
  return bx;
}

async function build() {
  for (const [n, c] of NEED) await icon(n, c);
  const req = at("photo_request"), reads = DEMO.events.filter(e => e.type === "photo_read"), fin = at("final");
  const inc = at("incident").summary, lg = inc.logged_during_weld, pop = inc.same_setpoint_population;
  const inBand = (v, d) => v >= d.p10 && v <= d.p90;

  // ══ 1. 표지 ═════════════════════════════════════════════════════════
  {
    const s = pres.addSlide({ masterName: "DARK" });
    txt(s, [{ text: "RootCause Stream", options: { bold: true, color: C.accent1 } }, { text: "   LLM 서비스 개발 프로젝트", options: { color: "8A9099" } }], { x: M, y: 0.7, w: 8, h: 0.4, fontSize: 15 });
    txt(s, [{ text: "모르면,\n", options: { color: "FFFFFF" } }, { text: "먼저 물어보는 AI", options: { color: "FFFFFF" } }],
        { x: M, y: 1.55, w: 7.0, h: 2.6, fontSize: 58, bold: true });
    txt(s, "공장 설비의 불량 원인을 찾다가, 기록만으로 모르면\n작업자에게 \"이걸 찍어 주세요\"라고 요청하는 진단 AI",
      { x: M, y: 4.55, w: 7.0, h: 1.0, fontSize: 20, color: "C9CDD2" });
    photo(s, "RGB_323F.jpg", 8.35, 0.9, 4.3, null, null, "2A3038");
    box(s, 7.55, 4.75, 5.2, 1.25, "FFFFFF", { r: 0.2, shadow: true });
    iconDot(s, "FaRobot", "FFFFFF", HEX.accent1, 7.75, 4.98, 0.8);
    txt(s, [{ text: "AI\n", options: { bold: true, color: C.accent1, fontSize: 13 } },
            { text: "이 용접, 뒷면도 찍어 주실 수 있나요?", options: { color: "15181D", fontSize: 17, bold: true } }],
        { x: 8.75, y: 5.0, w: 3.9, h: 0.85 });
    txt(s, "실제 용접 사진 (날림 불량)", { x: 8.35, y: 6.15, w: 4.3, h: 0.3, fontSize: 12, color: "8A9099", align: "right" });
    credit(s, 8.35, 6.45, 4.3);
    txt(s, "이재형, 2026년 11월", { x: M, y: 6.9, w: 5, h: 0.3, fontSize: 12, color: "8A9099" });
    s.addNotes(`안녕하세요. 제가 만든 건 '모르면 먼저 물어보는 AI'입니다. 공장에서 불량이 났을 때 AI가 원인을 찾다가, 기록만으로 모르겠으면 작업자에게 '이걸 찍어 주세요'라고 요청하고 그 사진으로 결론을 냅니다. 오늘은 이 아이디어가 실제로 효과가 있는지를 실제 용접 사진으로 확인한 결과를 말씀드리겠습니다.`);
  }

  // ══ 2. 배경 · 문제 — 날림은 숫자로는 안 보이고 사진에는 보인다 ═══════════
  {
    const s = light("배경 · 문제", "날림 불량은 숫자에는 안 잡히는데 사진에는 보인다");
    box(s, M, 1.9, 5.95, 1.2, C.background2);
    txt(s, [{ text: "점용접  ", options: { bold: true, color: C.accent1 } }, { text: "두 철판을 전기 열로 붙인 점. 차 한 대에 수천 개\n", options: { color: C.text1 } },
            { text: "날림  ", options: { bold: true, color: C.accent3 } }, { text: "용접 중 녹은 쇳물이 밖으로 튀어나가는 불량", options: { color: C.text1 } }],
        { x: M + 0.3, y: 2.0, w: 5.5, h: 1.0, fontSize: 16, valign: "middle", lineSpacingMultiple: 1.3 });
    const rows = [
      ["최대 전류", `${Math.round(lg.peak_current_A).toLocaleString()} A`, inBand(lg.peak_current_A, pop.peak_current_A)],
      ["평균 전류", `${Math.round(lg.mean_current_A).toLocaleString()} A`, inBand(lg.mean_current_A, pop.mean_current_A)],
      ["누르는 힘", `${Math.round(lg.peak_force_N)} N`, inBand(lg.peak_force_N, pop.peak_force_N)],
    ];
    txt(s, `이 용접의 기록을 같은 설정 용접 ${pop.n_welds}회와 비교하면`, { x: M, y: 3.3, w: 6, h: 0.35, fontSize: 15, color: SUB });
    rows.forEach(([k, v, ok], i) => {
      const y = 3.75 + i * 0.8;
      box(s, M, y, 5.95, 0.7, C.background2);
      txt(s, k, { x: M + 0.3, y: y + 0.15, w: 1.6, h: 0.4, fontSize: 16, color: SUB });
      txt(s, v, { x: M + 2.0, y: y + 0.1, w: 2.2, h: 0.5, fontSize: 22, bold: true, color: C.text1 });
      txt(s, ok ? "보통 범위" : "범위 끝자락", { x: M + 4.45, y: y + 0.17, w: 1.1, h: 0.38, fontSize: 15, bold: true, color: ok ? C.accent2 : "F5B547" });
    });
    const cnt = r => Math.round(r * E.photo.explode_n / 100);
    txt(s, [{ text: `숫자만 보는 방법은 날림 ${E.photo.explode_n}개 중 `, options: { color: SUB } },
            { text: `규칙 ${cnt(RB.rule_peak_current_p90.explode_recall)}개, 학습 AI ${cnt(RB.supervised_rf_reference.explode_recall)}개`, options: { bold: true, color: C.accent3 } },
            { text: "만 찾았다", options: { color: SUB } }],
        { x: M, y: 6.25, w: 6.4, h: 0.45, fontSize: 16 });
    arrow(s, 6.85, 3.75, 0.6, 0.5);
    photo(s, "RGB_323F.jpg", 7.75, 1.95, 4.0, null, null, HEX.accent3);
    s.addShape(pres.shapes.OVAL, { x: 9.15, y: 3.3, w: 1.2, h: 1.2, fill: { type: "none" }, line: { color: HEX.accent4, width: 4 } });
    txt(s, [{ text: "실제로는 날림 불량\n", options: { bold: true, color: C.accent3, fontSize: 20 } },
            { text: "가운데 튀어나온 쇳조각이 보인다", options: { color: C.text1, fontSize: 16 } }],
        { x: 7.75, y: 6.05, w: 4.6, h: 0.75 });
    credit(s);
    s.addNotes(`점용접은 두 철판을 전기 열로 녹여 붙이는 방식이고, 자동차 한 대에 수천 개가 들어갑니다. 까다로운 불량 중 하나가 '날림'인데, 용접 중 녹은 쇳물이 밖으로 튀어나가는 현상입니다. 이 용접의 기록을 같은 설정의 다른 용접들과 비교하면 최대 전류와 누르는 힘은 보통 범위이고, 평균 전류만 범위 끝자락입니다. 숫자만 보면 알 수 없습니다. 실제로는 날림이었고, 사진에는 가운데 튀어나온 쇳조각이 보입니다. 숫자만 보는 규칙은 날림 ${E.photo.explode_n}개 중 ${cnt(RB.rule_peak_current_p90.explode_recall)}개, 정답 수백 개로 학습한 AI도 ${cnt(RB.supervised_rf_reference.explode_recall)}개밖에 못 찾습니다.`);
  }

  // ══ 4. 전문가는 가서 본다 ═════════════════════════════════════════════
  {
    const s = light("아이디어", "전문가는 애매하면 직접 가서 본다");
    const rows = [
      ["FaUserDoctor", HEX.accent5, "의사", "증상만으로는 애매하다", "FaXRay", "\"엑스레이 찍어 보자\"", "사진을 읽고 진단"],
      ["FaIndustry", HEX.accent5, "숙련 엔지니어", "기록만으로는 애매하다", "FaCamera", "\"가서 직접 보자\"", "눈으로 확인하고 원인 확정"],
    ];
    rows.forEach(([ic, icol, who, a, ic2, b, c], i) => {
      const y = 2.05 + i * 1.75;
      box(s, M, y, 11.9, 1.45, C.background2);
      txt(s, who, { x: M + 0.4, y: y + 0.5, w: 2.4, h: 0.45, fontSize: 18, bold: true, color: C.text1 });
      txt(s, a, { x: M + 3.1, y: y + 0.5, w: 2.8, h: 0.45, fontSize: 17, color: C.text1 });
      arrow(s, M + 5.85, y + 0.55);
      txt(s, b, { x: M + 6.6, y: y + 0.5, w: 3.0, h: 0.45, fontSize: 17, bold: true, color: C.accent6 });
      arrow(s, M + 9.7, y + 0.55);
      txt(s, c, { x: M + 10.3, y: y + 0.38, w: 1.5, h: 0.7, fontSize: 15, color: C.text1 });
    });
    box(s, M, 5.75, 11.9, 0.95, "2A1A12");
    txt(s, [{ text: "질문  ", options: { bold: true, color: C.accent1 } },
            { text: "AI도 모를 때 사진을 요청하게 하면, 기록만 볼 때보다 불량을 더 잘 찾을까?", options: { bold: true, color: C.text1 } }],
        { x: M + 0.4, y: 5.98, w: 11.2, h: 0.5, fontSize: 20, valign: "middle" });
    s.addNotes("사람 전문가는 이럴 때 어떻게 할까요. 의사는 증상만으로 애매하면 엑스레이를 찍자고 합니다. 숙련 엔지니어도 기록만으로 애매하면 가서 직접 봅니다. 그래서 이 프로젝트의 질문은 하나입니다. AI도 모를 때 사진을 요청하게 하면, 기록만 볼 때보다 불량을 더 잘 찾을까?");
  }

  // ══ 5. 묻는 AI — 채팅으로 ═════════════════════════════════════════════
  {
    const s = light("해결", "그래서 AI가 모르면 사진을 부탁하게 만들었다");
    box(s, M, 1.9, 6.6, 4.95, "151327");
    bubble(s, "ai", M + 0.25, 2.1, 5.9, 0.75, "기록만으로는 정상인지 날림인지 갈리지 않아요.");
    bubble(s, "ai", M + 0.25, 3.0, 5.9, 1.05, "용접 자국 앞면과 뒷면을 가까이 찍어 주세요.\n탄 고리나 튄 쇳조각이 보이면 날림이에요.");
    box(s, M + 2.95, 4.2, 2.6, 1.25, "241F45", { r: 0.18 });
    s.addImage({ path: PH("RGB_323F.jpg"), x: M + 3.08, y: 4.3, w: 1.05, h: 1.05 });
    s.addImage({ path: PH("RGB_323B.jpg"), x: M + 4.3, y: 4.3, w: 1.05, h: 1.05 });
    iconDot(s, "FaHelmetSafety", "FFFFFF", HEX.accent6, M + 5.7, 4.2, 0.55);
    bubble(s, "ai", M + 0.25, 5.6, 5.9, 1.05, "앞면에 정상 샘플에는 없는 쇳조각이 보여요.\n뒷면은 정상이지만 날림으로 판단합니다.");
    tag(s, "LLM 에이전트", HEX.accent2, M + 6.15, 1.97, "right-edge");
    tag(s, "HITL", HEX.accent6, M + 0.35, 4.7);
    tag(s, "VLM 판독 + 에이전트", HEX.accent6, M + 3.9, 5.47);
    txt(s, "실행 기록의 요청과 판독을 대화로 줄여 적었다", { x: 7.7, y: 6.45, w: 4.9, h: 0.3, fontSize: 13, color: SUB });
    credit(s);
    const pts = [
      ["FaCamera", "무엇을 찍을지 스스로 정한다", "막히면 어떤 사진이 답을 가를지 골라서 요청한다"],
      ["FaListCheck", "보기 전에 기준부터 말한다", "사진을 보기 전에 '이게 보이면 날림'이라고 정해 둔다"],
      ["FaImage", "합격품 사진과 나란히 본다", "같은 설정의 정상품 사진을 옆에 놓고 읽는다"],
    ];
    pts.forEach(([ic, t, d], i) => {
      const y = 2.0 + i * 1.6;
      txt(s, t, { x: 7.7, y: y + 0.02, w: 4.9, h: 0.45, fontSize: 19, bold: true, color: C.text1 });
      txt(s, d, { x: 7.7, y: y + 0.5, w: 4.9, h: 0.8, fontSize: 16, color: SUB });
    });
    s.addNotes("그래서 만든 서비스입니다. 대화로 보면 이렇습니다. AI가 기록만으로는 갈리지 않는다고 판단하면, 작업자에게 앞면과 뒷면을 찍어 달라고 요청합니다. 이때 사진을 보기 전에 '탄 고리나 튄 쇳조각이 보이면 날림'이라고 기준부터 말합니다. 작업자가 사진을 올리면, AI가 합격품 사진과 나란히 비교해 앞면에서 쇳조각을 찾고, 뒷면은 정상이지만 날림이라고 결론 냅니다. 실제 화면은 채팅이 아니고, 실제 실행 기록의 요청과 판독 내용을 대화처럼 줄여 적은 것입니다. 원문은 뒤에서 그대로 보여드립니다.");
  }

  // ══ 6. 실제 화면 ════════════════════════════════════════════════════
  {
    const s = light("완성도", "관제 화면과 작업자 휴대폰으로 실제로 돌아간다");
    box(s, M, 1.85, 7.4, 4.4, "2A2F36", { r: 0.16 });
    s.addImage({ path: AS("ui_overview.png"), x: M + 0.12, y: 1.97, w: 7.16, h: 4.16, sizing: { type: "cover", w: 7.16, h: 4.16 } });
    box(s, 8.3, 1.85, 2.05, 4.4, "2A2F36", { r: 0.28 });
    s.addImage({ path: AS("ui_mobile.png"), x: 8.4, y: 1.98, w: 1.85, h: 4.14, sizing: { type: "cover", w: 1.85, h: 4.14 } });
    const caps = [[M, 7.4, "1", "AI의 가설과 점수, 촬영 요청, 실행 기록을 한 화면에서"], [8.3, 4.3, "2", "QR로 열어서 바로 찍는다"]];
    caps.forEach(([x, w, n, t]) => {
      dot(s, x, 6.43, 0.34, HEX.accent1);
      txt(s, n, { x, y: 6.43, w: 0.34, h: 0.34, fontSize: 12, bold: true, color: "FFFFFF", align: "center", valign: "middle" });
      txt(s, t, { x: x + 0.45, y: 6.41, w: w - 0.45, h: 0.4, fontSize: 15, bold: true, color: C.text1, valign: "middle" });
    });
    const st = [[String(F.tests), "자동 테스트"], ["GitHub", "코드 전체 공개"], ["HTML 1개", "서버 없이 여는\n시연 재생"]];
    st.forEach(([b, l], i) => {
      const y = 1.95 + i * 1.5;
      txt(s, b, { x: 10.85, y, w: 1.75, h: 0.55, fontSize: i ? 18 : 28, bold: true, color: C.accent1, valign: "bottom" });
      txt(s, l, { x: 10.85, y: y + 0.6, w: 1.75, h: 0.7, fontSize: 14, color: SUB });
    });
    s.addNotes(`실제로 돌아가는 서비스입니다. 왼쪽이 관제 화면입니다. AI가 세운 가설과 점수가 실시간으로 바뀌고, 촬영이 필요하면 무엇을 왜 찍어야 하는지 요청이 뜹니다. 작업자는 QR 코드로 오른쪽 휴대폰 화면을 열어 바로 찍어 올립니다. 자동 테스트 ${F.tests}개와 함께 GitHub에 공개했습니다.`);
  }

  // ══ 6-1. 시연 영상 — deck/assets/demo.mp4 가 있을 때만 (deck/replay/demo.html 을 화면 녹화한 것) ══
  const VIDEO = AS("demo.mp4");
  if (fs.existsSync(VIDEO)) {
    const s = pres.addSlide({ masterName: "DARK" });
    txt(s, "시연 영상", { x: M, y: 0.45, w: 8, h: 0.4, fontSize: 18, bold: true, color: C.text1 });
    const vh = 5.6, vw = vh * 16 / 9, vx = (13.333 - vw) / 2;     // 16:9 그대로 (녹화 1920×1080)
    s.addMedia({ type: "video", path: VIDEO, x: vx, y: 1.0, w: vw, h: vh,
                 cover: "image/png;base64," + fs.readFileSync(AS("ui_overview.png")).toString("base64") });
    txt(s, "실제 실행 기록을 시간만 줄여 재생했다. 날림(E-323), 정상(E-357), 공장 데이터 순서", { x: vx, y: 6.72, w: vw, h: 0.35, fontSize: 13, color: "8A9099" });
    s.addNotes("시연 영상입니다. 실제 실행 기록을 시간만 줄여 재생한 것이고, 사건 세 개가 이어집니다. 첫 번째는 날림 용접입니다. AI가 기록만으로 애매하다고 판단해 앞면과 뒷면 촬영을 요청하고, 사진을 합격품과 비교해 날림으로 결론 냅니다. 두 번째는 정상 용접입니다. 똑같이 사진을 요청하지만, 이번에는 튄 쇳조각이 없어서 정상으로 결론 냅니다. 마지막은 실제 공장 데이터입니다. 사진 없이 기록만 보고, 설비 고장이 아니라 다른 날 기록이 그대로 복사돼 들어간 것이라고 찾아냅니다.");
  }

  // ══ 7. 실제 실행 1분 ═════════════════════════════════════════════════
  {
    const s = light("실제 실행", `실제 실행에서는 ${Math.round(DEMO.meta.elapsed_s)}초 만에 날림을 찾았다`);
    const steps = [
      [0, "기록 확인", "숫자만으로는\n애매하다", HEX.accent5, null, ["LLM 에이전트", HEX.accent2]],
      [secs(req), "촬영 요청", "앞면과 뒷면을\n찍어 달라고 요청", HEX.accent6, null, ["HITL", HEX.accent6]],
      [secs(reads[0]), "앞면 판독", "정상 샘플에 없는\n쇳조각 발견", HEX.accent3, "RGB_323F.jpg", ["VLM", HEX.accent6]],
      [secs(reads[1]), "뒷면 판독", "특이점 없음", HEX.accent2, "RGB_323B.jpg", ["VLM", HEX.accent6]],
      [secs(fin), "결론: 날림", "뒷면이 정상이어도\n앞면 결함은 남는다", HEX.accent1, null, ["선언 검사 + 에이전트", HEX.accent1]],
    ];
    const x0 = M + 0.6, span = 10.0, y = 4.2;
    s.addShape(pres.shapes.LINE, { x: x0, y: y + 0.2, w: span, h: 0, line: { color: "2A313C", width: 3 } });
    steps.forEach(([t, title, d, col, ph, tg], i) => {
      const x = x0 + span * i / (steps.length - 1);
      tag(s, tg[0], tg[1], x, 3.84, "center");
      dot(s, x - 0.2, y, 0.4, col);
      txt(s, `${t}초`, { x: x - 0.8, y: y + 0.5, w: 1.6, h: 0.4, fontSize: 15, bold: true, color: col, align: "center" });
      txt(s, title, { x: x - 1.1, y: y + 0.9, w: 2.2, h: 0.45, fontSize: 18, bold: true, color: C.text1, align: "center" });
      txt(s, d, { x: x - 1.1, y: y + 1.38, w: 2.2, h: 0.75, fontSize: 15, color: SUB, align: "center" });
      if (ph) photo(s, ph, x - 0.85, 2.05, 1.7, null, null, col);
    });
    box(s, x0 + span - 1.25, 2.3, 2.5, 1.3, "2A1A12");
    txt(s, [{ text: "날림\n", options: { bold: true, fontSize: 28, color: C.accent1 } }, { text: "정답과 같다", options: { fontSize: 14, bold: true, color: C.accent2 } }],
        { x: x0 + span - 1.25, y: 2.42, w: 2.5, h: 1.1, align: "center" });
    box(s, x0 - 0.6, 2.3, 2.6, 1.3, C.background2);
    txt(s, [{ text: "같은 설정 용접들과\n비교하면 ", options: { fontSize: 14, color: C.text1 } }, { text: "거의 보통", options: { fontSize: 14, bold: true, color: C.accent5 } }],
        { x: x0 - 0.45, y: 2.5, w: 2.3, h: 1.0, align: "center" });
    txt(s, "시연 영상은 이 기록을 그대로 재생했다", { x: M, y: 6.45, w: 6.0, h: 0.35, fontSize: 13, color: SUB });
    credit(s);
    s.addNotes(`실제 실행 기록입니다. 0초에 기록을 확인했는데 숫자로는 애매합니다. ${secs(req)}초에 AI가 앞면과 뒷면 촬영을 요청합니다. ${secs(reads[0])}초에 앞면 사진에서 정상 샘플에 없는 쇳조각을 찾고, ${secs(reads[1])}초에 뒷면은 특이점이 없다고 읽습니다. 두 신호가 엇갈려 시스템이 한 번 되물었고, AI는 뒷면이 정상이어도 앞면 결함은 없어지지 않는다고 판단해 ${secs(fin)}초에 날림으로 결론 냈습니다. 정답입니다.`);
  }

  // ══ 7-2. 한 번의 진단에서 무엇이 들어가 무엇이 나오나 (E-323 실제 기록 발췌) ══════════
  {
    const must = (ok, m) => { if (!ok) throw new Error(`7-2장: 실행 기록과 다름 — ${m}`); };
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
    const sc2 = v => v.toFixed(2), n0 = v => Math.round(v).toLocaleString();

    const s = light("LLM · VLM 동작", `그 ${Math.round(DEMO.meta.elapsed_s)}초 동안 AI에 들어간 것과 나온 것`);
    const xC = M, wC = 2.75, xI = 3.6, wI = 4.05, xA = 7.78, xO = 8.3, wO = 12.63 - 8.3;
    txt(s, "들어간 것", { x: xI, y: 1.72, w: wI, h: 0.3, fontSize: 14, bold: true, color: SUB });
    txt(s, "나온 것", { x: xO, y: 1.72, w: wO, h: 0.3, fontSize: 14, bold: true, color: SUB });
    const B = (t, o = {}) => ({ text: t, options: { fontSize: 14, color: C.text1, ...o } });
    const BR = (t, o = {}) => B(t, { breakLine: true, ...o });
    const rows = [
      ["FaBrain", HEX.accent2, "LLM 에이전트", "Claude Sonnet 5.5",
        [BR(`용접 기록: 최대 전류 ${n0(lg.peak_current_A)} A`), B(`같은 설정 ${pop.n_welds}회 상위 10%: ${n0(pop.peak_current_A.p90)} A`, { color: SUB })],
        [BR(`가설 4개: 정상 ${sc2(H.H1.score)}, 날림 ${sc2(H.H2.score)}`), BR(`용입 부족 ${sc2(H.H3.score)}, 편심 ${sc2(H.H4.score)}`, { color: SUB }),
         B("숫자로는 안 갈려서 촬영을 요청", { bold: true, color: C.accent2 })]],
      ["FaComments", HEX.accent6, "사람에게 요청", "Human-in-the-loop",
        [BR(`찍을 곳: ${quote("전극이 닿은 윗면", r1.target)} 용접 자리`), BR("보기 전 선언: 튄 금속이나 변색이 보이면", { color: SUB }),
         B("날림은 올리고 정상은 내린다", { bold: true, color: C.accent6 })],
        [BR("작업자 휴대폰에 요청이 뜨고 진단은 멈춤"), B(`앞면과 뒷면 사진 ${reads.length}장이 오면 다시 진행`, { bold: true, color: C.accent6 })]],
      ["FaEye", HEX.accent6, "VLM 사진 판독", "Claude Haiku 5.5",
        null,
        [BR(`"${quote("왼쪽으로 뻗은 뾰족한 밝은 금속 돌기", front.observation)}"`), BR("이상 있음, 합격품과 다름", { color: SUB }),
         B("선언해 둔 '튄 금속, 변색'이 보인다", { bold: true, color: C.accent6 })]],
      ["FaListCheck", HEX.accent1, "검증과 결론", "코드 검사 + 에이전트",
        [BR("앞면은 이상 있음, 뒷면은 이상 없음"), BR("뒷면은 '정상' 선언인데 초안은 날림", { color: SUB }),
         B("코드가 한 번 되묻는다", { bold: true, color: C.accent1 })],
        [BR(`결론 날림 ${sc2(FH.H2.score)} (정상 ${sc2(FH.H1.score)}), 근거는 앞면과 뒷면`),
         B(`"${quote("뒷면이 정상이라는 사실은 이 앞면 결함을 없애지 못한다", fin.root_cause)}"`, { color: SUB })]],
    ];
    const y0 = 2.08, rh = 0.98, gap = 0.14;
    rows.forEach(([ic, col, name, model, IN, OUTr], i) => {
      const y = y0 + i * (rh + gap);
      box(s, xC, y, wC, rh, C.background2);
      s.addShape(pres.shapes.RECTANGLE, { x: xC, y: y + 0.18, w: 0.06, h: rh - 0.36, fill: { color: col }, line: { type: "none" } });
      txt(s, [B(name, { bold: true, breakLine: true, fontSize: 15 }), B(model, { fontSize: 12, color: SUB })],
          { x: xC + 0.3, y: y + 0.17, w: wC - 0.4, h: rh - 0.3, valign: "middle" });
      box(s, xI, y, wI, rh, C.background2);
      if (IN) txt(s, IN, { x: xI + 0.22, y: y + 0.1, w: wI - 0.4, h: rh - 0.2, valign: "middle" });
      else {
        s.addImage({ path: PH(reads[0].photo.split("tier_e/")[1]), x: xI + 0.14, y: y + 0.1, w: 0.78, h: 0.78, altText: "이 용접 앞면" });
        s.addImage({ path: PH(reads[0].reference.split("tier_e/")[1]), x: xI + 1.0, y: y + 0.1, w: 0.78, h: 0.78, altText: "합격품 앞면" });
        txt(s, [BR("이 용접과 합격품"), BR("사진 2장을 나란히", { color: SUB }), B("체크리스트도 함께", { color: SUB })],
            { x: xI + 1.95, y: y + 0.1, w: wI - 2.1, h: rh - 0.2, valign: "middle" });
      }
      arrow(s, xA, y + rh / 2 - 0.17, 0.4, 0.34, col);
      box(s, xO, y, wO, rh, "1D222B", { line: col, lineW: 1.25 });
      txt(s, OUTr, { x: xO + 0.22, y: y + 0.1, w: wO - 0.4, h: rh - 0.2, valign: "middle" });
    });
    txt(s, `E-323 실제 실행 기록에서 그대로 옮겼다 (처음부터 결론까지 ${Math.round(DEMO.meta.elapsed_s)}초)`, { x: M, y: 6.58, w: 7.5, h: 0.3, fontSize: 13, color: SUB });
    credit(s);
    s.addNotes(`방금 본 63초 안에서 실제로 무엇이 들어가고 무엇이 나왔는지입니다. 먼저 LLM 에이전트에 용접 기록이 들어갑니다. 최대 전류가 같은 설정 용접들의 상위 10% 바로 아래라 애매하고, 에이전트는 가설 네 개에 점수를 매긴 뒤 숫자로는 안 갈린다며 촬영을 요청합니다. 이때 무엇을 어떻게 찍을지와 함께, 사진을 보기 전에 '튄 금속이나 변색이 보이면 날림 쪽'이라고 기준을 먼저 선언합니다. 요청은 작업자 휴대폰에 뜨고, 사진이 올 때까지 진단은 멈춥니다. 사진이 오면 VLM이 이 용접 사진과 같은 설정의 합격품 사진을 나란히 보고, 왼쪽으로 뻗은 금속 돌기를 찾아 선언한 항목이 보인다고 답합니다. 마지막으로 코드가 선언과 결론을 대조합니다. 뒷면은 정상 쪽이라고 선언했는데 결론이 날림이라 한 번 되묻고, 에이전트는 뒷면이 정상이어도 앞면 결함은 없어지지 않는다며 앞면과 뒷면을 근거로 날림을 확정합니다.`);
  }

  // ══ 8. 기술 ════════════════════════════════════════════════════════
  {
    const s = light("LLM · VLM 기술", "이 과정에 LLM과 VLM 기술 9가지를 엮었다");
    const cols = [
      ["생각하기", HEX.accent2, [
        ["FaBrain", "추론 루프 (Agent)", "가설과 점수를 고치며 다음 행동을 고른다"],
        ["FaScrewdriverWrench", "도구 호출 (Tool Calling)", "기록, 매뉴얼, 도면, 과거 사례를 찾아본다"],
        ["FaBookOpen", "매뉴얼·도면 검색 (RAG)", `매뉴얼 ${F.manual_pages}쪽과 도면 ${F.diagrams_described}장에서 찾는다`],
      ]],
      ["보고 묻기", HEX.accent6, [
        ["FaEye", "사진 판독 (VLM)", "합격품 사진과 나란히 놓고 읽는다"],
        ["FaComments", "사람에게 요청 (HITL)", "Human-in-the-loop\n사진이 올 때까지 멈췄다가 이어간다"],
      ]],
      ["믿을 수 있게", HEX.accent1, [
        ["FaListCheck", "보기 전 선언과 되묻기", "기준과 다른 결론이면 되묻는다"],
        ["FaQuoteLeft", "근거 인용 검증", "근거를 안 단 결론은 받지 않는다"],
        ["FaClockRotateLeft", "대화 이어 쓰기", `입력 토큰을 ${F.resume_tokens[0].toLocaleString()}개에서 ${F.resume_tokens[1]}개로`],
        ["FaGavel", "AI 채점 (LLM-as-Judge)", "진단과 다른 모델(Opus)이 채점"],
      ]],
    ];
    const cw = 3.85, gx = 0.17, top = 2.45, H = 4.05;
    cols.forEach(([head, col, items], ci) => {
      const x = M + ci * (cw + gx);
      txt(s, head, { x: x + 0.05, y: 1.85, w: cw, h: 0.42, fontSize: 17, bold: true, color: col, valign: "middle" });
      s.addShape(pres.shapes.LINE, { x, y: 2.3, w: cw, h: 0, line: { color: col, width: 1.5 } });
      const gap = 0.14, h = (H - gap * (items.length - 1)) / items.length;
      items.forEach(([ic, t, d], k) => {
        const y = top + k * (h + gap);
        const off = h > 1.6 ? (h - 1.3) / 2 : 0.16;              // 큰 카드는 내용을 세로 가운데로
        box(s, x, y, cw, h, C.background2);
        txt(s, t, { x: x + 0.25, y: y + off, w: cw - 0.4, h: 0.45, fontSize: 15, bold: true, color: C.text1 });
        txt(s, d, { x: x + 0.25, y: y + off + 0.45, w: cw - 0.4, h: Math.min(0.85, Math.max(0.4, h - off - 0.55)), fontSize: 14, color: SUB });
      });
    });
    txt(s, "진단은 Claude Sonnet 5.5, 사진 판독은 Haiku 5.5, 채점은 Opus 5.5", { x: 4.6, y: 6.55, w: 8.0, h: 0.32, fontSize: 13, color: SUB, align: "right" });
    s.addNotes("기술적으로 보면 아홉 가지가 한 흐름으로 이어집니다. 생각하는 부분은 추론 루프, 도구 호출, 매뉴얼과 도면 검색입니다. 보고 묻는 부분은 사진 판독과 사람에게 요청하는 기능인데, 사진을 기다리는 동안 진단을 멈췄다가 사진이 오면 이어갑니다. 믿을 수 있게 하는 부분은 보기 전 선언과 되묻기, 근거 인용 검증, 대화 이어 쓰기, 그리고 다른 모델로 채점하는 것입니다.");
  }

  // ══ 9. 효과 ════════════════════════════════════════════════════════
  {
    const s = light("효과", `사진을 요청하게 하자 정답률이 ${r0(MC["E-none"].sonnet.pct)}에서 ${r0(E.photo.accuracy)}로 올랐다`);
    const bars = [
      ["숫자 규칙", RB.rule_peak_current_p90.accuracy],
      ["학습 AI", RB.supervised_rf_reference.accuracy],
      ["우리 AI\n사진 없이", MC["E-none"].sonnet.pct],
      ["우리 AI\n사진 요청", E.photo.accuracy],
    ];
    const last = bars.length - 1;
    txt(s, "정답률 (58문제)", { x: M, y: 1.9, w: 7.0, h: 0.4, fontSize: 16, bold: true, color: C.text1 });
    s.addChart(pres.charts.BAR, [
      { name: "비교", labels: bars.map(b => b[0]), values: bars.map((b, i) => i === last ? 0 : Math.round(b[1])) },
      { name: "우리", labels: bars.map(b => b[0]), values: bars.map((b, i) => i === last ? Math.round(b[1]) : 0) },
    ], {
      x: M, y: 2.3, w: 7.0, h: 3.0, barDir: "col", barGrouping: "stacked", barGapWidthPct: 55,
      chartColors: ["3A424E", HEX.accent1], showLegend: false,
      showValue: true, dataLabelPosition: "inEnd", dataLabelFormatCode: "0\"%\";;;", dataLabelColor: "FFFFFF",
      dataLabelFontSize: 18, dataLabelFontBold: true, dataLabelFontFace: "+mn-lt",
      catAxisLabelColor: HEX.dk1, catAxisLabelFontSize: 15, catAxisLabelFontFace: "+mn-lt",
      valAxisHidden: true, valAxisMaxVal: 100, valAxisMinVal: 0, valGridLine: { style: "none" }, catGridLine: { style: "none" },
      catAxisLineShow: false,
    });
    // 학습 AI 와 정답률은 비슷(p = 0.18) — 차이는 준비물: 학습 AI 는 5-fold 마다 판정 라벨 394개(493건의 4/5)로 학습 (scripts/95 · 94 와 같은 설정)
    const RF_TRAIN = 394;
    box(s, M, 5.38, 7.2, 0.86, C.background2);
    txt(s, [{ text: "학습 AI   ", options: { bold: true, color: C.accent5 } }, { text: `정답 ${RF_TRAIN}개를 보고 배운다`, options: { color: C.text1, breakLine: true } },
            { text: "우리 AI   ", options: { bold: true, color: C.accent1 } }, { text: "정답 0개로, 찍을 사진과 근거를 스스로 정한다", options: { bold: true, color: C.text1 } }],
        { x: M + 0.25, y: 5.38, w: 6.9, h: 0.86, fontSize: 15, valign: "middle", lineSpacingMultiple: 1.15 });
    txt(s, `날림과 정상이 반반이라 아무렇게나 찍어도 50%. 같은 문제끼리 비교하면 사진 없이 대비 ${pfmt(PT.photo_vs_none.p_two_sided)}, 숫자 규칙 대비 ${pfmt(PT.photo_vs_rule.p_two_sided)}, 학습 AI와는 차이 없음 (${pfmt(PT.photo_vs_rf.p_two_sided)})`, { x: M, y: 6.32, w: 7.25, h: 0.55, fontSize: 12, color: SUB });
    const x = 8.15;
    box(s, x, 1.95, 4.5, 2.2, "2A1A12");
    txt(s, `날림을 찾아낸 수 (${E.photo.explode_n}개 중)`, { x: x + 0.35, y: 2.1, w: 3.9, h: 0.4, fontSize: 16, color: SUB });
    txt(s, [{ text: `${Math.round(MC["E-none"].sonnet.explode_recall * E.photo.explode_n / 100)}개`, options: { color: C.accent5 } },
            { text: "  →  ", options: { color: C.accent5 } },
            { text: `${E.photo.explode_hit}개`, options: { color: C.accent1 } }],
        { x: x + 0.35, y: 2.55, w: 3.9, h: 0.85, fontSize: 40, bold: true });
    txt(s, `사진 없이 하다가 사진을 요청하게 하자\n(규칙은 ${Math.round(RB.rule_peak_current_p90.explode_recall * E.photo.explode_n / 100)}개, 학습 AI는 ${Math.round(RB.supervised_rf_reference.explode_recall * E.photo.explode_n / 100)}개)`, { x: x + 0.35, y: 3.4, w: 3.9, h: 0.7, fontSize: 15, color: C.text1 });
    box(s, x, 4.35, 4.5, 2.2, C.background2);
    txt(s, `정상을 정상으로 (${E.photo.good_n}개 중)`, { x: x + 0.35, y: 4.5, w: 3.9, h: 0.4, fontSize: 16, color: SUB });
    txt(s, `${E.photo.good_hit} / ${E.photo.good_n}`, { x: x + 0.35, y: 4.95, w: 3.9, h: 0.85, fontSize: 40, bold: true, color: C.accent2 });
    txt(s, "정상을 불량으로 잘못 본 경우는 거의 없다", { x: x + 0.35, y: 5.9, w: 3.9, h: 0.4, fontSize: 15, color: C.text1 });
    s.addNotes(`같은 시험 58문제로 비교했습니다. 날림과 정상이 반반이라 아무렇게나 찍으면 50%입니다. 숫자 규칙은 ${r0(RB.rule_peak_current_p90.accuracy)}, 정답 수백 개로 학습한 AI는 ${r0(RB.supervised_rf_reference.accuracy)}, 우리 AI도 사진 없이는 ${r0(MC["E-none"].sonnet.pct)}였습니다. 사진을 요청하게 하자 ${r0(E.photo.accuracy)}로 올랐습니다. 특히 날림은 사진 없이 하나도 못 찾았는데, 사진을 요청하자 ${E.photo.explode_n}개 중 ${E.photo.explode_hit}개를 찾았습니다. 같은 문제끼리 짝지어 비교하면, 사진 없이 할 때나 숫자 규칙보다 나은 건 우연이 아닙니다. 학습 AI와는 비슷한 수준입니다. 다만 학습 AI는 정답 394개를 보고 배웠고, 우리 AI는 정답을 하나도 보지 않은 채 무엇을 찍을지 스스로 정하고 근거를 달았습니다. 정답 라벨을 모으기 어려운 현장에서는 이 차이가 큽니다.`);
  }

  // ══ 10. 바꿔치기 ════════════════════════════════════════════════════
  {
    const s = light("검증", `사진을 다른 것으로 바꾸면 정답률이 ${r0(E.swap.accuracy)}로 떨어진다`);
    const cards = [
      ["이 용접의 진짜 사진을 주면", "RGB_323F.jpg", r0(E.photo.accuracy), HEX.accent1, "2A1A12"],
      ["다른 용접 사진으로 몰래 바꾸면", "RGB_310F.jpg", r0(E.swap.accuracy), HEX.accent5, C.background2],
    ];
    cards.forEach(([t, ph, v, col, bg], i) => {
      const x = M + i * 6.05;
      box(s, x, 1.9, 5.85, 3.6, bg);
      txt(s, t, { x: x + 0.35, y: 2.1, w: 5.2, h: 0.45, fontSize: 18, bold: true, color: C.text1 });
      photo(s, ph, x + 0.35, 2.75, 2.4, null, null, i ? "3A424E" : HEX.accent1);
      arrow(s, x + 2.95, 3.75, 0.5, 0.42);
      txt(s, [{ text: v, options: { fontSize: 54, bold: true, color: col } }, { text: "\n정답률", options: { fontSize: 16, color: SUB } }],
          { x: x + 3.6, y: 3.05, w: 2.1, h: 1.6, align: "center" });
    });
    txt(s, [{ text: "다른 환자의 엑스레이를 받은 의사가 오진하듯, 결론이 사진을 따라 바뀐다.\n", options: { color: C.text1, bold: true } },
            { text: `같은 문제끼리 비교: 진짜 사진에서만 맞힌 ${E.photo_vs_swap.only_photo_ref}문제, 바꿔치기에서만 맞힌 ${E.photo_vs_swap.only_swap_ref}문제 (${pfmt(E.photo_vs_swap.p_two_sided)})`, options: { color: SUB } }],
        { x: M, y: 5.8, w: 11.9, h: 0.95, fontSize: 16 });
    credit(s);
    s.addNotes(`AI가 정말 사진을 보는지, 그냥 그럴듯하게 말하는지 확인하려고 사진을 몰래 바꿔 봤습니다. 진짜 사진을 주면 ${r0(E.photo.accuracy)}, 다른 용접 사진으로 바꾸면 ${r0(E.swap.accuracy)}로 떨어집니다. 다른 환자의 엑스레이를 주면 의사가 오진하는 것과 같습니다. 결론이 사진 내용을 따라 바뀐다는 뜻입니다. 같은 문제끼리 보면 진짜 사진에서만 맞힌 문제가 ${E.photo_vs_swap.only_photo_ref}개, 바꿔치기에서만 맞힌 문제는 ${E.photo_vs_swap.only_swap_ref}개라 우연이 아닙니다.`);
  }

  // ══ 13. 마무리 ═════════════════════════════════════════════════════
  {
    const s = pres.addSlide({ masterName: "DARK" });
    txt(s, "AI가 모를 때 사진을 부탁하게 하니\n불량을 더 잘 찾았다", { x: M, y: 1.2, w: 8.3, h: 2.0, fontSize: 40, bold: true, color: "FFFFFF" });
    const fz = E.explode_funnel;
    const pts = [
      [{ text: "모르면 무엇을 찍을지 스스로 정해서 요청한다", options: {} }],
      [{ text: "합격품 사진과 비교해 읽고, 근거를 달아 결론을 낸다", options: {} }],
      [{ text: "날림은 ", options: {} }, { text: `0개에서 ${E.photo.explode_hit}개`, options: { bold: true, color: C.accent1 } },
       { text: "로 늘었고, 사진을 바꾸면 정답률이 ", options: {} }, { text: `${r0(E.swap.accuracy)}`, options: { bold: true, color: C.accent1 } }, { text: "로 떨어졌다", options: {} }],
    ];
    pts.forEach((runs, i) => {
      const y = 3.55 + i * 0.6;
      txt(s, runs, { x: M, y, w: 8.5, h: i === 2 ? 0.9 : 0.5, fontSize: 17, color: "E4E6E9", valign: "top" });
    });
    box(s, M, 5.65, 8.15, 0.85, "2A1A12");
    txt(s, [{ text: "남은 숙제  ", options: { bold: true, color: C.accent1 } },
            { text: `날림 ${fz.total}개 중 ${fz.total - E.photo.explode_hit}개는 아직 놓친다. 그중 ${fz.reader_saw_nothing}개는 사진에 흔적이 없었다.`, options: { color: "E4E6E9" } }],
        { x: M + 0.3, y: 5.65, w: 7.7, h: 0.85, fontSize: 16, valign: "middle" });
    ico(s, "FaGithub", "8A9099", M, 6.68, 0.32);
    txt(s, "github.com/dlwogud/rootcause-stream", { x: M + 0.5, y: 6.67, w: 6, h: 0.35, fontSize: 13, color: "8A9099", valign: "middle" });
    photo(s, "RGB_323F.jpg", 9.3, 1.3, 3.3, null, null, "2A3038");
    credit(s, 9.3, 4.75, 3.3);
    s.addNotes(`정리하겠습니다. 처음 질문, AI가 모를 때 사진을 요청하게 하면 더 잘 찾는가에 대한 답은 그렇다입니다. 사진 없이는 날림을 하나도 못 찾았는데 사진을 요청하자 ${E.photo.explode_hit}개를 찾았고, 사진을 바꿔치기하면 정답률이 ${r0(E.photo.accuracy)}에서 ${r0(E.swap.accuracy)}로 떨어져 AI가 실제로 사진을 보고 판단한다는 것도 확인했습니다. 다만 날림 ${fz.total}개 중 ${fz.total - E.photo.explode_hit}개는 아직 놓칩니다. 답하는 AI에서 묻는 AI로. 감사합니다.`);
  }

  // ══ 부록 ══════════════════════════════════════════════════════════
  // ══ 부록 A. 점용접 그림 (본문 2번에서 옮김) ═══════════════════════════════════════════════════
  {
    const s = light("부록 A", "날림은 튄 쇳물 자국이 사진에 남는다");
    // 점용접 그림
    box(s, M, 1.95, 6.0, 4.75, C.background2);
    txt(s, "점용접은 전기 열로 두 철판을 점 하나로 붙인다", { x: M + 0.35, y: 2.15, w: 5.4, h: 0.65, fontSize: 15, bold: true, color: C.text1 });
    const cx = M + 2.2;
    box(s, cx, 2.95, 1.1, 1.05, "B8683A", { r: 0.08 });
    s.addShape(pres.shapes.RECTANGLE, { x: M + 0.6, y: 4.05, w: 4.3, h: 0.32, fill: { color: "9CA3AF" }, line: { type: "none" } });
    s.addShape(pres.shapes.RECTANGLE, { x: M + 0.6, y: 4.42, w: 4.3, h: 0.32, fill: { color: "B9BFC8" }, line: { type: "none" } });
    s.addShape(pres.shapes.OVAL, { x: cx + 0.05, y: 4.12, w: 1.0, h: 0.55, fill: { color: HEX.accent1 }, line: { type: "none" } });
    box(s, cx, 4.8, 1.1, 1.05, "B8683A", { r: 0.08 });
    ico(s, "FaBolt", HEX.accent4, cx + 1.25, 3.15, 0.5);
    txt(s, "전극: 누르면서 전기를 흘림", { x: cx + 1.8, y: 3.2, w: 2.3, h: 0.5, fontSize: 13, color: C.text1 });
    txt(s, "철판 2장", { x: M + 4.95, y: 4.2, w: 1.0, h: 0.4, fontSize: 13, color: C.text1 });
    txt(s, "녹아 붙은 점", { x: cx + 1.8, y: 4.85, w: 2.3, h: 0.4, fontSize: 13, bold: true, color: C.accent1 });
    ico(s, "FaCarSide", HEX.accent5, M + 0.35, 6.0, 0.45);
    txt(s, "자동차 한 대에 이런 점이 수천 개 들어간다", { x: M + 0.95, y: 6.05, w: 4.8, h: 0.4, fontSize: 14, color: C.accent5 });
    // 날림
    const x = 7.05;
    txt(s, "까다로운 불량, 날림", { x, y: 1.95, w: 5.6, h: 0.45, fontSize: 20, bold: true, color: C.accent3 });
    txt(s, "용접 중 녹은 쇳물이 밖으로 튀어나가는 불량", { x, y: 2.45, w: 5.6, h: 0.4, fontSize: 16, color: C.text1 });
    photo(s, "RGB_310F.jpg", x, 3.05, 2.5, "정상", C.accent2);
    photo(s, "RGB_323F.jpg", x + 2.9, 3.05, 2.5, "날림", C.accent3);
    ico(s, "FaMicroscope", HEX.accent3, x, 6.15, 0.42);
    txt(s, "기록으론 잘 안 보여, 현장에선 용접 자국을 눈으로 본다", { x: x + 0.55, y: 6.2, w: 5.4, h: 0.4, fontSize: 14, color: C.text1 });
    credit(s);
    s.addNotes("점용접 질문이 나오면 쓰는 부록입니다. 점용접은 두 철판을 전극으로 누르면서 전기를 흘려, 그 열로 점 하나를 녹여 붙이는 방식입니다. 자동차 한 대에 이런 점이 수천 개 들어갑니다. 가장 까다로운 불량 중 하나가 '날림'인데, 용접 중에 녹은 쇳물이 밖으로 튀어나가는 현상입니다. 오른쪽 두 사진은 같은 설정으로 용접한 정상과 날림입니다. 공정 기록으로는 잘 안 보여서, 현장에서는 용접 자국을 눈으로 봅니다.");
  }

  {
    const RC = N.rsw_classes;
    const s = light("부록 B", "사진과 정답은 어디서 왔나");
    const items = [
      ["사진", "멕시코 케레타로 자치대학(UAQ)이 공개한 RSW Insights 데이터셋 (Mendeley Data, CC BY 4.0). 실험실 점용접 495회마다 용접 자국 앞·뒷면 사진 · 열화상 · 공정 기록이 있다"],
      ["정답", "데이터셋 제공자가 매긴 분류 (정상 · 날림 · 불량). 우리는 라벨을 만들거나 고치지 않았다"],
      ["주의", "분류 기준은 데이터셋에 적혀 있지 않다. 날림의 인장강도는 정상과 비슷해서, 강도 미달이 아니라 용접 중 금속이 튄 현상을 기록한 분류로 보인다"],
    ];
    items.forEach(([k, v], i) => {
      const y = 1.95 + i * 1.02;
      box(s, M, y, 7.1, 0.88, C.background2);
      txt(s, k, { x: M + 0.3, y, w: 1.0, h: 0.88, fontSize: 16, bold: true, color: i === 2 ? C.accent4 : C.accent1, valign: "middle" });
      txt(s, v, { x: M + 1.3, y, w: 5.65, h: 0.88, fontSize: 13, color: C.text1, valign: "middle" });
    });
    const head = t => ({ text: t, options: { bold: true, color: "FFFFFF", fill: { color: "2A313C" } } });
    s.addTable([
      [head("제공자 분류"), head("용접 수"), head("인장강도\n평균"), head("너깃 지름\n평균")],
      ["정상 (Good)", String(RC.Good.n), `${RC.Good.pull_mean.toLocaleString()} N`, `${RC.Good.nugget_mean} mm`],
      [{ text: "날림 (Explode)", options: { bold: true, color: HEX.accent1 } }, String(RC.Explode.n), { text: `${RC.Explode.pull_mean.toLocaleString()} N`, options: { bold: true, color: HEX.accent1 } }, `${RC.Explode.nugget_mean} mm`],
      ["불량 (Bad)", String(RC.Bad.n), `${RC.Bad.pull_mean.toLocaleString()} N`, `${RC.Bad.nugget_mean} mm`],
    ], { x: 8.1, y: 1.95, w: 4.55, colW: [1.45, 0.8, 1.2, 1.1], fontSize: 12, rowH: 0.6,
         border: { type: "solid", pt: 0.75, color: "2A313C" }, valign: "middle", margin: [0, 0.08, 0, 0.08], color: HEX.dk1 });
    txt(s, "같은 설정끼리 짝지어 날림 29 · 정상 29 를 시험 문제로 썼다 (불량은 설정값만으로 구별돼 뺐다)", { x: 8.1, y: 4.55, w: 4.55, h: 0.7, fontSize: 12, color: C.accent5 });
    s.addNotes(`예상 질문: 사진은 어디서 났고 불량인지 어떻게 알았나. 답: 멕시코 케레타로 자치대학이 공개한 데이터셋이고, 용접마다 사진과 제공자의 분류가 있습니다. 정답은 그 분류를 그대로 썼고 우리가 만들지 않았습니다. 다만 분류 기준은 데이터셋에 적혀 있지 않습니다. 날림 용접의 인장강도가 정상과 비슷해서(${RC.Explode.pull_mean} N 대 ${RC.Good.pull_mean} N), 강도 미달이 아니라 용접 중 금속이 튄 현상을 기록한 분류로 보입니다. 이 점은 한계로 보고서에 적었습니다.`);
  }

  // ══ 부록 C. 개발 과정 ═════════════════════════════════════════════════
  {
    const s = light("부록 C", "막힌 곳 4개를 차례로 풀었다");
    const st = [
      ["사진이 없으면\n날림을 못 찾는다", "사진 요청 기능", `날림 0 → ${r0(MC["E-photo"].sonnet.explode_recall)}`],
      ["AI가 미세한\n흔적을 못 본다", "합격품 사진과 비교", "구별력 3%p → 35%p"],
      ["사진을 보고도\n숫자를 더 믿는다", "보기 전 선언 지키기", "사진을 따르게 됨"],
      ["앞면에 흔적이\n없는 날림", "뒷면 촬영 허용", `날림 ${r0(E.front_only.explode_recall)} → ${r0(E.photo.explode_recall)}`],
    ];
    const w = 2.8, g = 0.233, base = 6.55;
    st.forEach(([prob, fix, res], i) => {
      const x = M + i * (w + g), h = 1.5 + i * 0.75, y = base - h;
      const shade = ["FFD7C4", "FFB892", "FF915C", HEX.accent1][i];
      box(s, x, y, w, h, shade, { r: 0.12 });
      txt(s, `${i + 1}`, { x: x + 0.25, y: y + 0.15, w: 0.6, h: 0.5, fontSize: 24, bold: true, color: i === 3 ? "FFFFFF" : "1A1D21" });
      txt(s, fix, { x: x + 0.25, y: y + 0.65, w: w - 0.4, h: 0.45, fontSize: 17, bold: true, color: i === 3 ? "FFFFFF" : "1A1D21" });
      txt(s, res, { x: x + 0.25, y: y + 1.05, w: w - 0.4, h: 0.4, fontSize: 14, bold: true, color: i === 3 ? "FFFFFF" : "8A3B12" });
      txt(s, prob, { x, y: y - 0.85, w, h: 0.75, fontSize: 14, color: C.accent5, valign: "bottom" });
    });
    txt(s, `4단계에선 "어느 면이든 찍을 수 있다"고만 알렸는데,\nAI가 ${E.asked_back[1]}건 중 ${E.asked_back[0]}건에서 스스로 뒷면을 요청했다`,
        { x: M, y: 1.85, w: 7.0, h: 0.75, fontSize: 15, bold: true, color: C.accent1 });
    s.addNotes(`한 번에 된 것은 아닙니다. 막힌 곳 네 개를 차례로 풀었습니다. 처음엔 사진이 없으면 날림을 못 찾아서 사진 요청 기능을 넣었습니다. 다음엔 AI가 미세한 흔적을 못 봐서 합격품 사진을 옆에 놓고 비교하게 했습니다. 그다음엔 사진을 보고도 숫자를 더 믿어서, 보기 전에 한 선언을 지키게 했습니다. 마지막으로 앞면에 흔적이 없는 날림이 남았는데, 어느 면이든 찍을 수 있다고만 알리자 AI가 거의 모든 경우에 스스로 뒷면을 요청했고 날림 발견이 두 배가 됐습니다.`);
  }

  {
    const s = light("부록 D", "측정 이력과 정정");
    const head = t => ({ text: t, options: { bold: true, color: "FFFFFF", fill: { color: "2A313C" } } });
    s.addTable([
      [head("실행"), head("조건 (진단 Sonnet 5.5 · 판독 Haiku 5.5 · 채점 Opus 5.5)"), head("정답률"), head("날림")],
      ["—", "사진 없음", r0(MC["E-none"].sonnet.pct), r0(MC["E-none"].sonnet.explode_recall)],
      ["—", "앞면 사진", r0(MC["E-photo"].sonnet.pct), r0(MC["E-photo"].sonnet.explode_recall)],
      [`#${E.front_only.run}`, "앞면 + 합격품 비교 + 보기 전 선언", r0(E.front_only.accuracy), r0(E.front_only.explode_recall)],
      [`#${E.run}`, "앞·뒷면 + 합격품 비교 + 보기 전 선언 (최종)", r0(E.photo.accuracy), r0(E.photo.explode_recall)],
      [`#${E.run}`, "↳ 바꿔치기 사진", r0(E.swap.accuracy), r0(E.swap.explode_recall)],
      ["—", "숫자 규칙 (최대 전류 > 같은 설정 상위 10%)", r0(RB.rule_peak_current_p90.accuracy), r0(RB.rule_peak_current_p90.explode_recall)],
      ["—", "학습 AI (랜덤 포레스트, 판정 라벨로 학습)", r0(RB.supervised_rf_reference.accuracy), r0(RB.supervised_rf_reference.explode_recall)],
    ], { x: M, y: 1.85, w: 11.9, colW: [1.2, 7.1, 1.8, 1.8], fontSize: 14, rowH: 0.45,
         border: { type: "solid", pt: 0.75, color: "2A313C" }, valign: "middle", margin: [0, 0.15, 0, 0.15], color: HEX.dk1 });
    const fixes = [
      ["증거 가림 버그", "한 단계에 증거가 여러 개면 마지막 것만 AI에게 보였다 → 고치고 다시 측정"],
      ["정답 누출 2건", "사건 요약의 라벨 필드 · 증거 요약의 파일 이름 → 제거하고 누출 검사 테스트 추가"],
      ["정답지 정정", "공장 데이터의 정답 '원인 불명'을 '기록 재활용'으로 고치고 다시 측정"],
    ];
    fixes.forEach(([t, d], i) => {
      const y = 5.65 + i * 0.42;
      txt(s, t, { x: M, y, w: 2.3, h: 0.38, fontSize: 13, bold: true, color: C.accent3 });
      txt(s, d, { x: M + 2.4, y, w: 9.5, h: 0.38, fontSize: 13, color: C.text1 });
    });
    s.addNotes(`최종 대 앞면만: 최종에서만 맞힘 ${E.final_vs_front.only_final}, 앞면만에서만 ${E.final_vs_front.only_front}, ${pfmt(E.final_vs_front.p_two_sided)} (경계). 10장 짝 검정 — 사진 요청 대 학습 AI: ${PT.photo_vs_rf.only_photo} 대 ${PT.photo_vs_rf.only_rf}, ${pfmt(PT.photo_vs_rf.p_two_sided)} (날림만 ${PT.photo_vs_rf_explode.only_photo} 대 ${PT.photo_vs_rf_explode.only_rf}, ${pfmt(PT.photo_vs_rf_explode.p_two_sided)}). 대 숫자 규칙: ${PT.photo_vs_rule.only_photo} 대 ${PT.photo_vs_rule.only_rule}, ${pfmt(PT.photo_vs_rule.p_two_sided)}. 대 사진 없이: ${PT.photo_vs_none.only_photo} 대 ${PT.photo_vs_none.only_none}, ${pfmt(PT.photo_vs_none.p_two_sided)}.`);
  }

  {
    const au = F.audit, kb = N.rule_baseline.kamp;
    const s = light("부록 E", "공장 데이터의 이상은 '기록 재활용'이었다");
    box(s, M, 1.9, 5.6, 2.4, C.background2);
    txt(s, `${au.dup_index_pct}% → ${au.reused_pct}%`, { x: M + 0.3, y: 2.05, w: 5.0, h: 0.8, fontSize: 36, bold: true, color: C.accent1 });
    txt(s, `알려진 중복 비율 → 실제로 다른 날 기록과 수백 줄씩 똑같은 비율 (순서를 섞으면 최대 ${au.chance_longest}줄)`, { x: M + 0.3, y: 2.95, w: 5.0, h: 1.2, fontSize: 14, color: C.text1 });
    const head = t => ({ text: t, options: { bold: true, color: "FFFFFF", fill: { color: "2A313C" } } });
    s.addTable([
      [head("원인 정답률"), head("AI"), head("규칙 한 줄")],
      ["A 조용한 수준 이동", `${r0(MC.A.sonnet.pct)} (Sonnet)`, r0(kb.A.pct)],
      ["C 알람 폭주", `${r0(N.conditions.full.C.M1_match.mean)} (Haiku)`, r0(kb.C.pct)],
      ["B 주입 고장 (주 변수)", `${r0(N.conditions.full.B.M2_primary_variable.mean)} (Haiku)`, r0(kb.B.pct)],
    ], { x: 6.6, y: 1.9, w: 6.0, colW: [2.6, 1.9, 1.5], fontSize: 14, rowH: 0.55,
         border: { type: "solid", pt: 0.75, color: "2A313C" }, valign: "middle", margin: [0, 0.15, 0, 0.15], color: HEX.dk1 });
    txt(s, [{ text: "정직한 위치  ", options: { bold: true, color: C.accent1 } },
            { text: "결정적 신호(다른 날과의 연속 일치 비율)는 사람이 설계했고, 그 신호가 있으면 규칙 한 줄도 AI만큼 맞힌다. 신호 없이 원본 기록과 SQL만 주자 AI는 스스로 찾지 못했다 (Sonnet 0%). 그래서 AI만의 기여는 사진 실험으로 주장한다.", options: { color: C.text1 } }],
        { x: M, y: 4.65, w: 11.9, h: 1.5, fontSize: 15 });
    s.addNotes(`공장 데이터 질문이 나오면 쓰는 부록입니다. 실제 공장 데이터의 이상 신호를 따라가 보니, 기록의 ${au.reused_pct}%가 다른 날 기록과 수백 줄씩 똑같았습니다. 설비 고장이 아니라 기록이 재활용된 것입니다. 다만 이 신호는 제가 설계했고, 신호가 있으면 규칙 한 줄로도 맞힙니다. 그래서 공장 데이터에서는 AI가 규칙보다 낫다고 주장하지 않습니다. AI만의 기여는 사진을 요청해서 판단하는 부분이고, 그건 사진 실험으로 보여드렸습니다.`);
  }

  // ══ 부록 F. 남은 숙제 (본문 결론에 한 줄로 요약) ═══════════════════════════════════════════════════
  {
    const s = light("부록 F", "날림의 절반 이상은 아직 놓친다");
    const fz = E.explode_funnel;
    const rows = [["날림 불량", fz.total, "B9BFC8"], ["사진에서 이상을 찾음", fz.reader_flagged, HEX.accent6], ["날림이라고 결론", fz.flagged_and_concluded, HEX.accent1]];
    rows.forEach(([l, v, col], i) => {
      const y = 2.0 + i * 1.0, w = 5.2 * v / fz.total;
      txt(s, l, { x: M, y, w: 4, h: 0.35, fontSize: 15, color: C.text1 });
      s.addShape(pres.shapes.RECTANGLE, { x: M, y: y + 0.4, w, h: 0.42, fill: { color: col }, line: { type: "none" } });
      txt(s, `${v}개`, { x: M + w + 0.12, y: y + 0.4, w: 0.9, h: 0.42, fontSize: 17, bold: true, color: C.text1, valign: "middle" });
    });
    box(s, M, 5.15, 6.2, 1.5, C.background2);
    ico(s, "FaCircleQuestion", HEX.accent4, M + 0.25, 5.35, 0.45);
    txt(s, [{ text: `${fz.reader_saw_nothing}개는 앞·뒷면 어디에서도 흔적을 못 찾았다.\n`, options: { bold: true, color: C.text1 } },
            { text: "날림 분류 기준은 데이터에 적혀 있지 않다. 겉으로 흔적이 남지 않는 날림일 수 있다.", options: { color: C.accent5 } }],
        { x: M + 0.9, y: 5.3, w: 5.15, h: 1.25, fontSize: 14 });
    const lims = [
      ["같은 시험 문제를 여러 번 썼다", "날림 사례가 31개뿐이라 개선은 여기서 멈췄다"],
      ["실행할 때마다 답이 조금 달라진다", "시연은 실제 실행 기록을 그대로 재생"],
      ["사진은 공개 데이터의 실제 사진", "현장에서 직접 찍는 검증은 다음 단계"],
    ];
    lims.forEach(([t, d], i) => {
      const y = 2.0 + i * 1.25;
      box(s, 7.35, y, 5.25, 1.05, C.background2);
      txt(s, t, { x: 7.6, y: y + 0.15, w: 4.9, h: 0.4, fontSize: 16, bold: true, color: C.text1 });
      txt(s, d, { x: 7.6, y: y + 0.57, w: 4.9, h: 0.4, fontSize: 13, color: C.accent5 });
    });
    box(s, 7.35, 5.75, 5.25, 0.9, "2A1A12");
    txt(s, [{ text: "다음 단계  ", options: { bold: true, color: C.accent1 } }, { text: "현장 검사 사진을 예시로 함께 보여주기", options: { color: C.text1 } }],
        { x: 7.6, y: 5.75, w: 4.9, h: 0.9, fontSize: 15, valign: "middle" });
    s.addNotes(`한계도 말씀드립니다. 날림 ${fz.total}개 중 사진에서 이상을 찾은 건 ${fz.reader_flagged}개, 날림이라고 결론 낸 건 ${fz.flagged_and_concluded}개입니다. ${fz.reader_saw_nothing}개는 사진 어디에서도 흔적을 못 찾았는데, 날림을 어떤 기준으로 분류했는지 데이터에 적혀 있지 않아서, 겉으로 흔적이 남지 않는 날림일 수 있습니다. 또 날림 사례가 적어서 같은 시험 문제로 고치고 재기를 반복했습니다. 더 고치면 이 문제에만 맞춰질 수 있어서, 개선은 여기서 멈췄습니다.`);
  }

  {
    const s = light("부록 G", "데이터와 출처");
    const items = [
      ["사진 실험", "RSW Insights — L. A. Dominguez Molina, Mendeley Data V3 (2025), CC BY 4.0.\n용접 495회 · 앞·뒷면 사진 · 제공자 분류(기준 비공개)"],
      ["시험 문제", "날림 29 + 같은 설정의 정상 29 = 58건 (개발용 4건 제외), 같은 문제를 조건만 바꿔 비교"],
      ["사용 모델", "진단 Claude Sonnet 5.5 · 사진 판독 Haiku 5.5 · 채점 Opus 5.5 (진단과 다른 모델).\nClaude Code CLI로 실행했다. 측정별 버전은 eval/MODEL_VERSIONS.md"],
      ["공장 데이터", "KAMP 저항 점용접 공정 데이터. 재배포 권한이 확인되지 않아 레포에는 받는 방법만 적었다"],
      ["매뉴얼", `제조사 매뉴얼 ${F.manual_docs}종 ${F.manual_pages}쪽, 도면 ${F.diagrams_described}장. 레포에는 받는 방법만 적었다`],
      ["재현", "eval/run_tier_e.py (사진 실험) · deck/export_numbers.py (발표 수치) · deck/replay/*.html (시연 재생)"],
    ];
    items.forEach(([k, v], i) => {
      const y = 1.95 + i * 0.84;
      box(s, M, y, 11.9, 0.72, C.background2);
      txt(s, k, { x: M + 0.3, y, w: 2.0, h: 0.72, fontSize: 15, bold: true, color: C.accent1, valign: "middle" });
      txt(s, v, { x: M + 2.4, y, w: 9.3, h: 0.72, fontSize: 13, color: C.text1, valign: "middle" });
    });
    s.addNotes("데이터 출처 부록입니다. 모델 질문이 나오면: 진단은 Sonnet 5.5, 사진 판독은 Haiku 5.5, 채점은 진단과 다른 모델인 Opus 5.5입니다. 초기 시험 실행 몇 번은 버전이 바뀌기 전이라 옛 버전이었지만, 발표에 나온 숫자는 모두 5.5로 낸 것입니다.");
  }


  await pres.writeFile({ fileName: OUT });
  await applyTheme(OUT, THEME);
  await koreanFont(OUT);
  console.log("→", OUT);
}
// 한글은 동아시아 글꼴(ea) 칸을 따른다. 테마의 ea 가 비어 있으면 윈도우가 아무 글꼴이나 고르고,
// Courier New 라벨의 ea 도 Courier New 라 한글이 대체된다 → 둘 다 맑은 고딕으로 못 박는다.
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

build().catch(e => { console.error(e); process.exit(1); });
