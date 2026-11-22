// RootCause Stream 발표자료 생성기 (2026-11-22 재구성 — 사진 중심, 발표 약 10분)
//   수치는 numbers.json(← export_numbers.py ← 평가 결과)에서만 읽는다. 손으로 적지 않는다.
//   시연 장면은 data/demo_runs/e323-faces.json(실제 실행 기록)에서 옮긴다.
//   실행: .venv/bin/python deck/export_numbers.py && NODE_PATH=deck/node_modules node deck/build.js
//   평가 기준(수업 공지): 참신한 아이디어 · LLM 의 다양한 기술 · 완성도
//   (이전 구성 — 공장 데이터 중심 16장 — 은 git 기록에 있다)
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
const MC = N.model_comparison.tiers;            // sonnet 사진 없음 · 앞면 사진
const DEMO = JSON.parse(fs.readFileSync(path.join(ROOT, "data/demo_runs/e323-faces.json"), "utf8"));
const OUT = path.join(__dirname, "RootCause_Stream_발표자료.pptx");
const PH = p => path.join(ROOT, "data/photos/tier_e", p);

// ── 테마: 용접 전극의 구리색 + 차콜. Agent=청록, 결함·실패=적색, 사람·사진=보라 ─────
const THEME = {
  name: "RootCause Copper",
  headFontFace: "Apple SD Gothic Neo",
  bodyFontFace: "Apple SD Gothic Neo",
  colors: {
    dk1: "1A1D21", lt1: "FFFFFF", dk2: "23282E", lt2: "F2F3F5",
    accent1: "C8672B", accent2: "2E8B7E", accent3: "B5403A",
    accent4: "C9921F", accent5: "6B7280", accent6: "6E56CF",
    hlink: "2E8B7E", folHlink: "6E56CF",
  },
};
const HEX = THEME.colors;

const pres = new pptxgen();
pres.layout = "LAYOUT_WIDE";                // 13.333 × 7.5
pres.theme = { headFontFace: THEME.headFontFace, bodyFontFace: THEME.bodyFontFace };
pres.title = "RootCause Stream — 센서로 모르면, 사람에게 사진을 요청하는 진단 Agent";
pres.author = "이재형";
const C = pres.SchemeColor;
const M = 0.6;

const r0 = v => `${Math.round(v)}%`;
const pfmt = p => (p < 0.001 ? "p < 0.001" : `p = ${p.toFixed(p < 0.01 ? 3 : 2)}`);
const shadow = () => ({ type: "outer", blur: 8, offset: 2, angle: 90, color: "000000", opacity: 0.10 });
const t0 = DEMO.events[0].t;
const at = type => DEMO.events.find(e => e.type === type);
const secs = e => Math.round(e.t - t0);

// ── 레이아웃 ──────────────────────────────────────────────────────────
pres.defineSlideMaster({
  title: "TITLE_DARK",
  background: { color: C.text2 },
  objects: [
    { placeholder: { options: { name: "kicker", type: "body", x: M, y: 0.8, w: 12, h: 0.5,
        fontSize: 16, color: C.accent1, bold: true, margin: 0 }, text: "" } },
    { placeholder: { options: { name: "title", type: "title", x: M, y: 1.45, w: 12, h: 2.2,
        fontSize: 44, color: C.background1, bold: true, valign: "top", margin: 0 }, text: "" } },
    { placeholder: { options: { name: "sub", type: "body", x: M, y: 3.7, w: 12, h: 0.6,
        fontSize: 20, color: "C9CDD2", margin: 0 }, text: "" } },
  ],
});
pres.defineSlideMaster({
  title: "CONTENT",
  background: { color: C.background1 },
  margin: [0.4, 0.6, 0.6, 0.6],
  slideNumber: { x: 12.3, y: 7.0, w: 0.5, h: 0.3, fontSize: 10, color: C.accent5, align: "right" },
  objects: [
    { placeholder: { options: { name: "title", type: "title", x: M, y: 0.42, w: 12.1, h: 0.75,
        fontSize: 32, bold: true, color: C.text1, valign: "middle", margin: 0 }, text: "" } },
    { placeholder: { options: { name: "lead", type: "body", x: M, y: 1.17, w: 12.1, h: 0.5,
        fontSize: 16, color: C.accent1, valign: "top", margin: 0 }, text: "" } },
    { text: { text: "RootCause Stream", options: { x: M, y: 7.0, w: 4, h: 0.3, fontSize: 10,
        color: C.accent5, margin: 0 } } },
  ],
});
pres.defineSlideMaster({
  title: "CLOSING_DARK",
  background: { color: C.text2 },
  objects: [
    { placeholder: { options: { name: "title", type: "title", x: M, y: 1.7, w: 12.1, h: 1.9,
        fontSize: 40, bold: true, color: C.background1, valign: "middle", margin: 0 }, text: "" } },
  ],
});

// ── 공통 조각 ─────────────────────────────────────────────────────────
function card(s, x, y, w, h, opt = {}) {
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, {
    x, y, w, h, rectRadius: 0.12, fill: { color: opt.fill || C.background2 },
    line: opt.line ? { color: opt.line, width: opt.lineW || 1.5 } : { type: "none" },
    shadow: opt.shadow ? shadow() : undefined, objectName: opt.name,
  });
}
function badge(s, x, y, d, label, color, size = 14) {
  s.addShape(pres.shapes.OVAL, { x, y, w: d, h: d, fill: { color }, line: { type: "none" } });
  if (label) s.addText(label, { x, y, w: d, h: d, fontSize: size, bold: true, color: C.background1,
    align: "center", valign: "middle", margin: 0, isTextBox: true });
}
function txt(s, runs, o) { s.addText(runs, { isTextBox: true, margin: 0, valign: "top", ...o }); }
function arrow(s, x, y, w = 0.45, h = 0.4, color = C.accent5) {
  s.addShape(pres.shapes.RIGHT_ARROW, { x, y, w, h, fill: { color }, line: { type: "none" } });
}
function photo(s, file, x, y, d, caption, capColor = C.accent5) {
  s.addImage({ path: PH(file), x, y, w: d, h: d, altText: caption || file });
  if (caption) txt(s, caption, { x, y: y + d + 0.06, w: d, h: 0.3, fontSize: 12, color: capColor, align: "center" });
}
function content(section, title, lead) {
  const s = pres.addSlide({ masterName: "CONTENT", sectionTitle: section });
  s.addText(title, { placeholder: "title" });
  if (lead) s.addText(lead, { placeholder: "lead" });
  return s;
}

// ══ 1. 표지 ═══════════════════════════════════════════════════════════
pres.addSection({ title: "도입" });
{
  const s = pres.addSlide({ masterName: "TITLE_DARK", sectionTitle: "도입" });
  s.addText("LLM · VLM 기반 서비스 개발 프로젝트", { placeholder: "kicker" });
  s.addText("센서로 모르면,\n사람에게 사진을 요청하는 진단 Agent", { placeholder: "title" });
  s.addText("RootCause Stream — 설비 이상의 원인을 데이터 · 매뉴얼 · 현장 사진으로 추적한다", { placeholder: "sub" });
  const chips = [
    [r0(E.photo.accuracy), `실제 용접 결함 판정 정확도\n규칙 ${r0(RB.rule_peak_current_p90.accuracy)} · 학습 모델 ${r0(RB.supervised_rf_reference.accuracy)}`],
    [`${E.asked_back[0]} / ${E.asked_back[1]}`, "Agent가 스스로\n뒷면 촬영까지 요청한 사건"],
    [r0(E.swap.accuracy), "사진을 다른 용접 것으로 바꾸면\n— 사진을 진짜 근거로 쓴다"],
  ];
  chips.forEach(([big, small], i) => {
    const x = M + i * 4.1;
    card(s, x, 4.75, 3.8, 1.75, { fill: "2E343B" });
    txt(s, big, { x: x + 0.3, y: 4.9, w: 3.3, h: 0.75, fontSize: 32, bold: true, color: C.accent1 });
    txt(s, small, { x: x + 0.3, y: 5.65, w: 3.3, h: 0.75, fontSize: 14, color: "C9CDD2" });
  });
  txt(s, "이재형  ·  2026. 11", { x: M, y: 6.8, w: 6, h: 0.35, fontSize: 12, color: "8A9099" });
  s.addNotes(`한 문장으로 시작합니다. 이 서비스는 설비에 이상이 생겼을 때 AI가 원인을 추리하다가, 기록만으로 모르겠으면 현장 작업자에게 무엇을 찍어 달라고 요청하고 그 사진으로 결론을 내립니다. 아래 세 숫자가 결과입니다. 실제 용접 결함 판정에서 ${r0(E.photo.accuracy)}로 규칙과 학습 모델보다 높았고, ${E.asked_back[1]}건 중 ${E.asked_back[0]}건에서 AI가 스스로 뒷면 촬영까지 요청했습니다. 사진을 다른 용접 것으로 바꿔치기하면 ${r0(E.swap.accuracy)}로 떨어집니다. AI가 사진을 장식이 아니라 근거로 쓴다는 뜻입니다.`);
}

// ══ 2. 문제 ═══════════════════════════════════════════════════════════
{
  const s = content("도입", "경보는 \"이상\"까지만 말한다",
    "용접 불량의 원인 대부분은 센서 밖 — 매뉴얼의 도면과 현장의 눈에 있다");
  card(s, M, 1.95, 4.4, 4.75);
  txt(s, "센서가 재는 것", { x: M + 0.35, y: 2.15, w: 3.8, h: 0.4, fontSize: 18, bold: true, color: C.text1 });
  ["가압력 (bar)", "전류 (kA)", "전압 (V)", "통전 시간 (ms)"].forEach((t, i) => {
    badge(s, M + 0.4, 2.8 + i * 0.9, 0.55, String(i + 1), C.accent2, 15);
    txt(s, t, { x: M + 1.15, y: 2.85 + i * 0.9, w: 3.0, h: 0.45, fontSize: 17, color: C.text1 });
  });
  txt(s, "이게 전부다", { x: M + 0.4, y: 6.25, w: 3.6, h: 0.35, fontSize: 14, color: C.accent5, italic: true });
  const head = (t) => ({ text: t, options: { bold: true, color: C.background1, fill: { color: C.text2 } } });
  const row = (a, b) => [{ text: a, options: { color: C.text1 } },
                         { text: b, options: { color: C.accent3, bold: true } }];
  s.addTable([
    [head("실제 원인"), head("어떻게 알 수 있나")],
    row("날림 (녹은 금속이 튀어나감)", "용접 자국을 봐야 앎"),
    row("전극 팁 마모·오염", "눈으로 봐야 앎"),
    row("가압 공압 저하", "게이지를 봐야 앎"),
    row("전극 정렬 불량", "눈으로 봐야 앎"),
    row("데이터 수집 계통 이상", "오히려 정상처럼 보임"),
  ], { x: 5.4, y: 1.95, w: 7.3, colW: [3.65, 3.65], fontSize: 16, rowH: 0.62,
       border: { type: "solid", pt: 0.75, color: "D7DADF" }, valign: "middle", margin: [0, 0.15, 0, 0.15] });
  txt(s, [{ text: "매뉴얼 점검표도 사람의 확인을 요구한다 — ", options: { color: C.accent5 } },
          { text: "\"Check that the air pressure is 0.5 MPa {71 psi}.\"", options: { italic: true, color: C.text1 } },
          { text: "  (Spot Weld Inc. 매뉴얼 p.19)", options: { color: C.accent5 } }],
      { x: 5.4, y: 6.05, w: 7.3, h: 0.6, fontSize: 14 });
  s.addNotes("용접기 센서가 재는 건 네 가지뿐입니다. 그런데 실제 불량 원인은 대부분 현장에 가서 눈으로 봐야 압니다. 기존 이상탐지는 '이상입니다'에서 멈춥니다. 그다음, 즉 무엇을 확인해야 하는지가 이 프로젝트의 출발점입니다.");
}

// ══ 3. 아이디어 — 방향을 뒤집는다 ═════════════════════════════════════
{
  const s = content("도입", "AI가 답하는 서비스가 아니라, AI가 묻는 서비스",
    "모르는 것을 알고, 무엇을 봐야 하는지 사람에게 정확히 요청한다");
  card(s, M, 1.95, 5.2, 4.75);
  txt(s, "보통의 LLM 서비스", { x: M + 0.35, y: 2.15, w: 4.5, h: 0.4, fontSize: 18, bold: true, color: C.accent5 });
  [["사람", "사진·글을 올린다", C.accent6], ["AI", "답한다", C.accent5]].forEach(([who, what, col], i) => {
    const y = 2.9 + i * 1.35;
    badge(s, M + 0.4, y, 0.8, who, col, 16);
    txt(s, what, { x: M + 1.45, y: y + 0.17, w: 3.4, h: 0.5, fontSize: 18, color: C.text1 });
  });
  s.addShape(pres.shapes.LINE, { x: M + 0.8, y: 3.75, w: 0, h: 0.5, line: { color: C.accent5, width: 2, endArrowType: "triangle" } });
  txt(s, "예: 음식 사진 → 레시피\n강의자료 → 시험문제", { x: M + 0.4, y: 5.5, w: 4.6, h: 0.9, fontSize: 14, color: C.accent5 });
  card(s, 6.1, 1.95, 6.6, 4.75, { fill: "EFEBFA", line: C.accent6, lineW: 2 });
  txt(s, "RootCause Stream", { x: 6.45, y: 2.15, w: 6, h: 0.4, fontSize: 18, bold: true, color: C.accent6 });
  const flowR = [
    ["AI", "기록 · 매뉴얼로 추리하다가 막히면", C.accent2],
    ["AI", "\"이 용접의 앞면과 뒷면을 찍어 주세요.\n탄 고리가 보이면 날림입니다\"", C.accent2],
    ["사람", "휴대폰으로 찍어 올린다", C.accent6],
    ["AI", "정상 샘플과 비교해 읽고 결론", C.accent2],
  ];
  flowR.forEach(([who, what, col], i) => {
    const y = 2.75 + i * 0.95;
    badge(s, 6.45, y, 0.7, who, col, who === "AI" ? 16 : 13);
    txt(s, what, { x: 7.35, y: y - 0.02, w: 5.1, h: 0.75, fontSize: 16, color: C.text1, valign: "middle" });
  });
  s.addNotes("참신성에 해당하는 슬라이드입니다. 예시로 주신 서비스들은 사람이 올리면 AI가 답합니다. 저희는 방향을 뒤집었습니다. AI가 기록만으로 모르겠으면, 무엇을 찍어야 가설이 갈리는지 스스로 판단해서 사람에게 요청합니다. 그리고 사진을 보기 전에 '이게 보이면 이 결론'이라고 먼저 선언합니다.");
}

// ══ 4. 동작 — 다섯 단계 ═══════════════════════════════════════════════
pres.addSection({ title: "서비스" });
{
  const s = content("서비스", "진단은 다섯 단계로 움직인다",
    "가설을 세우고 증거를 모으다가 — 갈리지 않으면 촬영을 요청하고 기다린다");
  const steps = [
    ["1", "가설 세우기", "알람과 공정 기록으로\n원인 후보와 점수", C.accent2, "Agent"],
    ["2", "증거 모으기", "시계열 · 매뉴얼 · 도면 ·\n과거 사례 도구를 고른다", C.accent2, "Tool Calling · RAG"],
    ["3", "촬영 요청", "무엇을 어떻게 찍을지 +\n보기 전에 해석 선언", C.accent6, "사람을 기다림"],
    ["4", "사진 판독", "같은 설정의 정상 샘플과\n나란히 놓고 비교", C.accent6, "VLM"],
    ["5", "결론", "근거 증거 인용 필수\n선언과 어긋나면 되묻기", C.accent1, "구조화 출력 · 검증"],
  ];
  const bw = 2.25, gap = 0.2, y = 2.0;
  steps.forEach(([n, t, d, col, tag], i) => {
    const x = M + i * (bw + gap);
    const hot = i === 2 || i === 3;
    card(s, x, y, bw, 3.1, { fill: hot ? "EFEBFA" : C.background2, line: hot ? C.accent6 : null, lineW: 2 });
    badge(s, x + 0.25, y + 0.25, 0.6, n, col, 18);
    txt(s, t, { x: x + 0.25, y: y + 1.0, w: bw - 0.4, h: 0.45, fontSize: 19, bold: true, color: C.text1 });
    txt(s, d, { x: x + 0.25, y: y + 1.5, w: bw - 0.4, h: 1.0, fontSize: 14, color: C.text1 });
    txt(s, tag, { x: x + 0.25, y: y + 2.6, w: bw - 0.4, h: 0.35, fontSize: 12, bold: true, color: col });
  });
  card(s, M, 5.4, 12.1, 1.1, { fill: "F7EEE7" });
  txt(s, [
    { text: "핵심 설계  ", options: { bold: true, color: C.accent1 } },
    { text: "촬영 요청은 도구 호출이 아니라 비동기 중단점이다. 사람이 현장에 가는 데 수 분이 걸리므로 진단 상태를 저장해 두고, 사진이 오면 같은 대화를 이어서 재개한다. 15분 안에 응답이 없으면 가진 증거만으로 결론을 낸다.",
      options: { color: C.text1 } }],
    { x: M + 0.35, y: 5.55, w: 11.4, h: 0.85, fontSize: 15 });
  s.addNotes("다섯 단계입니다. 핵심은 3번과 4번입니다. 센서로 두 가설이 갈리지 않으면 Agent가 '이 사진이 있으면 갈린다'를 판단해 요청합니다. 사진을 보기 전에 해석을 먼저 선언하게 해서 사후 끼워 맞추기를 막았고, 결론이 그 선언과 어긋나면 시스템이 한 번 되묻습니다. 사진은 같은 설정으로 만든 합격품 사진과 나란히 놓고 읽습니다.");
}

// ══ 5. 시연 — 실제 실행 기록 E-323 ═══════════════════════════════════
{
  const req = at("photo_request"), reads = DEMO.events.filter(e => e.type === "photo_read"), fin = at("final");
  const inc = at("incident").summary, lg = inc.logged_during_weld, pop = inc.same_setpoint_population;
  const s = content("서비스", "실제 실행: 기록으로는 애매, 사진은 날림",
    `실제 용접 E-323 · 실제 사진 · 실제 실행 기록 ${Math.round(DEMO.meta.elapsed_s)}초 (시연 영상은 이 기록을 재생한 것)`);
  const col = [
    { x: M, w: 2.75, t: "0초 · 사건", c: C.accent5 },
    { x: M + 2.95, w: 2.75, t: `${secs(req)}초 · 촬영 요청`, c: C.accent6 },
    { x: M + 5.9, w: 3.9, t: `${secs(reads[0])}~${secs(reads[1])}초 · 판독`, c: C.accent6 },
    { x: M + 10.0, w: 2.1, t: `${secs(fin)}초 · 결론`, c: C.accent1 },
  ];
  col.forEach(k => {
    card(s, k.x, 1.9, k.w, 4.9, { fill: C.background2 });
    txt(s, k.t, { x: k.x + 0.2, y: 2.02, w: k.w - 0.3, h: 0.35, fontSize: 14, bold: true, color: k.c });
  });
  // 같은 설정 용접들의 10~90% 범위와 비교한 위치 — 기록에서 계산한다 (손으로 '정상'이라 쓰지 않는다)
  const where = (v, d) => v > d.p90 ? `같은 설정 ${pop.n_welds}회 중 상위 10% 경계\n(경계 ${Math.round(d.p90).toLocaleString()})`
    : v < d.p10 ? `같은 설정 ${pop.n_welds}회 중 하위 10% 경계\n(경계 ${Math.round(d.p10).toLocaleString()})`
    : `같은 설정 ${pop.n_welds}회의 10~90% 범위 안`;
  txt(s, [
    { text: "평균 전류\n", options: { color: C.accent5, fontSize: 13 } },
    { text: `${Math.round(lg.mean_current_A).toLocaleString()} A\n`, options: { bold: true, fontSize: 22, color: C.text1 } },
    { text: `${where(lg.mean_current_A, pop.mean_current_A)}\n\n`, options: { fontSize: 13, color: C.text1 } },
    { text: "가압력\n", options: { color: C.accent5, fontSize: 13 } },
    { text: `${lg.peak_force_N} N\n`, options: { bold: true, fontSize: 22, color: C.text1 } },
    { text: where(lg.peak_force_N, pop.peak_force_N), options: { fontSize: 13, color: C.text1 } },
  ], { x: M + 0.2, y: 2.5, w: 2.4, h: 3.6 });
  txt(s, "기록만으로는 판단이 어렵다", { x: M + 0.2, y: 6.2, w: 2.4, h: 0.4, fontSize: 14, bold: true, color: C.accent3 });
  const x2 = M + 3.15;
  txt(s, [
    { text: "\"용접부 앞면과 뒷면을\n수직으로 가까이\n찍어 주세요\"\n\n", options: { fontSize: 14, color: C.text1, bold: true } },
    { text: "보기 전에 선언\n", options: { fontSize: 13, color: C.accent6, bold: true } },
    { text: "튄 금속 · 패임 · 탄 고리가\n보이면 → 날림 지지\n\n", options: { fontSize: 13, color: C.text1 } },
    { text: "깨끗한 둥근 자국이면\n→ 정상 지지", options: { fontSize: 13, color: C.text1 } },
  ], { x: x2, y: 2.5, w: 2.4, h: 3.9 });
  const x3 = M + 6.1;
  photo(s, "RGB_323F.jpg", x3, 2.5, 1.65, "받은 사진 · 앞면", C.accent6);
  photo(s, "ref/RGB_286F.jpg", x3 + 1.8, 2.5, 1.65, "정상 샘플 · 앞면");
  txt(s, [
    { text: "앞면  ", options: { bold: true, color: C.accent3 } },
    { text: "가운데 들쭉날쭉한 금속 돌기 — 정상 샘플에는 없음\n", options: { color: C.text1 } },
    { text: "뒷면  ", options: { bold: true, color: C.accent2 } },
    { text: "정상 범위의 차이", options: { color: C.text1 } },
  ], { x: x3, y: 4.6, w: 3.5, h: 1.2, fontSize: 14 });
  txt(s, "판독 모델이 정상 샘플과 나란히 비교", { x: x3, y: 6.2, w: 3.5, h: 0.4, fontSize: 13, color: C.accent5 });
  const x4 = M + 10.2;
  txt(s, [
    { text: "날림\n", options: { bold: true, fontSize: 30, color: C.accent3 } },
    { text: `확신 ${fin.confidence.toFixed(2)}\n\n`, options: { fontSize: 13, color: C.accent5 } },
    { text: "앞·뒷면 신호가 엇갈려 한 번 되물음 → \"앞면 증거가 더 구체적\"", options: { fontSize: 13, color: C.text1 } },
  ], { x: x4, y: 2.5, w: 1.75, h: 3.6 });
  txt(s, "정답: 날림 ✓", { x: x4, y: 6.2, w: 1.75, h: 0.4, fontSize: 14, bold: true, color: C.accent2 });
  [M + 2.75, M + 5.7, M + 9.8].forEach(x => arrow(s, x - 0.02, 4.1, 0.24, 0.3, C.accent5));
  s.addNotes(`실제 실행 기록입니다. 이 용접은 가압력은 같은 설정의 용접들과 비슷하고, 평균 전류만 상위 10% 경계에 걸쳐 있어 기록만으로는 판단이 어렵습니다. AI가 ${secs(req)}초 만에 앞면과 뒷면을 찍어 달라고 요청하면서, 보기 전에 '탄 고리나 튄 금속이 보이면 날림'이라고 선언합니다. 앞면 사진에서 판독 모델이 정상 샘플에 없는 금속 돌기를 찾았고, 뒷면은 정상이었습니다. 두 신호가 엇갈리자 시스템이 한 번 되물었고, AI는 '앞면 증거가 더 구체적'이라며 날림으로 결론 냈습니다. 정답입니다. 전체 ${Math.round(DEMO.meta.elapsed_s)}초 걸렸습니다.`);
}

// ══ 6. 사용한 LLM 기술 ════════════════════════════════════════════════
{
  const s = content("서비스", "LLM · VLM 기술 아홉 가지를 한 흐름에 엮었다",
    "각 기술이 진단의 한 단계를 맡는다 — 보라색은 이 서비스만의 부분");
  const items = [
    ["Agent 루프", "가설과 점수를 스텝마다 갱신하며 다음 행동을 스스로 고른다"],
    ["Tool Calling", "시계열 · 매뉴얼 · 도면 · 과거 사례 · SQL 도구를 골라 호출"],
    ["Multimodal RAG", `매뉴얼 ${F.manual_docs}종 ${F.manual_pages}쪽 + 도면 ${F.diagrams_described}장 VLM 서술 색인, 하이브리드 검색 + 재순위`],
    ["VLM 판독", "받은 사진을 같은 설정의 정상 샘플과 나란히 놓고 비교"],
    ["Human-in-the-loop", "촬영 요청 = 비동기 중단점. 상태를 저장했다가 사진이 오면 재개"],
    ["구조화 출력 · 인용 검증", "모든 결론에 근거 증거 id 필수, 없는 증거를 대면 거부"],
    ["사전 선언 · 자기 점검", "보기 전에 해석을 선언, 결론이 어긋나면 한 번 되묻는다"],
    ["세션 유지", `같은 대화를 이어 써서 스텝당 입력 토큰 ${F.resume_tokens[0].toLocaleString()} → ${F.resume_tokens[1]}`],
    ["LLM-as-Judge 평가", "진단 모델과 다른 모델(Opus)로 정답 일치를 채점"],
  ];
  const cw = 3.9, ch = 1.45, gx = 0.2, gy = 0.2;
  items.forEach(([t, d], i) => {
    const x = M + (i % 3) * (cw + gx), y = 1.95 + Math.floor(i / 3) * (ch + gy);
    const own = [3, 4, 6].includes(i);
    card(s, x, y, cw, ch, { fill: own ? "EFEBFA" : C.background2 });
    badge(s, x + 0.2, y + 0.22, 0.5, String(i + 1), own ? C.accent6 : C.accent2, 15);
    txt(s, t, { x: x + 0.85, y: y + 0.24, w: cw - 1.0, h: 0.45, fontSize: 17, bold: true, color: C.text1 });
    txt(s, d, { x: x + 0.85, y: y + 0.7, w: cw - 1.0, h: 0.7, fontSize: 13, color: C.text1 });
  });
  s.addNotes("LLM의 다양한 기술에 해당합니다. 아홉 가지를 썼고, 각각이 진단의 한 단계를 맡습니다. 보라색 세 가지, 즉 사진 판독, 사람을 기다리는 중단점, 사전 선언과 되묻기가 이 서비스만의 부분입니다. 모델은 진단에 Claude Sonnet, 사진 판독에 Haiku, 채점에 Opus를 썼습니다.");
}

// ══ 7. 완성도 — 실제로 쓰는 화면 ═════════════════════════════════════
{
  const s = content("서비스", "관제 화면과 휴대폰이 한 진단을 나눠 맡는다",
    "웹 서비스 · 모바일 업로드 · 녹화 재생 · 평가 하네스까지 GitHub에 공개");
  const boxes = [
    [M, 2.05, "관제 화면", "가설 보드 · 추론 트레이스\n실시간 스트림 (SSE)\n판독 · 정상 샘플 나란히", C.accent2],
    [M + 4.25, 2.05, "Agent 서버", "진단 루프 · 도구 실행\n상태 저장 · 재개\n선언 대조 · 인용 검증", C.accent1],
    [M + 8.5, 2.05, "작업자 휴대폰", "QR로 접속 (15분 토큰)\n촬영 요청 내용 확인\n사진 업로드", C.accent6],
  ];
  boxes.forEach(([x, y, t, d, col]) => {
    card(s, x, y, 3.6, 2.55, { fill: C.background2, shadow: true });
    badge(s, x + 0.3, y + 0.32, 0.36, "", col);
    txt(s, t, { x: x + 0.85, y: y + 0.27, w: 2.6, h: 0.45, fontSize: 19, bold: true, color: C.text1 });
    txt(s, d, { x: x + 0.3, y: y + 0.95, w: 3.1, h: 1.4, fontSize: 15, color: C.text1 });
  });
  arrow(s, M + 3.7, 3.1, 0.45, 0.4, C.accent5);
  arrow(s, M + 7.95, 3.1, 0.45, 0.4, C.accent6);
  const stats = [
    [String(F.tests), "자동 테스트\n정답 누출 · 재생 · 경로 보안 포함"],
    ["역할 분리", "Claude Sonnet 진단 · Haiku 판독\n· Opus 채점"],
    [`${Math.round(DEMO.meta.elapsed_s)}초`, "실제 진단 1건\n(촬영 대기 포함, 시연 기록)"],
    ["HTML 1개", "서버 없이 여는 시연 재생 파일\n(오프라인)"],
  ];
  stats.forEach(([big, small], i) => {
    const x = M + i * 3.08;
    txt(s, big, { x, y: 4.95, w: 2.9, h: 0.65, fontSize: 28, bold: true, color: C.accent1 });
    txt(s, small, { x, y: 5.65, w: 2.9, h: 0.8, fontSize: 13, color: C.text1 });
  });
  txt(s, "github.com/dlwogud/rootcause-stream", { x: M, y: 6.6, w: 6, h: 0.3, fontSize: 12, color: C.accent5 });
  s.addNotes(`완성도입니다. 관제 화면에서 사건을 고르면 Agent가 진단을 시작하고, 촬영 요청이 오면 QR 코드가 뜹니다. 작업자가 휴대폰으로 찍어 올리면 서버가 판독하고 같은 대화를 이어서 재개합니다. 테스트 ${F.tests}개와 평가 하네스, 서버 없이 여는 재생 파일까지 GitHub에 공개했습니다.`);
}

// ══ 8. 검증 설계 ══════════════════════════════════════════════════════
pres.addSection({ title: "검증" });
{
  const s = content("검증", "어느 쪽이 날림일까 — 숫자로는 거의 안 갈린다",
    "실제 용접 · 실제 사진 · 파괴시험 판정이 공개된 데이터로 검증했다");
  photo(s, "RGB_323F.jpg", M, 2.0, 2.4, "A", C.text1);
  photo(s, "RGB_310F.jpg", M + 2.6, 2.0, 2.4, "B", C.text1);    // E-323 과 짝지어 뽑은 같은 설정의 정상 용접
  txt(s, [{ text: "정답  ", options: { bold: true, color: C.accent5 } },
          { text: "A 날림 · B 정상 — 같은 설정(공압 60 psi · 통전 800 ms)으로 용접했다", options: { color: C.text1 } }],
      { x: M, y: 4.85, w: 5.0, h: 0.6, fontSize: 14 });
  txt(s, `공정 신호로 학습한 분류기도 날림을 ${r0(N.tier_e_sensor_only.per_class.Explode.recall)}만 잡는다`,
      { x: M, y: 5.6, w: 5.0, h: 0.6, fontSize: 14, bold: true, color: C.accent3 });
  const x = 6.05;
  card(s, x, 2.0, 6.65, 1.7, { fill: C.background2 });
  txt(s, [
    { text: "데이터  ", options: { bold: true, color: C.accent1 } },
    { text: "RSW Insights (Mendeley, 2025, CC BY 4.0)\n", options: { color: C.text1 } },
    { text: "용접 495회마다 공정 신호 + 앞·뒷면 사진 + 파괴시험 판정", options: { color: C.text1 } },
  ], { x: x + 0.3, y: 2.2, w: 6.1, h: 1.3, fontSize: 15 });
  card(s, x, 3.9, 6.65, 1.1, { fill: C.background2 });
  txt(s, [
    { text: "시험 58건  ", options: { bold: true, color: C.accent1 } },
    { text: "날림 29 + 같은 설정의 정상 29 (짝지어 뽑음)", options: { color: C.text1 } },
  ], { x: x + 0.3, y: 4.2, w: 6.1, h: 0.6, fontSize: 15 });
  card(s, x, 5.2, 6.65, 1.5, { fill: "EFEBFA" });
  txt(s, [
    { text: "비교 대상  ", options: { bold: true, color: C.accent6 } },
    { text: "규칙 한 줄 · 정답으로 학습한 분류기 · 사진 없음 ·\n", options: { color: C.text1 } },
    { text: "바꿔치기", options: { bold: true, color: C.accent6 } },
    { text: " — 같은 요청에 반대 판정 용접의 사진을 준다", options: { color: C.text1 } },
  ], { x: x + 0.3, y: 5.4, w: 6.1, h: 1.2, fontSize: 15 });
  s.addNotes(`검증은 공개 데이터로 했습니다. 용접마다 사진과, 실제로 뜯어서 강도를 잰 판정이 함께 공개된 데이터입니다. 왼쪽 두 사진은 같은 설정으로 용접했고 하나가 날림입니다. 숫자로 학습한 분류기도 날림을 ${r0(N.tier_e_sensor_only.per_class.Explode.recall)}밖에 못 잡습니다. 비교 대상 중 가장 중요한 것은 바꿔치기입니다. AI가 사진을 진짜 보고 판단한다면, 다른 용접의 사진을 줬을 때 틀려야 합니다.`);
}

// ══ 9. 결과 ═══════════════════════════════════════════════════════════
{
  const s = content("검증", `사진을 요청하는 Agent가 가장 정확했다 — ${r0(E.photo.accuracy)}`,
    `실제 용접 ${E.photo.n}건 · 날림과 정상 반반 · 같은 사건을 조건만 바꿔 비교`);
  const rows = [
    ["바꿔치기 사진", E.swap.accuracy],
    ["사진 없음", MC["E-none"].sonnet.pct],
    ["규칙 한 줄", RB.rule_peak_current_p90.accuracy],
    ["앞면 + 정상 샘플", E.front_only.accuracy],
    ["학습 분류기*", RB.supervised_rf_reference.accuracy],
    ["앞·뒷면 + 정상 샘플", E.photo.accuracy],
  ];
  const last = rows.length - 1;
  s.addChart(pres.charts.BAR, [
    { name: "비교", labels: rows.map(r => r[0]), values: rows.map((r, i) => i === last ? 0 : Math.round(r[1])) },
    { name: "최종", labels: rows.map(r => r[0]), values: rows.map((r, i) => i === last ? Math.round(r[1]) : 0) },
  ], {
    x: M, y: 1.85, w: 7.4, h: 4.6, barDir: "bar", barGrouping: "stacked", barGapWidthPct: 45,
    chartColors: [HEX.accent5, HEX.accent1], showLegend: false,
    showValue: true, dataLabelPosition: "inEnd", dataLabelFormatCode: "0\"%\";;;", dataLabelColor: "FFFFFF",
    dataLabelFontSize: 13, dataLabelFontFace: "+mn-lt",
    catAxisLabelColor: HEX.dk1, catAxisLabelFontSize: 14, catAxisLabelFontFace: "+mn-lt",
    valAxisHidden: true, valAxisMaxVal: 100, valAxisMinVal: 0,
    valGridLine: { style: "none" }, catGridLine: { style: "none" },
    showTitle: true, title: "정확도 (50% = 동전 던지기)", titleFontSize: 14, titleColor: HEX.accent5, titleFontFace: "+mn-lt",
  });
  txt(s, "* 판정 라벨 수백 개로 학습. Agent와 규칙은 라벨을 쓰지 않는다", { x: M, y: 6.5, w: 7.4, h: 0.3, fontSize: 11, color: C.accent5 });
  const x = 8.4;
  card(s, x, 1.95, 4.3, 2.15, { fill: C.background2 });
  txt(s, `${r0(MC["E-none"].sonnet.explode_recall)} → ${r0(E.photo.explode_recall)}`, { x: x + 0.3, y: 2.1, w: 3.8, h: 0.8, fontSize: 36, bold: true, color: C.accent1 });
  txt(s, `날림을 날림으로 맞힌 비율\n사진 없음 → 앞·뒷면 사진 (${E.photo.explode_hit}/${E.photo.explode_n}건)`, { x: x + 0.3, y: 2.95, w: 3.8, h: 0.9, fontSize: 14, color: C.text1 });
  card(s, x, 4.3, 4.3, 2.2, { fill: "EFEBFA" });
  txt(s, `${E.photo_vs_swap.only_photo_ref} : ${E.photo_vs_swap.only_swap_ref}`, { x: x + 0.3, y: 4.45, w: 3.8, h: 0.8, fontSize: 36, bold: true, color: C.accent6 });
  txt(s, `진짜 사진에서만 맞힌 사건 : 바꿔치기에서만 맞힌 사건 (같은 사건 짝 비교, ${pfmt(E.photo_vs_swap.p_two_sided)})`, { x: x + 0.3, y: 5.3, w: 3.8, h: 1.0, fontSize: 14, color: C.text1 });
  s.addNotes(`결과입니다. 앞면과 뒷면 사진을 정상 샘플과 비교한 Agent가 ${r0(E.photo.accuracy)}로 가장 높았습니다. 규칙 한 줄은 ${r0(RB.rule_peak_current_p90.accuracy)}, 정답 라벨로 학습한 분류기는 ${r0(RB.supervised_rf_reference.accuracy)}입니다. 사진이 없으면 날림을 하나도 못 잡고, 사진이 있으면 ${r0(E.photo.explode_recall)}를 잡습니다. 가장 중요한 건 오른쪽 아래입니다. 같은 사건에 진짜 사진과 바꿔치기 사진을 주면, 진짜에서만 맞힌 게 ${E.photo_vs_swap.only_photo_ref}건, 바꿔치기에서만 맞힌 게 ${E.photo_vs_swap.only_swap_ref}건입니다. AI가 사진 내용을 근거로 쓴다는 강한 증거입니다.`);
}

// ══ 10. 병목을 하나씩 ═════════════════════════════════════════════════
{
  const s = content("검증", "막힌 곳을 하나씩 찾아 풀었다",
    "단계마다 무엇이 병목인지 측정하고, 현장에서 자연스러운 방법으로만 고쳤다");
  const steps = [
    ["사진이 없다", "날림 0%", "촬영 요청", `날림 ${r0(MC["E-photo"].sonnet.explode_recall)}`, "Agent가 스스로 촬영을 요청한다"],
    ["판독 모델이 미세한 흔적을 못 본다", "날림·정상 구별 +3%p", "정상 샘플과 나란히", "구별 +35%p", "같은 설정의 합격품 사진 (골든 샘플)"],
    ["판독을 결론에 반영 안 한다", "\"숫자가 정상이니 문제없음\"", "사전 선언 대조 · 되묻기", "사진을 따르게 됨", "보기 전에 한 선언을 결론까지 지키게"],
    ["앞면에 흔적이 없는 날림", `날림 ${r0(E.front_only.explode_recall)}`, "뒷면 촬영 허용", `날림 ${r0(E.photo.explode_recall)}`, `Agent가 ${E.asked_back[0]}/${E.asked_back[1]}건에서 스스로 요청`],
  ];
  steps.forEach(([prob, before, fix, after, how], i) => {
    const y = 1.95 + i * 1.18;
    card(s, M, y, 4.6, 1.0, { fill: "FBECEA" });
    txt(s, prob, { x: M + 0.25, y: y + 0.12, w: 4.1, h: 0.4, fontSize: 16, bold: true, color: C.accent3 });
    txt(s, before, { x: M + 0.25, y: y + 0.55, w: 4.1, h: 0.35, fontSize: 13, color: C.text1 });
    arrow(s, M + 4.7, y + 0.3, 0.4, 0.4, C.accent5);
    card(s, M + 5.2, y, 3.6, 1.0, { fill: "EFEBFA" });
    txt(s, fix, { x: M + 5.45, y: y + 0.12, w: 3.2, h: 0.4, fontSize: 16, bold: true, color: C.accent6 });
    txt(s, how, { x: M + 5.45, y: y + 0.55, w: 3.2, h: 0.35, fontSize: 12, color: C.text1 });
    arrow(s, M + 8.9, y + 0.3, 0.4, 0.4, C.accent5);
    card(s, M + 9.4, y, 2.7, 1.0, { fill: "E6F2EF" });
    txt(s, after, { x: M + 9.6, y: y + 0.25, w: 2.4, h: 0.5, fontSize: 18, bold: true, color: C.accent2, valign: "middle" });
  });
  s.addNotes(`한 번에 된 것이 아닙니다. 처음엔 사진이 없으면 날림을 전혀 못 잡았고, 촬영 요청을 넣자 ${r0(MC["E-photo"].sonnet.explode_recall)}를 잡았습니다. 다음 병목은 판독 모델이 미세한 흔적을 못 보는 것이었는데, 공장의 골든 샘플처럼 합격품 사진을 옆에 놓자 구별력이 3%p에서 35%p로 올랐습니다. 그다음엔 AI가 판독 결과를 무시하고 숫자를 믿었는데, 사전 선언 대조로 사진을 따르게 했습니다. 마지막으로 앞면에 흔적이 없는 날림이 남았고, 뒷면도 찍을 수 있다고만 알리자 AI가 거의 모든 사건에서 스스로 뒷면을 요청했고 날림을 두 배로 잡았습니다.`);
}

// ══ 11. 한계 ══════════════════════════════════════════════════════════
{
  const s = content("검증", "아직 날림의 절반 이상을 놓친다",
    "어디서 놓치는지 알고, 무엇을 주장하지 않는지 밝힌다");
  const fz = E.explode_funnel;
  const bars = [
    ["날림 사건", fz.total, C.accent5],
    ["판독 모델이 사진에서 이상을 찾음", fz.reader_flagged, C.accent6],
    ["Agent가 날림으로 결론", fz.flagged_and_concluded, C.accent2],
  ];
  bars.forEach(([lab, v, col], i) => {
    const y = 2.0 + i * 0.95, w = 5.0 * v / fz.total;
    s.addShape(pres.shapes.RECTANGLE, { x: M, y: y + 0.38, w, h: 0.42, fill: { color: col }, line: { type: "none" } });
    txt(s, lab, { x: M, y, w: 5.6, h: 0.35, fontSize: 14, color: C.text1 });
    txt(s, String(v), { x: M + w + 0.12, y: y + 0.38, w: 0.5, h: 0.42, fontSize: 16, bold: true, color: col, valign: "middle" });
  });
  txt(s, [
    { text: `${fz.reader_saw_nothing}건은 앞·뒷면 어디에서도 흔적을 못 찾았다. `, options: { bold: true, color: C.accent3 } },
    { text: "판정은 사진이 아니라 파괴시험 기준이라, 겉면에 흔적이 없는 날림일 수 있다.", options: { color: C.text1 } },
  ], { x: M, y: 4.95, w: 5.6, h: 0.95, fontSize: 14 });
  const x = 6.7;
  const lims = [
    ["같은 58건을 여러 설계에 썼다", "날림은 데이터 전체에 31건뿐 — 설계 반복은 여기서 멈췄다"],
    ["실행마다 결론이 달라질 수 있다", "같은 사건도 사진 요청 여부가 갈린다 — 시연은 실제 기록 재생"],
    ["측정 중 버그를 찾아 고치고 다시 쟀다", "증거가 여러 개면 마지막 것만 보이던 문제 · 정답 누출 2건"],
    ["사진은 데이터셋의 실제 사진으로 재현", "현장 촬영 자체는 다음 단계에서 검증"],
  ];
  lims.forEach(([t, d], i) => {
    const y = 1.95 + i * 1.02;
    card(s, x, y, 6.0, 0.9, { fill: C.background2 });
    txt(s, t, { x: x + 0.25, y: y + 0.08, w: 5.6, h: 0.4, fontSize: 15, bold: true, color: C.text1 });
    txt(s, d, { x: x + 0.25, y: y + 0.5, w: 5.6, h: 0.35, fontSize: 13, color: C.accent5 });
  });
  card(s, M, 6.15, 12.1, 0.62, { fill: "F7EEE7" });
  txt(s, [{ text: "다음 단계  ", options: { bold: true, color: C.accent1 } },
          { text: "현장에서 쌓이는 검사 사진을 정상·결함 예시로 판독 모델에 함께 보여준다 (공개된 점용접 날림 사진 데이터는 없었다)", options: { color: C.text1 } }],
      { x: M + 0.3, y: 6.28, w: 11.6, h: 0.4, fontSize: 14 });
  s.addNotes(`한계도 말씀드립니다. 날림 ${fz.total}건 중 판독 모델이 이상을 찾은 건 ${fz.reader_flagged}건, AI가 날림으로 결론 낸 건 ${fz.flagged_and_concluded}건입니다. ${fz.reader_saw_nothing}건은 사진 어디에서도 흔적을 못 찾았는데, 이 데이터의 판정은 뜯어서 잰 결과라 겉면에 흔적이 없을 수 있습니다. 같은 시험 문제를 여러 번 썼고, 측정 중 버그를 찾아 고친 뒤 다시 쟀다는 것도 그대로 밝힙니다.`);
}

// ══ 12. 마무리 ════════════════════════════════════════════════════════
pres.addSection({ title: "마무리" });
{
  const s = pres.addSlide({ masterName: "CLOSING_DARK", sectionTitle: "마무리" });
  s.addText("AI가 모르는 것을 알고,\n사람에게 정확히 묻는다", { placeholder: "title" });
  const pts = [
    ["참신성", "답하는 AI가 아니라 묻는 AI — 무엇을 찍을지 스스로 판단"],
    ["기술", "Agent · 도구 · 멀티모달 RAG · VLM · 사람 개입 · 자기 점검"],
    ["검증", `실제 용접 ${E.photo.n}건 정확도 ${r0(E.photo.accuracy)} · 진짜 대 바꿔치기 ${E.photo_vs_swap.only_photo_ref} : ${E.photo_vs_swap.only_swap_ref}`],
  ];
  pts.forEach(([k, v], i) => {
    const y = 4.0 + i * 0.68;
    txt(s, k, { x: M, y, w: 1.6, h: 0.5, fontSize: 18, bold: true, color: C.accent1 });
    txt(s, v, { x: M + 1.7, y, w: 10.3, h: 0.5, fontSize: 18, color: "E4E6E9" });
  });
  txt(s, "github.com/dlwogud/rootcause-stream", { x: M, y: 6.7, w: 6, h: 0.35, fontSize: 13, color: "8A9099" });
  s.addNotes("정리하겠습니다. 이 서비스는 답하는 AI가 아니라 묻는 AI입니다. 기록만으로 모르면 무엇을 찍어야 하는지 스스로 판단해서 요청하고, 사진을 근거로 결론을 냅니다. 감사합니다.");
}

// ══ 부록 ══════════════════════════════════════════════════════════════
pres.addSection({ title: "부록" });
{
  const au = F.audit;
  const s = content("부록", "부록 A · 공장 데이터: 이상의 정체는 기록 재활용이었다",
    "KAMP 저항 점용접 데이터 — 도구를 골라 쓰는 진단의 예시, 그리고 규칙과의 비교");
  card(s, M, 1.95, 5.6, 2.3, { fill: C.background2 });
  txt(s, `${au.dup_index_pct}% → ${au.reused_pct}%`, { x: M + 0.3, y: 2.1, w: 5.0, h: 0.8, fontSize: 34, bold: true, color: C.accent1 });
  txt(s, `기존에 복제로 알려진 비율 → 실제로 다른 작업일과 수백 행씩 연속 일치하는 비율 (순서를 섞은 대조에서는 최대 ${au.chance_longest}행)`,
      { x: M + 0.3, y: 2.95, w: 5.0, h: 1.2, fontSize: 14, color: C.text1 });
  const head = t => ({ text: t, options: { bold: true, color: C.background1, fill: { color: C.text2 } } });
  const kb = N.rule_baseline.kamp;
  s.addTable([
    [head("근본원인 정확도"), head("Agent"), head("규칙 한 줄")],
    ["A 조용한 수준 이동", `${r0(MC.A.sonnet.pct)} (sonnet)`, r0(kb.A.pct)],
    ["C 알람 폭주", `${r0(N.conditions.full.C.M1_match.mean)} (haiku)`, r0(kb.C.pct)],
    ["B 주입 고장 (주 변수)", `${r0(N.conditions.full.B.M2_primary_variable.mean)} (haiku)`, r0(kb.B.pct)],
  ], { x: 6.5, y: 1.95, w: 6.2, colW: [2.6, 1.9, 1.7], fontSize: 15, rowH: 0.55,
       border: { type: "solid", pt: 0.75, color: "D7DADF" }, valign: "middle", margin: [0, 0.15, 0, 0.15], color: HEX.dk1 });
  txt(s, [
    { text: "정직한 위치  ", options: { bold: true, color: C.accent1 } },
    { text: "결정적 신호(다른 작업일과의 연속 일치 비율)는 사람이 설계했고, 그 신호가 있으면 규칙 한 줄도 Agent만큼 맞힌다. 신호 없이 원시 기록과 SQL만 주자 Agent는 재활용을 스스로 찾지 못했다 (Sonnet 0%). 그래서 LLM · VLM의 고유한 기여는 사진 실험으로 주장한다.", options: { color: C.text1 } },
  ], { x: M, y: 4.6, w: 12.1, h: 1.6, fontSize: 15 });
  s.addNotes("공장 데이터에 대한 질문이 나오면 쓰는 부록입니다.");
}
{
  const s = content("부록", "부록 B · 측정 이력과 정정",
    "숫자는 모두 eval/results 의 원 자료에서 나온다 — 정정한 것도 그대로 남겼다");
  const head = t => ({ text: t, options: { bold: true, color: C.background1, fill: { color: C.text2 } } });
  s.addTable([
    [head("실행"), head("조건 (진단 Sonnet · 판독 Haiku · 채점 Opus)"), head("정확도"), head("날림")],
    ["—", "사진 없음", r0(MC["E-none"].sonnet.pct), r0(MC["E-none"].sonnet.explode_recall)],
    ["—", "앞면 사진", r0(MC["E-photo"].sonnet.pct), r0(MC["E-photo"].sonnet.explode_recall)],
    [`#${E.front_only.run}`, "앞면 + 정상 샘플 + 사전 선언 대조", r0(E.front_only.accuracy), r0(E.front_only.explode_recall)],
    [`#${E.run}`, "앞·뒷면 + 정상 샘플 + 사전 선언 대조 (최종)", r0(E.photo.accuracy), r0(E.photo.explode_recall)],
    [`#${E.run}`, "↳ 바꿔치기 사진", r0(E.swap.accuracy), r0(E.swap.explode_recall)],
  ], { x: M, y: 1.95, w: 12.1, colW: [1.2, 7.3, 1.8, 1.8], fontSize: 15, rowH: 0.52,
       border: { type: "solid", pt: 0.75, color: "D7DADF" }, valign: "middle", margin: [0, 0.15, 0, 0.15], color: HEX.dk1 });
  const fixes = [
    ["증거 가림 버그", "한 단계에 증거가 여러 개면 마지막 것만 Agent에게 보였다 → 고치고 재측정"],
    ["정답 누출 2건", "사건 요약의 라벨 필드 · 증거 요약의 파일 이름 → 제거, 누출 검사 테스트 추가"],
    ["정답지 정정", "공장 데이터 '원인 불명' → '기록 재활용'으로 고치고 다시 쟀다"],
  ];
  fixes.forEach(([t, d], i) => {
    const y = 5.3 + i * 0.5;
    txt(s, t, { x: M, y, w: 2.4, h: 0.4, fontSize: 14, bold: true, color: C.accent3 });
    txt(s, d, { x: M + 2.5, y, w: 9.6, h: 0.4, fontSize: 14, color: C.text1 });
  });
  s.addNotes(`최종 대 앞면만: 최종에서만 맞힘 ${E.final_vs_front.only_final}건, 앞면만에서만 ${E.final_vs_front.only_front}건, ${pfmt(E.final_vs_front.p_two_sided)} (경계). 앞면만 실행은 버그 영향이 작았다(6/50).`);
}

(async () => {
  await pres.writeFile({ fileName: OUT });
  await applyTheme(OUT, THEME);
  console.log("→", OUT);
})();
