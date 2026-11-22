// RootCause Stream 발표자료 생성기 — v3 (2026-11-22, 처음 보는 사람도 이해하도록 다시 짬)
//   이야기 순서: 용접이 뭔가 → 날림은 왜 어려운가 → 전문가는 가서 본다 → 묻는 AI → 실제 화면 →
//               기술 → 효과 → 진짜 사진을 보나 → 막힌 곳 → 남은 숙제
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
const RB = N.rule_baseline.tier_e;              // 규칙 · 지도학습 분류기
const MC = N.model_comparison.tiers;            // sonnet 사진 없음 · 앞면 사진
const DEMO = JSON.parse(fs.readFileSync(path.join(ROOT, "data/demo_runs/e323-ko.json"), "utf8"));   // 한국어 실제 실행 기록
const OUT = path.join(__dirname, "RootCause_Stream_발표자료.pptx");
const PH = p => path.join(ROOT, "data/photos/tier_e", p);
const AS = p => path.join(__dirname, "assets", p);

// ── 테마: 차콜 + 용접 불꽃 주황 하나. 보라는 '사람·사진'에만 아껴 쓴다 ────────────
const THEME = {
  name: "RootCause Spark",
  headFontFace: "Apple SD Gothic Neo",
  bodyFontFace: "Apple SD Gothic Neo",
  colors: {
    dk1: "15181D", lt1: "FFFFFF", dk2: "1F242B", lt2: "F3F4F6",
    accent1: "FF6A2B", accent2: "0F9D8A", accent3: "D93B3B",
    accent4: "F5B547", accent5: "6B7280", accent6: "6D5DF6",
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
  ["FaCamera", HEX.accent1], ["FaCamera", HEX.accent6], ["FaCamera", HEX.lt1], ["FaRobot", HEX.lt1], ["FaRobot", HEX.accent1],
  ["FaHelmetSafety", HEX.lt1], ["FaHelmetSafety", HEX.accent6], ["FaUserDoctor", HEX.accent5], ["FaXRay", HEX.accent6],
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
pres.defineSlideMaster({ title: "DARK", background: { color: C.text1 }, objects: [
  { line: { x: 0.4, y: 0.3, w: 0, h: 6.9, line: { color: "2A3038", width: 0.75 } } },
  { line: { x: 12.93, y: 0.3, w: 0, h: 6.9, line: { color: "2A3038", width: 0.75 } } },
  { line: { x: 0.4, y: 0.3, w: 12.53, h: 0, line: { color: "2A3038", width: 0.75 } } },
  { line: { x: 0.4, y: 7.2, w: 12.53, h: 0, line: { color: "2A3038", width: 0.75 } } },
] });
pres.defineSlideMaster({
  title: "LIGHT",
  background: { color: C.background1 },
  margin: [0.4, 0.7, 0.6, 0.7],
  slideNumber: { x: 12.3, y: 7.0, w: 0.5, h: 0.3, fontSize: 10, color: C.accent5, align: "right" },
  objects: [
    { line: { x: 0.4, y: 0.3, w: 0, h: 6.9, line: { color: "E3E5E9", width: 0.75 } } },
    { line: { x: 12.93, y: 0.3, w: 0, h: 6.9, line: { color: "E3E5E9", width: 0.75 } } },
    { line: { x: 0.4, y: 0.3, w: 12.53, h: 0, line: { color: "E3E5E9", width: 0.75 } } },
    { line: { x: 0.4, y: 6.93, w: 12.53, h: 0, line: { color: "E3E5E9", width: 0.75 } } },
    { placeholder: { options: { name: "kicker", type: "body", x: M, y: 0.45, w: 11.9, h: 0.35,
        fontSize: 13, bold: true, color: C.accent1, margin: 0, fontFace: "Courier New", charSpacing: 1 }, text: "" } },
    { placeholder: { options: { name: "title", type: "title", x: M, y: 0.8, w: 11.9, h: 0.85,
        fontSize: 34, bold: true, color: C.text1, valign: "middle", margin: 0 }, text: "" } },
    { text: { text: "RootCause Stream", options: { x: M, y: 7.0, w: 4, h: 0.3, fontSize: 10, color: C.accent5, margin: 0 } } },
  ],
});

// ── 공통 조각 ─────────────────────────────────────────────────────────
function box(s, x, y, w, h, fill, opt = {}) {
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w, h, rectRadius: opt.r ?? 0.14, fill: { color: fill },
    line: opt.line ? { color: opt.line, width: opt.lineW || 1.5 } : { type: "none" }, shadow: opt.shadow ? soft() : undefined });
}
function dot(s, x, y, d, fill) { s.addShape(pres.shapes.OVAL, { x, y, w: d, h: d, fill: { color: fill }, line: { type: "none" } }); }
function txt(s, runs, o) { s.addText(runs, { isTextBox: true, margin: 0, valign: "top", ...o }); }
function ico(s, name, color, x, y, d) {
  const data = ICON[`${name}-${color}`];
  if (!data) throw new Error(`아이콘 ${name}-${color} 을 NEED 에 추가하라`);
  s.addImage({ data, x, y, w: d, h: d, altText: name });
}
function iconDot(s, name, color, bg, x, y, d) { dot(s, x, y, d, bg); ico(s, name, color, x + d * 0.24, y + d * 0.24, d * 0.52); }
function arrow(s, x, y, w = 0.45, h = 0.38, color = "C3C7CE") {
  s.addShape(pres.shapes.RIGHT_ARROW, { x, y, w, h, fill: { color }, line: { type: "none" } });
}
function photo(s, file, x, y, d, cap, capColor = C.accent5, line) {
  if (line) s.addShape(pres.shapes.RECTANGLE, { x: x - 0.05, y: y - 0.05, w: d + 0.1, h: d + 0.1, fill: { color: line }, line: { type: "none" } });
  s.addImage({ path: PH(file), x, y, w: d, h: d, altText: cap || file });
  if (cap) txt(s, cap, { x: x - 0.2, y: y + d + 0.1, w: d + 0.4, h: 0.3, fontSize: 13, color: capColor, align: "center", bold: true });
}
// 참고 디자인 (Behance, 2026-11-22): ORYN 의 '■ 01 표식 · 얇은 격자선', Tensora 의 '회색 + 진한 두 톤 제목'
function twoTone(title, dim = "9AA0A8", strong = C.text1) {
  const [a, b] = title.includes("|") ? title.split("|") : ["", title];
  return [a ? { text: a, options: { color: dim } } : null, { text: b, options: { color: strong } }].filter(Boolean);
}
let SECTION = 0;
function light(kicker, title) {
  const s = pres.addSlide({ masterName: "LIGHT" });
  const n = kicker.startsWith("부록") ? "" : String(++SECTION).padStart(2, "0") + "  ";
  s.addText(`■ ${n}${kicker}`, { placeholder: "kicker" });
  s.addText(twoTone(title), { placeholder: "title" });
  return s;
}
// 채팅 말풍선 (who: 'ai' | 'human')
function bubble(s, who, x, y, w, h, text, size = 15) {
  const ai = who === "ai";
  iconDot(s, ai ? "FaRobot" : "FaHelmetSafety", HEX.lt1, ai ? HEX.accent1 : HEX.accent6, ai ? x : x + w + 0.15, y, 0.55);
  const bx = ai ? x + 0.7 : x;
  box(s, bx, y, w - 0.7 + (ai ? 0 : 0.7) - (ai ? 0 : 0.7), h, ai ? C.background1 : "ECE9FE", { r: 0.18, shadow: ai });
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
    txt(s, "■ LLM · VLM 서비스 개발 프로젝트  /  ROOTCAUSE STREAM", { x: M, y: 0.7, w: 8, h: 0.4, fontSize: 13, bold: true, color: C.accent1, fontFace: "Courier New", charSpacing: 1 });
    txt(s, [{ text: "모르면,\n", options: { color: "6B7280" } }, { text: "먼저 물어보는 AI", options: { color: C.background1 } }],
        { x: M, y: 1.55, w: 7.0, h: 2.6, fontSize: 58, bold: true });
    txt(s, "공장 설비의 불량 원인을 찾다가, 기록만으로 모르면\n작업자에게 \"이걸 찍어 주세요\"라고 요청하는 진단 AI",
      { x: M, y: 4.35, w: 7.0, h: 1.0, fontSize: 19, color: "C9CDD2" });
    const chips = [[r0(E.photo.accuracy), "실제 용접 불량 판정"], [`${E.asked_back[0]}/${E.asked_back[1]}`, "스스로 뒷면 촬영 요청"], [`${E.photo_vs_swap.only_photo_ref} : ${E.photo_vs_swap.only_swap_ref}`, "진짜 사진 vs 바꿔치기"]];
    chips.forEach(([b, l], i) => {
      const x = M + i * 2.3;
      txt(s, b, { x, y: 5.6, w: 2.2, h: 0.6, fontSize: 28, bold: true, color: C.accent1 });
      txt(s, l, { x, y: 6.2, w: 2.2, h: 0.35, fontSize: 13, color: "9AA0A8" });
    });
    photo(s, "RGB_323F.jpg", 8.35, 0.9, 4.3, null, null, "2A3038");
    box(s, 7.55, 4.75, 5.2, 1.25, C.background1, { r: 0.2, shadow: true });
    iconDot(s, "FaRobot", HEX.lt1, HEX.accent1, 7.75, 4.98, 0.8);
    txt(s, [{ text: "AI\n", options: { bold: true, color: C.accent1, fontSize: 13 } },
            { text: "이 용접, 뒷면도 찍어 주실 수 있나요?", options: { color: C.text1, fontSize: 17, bold: true } }],
        { x: 8.75, y: 5.0, w: 3.9, h: 0.85 });
    txt(s, "실제 용접 사진 (날림 불량)", { x: 8.35, y: 6.15, w: 4.3, h: 0.3, fontSize: 11, color: "8A9099", align: "right" });
    txt(s, "이재형  ·  2026. 11", { x: M, y: 6.9, w: 5, h: 0.3, fontSize: 12, color: "8A9099" });
    s.addNotes(`안녕하세요. 제가 만든 건 '모르면 먼저 물어보는 AI'입니다. 공장에서 불량이 났을 때 AI가 원인을 찾다가, 기록만으로 모르겠으면 작업자에게 '이걸 찍어 주세요'라고 요청하고 그 사진으로 결론을 냅니다. 실제 용접 불량 판정에서 ${r0(E.photo.accuracy)}를 맞혔고, ${E.asked_back[1]}건 중 ${E.asked_back[0]}건에서 AI가 스스로 뒷면 촬영까지 요청했습니다.`);
  }

  // ══ 2. 용접과 날림 ═══════════════════════════════════════════════════
  {
    const s = light("배경", "용접 점 하나가 약하면, |차가 약해진다");
    // 점용접 그림
    box(s, M, 1.95, 6.0, 4.75, C.background2);
    txt(s, "점용접 — 두 철판을 눌러 전기를 흘리면, 열로 점 하나가 녹아 붙는다", { x: M + 0.35, y: 2.15, w: 5.4, h: 0.65, fontSize: 15, bold: true, color: C.text1 });
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
    txt(s, "가장 까다로운 불량 — 날림", { x, y: 1.95, w: 5.6, h: 0.45, fontSize: 20, bold: true, color: C.accent3 });
    txt(s, "녹은 쇳물이 밖으로 튀어나가 점이 약해진다", { x, y: 2.45, w: 5.6, h: 0.4, fontSize: 16, color: C.text1 });
    photo(s, "RGB_310F.jpg", x, 3.05, 2.5, "정상", C.accent2);
    photo(s, "RGB_323F.jpg", x + 2.9, 3.05, 2.5, "날림", C.accent3);
    ico(s, "FaMicroscope", HEX.accent3, x, 6.15, 0.42);
    txt(s, "확실히 알려면 뜯어서 강도를 재야 한다 (파괴 검사)", { x: x + 0.55, y: 6.2, w: 5.2, h: 0.4, fontSize: 14, color: C.text1 });
    s.addNotes("배경부터 설명드리겠습니다. 점용접은 두 철판을 전극으로 누르면서 전기를 흘려, 그 열로 점 하나를 녹여 붙이는 방식입니다. 자동차 한 대에 이런 점이 수천 개 들어갑니다. 가장 까다로운 불량이 '날림'인데, 녹은 쇳물이 튀어나가 점이 약해지는 현상입니다. 오른쪽 두 사진은 같은 설정으로 용접한 정상과 날림입니다. 확실히 알려면 뜯어서 강도를 재야 합니다.");
  }

  // ══ 3. 숫자로는 안 갈린다 ═════════════════════════════════════════════
  {
    const s = light("문제", "기계의 숫자만 보면, |불량인지 알 수 없다");
    const rows = [
      ["최대 전류", `${Math.round(lg.peak_current_A).toLocaleString()} A`, inBand(lg.peak_current_A, pop.peak_current_A)],
      ["평균 전류", `${Math.round(lg.mean_current_A).toLocaleString()} A`, inBand(lg.mean_current_A, pop.mean_current_A)],
      ["누르는 힘", `${Math.round(lg.peak_force_N)} N`, inBand(lg.peak_force_N, pop.peak_force_N)],
    ];
    txt(s, `이 용접의 기록 — 같은 설정의 다른 용접 ${pop.n_welds}회와 비교`, { x: M, y: 1.95, w: 6, h: 0.4, fontSize: 15, color: C.accent5 });
    rows.forEach(([k, v, ok], i) => {
      const y = 2.5 + i * 1.12;
      box(s, M, y, 5.9, 0.95, C.background2);
      txt(s, k, { x: M + 0.3, y: y + 0.27, w: 1.6, h: 0.45, fontSize: 17, color: C.accent5 });
      txt(s, v, { x: M + 2.0, y: y + 0.2, w: 2.2, h: 0.55, fontSize: 26, bold: true, color: C.text1 });
      ico(s, ok ? "FaCircleCheck" : "FaTriangleExclamation", ok ? HEX.accent2 : HEX.accent4, M + 4.3, y + 0.25, 0.45);
      txt(s, ok ? "보통 범위" : "범위 끝자락", { x: M + 4.85, y: y + 0.3, w: 1.0, h: 0.4, fontSize: 14, bold: true, color: ok ? C.accent2 : "B7791F" });
    });
    txt(s, [{ text: "숫자만 보는 방법들이 날림을 찾는 비율  ", options: { color: C.accent5 } },
            { text: `규칙 ${r0(RB.rule_peak_current_p90.explode_recall)} · 학습 AI ${r0(RB.supervised_rf_reference.explode_recall)}`, options: { bold: true, color: C.accent3 } }],
        { x: M, y: 5.95, w: 6.2, h: 0.5, fontSize: 16 });
    arrow(s, 6.85, 3.75, 0.6, 0.5);
    photo(s, "RGB_323F.jpg", 7.75, 1.95, 4.0, null, null, HEX.accent3);
    s.addShape(pres.shapes.OVAL, { x: 9.15, y: 3.3, w: 1.2, h: 1.2, fill: { type: "none" }, line: { color: HEX.accent4, width: 4 } });
    txt(s, [{ text: "실제로는 날림 불량\n", options: { bold: true, color: C.accent3, fontSize: 20 } },
            { text: "사진에는 가운데 튀어나온 쇳조각이 보인다", options: { color: C.text1, fontSize: 15 } }],
        { x: 7.75, y: 6.05, w: 4.6, h: 0.75 });
    s.addNotes(`문제는 이겁니다. 이 용접의 기록을 같은 설정의 다른 용접들과 비교하면 최대 전류와 누르는 힘은 보통 범위이고, 평균 전류만 범위 끝자락입니다. 숫자만 보면 정상인지 불량인지 알 수 없습니다. 실제로는 날림이었고, 사진에는 가운데 튀어나온 쇳조각이 보입니다. 숫자만 보는 규칙은 날림을 ${r0(RB.rule_peak_current_p90.explode_recall)}, 정답으로 학습한 AI도 ${r0(RB.supervised_rf_reference.explode_recall)}밖에 못 찾습니다.`);
  }

  // ══ 4. 전문가는 가서 본다 ═════════════════════════════════════════════
  {
    const s = light("아이디어", "전문가는 모르면, |\"가서 보자\"고 한다");
    const rows = [
      ["FaUserDoctor", HEX.accent5, "의사", "증상만으로는 애매하다", "FaXRay", "\"엑스레이 찍어 봅시다\"", "사진을 읽고 진단"],
      ["FaIndustry", HEX.accent5, "숙련 엔지니어", "기록만으로는 애매하다", "FaCamera", "\"가서 직접 보자\"", "눈으로 확인하고 원인 확정"],
    ];
    rows.forEach(([ic, icol, who, a, ic2, b, c], i) => {
      const y = 2.05 + i * 1.75;
      box(s, M, y, 11.9, 1.45, C.background2);
      iconDot(s, ic, icol, C.background1, M + 0.3, y + 0.32, 0.8);
      txt(s, who, { x: M + 1.3, y: y + 0.5, w: 1.9, h: 0.45, fontSize: 18, bold: true, color: C.text1 });
      txt(s, a, { x: M + 3.1, y: y + 0.5, w: 2.8, h: 0.45, fontSize: 17, color: C.text1 });
      arrow(s, M + 5.85, y + 0.55);
      iconDot(s, ic2, HEX.accent6, "ECE9FE", M + 6.45, y + 0.32, 0.8);
      txt(s, b, { x: M + 7.4, y: y + 0.5, w: 2.4, h: 0.45, fontSize: 17, bold: true, color: C.accent6 });
      arrow(s, M + 9.7, y + 0.55);
      txt(s, c, { x: M + 10.3, y: y + 0.38, w: 1.5, h: 0.7, fontSize: 15, color: C.text1 });
    });
    box(s, M, 5.75, 11.9, 0.95, "FFF1EA");
    iconDot(s, "FaRobot", HEX.lt1, HEX.accent1, M + 0.25, 5.88, 0.68);
    txt(s, [{ text: "지금까지의 AI는 숫자만 보고 답했다.  ", options: { color: C.text1 } },
            { text: "우리 AI는 엔지니어처럼 \"가서 보자\"를 할 줄 안다.", options: { bold: true, color: C.accent1 } }],
        { x: M + 1.15, y: 5.98, w: 10.5, h: 0.5, fontSize: 19, valign: "middle" });
    s.addNotes("사람 전문가는 이럴 때 어떻게 할까요. 의사는 증상만으로 애매하면 엑스레이를 찍자고 합니다. 숙련 엔지니어도 기록만으로 애매하면 가서 직접 봅니다. 지금까지의 AI는 숫자만 보고 답했습니다. 저는 AI가 엔지니어처럼 '가서 보자'를 할 줄 알게 만들었습니다.");
  }

  // ══ 5. 묻는 AI — 채팅으로 ═════════════════════════════════════════════
  {
    const s = light("해결", "그래서 만든 것 — |모르면 먼저 물어보는 AI");
    box(s, M, 1.9, 6.6, 4.95, "F6F5FB");
    bubble(s, "ai", M + 0.25, 2.1, 5.9, 0.75, "기록만으로는 정상인지 날림인지 갈리지 않아요.");
    bubble(s, "ai", M + 0.25, 3.0, 5.9, 1.05, "용접 자국 앞면과 뒷면을 가까이 찍어 주세요.\n탄 고리나 튄 쇳조각이 보이면 날림이에요.");
    box(s, M + 2.95, 4.2, 2.6, 1.25, "ECE9FE", { r: 0.18 });
    s.addImage({ path: PH("RGB_323F.jpg"), x: M + 3.08, y: 4.3, w: 1.05, h: 1.05 });
    s.addImage({ path: PH("RGB_323B.jpg"), x: M + 4.3, y: 4.3, w: 1.05, h: 1.05 });
    iconDot(s, "FaHelmetSafety", HEX.lt1, HEX.accent6, M + 5.7, 4.2, 0.55);
    bubble(s, "ai", M + 0.25, 5.6, 5.9, 1.05, "앞면에 정상 샘플에는 없는 쇳조각이 보여요.\n→ 날림으로 판단합니다. (근거: 앞면 사진)");
    txt(s, "왼쪽 대화는 실제 실행 기록을 우리말로 옮긴 것", { x: 7.7, y: 6.45, w: 4.9, h: 0.3, fontSize: 11, color: C.accent5 });
    const pts = [
      ["FaCamera", "무엇을 찍을지 스스로 정한다", "기록과 매뉴얼로 추리하다 막히면, 어떤 사진이 답을 가를지 판단해 요청"],
      ["FaListCheck", "보기 전에 기준부터 말한다", "\"이게 보이면 날림\"을 먼저 선언 — 사진을 본 뒤 말 바꾸기 금지"],
      ["FaImage", "합격품 사진과 나란히 비교한다", "같은 설정으로 만든 정상 용접 사진을 옆에 놓고 다른 점을 찾는다"],
    ];
    pts.forEach(([ic, t, d], i) => {
      const y = 2.0 + i * 1.6;
      iconDot(s, ic, HEX.accent1, "FFF1EA", 7.7, y, 0.8);
      txt(s, t, { x: 8.7, y: y + 0.02, w: 4.0, h: 0.45, fontSize: 19, bold: true, color: C.text1 });
      txt(s, d, { x: 8.7, y: y + 0.5, w: 4.0, h: 0.8, fontSize: 14, color: C.accent5 });
    });
    s.addNotes("그래서 만든 서비스입니다. 대화로 보면 이렇습니다. AI가 기록만으로는 갈리지 않는다고 판단하면, 작업자에게 앞면과 뒷면을 찍어 달라고 요청합니다. 이때 사진을 보기 전에 '탄 고리나 튄 쇳조각이 보이면 날림'이라고 기준부터 말합니다. 작업자가 사진을 올리면, AI가 합격품 사진과 나란히 비교해 날림이라고 결론 냅니다. 실제 실행 기록을 우리말로 옮긴 것입니다.");
  }

  // ══ 6. 실제 화면 ════════════════════════════════════════════════════
  {
    const s = light("완성도", "실제로 돌아가는 서비스 — |관제 화면과 작업자 휴대폰");
    box(s, M, 1.85, 7.4, 4.4, "2A2F36", { r: 0.16 });
    s.addImage({ path: AS("ui_overview.png"), x: M + 0.12, y: 1.97, w: 7.16, h: 4.16, sizing: { type: "cover", w: 7.16, h: 4.16 } });
    box(s, 8.3, 1.85, 2.05, 4.4, "2A2F36", { r: 0.28 });
    s.addImage({ path: AS("ui_mobile.png"), x: 8.4, y: 1.98, w: 1.85, h: 4.14, sizing: { type: "cover", w: 1.85, h: 4.14 } });
    const caps = [[M, 7.4, "1", "AI 의 가설과 점수 · 촬영 요청 · 실행 기록이 한 화면에"], [8.3, 2.05, "2", "QR 로 열고 바로 촬영"]];
    caps.forEach(([x, w, n, t]) => {
      dot(s, x, 6.43, 0.34, HEX.accent1);
      txt(s, n, { x, y: 6.43, w: 0.34, h: 0.34, fontSize: 12, bold: true, color: C.background1, align: "center", valign: "middle" });
      txt(s, t, { x: x + 0.45, y: 6.41, w: w - 0.45, h: 0.4, fontSize: 13, bold: true, color: C.text1, valign: "middle" });
    });
    const st = [[String(F.tests), "자동 테스트"], ["GitHub", "코드 전체 공개"], ["HTML 1개", "서버 없이 여는\n시연 재생"]];
    st.forEach(([b, l], i) => {
      const y = 1.95 + i * 1.5;
      txt(s, b, { x: 10.85, y, w: 1.75, h: 0.55, fontSize: i ? 18 : 28, bold: true, color: C.accent1, valign: "bottom" });
      txt(s, l, { x: 10.85, y: y + 0.6, w: 1.75, h: 0.7, fontSize: 12, color: C.accent5 });
    });
    s.addNotes(`실제로 돌아가는 서비스입니다. 왼쪽이 관제 화면입니다. AI가 세운 가설과 점수가 실시간으로 바뀌고, 촬영이 필요하면 요청 내용과 QR 코드가 뜹니다. 작업자가 QR을 찍으면 오른쪽 휴대폰 화면이 열리고 바로 촬영해 올릴 수 있습니다. 자동 테스트 ${F.tests}개와 함께 GitHub에 공개했습니다.`);
  }

  // ══ 6-1. 시연 영상 — deck/assets/demo.mp4 가 있을 때만 (deck/replay/demo.html 을 화면 녹화한 것) ══
  const VIDEO = AS("demo.mp4");
  if (fs.existsSync(VIDEO)) {
    const s = pres.addSlide({ masterName: "DARK" });
    txt(s, "■ 시연 영상  /  실제 실행 기록 재생", { x: M, y: 0.5, w: 8, h: 0.35, fontSize: 13, bold: true, color: C.accent1, fontFace: "Courier New", charSpacing: 1 });
    const vh = 5.6, vw = vh * 16 / 9, vx = (13.333 - vw) / 2;     // 16:9 그대로 (녹화 1920×1080)
    s.addMedia({ type: "video", path: VIDEO, x: vx, y: 1.0, w: vw, h: vh,
                 cover: "image/png;base64," + fs.readFileSync(AS("ui_overview.png")).toString("base64") });
    txt(s, "왼쪽 사건을 누르면 그 사건의 실제 실행 기록이 재생된다 — 날림 E-323 · 정상 E-357 · 공장 데이터", { x: vx, y: 6.75, w: vw, h: 0.3, fontSize: 11, color: "8A9099" });
    s.addNotes("시연 영상입니다. 실제 실행 기록을 시간만 압축해 재생한 것입니다. 날림 사건에서는 AI가 기록만으로 애매하다고 판단해 앞면과 뒷면 촬영을 요청하고, 사진을 합격품과 비교해 날림으로 결론 냅니다.");
  }

  // ══ 7. 실제 실행 1분 ═════════════════════════════════════════════════
  {
    const s = light("실제 실행", `실제 실행 기록 — |${Math.round(DEMO.meta.elapsed_s)}초 만에 날림을 찾아냈다`);
    const steps = [
      [0, "기록 확인", "숫자만으로는\n애매하다", HEX.accent5, null],
      [secs(req), "촬영 요청", "앞면·뒷면을\n찍어 달라고 요청", HEX.accent6, null],
      [secs(reads[0]), "앞면 판독", "정상 샘플에 없는\n쇳조각 발견", HEX.accent3, "RGB_323F.jpg"],
      [secs(reads[1]), "뒷면 판독", "특이점 없음", HEX.accent2, "RGB_323B.jpg"],
      [secs(fin), "결론: 날림", "뒷면이 정상이어도\n앞면 결함은 남는다", HEX.accent1, null],
    ];
    const x0 = M + 0.6, span = 10.7, y = 4.2;
    s.addShape(pres.shapes.LINE, { x: x0, y: y + 0.2, w: span, h: 0, line: { color: "D5D8DD", width: 3 } });
    steps.forEach(([t, title, d, col, ph], i) => {
      const x = x0 + span * i / (steps.length - 1);
      dot(s, x - 0.2, y, 0.4, col);
      txt(s, `${t}초`, { x: x - 0.8, y: y + 0.5, w: 1.6, h: 0.4, fontSize: 15, bold: true, color: col, align: "center" });
      txt(s, title, { x: x - 1.1, y: y + 0.9, w: 2.2, h: 0.45, fontSize: 18, bold: true, color: C.text1, align: "center" });
      txt(s, d, { x: x - 1.1, y: y + 1.38, w: 2.2, h: 0.75, fontSize: 14, color: C.accent5, align: "center" });
      if (ph) photo(s, ph, x - 0.85, 2.05, 1.7, null, null, col);
    });
    box(s, x0 + span - 1.25, 2.3, 2.5, 1.3, "FFF1EA");
    txt(s, [{ text: "날림\n", options: { bold: true, fontSize: 28, color: C.accent1 } }, { text: "정답과 일치 ✓", options: { fontSize: 14, bold: true, color: C.accent2 } }],
        { x: x0 + span - 1.25, y: 2.42, w: 2.5, h: 1.1, align: "center" });
    box(s, x0 - 0.6, 2.3, 2.6, 1.3, C.background2);
    txt(s, [{ text: "같은 설정 용접들과\n비교하면 ", options: { fontSize: 14, color: C.text1 } }, { text: "거의 보통", options: { fontSize: 14, bold: true, color: C.accent5 } }],
        { x: x0 - 0.45, y: 2.5, w: 2.3, h: 1.0, align: "center" });
    txt(s, "실제 실행 기록 · 시연 영상은 이 기록을 그대로 재생한 것 (deck/replay/demo.html)", { x: M, y: 6.5, w: 11.9, h: 0.3, fontSize: 11, color: C.accent5 });
    s.addNotes(`실제 실행 기록입니다. 0초에 기록을 확인했는데 숫자로는 애매합니다. ${secs(req)}초에 AI가 앞면과 뒷면 촬영을 요청합니다. ${secs(reads[0])}초에 앞면 사진에서 정상 샘플에 없는 쇳조각을 찾고, ${secs(reads[1])}초에 뒷면은 특이점이 없다고 읽습니다. 두 신호가 엇갈려 시스템이 한 번 되물었고, AI는 뒷면이 정상이어도 앞면 결함은 없어지지 않는다고 판단해 ${secs(fin)}초에 날림으로 결론 냈습니다. 정답입니다.`);
  }

  // ══ 8. 기술 ════════════════════════════════════════════════════════
  {
    const s = light("LLM · VLM 기술", "속을 들여다보면 — |기술 9가지가 한 흐름으로");
    const cols = [
      ["생각한다", HEX.accent2, [
        ["FaBrain", "추론 루프 (Agent)", "가설과 점수를 고치며 다음 행동을 스스로 고른다"],
        ["FaScrewdriverWrench", "도구 호출 (Tool Calling)", "기록 조회 · 매뉴얼 · 도면 · 과거 사례를 골라 쓴다"],
        ["FaBookOpen", "매뉴얼·도면 검색 (RAG)", `매뉴얼 ${F.manual_pages}쪽과 도면 ${F.diagrams_described}장을 찾아 읽는다 (Multimodal)`],
      ]],
      ["보고 · 묻는다", HEX.accent6, [
        ["FaEye", "사진 판독 (VLM)", "합격품 사진과 나란히 놓고 다른 점을 찾는다"],
        ["FaComments", "사람에게 요청하기", "Human-in-the-loop — 사진을 기다리는 동안 멈췄다가, 오면 이어서 진단"],
      ]],
      ["믿을 수 있게", HEX.accent1, [
        ["FaListCheck", "보기 전 선언 · 되묻기", "기준과 다른 결론이면 한 번 더 묻는다"],
        ["FaQuoteLeft", "근거 인용 검증", "모든 결론에 근거를 달고, 없는 근거는 거부"],
        ["FaClockRotateLeft", "대화 이어 쓰기", `같은 대화를 이어 써서 입력량 ${F.resume_tokens[0].toLocaleString()} → ${F.resume_tokens[1]}`],
        ["FaGavel", "AI 채점 (LLM-as-Judge)", "다른 모델(Opus)이 정답과 비교해 채점"],
      ]],
    ];
    const cw = 3.85, gx = 0.17, top = 2.45, H = 4.05;
    cols.forEach(([head, col, items], ci) => {
      const x = M + ci * (cw + gx);
      box(s, x, 1.85, cw, 0.48, col, { r: 0.24 });
      txt(s, head, { x, y: 1.85, w: cw, h: 0.48, fontSize: 16, bold: true, color: C.background1, align: "center", valign: "middle" });
      const gap = 0.14, h = (H - gap * (items.length - 1)) / items.length;
      items.forEach(([ic, t, d], k) => {
        const y = top + k * (h + gap);
        const off = h > 1.6 ? (h - 1.3) / 2 : 0.16;              // 큰 카드는 내용을 세로 가운데로
        box(s, x, y, cw, h, C.background2);
        ico(s, ic, col, x + 0.22, y + off + 0.03, 0.4);
        txt(s, t, { x: x + 0.78, y: y + off, w: cw - 0.95, h: 0.45, fontSize: 15, bold: true, color: C.text1 });
        txt(s, d, { x: x + 0.78, y: y + off + 0.45, w: cw - 0.95, h: Math.min(0.85, Math.max(0.4, h - off - 0.55)), fontSize: 12.5, color: C.accent5 });
      });
    });
    txt(s, "모델: 진단 Claude Sonnet · 사진 판독 Claude Haiku · 채점 Claude Opus", { x: 5.6, y: 6.57, w: 7.0, h: 0.3, fontSize: 11, color: C.accent5, align: "right" });
    s.addNotes("기술적으로 보면 아홉 가지가 한 흐름으로 이어집니다. 생각하는 부분은 추론 루프, 도구 호출, 매뉴얼과 도면 검색입니다. 보고 묻는 부분은 사진 판독과 사람에게 요청하는 기능인데, 사진을 기다리는 동안 진단을 멈췄다가 사진이 오면 이어갑니다. 믿을 수 있게 하는 부분은 보기 전 선언과 되묻기, 근거 인용 검증, 대화 이어 쓰기, 그리고 다른 모델로 채점하는 것입니다.");
  }

  // ══ 9. 효과 ════════════════════════════════════════════════════════
  {
    const s = light("효과", "같은 시험 58문제 — |사진을 요청하는 AI가 가장 많이 맞혔다");
    const bars = [
      ["숫자 규칙", RB.rule_peak_current_p90.accuracy],
      ["학습 AI *", RB.supervised_rf_reference.accuracy],
      ["우리 AI\n사진 없이", MC["E-none"].sonnet.pct],
      ["우리 AI\n사진 요청", E.photo.accuracy],
    ];
    const last = bars.length - 1;
    s.addChart(pres.charts.BAR, [
      { name: "비교", labels: bars.map(b => b[0]), values: bars.map((b, i) => i === last ? 0 : Math.round(b[1])) },
      { name: "우리", labels: bars.map(b => b[0]), values: bars.map((b, i) => i === last ? Math.round(b[1]) : 0) },
    ], {
      x: M, y: 1.9, w: 7.0, h: 4.45, barDir: "col", barGrouping: "stacked", barGapWidthPct: 55,
      chartColors: ["C3C7CE", HEX.accent1], showLegend: false,
      showValue: true, dataLabelPosition: "inEnd", dataLabelFormatCode: "0\"%\";;;", dataLabelColor: "FFFFFF",
      dataLabelFontSize: 18, dataLabelFontBold: true, dataLabelFontFace: "+mn-lt",
      catAxisLabelColor: HEX.dk1, catAxisLabelFontSize: 14, catAxisLabelFontFace: "+mn-lt",
      valAxisHidden: true, valAxisMaxVal: 100, valAxisMinVal: 0, valGridLine: { style: "none" }, catGridLine: { style: "none" },
      catAxisLineShow: false,
    });
    txt(s, "정답률 · 날림과 정상이 반반이라 아무렇게나 찍으면 50%   * 정답 수백 개로 학습", { x: M, y: 6.62, w: 7.2, h: 0.3, fontSize: 11, color: C.accent5 });
    const x = 8.15;
    box(s, x, 1.95, 4.5, 2.2, "FFF1EA");
    txt(s, "날림을 찾아낸 수", { x: x + 0.35, y: 2.1, w: 3.9, h: 0.4, fontSize: 15, color: C.accent5 });
    txt(s, [{ text: `${Math.round(MC["E-none"].sonnet.explode_recall * E.photo.explode_n / 100)}개`, options: { color: C.accent5 } },
            { text: "  →  ", options: { color: C.accent5 } },
            { text: `${E.photo.explode_hit}개`, options: { color: C.accent1 } }],
        { x: x + 0.35, y: 2.55, w: 3.9, h: 0.85, fontSize: 40, bold: true });
    txt(s, `날림 ${E.photo.explode_n}개 중 · 사진 없이 → 사진 요청`, { x: x + 0.35, y: 3.5, w: 3.9, h: 0.4, fontSize: 14, color: C.text1 });
    box(s, x, 4.35, 4.5, 2.2, C.background2);
    txt(s, "정상을 정상으로", { x: x + 0.35, y: 4.5, w: 3.9, h: 0.4, fontSize: 15, color: C.accent5 });
    txt(s, `${E.photo.good_hit} / ${E.photo.good_n}`, { x: x + 0.35, y: 4.95, w: 3.9, h: 0.85, fontSize: 40, bold: true, color: C.accent2 });
    txt(s, "멀쩡한 용접을 불량이라고 한 경우는 거의 없다", { x: x + 0.35, y: 5.9, w: 3.9, h: 0.4, fontSize: 14, color: C.text1 });
    s.addNotes(`같은 시험 58문제로 비교했습니다. 날림과 정상이 반반이라 아무렇게나 찍으면 50%입니다. 숫자 규칙은 ${r0(RB.rule_peak_current_p90.accuracy)}, 정답 수백 개로 학습한 AI는 ${r0(RB.supervised_rf_reference.accuracy)}, 우리 AI도 사진 없이는 ${r0(MC["E-none"].sonnet.pct)}였습니다. 사진을 요청하게 하자 ${r0(E.photo.accuracy)}로 가장 높았습니다. 특히 날림을 사진 없이는 하나도 못 찾았는데, 사진을 요청하자 ${E.photo.explode_n}개 중 ${E.photo.explode_hit}개를 찾았습니다.`);
  }

  // ══ 10. 바꿔치기 ════════════════════════════════════════════════════
  {
    const s = light("검증", "AI가 사진을 진짜 볼까? — |사진을 몰래 바꿔 봤다");
    const cards = [
      ["이 용접의 진짜 사진을 주면", "RGB_323F.jpg", r0(E.photo.accuracy), HEX.accent1, "FFF1EA"],
      ["다른 용접 사진으로 몰래 바꾸면", "RGB_310F.jpg", r0(E.swap.accuracy), HEX.accent5, C.background2],
    ];
    cards.forEach(([t, ph, v, col, bg], i) => {
      const x = M + i * 6.05;
      box(s, x, 1.9, 5.85, 3.6, bg);
      txt(s, t, { x: x + 0.35, y: 2.1, w: 5.2, h: 0.45, fontSize: 18, bold: true, color: C.text1 });
      photo(s, ph, x + 0.35, 2.75, 2.4, null, null, i ? "C3C7CE" : HEX.accent1);
      arrow(s, x + 2.95, 3.75, 0.5, 0.42);
      txt(s, [{ text: v, options: { fontSize: 54, bold: true, color: col } }, { text: "\n정답률", options: { fontSize: 15, color: C.accent5 } }],
          { x: x + 3.6, y: 3.05, w: 2.1, h: 1.6, align: "center" });
    });
    iconDot(s, "FaUserDoctor", HEX.accent6, "ECE9FE", M, 5.8, 0.8);
    txt(s, [{ text: "다른 환자의 엑스레이를 주면 의사가 오진하는 것처럼 — 결론이 사진을 따라 바뀐다.\n", options: { color: C.text1, bold: true } },
            { text: `같은 문제끼리 비교: 진짜 사진에서만 맞힌 ${E.photo_vs_swap.only_photo_ref}문제, 바꿔치기에서만 맞힌 ${E.photo_vs_swap.only_swap_ref}문제 (${pfmt(E.photo_vs_swap.p_two_sided)})`, options: { color: C.accent5 } }],
        { x: M + 1.0, y: 5.8, w: 10.9, h: 0.95, fontSize: 16 });
    s.addNotes(`AI가 정말 사진을 보는지, 그냥 그럴듯하게 말하는지 확인하려고 사진을 몰래 바꿔 봤습니다. 진짜 사진을 주면 ${r0(E.photo.accuracy)}, 다른 용접 사진으로 바꾸면 ${r0(E.swap.accuracy)}로 떨어집니다. 다른 환자의 엑스레이를 주면 의사가 오진하는 것과 같습니다. 결론이 사진 내용을 따라 바뀐다는 뜻이고, 같은 문제끼리 비교하면 ${E.photo_vs_swap.only_photo_ref} 대 ${E.photo_vs_swap.only_swap_ref}로 우연이 아닙니다.`);
  }

  // ══ 11. 막힌 곳 4개 ═════════════════════════════════════════════════
  {
    const s = light("개발 과정", "한 번에 된 게 아니다 — |막힌 곳 4개를 차례로 풀었다");
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
      txt(s, `${i + 1}`, { x: x + 0.25, y: y + 0.15, w: 0.6, h: 0.5, fontSize: 24, bold: true, color: i === 3 ? C.background1 : C.text1 });
      txt(s, fix, { x: x + 0.25, y: y + 0.65, w: w - 0.4, h: 0.45, fontSize: 17, bold: true, color: i === 3 ? C.background1 : C.text1 });
      txt(s, res, { x: x + 0.25, y: y + 1.05, w: w - 0.4, h: 0.4, fontSize: 14, bold: true, color: i === 3 ? C.background1 : "8A3B12" });
      txt(s, prob, { x, y: y - 0.85, w, h: 0.75, fontSize: 14, color: C.accent5, valign: "bottom" });
    });
    txt(s, `4단계에선 "어느 면이든 찍을 수 있다"고만 알렸는데, AI가 ${E.asked_back[1]}건 중 ${E.asked_back[0]}건에서 스스로 뒷면을 요청했다`,
        { x: M, y: 1.85, w: 7.0, h: 0.75, fontSize: 15, bold: true, color: C.accent1 });
    s.addNotes(`한 번에 된 것은 아닙니다. 막힌 곳 네 개를 차례로 풀었습니다. 처음엔 사진이 없으면 날림을 못 찾아서 사진 요청 기능을 넣었습니다. 다음엔 AI가 미세한 흔적을 못 봐서 합격품 사진을 옆에 놓고 비교하게 했습니다. 그다음엔 사진을 보고도 숫자를 더 믿어서, 보기 전에 한 선언을 지키게 했습니다. 마지막으로 앞면에 흔적이 없는 날림이 남았는데, 어느 면이든 찍을 수 있다고만 알리자 AI가 거의 모든 경우에 스스로 뒷면을 요청했고 날림 발견이 두 배가 됐습니다.`);
  }

  // ══ 12. 남은 숙제 ═══════════════════════════════════════════════════
  {
    const s = light("한계", "아직 남은 숙제 — |날림의 절반 이상은 놓친다");
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
            { text: "불량 판정은 사진이 아니라 뜯어서 잰 결과라, 겉으로는 흔적이 없을 수 있다.", options: { color: C.accent5 } }],
        { x: M + 0.9, y: 5.3, w: 5.15, h: 1.25, fontSize: 14 });
    const lims = [
      ["같은 시험 문제를 여러 번 썼다", "날림 사례가 31개뿐 — 그래서 개선은 여기서 멈췄다"],
      ["실행할 때마다 답이 조금 달라진다", "시연은 실제 실행 기록을 그대로 재생"],
      ["사진은 공개 데이터의 실제 사진", "현장에서 직접 찍는 검증은 다음 단계"],
    ];
    lims.forEach(([t, d], i) => {
      const y = 2.0 + i * 1.25;
      box(s, 7.35, y, 5.25, 1.05, C.background2);
      txt(s, t, { x: 7.6, y: y + 0.15, w: 4.9, h: 0.4, fontSize: 16, bold: true, color: C.text1 });
      txt(s, d, { x: 7.6, y: y + 0.57, w: 4.9, h: 0.4, fontSize: 13, color: C.accent5 });
    });
    box(s, 7.35, 5.75, 5.25, 0.9, "FFF1EA");
    txt(s, [{ text: "다음 단계  ", options: { bold: true, color: C.accent1 } }, { text: "현장에 쌓이는 검사 사진을 예시로 함께 보여주기", options: { color: C.text1 } }],
        { x: 7.6, y: 5.75, w: 4.9, h: 0.9, fontSize: 15, valign: "middle" });
    s.addNotes(`한계도 말씀드립니다. 날림 ${fz.total}개 중 사진에서 이상을 찾은 건 ${fz.reader_flagged}개, 날림이라고 결론 낸 건 ${fz.flagged_and_concluded}개입니다. ${fz.reader_saw_nothing}개는 사진 어디에서도 흔적을 못 찾았는데, 불량 판정이 뜯어서 잰 결과라 겉으로는 흔적이 없을 수 있습니다. 또 날림 사례가 적어서 같은 시험 문제를 여러 번 썼고, 그래서 개선은 여기서 멈췄습니다.`);
  }

  // ══ 13. 마무리 ═════════════════════════════════════════════════════
  {
    const s = pres.addSlide({ masterName: "DARK" });
    txt(s, [{ text: "답하는 AI에서,\n", options: { color: "6B7280" } }, { text: "묻는 AI로", options: { color: C.background1 } }],
        { x: M, y: 1.3, w: 8, h: 2.4, fontSize: 54, bold: true });
    const pts = [
      ["FaCamera", "모르면 무엇을 찍을지 스스로 정해 요청한다"],
      ["FaImage", "합격품 사진과 비교해 읽고, 근거를 달아 결론 낸다"],
      ["FaShuffle", `실제 용접 58건 정답률 ${r0(E.photo.accuracy)} — 사진을 바꾸면 ${r0(E.swap.accuracy)}`],
    ];
    pts.forEach(([ic, t], i) => {
      const y = 4.15 + i * 0.75;
      ico(s, ic, ic === "FaCamera" ? HEX.accent1 : ic === "FaImage" ? HEX.accent6 : HEX.accent6, M, y + 0.05, 0.42);
      txt(s, t, { x: M + 0.65, y, w: 10, h: 0.5, fontSize: 19, color: "E4E6E9", valign: "middle" });
    });
    ico(s, "FaGithub", "8A9099", M, 6.65, 0.35);
    txt(s, "github.com/dlwogud/rootcause-stream", { x: M + 0.5, y: 6.65, w: 6, h: 0.35, fontSize: 13, color: "8A9099", valign: "middle" });
    photo(s, "RGB_323F.jpg", 9.3, 1.3, 3.3, null, null, "2A3038");
    s.addNotes("정리하겠습니다. 답하는 AI에서 묻는 AI로. 모르면 무엇을 찍을지 스스로 정해 요청하고, 합격품 사진과 비교해 근거를 달아 결론을 냅니다. 감사합니다.");
  }

  // ══ 부록 ══════════════════════════════════════════════════════════
  {
    const s = light("부록 A", "측정 이력과 정정 — |숫자는 모두 원 자료에서");
    const head = t => ({ text: t, options: { bold: true, color: C.background1, fill: { color: C.text1 } } });
    s.addTable([
      [head("실행"), head("조건 (진단 Sonnet · 판독 Haiku · 채점 Opus)"), head("정답률"), head("날림")],
      ["—", "사진 없음", r0(MC["E-none"].sonnet.pct), r0(MC["E-none"].sonnet.explode_recall)],
      ["—", "앞면 사진", r0(MC["E-photo"].sonnet.pct), r0(MC["E-photo"].sonnet.explode_recall)],
      [`#${E.front_only.run}`, "앞면 + 합격품 비교 + 보기 전 선언", r0(E.front_only.accuracy), r0(E.front_only.explode_recall)],
      [`#${E.run}`, "앞·뒷면 + 합격품 비교 + 보기 전 선언 (최종)", r0(E.photo.accuracy), r0(E.photo.explode_recall)],
      [`#${E.run}`, "↳ 바꿔치기 사진", r0(E.swap.accuracy), r0(E.swap.explode_recall)],
      ["—", "숫자 규칙 (최대 전류 > 같은 설정 상위 10%)", r0(RB.rule_peak_current_p90.accuracy), r0(RB.rule_peak_current_p90.explode_recall)],
      ["—", "학습 AI (랜덤 포레스트, 판정 라벨로 학습)", r0(RB.supervised_rf_reference.accuracy), r0(RB.supervised_rf_reference.explode_recall)],
    ], { x: M, y: 1.85, w: 11.9, colW: [1.2, 7.1, 1.8, 1.8], fontSize: 14, rowH: 0.45,
         border: { type: "solid", pt: 0.75, color: "D7DADF" }, valign: "middle", margin: [0, 0.15, 0, 0.15], color: HEX.dk1 });
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
    s.addNotes(`최종 대 앞면만: 최종에서만 맞힘 ${E.final_vs_front.only_final}, 앞면만에서만 ${E.final_vs_front.only_front}, ${pfmt(E.final_vs_front.p_two_sided)} (경계).`);
  }
  {
    const au = F.audit, kb = N.rule_baseline.kamp;
    const s = light("부록 B", "공장 데이터(KAMP)에서 — |이상의 정체는 '기록 재활용'");
    box(s, M, 1.9, 5.6, 2.4, C.background2);
    txt(s, `${au.dup_index_pct}% → ${au.reused_pct}%`, { x: M + 0.3, y: 2.05, w: 5.0, h: 0.8, fontSize: 36, bold: true, color: C.accent1 });
    txt(s, `알려진 중복 비율 → 실제로 다른 날 기록과 수백 줄씩 똑같은 비율 (순서를 섞으면 최대 ${au.chance_longest}줄)`, { x: M + 0.3, y: 2.95, w: 5.0, h: 1.2, fontSize: 14, color: C.text1 });
    const head = t => ({ text: t, options: { bold: true, color: C.background1, fill: { color: C.text1 } } });
    s.addTable([
      [head("원인 정답률"), head("AI"), head("규칙 한 줄")],
      ["A 조용한 수준 이동", `${r0(MC.A.sonnet.pct)} (sonnet)`, r0(kb.A.pct)],
      ["C 알람 폭주", `${r0(N.conditions.full.C.M1_match.mean)} (haiku)`, r0(kb.C.pct)],
      ["B 주입 고장 (주 변수)", `${r0(N.conditions.full.B.M2_primary_variable.mean)} (haiku)`, r0(kb.B.pct)],
    ], { x: 6.6, y: 1.9, w: 6.0, colW: [2.6, 1.9, 1.5], fontSize: 14, rowH: 0.55,
         border: { type: "solid", pt: 0.75, color: "D7DADF" }, valign: "middle", margin: [0, 0.15, 0, 0.15], color: HEX.dk1 });
    txt(s, [{ text: "정직한 위치  ", options: { bold: true, color: C.accent1 } },
            { text: "결정적 신호(다른 날과의 연속 일치 비율)는 사람이 설계했고, 그 신호가 있으면 규칙 한 줄도 AI만큼 맞힌다. 신호 없이 원본 기록과 SQL만 주자 AI는 스스로 찾지 못했다 (Sonnet 0%). 그래서 AI만의 기여는 사진 실험으로 주장한다.", options: { color: C.text1 } }],
        { x: M, y: 4.65, w: 11.9, h: 1.5, fontSize: 15 });
    s.addNotes("공장 데이터 관련 질문이 나오면 쓰는 부록입니다.");
  }
  {
    const s = light("부록 C", "데이터와 출처");
    const items = [
      ["사진 실험", "RSW Insights — L. A. Dominguez Molina, Mendeley Data V3 (2025), CC BY 4.0. 용접 495회 · 앞·뒷면 사진 · 파괴 시험 판정"],
      ["시험 문제", "날림 29 + 같은 설정의 정상 29 = 58건 (개발용 4건 제외), 같은 문제를 조건만 바꿔 비교"],
      ["공장 데이터", "KAMP 저항 점용접 공정 데이터 — 재배포 권한이 확인되지 않아 레포에는 받는 방법만"],
      ["매뉴얼", `제조사 매뉴얼 ${F.manual_docs}종 ${F.manual_pages}쪽, 도면 ${F.diagrams_described}장 — 받는 방법만`],
      ["재현", "eval/run_tier_e.py (사진 실험) · deck/export_numbers.py (발표 수치) · deck/replay/*.html (시연 재생)"],
    ];
    items.forEach(([k, v], i) => {
      const y = 1.95 + i * 0.95;
      box(s, M, y, 11.9, 0.8, C.background2);
      txt(s, k, { x: M + 0.3, y, w: 2.0, h: 0.8, fontSize: 15, bold: true, color: C.accent1, valign: "middle" });
      txt(s, v, { x: M + 2.4, y, w: 9.3, h: 0.8, fontSize: 14, color: C.text1, valign: "middle" });
    });
    s.addNotes("데이터 출처 부록입니다.");
  }

  await pres.writeFile({ fileName: OUT });
  await applyTheme(OUT, THEME);
  console.log("→", OUT);
}
build().catch(e => { console.error(e); process.exit(1); });
