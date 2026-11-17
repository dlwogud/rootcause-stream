// RootCause Stream 발표자료 생성기.
//   수치는 numbers.json(← export_numbers.py ← 평가 DB)에서만 읽는다. 손으로 적지 않는다.
//   실행: python3 deck/export_numbers.py && NODE_PATH=deck/node_modules node deck/build.js
const path = require("path");
const fs = require("fs");
const pptxgen = require("pptxgenjs");
// 테마 색을 덱에 써넣는 도구(apply_theme.js)는 이 레포에 없다. 경로를 환경변수로 받고,
// 없으면 건너뛴다 — 그 경우 색은 Office 기본 팔레트로 보인다(배포본 pptx 는 적용된 상태다).
const APPLY_THEME = process.env.APPLY_THEME_JS;
const applyTheme = APPLY_THEME && fs.existsSync(APPLY_THEME)
  ? require(APPLY_THEME).applyTheme
  : async () => console.warn("APPLY_THEME_JS 없음 — 테마 색 적용을 건너뜀");

const N = JSON.parse(fs.readFileSync(path.join(__dirname, "numbers.json"), "utf8"));
const F = N.facts;
const OUT = path.join(__dirname, "RootCause_Stream_발표자료.pptx");

// ── 테마: 용접 전극의 구리색 + 차콜. Agent=청록, 실패=적색, 사람/사진=보라 ─────────
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
pres.title = "RootCause Stream — 알람 너머의 근본원인을 증거로 추적하는 Agent";
pres.author = "이재형";
const C = pres.SchemeColor;
const W = 13.333, M = 0.6;

const pct = (t, label = "full") => {
  const m = { A: "M1_match", B: "M2_primary_variable", C: "M1_match" }[t];   // A: 11/17 정답 정정 후 M1
  const c = N.conditions[label]?.[t]?.[m];
  return c ? c.mean : null;
};
const runs = (t, label = "full") => {
  const m = { A: "M1_match", B: "M2_primary_variable", C: "M1_match" }[t];   // A: 11/17 정답 정정 후 M1
  return N.conditions[label]?.[t]?.[m]?.n_runs ?? 0;
};
// 사건 수는 측정 결과가 아니라 사건 파일에서 센다 (측정 전에도 맞는 값이 나오게)
const ncase = (t) => N.case_counts?.[t] ?? 0;
const stat = (t, label = "full") => {
  const m = { A: "M1_match", B: "M2_primary_variable", C: "M1_match" }[t];   // A: 11/17 정답 정정 후 M1
  return N.conditions[label]?.[t]?.[m] ?? null;
};
// "3회 반복 · 매회 100%" / "3회 반복 · 회차별 50–88%"
const spread = (t, label = "full") => {
  const x = stat(t, label);
  if (!x) return "미측정";
  if (x.n_runs <= 1) return "1회 측정";
  return x.min === x.max ? `${x.n_runs}회 반복 · 매회 ${Math.round(x.min)}%`
                         : `${x.n_runs}회 반복 · 회차별 ${Math.round(x.min)}–${Math.round(x.max)}%`;
};
function dSGtag() {
  const d = delta("C", "full", "no_signal_guide");
  if (d === null) return "미측정";
  return Math.abs(d) < 15 ? "측정: 차이 없음" : `측정: C ${fmt(pct("C"))}→${fmt(pct("C", "no_signal_guide"))}`;
}
const delta = (t, a, b) => (pct(t, a) === null || pct(t, b) === null) ? null : pct(t, b) - pct(t, a);
const fmt = v => (v === null || v === undefined) ? "–" : `${Math.round(v)}%`;
const shadow = () => ({ type: "outer", blur: 8, offset: 2, angle: 90, color: "000000", opacity: 0.10 });

// ── 레이아웃 ──────────────────────────────────────────────────────────
pres.defineSlideMaster({
  title: "TITLE_DARK",
  background: { color: C.text2 },
  objects: [
    { placeholder: { options: { name: "kicker", type: "body", x: M, y: 0.8, w: 12, h: 0.5,
        fontSize: 16, color: C.accent1, bold: true, margin: 0 }, text: "" } },
    { placeholder: { options: { name: "title", type: "title", x: M, y: 1.5, w: 12, h: 2.2,
        fontSize: 44, color: C.background1, bold: true, valign: "top", margin: 0 }, text: "" } },
    { placeholder: { options: { name: "sub", type: "body", x: M, y: 3.75, w: 12, h: 0.6,
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
    { placeholder: { options: { name: "title", type: "title", x: M, y: 2.0, w: 12.1, h: 1.9,
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
  s.addText(label, { x, y, w: d, h: d, fontSize: size, bold: true, color: C.background1,
    align: "center", valign: "middle", margin: 0, isTextBox: true });
}
function txt(s, runs, o) { s.addText(runs, { isTextBox: true, margin: 0, valign: "top", ...o }); }
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
  s.addText("알람 너머의 근본원인을,\n증거로 추적하는 Agent", { placeholder: "title" });
  s.addText("RootCause Stream — 데이터 · 매뉴얼 · 현장 사진에 묻는 설비 진단", { placeholder: "sub" });
  const chips = [
    [`${F.weld_points.toLocaleString()}점`, "실제 용접 공정 기록"],
    [`${fmt(pct("A", "baseline"))} → ${fmt(pct("A"))}`, `조용한 이상의 진짜 원인 · ${runs("A")}회 반복 평균`],
    [`${F.audit.dup_index_pct}% → ${F.audit.reused_pct}%`, "Agent가 짚어 낸 정답지의 결함 — 재활용 기록"],
  ];
  chips.forEach(([big, small], i) => {
    const x = M + i * 4.1;
    card(s, x, 4.9, 3.8, 1.55, { fill: "2E343B" });
    txt(s, big, { x: x + 0.3, y: 5.05, w: 3.3, h: 0.7, fontSize: 30, bold: true, color: C.accent1 });
    txt(s, small, { x: x + 0.3, y: 5.75, w: 3.3, h: 0.55, fontSize: 13, color: "C9CDD2" });
  });
  txt(s, "이재형  ·  2026. 11", { x: M, y: 6.75, w: 6, h: 0.35, fontSize: 12, color: "8A9099" });
  s.addNotes("한 문장으로 시작합니다. 이 프로젝트는 알람이 울렸을 때 LLM이 바로 답을 내게 하지 않고, 가설을 세우고 데이터·매뉴얼·현장 사진으로 증거를 모아 근본원인을 좁히는 진단 Agent입니다. 가운데 숫자는 조용한 이상 사건의 진짜 원인을 맞힌 비율입니다. 오른쪽 숫자가 이 프로젝트에서 가장 중요한 장면입니다. 제가 쓰던 정답지가 데이터의 27%만 복제로 보고 있었는데, Agent가 실제로는 97%가 재활용 기록이라는 걸 먼저 짚었습니다.");
}

// ══ 2. 문제 ═══════════════════════════════════════════════════════════
{
  const s = content("도입", "경보는 \"이상\"까지만 말한다",
    "용접 불량의 원인 대부분은 센서 밖 — 매뉴얼의 도면과 현장의 눈에 있다");
  // 왼쪽: 센서가 재는 4가지
  card(s, M, 1.95, 4.4, 4.75);
  txt(s, "센서가 재는 것", { x: M + 0.35, y: 2.15, w: 3.8, h: 0.4, fontSize: 18, bold: true, color: C.text1 });
  ["가압력 (bar)", "전류 (kA)", "전압 (V)", "통전 시간 (ms)"].forEach((t, i) => {
    badge(s, M + 0.4, 2.8 + i * 0.9, 0.55, String(i + 1), C.accent2, 15);
    txt(s, t, { x: M + 1.15, y: 2.85 + i * 0.9, w: 3.0, h: 0.45, fontSize: 17, color: C.text1 });
  });
  txt(s, "이게 전부다", { x: M + 0.4, y: 6.25, w: 3.6, h: 0.35, fontSize: 13, color: C.accent5, italic: true });
  // 오른쪽: 원인 표
  const head = (t) => ({ text: t, options: { bold: true, color: C.background1, fill: { color: C.text2 } } });
  const row = (a, b) => [{ text: a, options: { color: C.text1 } },
                         { text: b, options: { color: C.accent3, bold: true } }];
  s.addTable([
    [head("실제 원인"), head("어떻게 알 수 있나")],
    row("전극 팁 마모·오염", "눈으로 봐야 앎"),
    row("가압 공압 저하", "게이지를 봐야 앎"),
    row("냉각수 유량 저하", "유량계를 봐야 앎"),
    row("전극 정렬 불량", "눈으로 봐야 앎"),
    row("데이터 수집 계통 이상", "오히려 정상처럼 보임"),
  ], { x: 5.4, y: 1.95, w: 7.3, colW: [3.65, 3.65], fontSize: 16, rowH: 0.62,
       border: { type: "solid", pt: 0.75, color: "D7DADF" }, valign: "middle", margin: [0, 0.15, 0, 0.15] });
  txt(s, [{ text: "매뉴얼 점검표도 사람의 확인을 요구한다 — ", options: { color: C.accent5 } },
          { text: "\"Check that the air pressure is 0.5 MPa {71 psi}.\"", options: { italic: true, color: C.text1 } },
          { text: "  (Spot Weld Inc. 매뉴얼 p.19)", options: { color: C.accent5 } }],
      { x: 5.4, y: 6.05, w: 7.3, h: 0.6, fontSize: 13 });
  s.addNotes("용접기 센서가 재는 건 네 가지뿐입니다. 그런데 실제 불량 원인 상위 항목은 전부 현장에 가서 눈으로 봐야 압니다. 기존 이상탐지는 '이상입니다'에서 멈춥니다. 이 간극이 출발점입니다.");
}

// ══ 3. 핵심 아이디어 ══════════════════════════════════════════════════
pres.addSection({ title: "설계" });
{
  const s = content("설계", "센서로 못 가르면, 사람에게 묻는다",
    "Agent는 가설을 세우고 증거를 모으다가 — 갈리지 않으면 촬영을 요청하고 기다린다");
  const steps = [
    ["1", "가설 세우기", "알람 요약과 공정 데이터로\n근본원인 후보 3~5개", C.accent2, "LLM"],
    ["2", "증거 모으기", "시계열 · 매뉴얼 · 도면 · 과거 사례\n도구를 골라 호출", C.accent2, "Tool Calling"],
    ["3", "촬영 요청", "어떤 사진이 어떤 가설을 가르는지\n사진을 보기 전에 선언", C.accent6, "사람을 기다림"],
    ["4", "사진 판독", "손상 · 에러코드 · 경고등\n범주 판정만", C.accent6, "VLM"],
    ["5", "확정", "근거 증거 id 인용 필수\n없으면 거부", C.accent1, "Structured Output"],
  ];
  const bw = 2.25, gap = 0.2, y = 2.05;
  steps.forEach(([n, t, d, col, tag], i) => {
    const x = M + i * (bw + gap);
    card(s, x, y, bw, 3.05, { fill: i === 2 ? "EFEBFA" : C.background2, line: i === 2 ? C.accent6 : null, lineW: 2 });
    badge(s, x + 0.25, y + 0.25, 0.6, n, col, 18);
    txt(s, t, { x: x + 0.25, y: y + 1.0, w: bw - 0.4, h: 0.45, fontSize: 19, bold: true, color: C.text1 });
    txt(s, d, { x: x + 0.25, y: y + 1.5, w: bw - 0.4, h: 1.0, fontSize: 13, color: C.text1 });
    txt(s, tag, { x: x + 0.25, y: y + 2.55, w: bw - 0.4, h: 0.35, fontSize: 12, bold: true, color: col });
  });
  card(s, M, 5.4, 12.1, 1.08, { fill: "F7EEE7" });
  txt(s, [
    { text: "핵심 설계  ", options: { bold: true, color: C.accent1 } },
    { text: "촬영 요청은 도구 호출이 아니라 비동기 중단점이다. 사람이 현장에 가는 데 수 분이 걸리므로 루프 상태를 DB로 내보내고, 사진이 오면 같은 대화를 이어서 재개한다. 15분 안에 응답이 없으면 가진 증거만으로 결론을 낸다.",
      options: { color: C.text1 } }],
    { x: M + 0.35, y: 5.55, w: 11.4, h: 0.85, fontSize: 15 });
  s.addNotes("다섯 단계입니다. 핵심은 3번입니다. 센서 데이터로 두 가설이 갈리지 않으면 Agent가 스스로 '이 사진이 있으면 갈린다'를 판단하고 요청합니다. 사진을 보기 전에 '이렇게 보이면 이 가설'을 먼저 선언하게 해서 사후 합리화를 막았습니다.");
}

// ══ 4. 실제 동작 ═══════════════════════════════════════════════════════
//   data/demo_runs/a25-timeout.json (scripts/record_demo.py, 2026-11-17 실제 실행)의 값을 옮긴다.
//   발표 영상은 같은 기록을 /?replay=a25-timeout 으로 시간 압축 재생한 것이다.
{
  const s = content("설계", "실제 실행: 설비보다 기록을 먼저 의심했다",
    `2020-03-25 · 가압력 중앙값 ${F.a25_force_drop_bar.toFixed(2)} bar 하락, 전류·전압은 그대로 — 처음엔 네 가설이 비슷했다`);
  // 왼쪽: 가설 보드 (시작 → 시계열 조회 후 → 결론)
  card(s, M, 1.95, 6.3, 4.75, { shadow: true, fill: C.background1, line: "E3E5E8" });
  txt(s, "가설 보드   시작 → 시계열 조회 후 → 결론", { x: M + 0.35, y: 2.12, w: 5.8, h: 0.4, fontSize: 15, bold: true, color: C.text1 });
  const hyps = [
    ["H4", "기록이 다른 작업일에서 복사됐다", [0.15, 0.60, 0.80], C.accent2],
    ["H3", "가압력 센서·측정 경로가 틀어졌다", [0.25, 0.20, 0.10], C.accent5],
    ["H1", "설비 고장으로 실제 가압력이 줄었다", [0.30, 0.10, 0.03], C.accent5],
    ["H2", "누군가 설정값을 낮췄다", [0.30, 0.10, 0.03], C.accent5],
  ];
  hyps.forEach(([id, st, sc, col], i) => {
    const y = 2.68 + i * 0.78;
    txt(s, [{ text: id + "  ", options: { bold: true } }, { text: st }],
        { x: M + 0.35, y, w: 3.9, h: 0.35, fontSize: 14, color: C.text1 });
    txt(s, sc.map(v => v.toFixed(2)).join(" → "), { x: M + 4.05, y, w: 2.0, h: 0.35, fontSize: 13, bold: true, color: col, align: "right" });
    s.addShape(pres.shapes.RECTANGLE, { x: M + 0.35, y: y + 0.4, w: 5.7, h: 0.12, fill: { color: "E8EAED" }, line: { type: "none" } });
    s.addShape(pres.shapes.RECTANGLE, { x: M + 0.35, y: y + 0.4, w: 5.7 * sc[2], h: 0.12, fill: { color: col }, line: { type: "none" } });
  });
  txt(s, [{ text: "근거  ", options: { bold: true, color: C.accent2 } },
          { text: "이 구간의 260행이 다른 작업일에 연속 그대로 있다 (시계열 도구가 계산) · 참고 매뉴얼의 로그 반출 절차: 플래시카드 → PC 양식으로 복사 (Pro Spot i4 §8.2)", options: { color: C.text1 } }],
      { x: M + 0.35, y: 5.85, w: 5.75, h: 0.75, fontSize: 12 });
  // 오른쪽: 촬영 요청
  card(s, 7.2, 1.95, 5.5, 4.75, { fill: "EFEBFA", line: C.accent6, lineW: 2 });
  txt(s, "남은 가설을 가르려 촬영을 요청", { x: 7.5, y: 2.12, w: 5.0, h: 0.4, fontSize: 16, bold: true, color: C.accent6 });
  card(s, 7.5, 2.65, 4.9, 2.2, { fill: C.background1 });
  txt(s, "용접기 표시창과 제어반 표시등", { x: 7.75, y: 2.78, w: 4.5, h: 0.4, fontSize: 15, bold: true, color: C.text1 });
  txt(s, "사진을 보기 전에 선언한 해석", { x: 7.75, y: 3.25, w: 4.5, h: 0.3, fontSize: 11, color: C.accent5 });
  txt(s, [{ text: "센서 에러 · 경고등이 보이면 → H3 지지, H4 약화", options: { bullet: true, breakLine: true } },
          { text: "정상 화면이면 → H4 지지, H3 약화", options: { bullet: true } }],
      { x: 7.75, y: 3.6, w: 4.5, h: 1.1, fontSize: 13, color: C.text1, paraSpaceAfter: 4 });
  txt(s, [{ text: "응답 없음 (15분) → 가진 증거로 결론", options: { bold: true, color: C.accent6, breakLine: true } },
          { text: "\"데이터 수집 계통 이상 — 다른 날 기록의 재사용\" (확신 0.80). 센서 확인은 열린 항목으로 남겼다", options: { color: C.text1 } }],
      { x: 7.5, y: 5.05, w: 4.95, h: 1.0, fontSize: 13 });
  txt(s, "실제 실행 115초 · 발표 영상은 이 기록을 시간만 압축해 재생", { x: 7.5, y: 6.2, w: 5.0, h: 0.35, fontSize: 11, color: C.accent5 });
  s.addNotes("실제 실행 기록입니다. 가압력이 아주 조금 낮아졌고 전류는 그대로였습니다. 처음엔 설비 고장, 설정 변경, 센서 이상, 기록 복사 네 가설이 비슷했습니다. 시계열 도구가 이 구간 260행이 다른 날에 그대로 있다는 신호를 주자, Agent는 기록 복사 가설을 0.15에서 0.6으로 올렸고, 참고 매뉴얼에서 로그를 플래시카드에서 PC 양식으로 복사해 내보내는 절차를 찾아 '복사 과정에서 다른 날 파일이 섞였을 수 있다'는 경로를 제시했습니다. 이 매뉴얼은 같은 계열 장비의 공개 매뉴얼이지 이 설비의 것은 아닙니다. 그래도 센서 이상을 완전히 배제할 수 없어서, 사진을 보기 전에 '에러가 보이면 센서, 정상이면 기록 문제'라고 선언하고 제어반 촬영을 요청했습니다. 응답이 없자 가진 증거로 결론을 냈고, 센서 확인은 열린 항목으로 남겼습니다.");
}

// ══ 5. 데이터와 평가 설계 ══════════════════════════════════════════════
pres.addSection({ title: "평가" });
{
  const s = content("평가", "정답지의 출처를 밝힌다",
    "실제 생산 기록 · 선행 프로젝트의 라벨 · 누구나 다시 돌릴 수 있는 감사 스크립트 — 합성은 따로 표기");
  const stats = [
    [F.weld_points.toLocaleString(), "용접점 (2020년 실제 생산)"],
    [`${F.workdays}일`, "작업일"],
    [`${F.audit.reused_pct}%`, "다른 날과 30행+ 연속 일치 (감사)"],
  ];
  stats.forEach(([b, l], i) => {
    const y = 1.95 + i * 1.55;
    card(s, M, y, 3.6, 1.35);
    txt(s, b, { x: M + 0.3, y: y + 0.15, w: 3.1, h: 0.65, fontSize: 30, bold: true, color: C.accent1 });
    txt(s, l, { x: M + 0.3, y: y + 0.82, w: 3.1, h: 0.4, fontSize: 13, color: C.text1 });
  });
  const H = t => ({ text: t, options: { bold: true, color: C.background1, fill: { color: C.text2 } } });
  const c = (t, o = {}) => ({ text: t, options: { color: C.text1, ...o } });
  s.addTable([
    [H("Tier"), H("사건"), H("정답의 출처"), H("n"), H("주 지표")],
    [c("A", { bold: true, color: C.accent4 }), c("실측 · 조용한 수준 이동"), c(`감사 스크립트 — 복제 라벨 밖 기록도 다른 날과 수백 행 연속 일치 (우연 대조 ${F.audit.chance_longest}행)`), c(String(ncase("A"))), c("근본원인")],
    [c("C", { bold: true, color: C.accent3 }), c("실측 · 알람 폭주"), c(`선행 프로젝트의 복제 구간 탐지 (${F.dup_ratio_pct}%)`), c(String(ncase("C"))), c("근본원인")],
    [c("B", { bold: true, color: C.accent5 }), c("합성 · 결함 주입 7종"), c("본 프로젝트가 주입 — 합성 표기"), c(String(ncase("B"))), c("주 변수")],
    [c("D", { bold: true, color: C.accent6 }), c("구성 · 사진 결정"), c("측정 불성립 — 한계로 보고"), c("2"), c("—")],
  ], { x: 4.5, y: 1.95, w: 8.2, colW: [0.7, 2.1, 3.65, 0.55, 1.2], fontSize: 13, rowH: 0.78,
       border: { type: "solid", pt: 0.75, color: "D7DADF" }, valign: "middle", margin: [0, 0.1, 0, 0.1] });
  txt(s, "A의 정답은 11/17 정정 — 다음 장들에서 설명", { x: 4.5, y: 6.1, w: 8.2, h: 0.4, fontSize: 13, color: C.accent5 });
  s.addNotes("정답지의 출처입니다. Tier C는 선행 프로젝트가 찾은 복제 구간이 정답입니다. Tier A의 정답은 원래 '센서로는 원인을 특정할 수 없다'였는데, 평가 도중 Agent가 이 기록도 재활용이라는 걸 짚었고, 제가 감사 스크립트로 확인해 정답을 고쳤습니다. 이 스크립트는 레포에서 누구나 다시 돌릴 수 있습니다. 합성 사건은 항상 따로 표기합니다.");
}

// ══ 6. 데이터가 설계를 바꿨다 ══════════════════════════════════════════
{
  const s = content("평가", "같은 결함, 두 가지 얼굴",
    "기록 재활용은 알람 폭주로도, 조용한 수준 이동으로도 나타난다 — 그래서 Agent의 첫 질문이 달라야 한다");
  const cols = [
    { title: "조용한 수준 이동", tag: "Tier A · 공정 이상처럼 보였다", col: C.accent4, fill: "FBF4E4",
      big: F.anom_alarms_genuine.join(" / "), bigLabel: "이상일 3일의 알람 (복제 라벨 제외)",
      lines: [`버스트 사건 ${F.anom_bursts_genuine}건 — 작업일 평균만 조용히 이동`,
              `그런데 남은 기록도 ${F.audit.a25_genuine_reused_pct}%가 다른 날과 연속 일치 (3/25)`,
              "첫 질문: 무엇이 함께 움직였나, 이 기록은 이날의 것인가"] },
    { title: "알람 폭주", tag: "Tier C · 데이터 수집 이상", col: C.accent3, fill: "F8E9E8",
      big: F.dup_day_alarms.toLocaleString(), bigLabel: "복제 구간 하루의 알람",
      lines: ["800행 기록 덩어리가 다른 날에 통째로 재현",
              "설비는 정상 — 이상 신호가 허상",
              "첫 질문: 어느 알람이 원인이고 어느 게 결과인가"] },
  ];
  cols.forEach((k, i) => {
    const x = M + i * 6.2;
    card(s, x, 1.95, 5.9, 4.75, { fill: k.fill });
    txt(s, k.tag, { x: x + 0.4, y: 2.15, w: 5.1, h: 0.35, fontSize: 13, bold: true, color: k.col });
    txt(s, k.title, { x: x + 0.4, y: 2.5, w: 5.1, h: 0.55, fontSize: 24, bold: true, color: C.text1 });
    txt(s, k.big, { x: x + 0.4, y: 3.2, w: 5.1, h: 0.9, fontSize: 44, bold: true, color: k.col });
    txt(s, k.bigLabel, { x: x + 0.4, y: 4.1, w: 5.1, h: 0.35, fontSize: 13, color: C.accent5 });
    txt(s, k.lines.map((t, j) => ({ text: t, options: { bullet: true, breakLine: j < k.lines.length - 1 } })),
        { x: x + 0.4, y: 4.6, w: 5.2, h: 1.9, fontSize: 15, color: C.text1, paraSpaceAfter: 6 });
  });
  s.addNotes("처음엔 모든 사건을 알람 폭주로 설계했습니다. 측정해보니 복제 라벨을 빼면 이상일에는 알람이 30~40건뿐이고 폭주가 없었고, 작업일 평균만 조용히 움직였습니다. 그래서 사건 유형을 둘로 나누고 Agent의 첫 질문을 다르게 했습니다. 나중에 밝혀진 건, 이 조용한 이동도 공정 변화가 아니라 재활용된 기록이 만든 것이었다는 점입니다. 같은 결함이 두 가지 증상으로 나타난 셈입니다.");
}

// ══ 7. 결과 ① ═════════════════════════════════════════════════════════
pres.addSection({ title: "결과" });
{
  const s = content("결과", "알람 요약만 본 LLM 대 Agent",
    "같은 사건 · 같은 모델(haiku) · 같은 채점자(sonnet) — 베이스라인은 알람 요약을 보고 한 번 호출");
  const items = [
    ["A", "조용한 이상의 원인 찾기", "근본원인 정확도", C.accent4, `베이스라인: ${runs("A","baseline") * ncase("A")}번 모두 '실제 가압력 저하'로 단정`],
    ["C", "데이터 이상을 알아보기", "근본원인 정확도", C.accent3, `베이스라인: 회차별 ${Math.round(stat("C","baseline")?.min ?? 0)}–${Math.round(stat("C","baseline")?.max ?? 0)}% — 대부분 설비 고장으로 오진`],
    ["B", "주입한 변수 찾기", "주 변수 식별 · 합성", C.accent5, "합성 사건 — 참고 지표"],
  ];
  items.forEach(([t, title, metric, col, note], i) => {
    const x = M + i * 4.1;
    card(s, x, 1.95, 3.8, 4.75, { shadow: true, fill: C.background1, line: "E3E5E8" });
    badge(s, x + 0.35, 2.2, 0.6, t, col, 18);
    txt(s, title, { x: x + 1.1, y: 2.27, w: 2.6, h: 0.5, fontSize: 17, bold: true, color: C.text1 });
    txt(s, metric, { x: x + 0.35, y: 3.05, w: 3.1, h: 0.35, fontSize: 13, color: C.accent5 });
    txt(s, fmt(pct(t, "baseline")), { x: x + 0.35, y: 3.5, w: 1.4, h: 0.8, fontSize: 32, bold: true, color: C.accent5 });
    txt(s, "→", { x: x + 1.55, y: 3.55, w: 0.5, h: 0.7, fontSize: 28, color: C.accent5 });
    txt(s, fmt(pct(t)), { x: x + 2.0, y: 3.4, w: 1.7, h: 0.95, fontSize: 44, bold: true, color: C.accent2 });
    txt(s, `사건 ${ncase(t)}건 · ${spread(t)}`, { x: x + 0.35, y: 4.55, w: 3.3, h: 0.35, fontSize: 12, color: C.accent5 });
    txt(s, note, { x: x + 0.35, y: 5.05, w: 3.1, h: 1.3, fontSize: 14, color: C.text1 });
  });
  s.addNotes("세 가지를 봤습니다. 알람 폭주 사건에서 베이스라인은 대부분 설비 고장으로 오진했고, Agent는 기록이 다른 날에 통째로 재현된다는 걸 찾아 데이터 수집 이상으로 판정했습니다. 조용한 수준 이동 사건에서 베이스라인은 매번 '실제로 힘이 약해졌다'고 단정했고, Agent는 대부분 재활용 기록이라는 원인을 찾았습니다. 이 사건의 정답은 평가 도중 고쳤고, 고친 뒤 처음부터 다시 측정한 값입니다.");
}

// ══ 8. 결과 ② ablation ═════════════════════════════════════════════════
{
  const s = content("결과", "기술을 하나씩 꺼봤다",
    "같은 코드 경로에서 스위치만 끈다 — 평가 전용 분기를 만들지 않는다");
  const conds = [["full", "전체"], ["no_photo", "촬영 요청 끔"], ["no_signal_guide", "신호 해석 설명 끔"],
                 ["no_tools", "도구 끔 (시계열만)"], ["no_diagram", "도면 RAG 끔"], ["baseline", "베이스라인"]];
  const cell = v => {
    if (v === null) return { text: "–", options: { color: C.accent5, align: "center" } };
    const fill = v >= 99 ? "D5EDE9" : v <= 1 ? "F4D6D4" : "F6EBCB";
    const color = v >= 99 ? C.accent2 : v <= 1 ? C.accent3 : C.accent4;
    return { text: `${Math.round(v)}%`, options: { bold: true, color, fill: { color: fill }, align: "center" } };
  };
  const H = t => ({ text: t, options: { bold: true, color: C.background1, fill: { color: C.text2 }, align: "center" } });
  const rows = [[H("조건"), H("A  근본원인"), H("C  근본원인"), H("B  주 변수")]];
  conds.forEach(([k, label]) => rows.push([
    { text: label, options: { color: C.text1, bold: k === "full" } }, cell(pct("A", k)), cell(pct("C", k)), cell(pct("B", k))]));
  s.addTable(rows, { x: M, y: 1.95, w: 7.0, colW: [2.5, 1.5, 1.5, 1.5], fontSize: 15, rowH: 0.58,
    border: { type: "solid", pt: 0.75, color: "FFFFFF" }, valign: "middle", margin: [0, 0.12, 0, 0.12] });
  const dSG = delta("C", "full", "no_signal_guide");
  const sgNote = dSG === null ? ["미측정", "—"]
    : Math.abs(dSG) < 15 ? [`C ${fmt(pct("C"))} vs ${fmt(pct("C", "no_signal_guide"))}`, "차이 없음 — 설명이 없어도 데이터 이상을 알아본다"]
    : [`C ${fmt(pct("C"))} → ${fmt(pct("C", "no_signal_guide"))}`, dSG < 0 ? "설명이 데이터 이상 판별에 기여한다" : "설명이 오히려 방해한다"];
  const notes = [
    [C.accent1, "신호 해석 설명을 끄면", `A ${fmt(pct("A"))}→${fmt(pct("A", "no_signal_guide"))} · ${sgNote[0]}`, "측정값의 의미를 알아야 데이터 이상을 알아본다"],
    [C.accent2, "도구를 끄면 (시계열만)", `A ${fmt(pct("A"))} → ${fmt(pct("A", "no_tools"))}`, "매뉴얼 · 사례 검색이 원인 특정을 돕는다"],
    [C.accent5, "촬영 요청 · 도면 RAG를 끄면", `A ${fmt(pct("A", "no_photo"))} · ${fmt(pct("A", "no_diagram"))}`, "답이 데이터에 있는 사건 — 사진·도면 효과는 못 잰다"],
  ];
  notes.forEach(([col, a, b, c], i) => {
    const y = 1.95 + i * 1.55;
    card(s, 7.95, y, 4.75, 1.35);
    txt(s, a, { x: 8.25, y: y + 0.12, w: 4.2, h: 0.35, fontSize: 13, color: C.accent5 });
    txt(s, b, { x: 8.25, y: y + 0.42, w: 4.2, h: 0.45, fontSize: 20, bold: true, color: col });
    txt(s, c, { x: 8.25, y: y + 0.88, w: 4.3, h: 0.4, fontSize: 13, color: C.text1 });
  });
  txt(s, `회차 평균. A ${ncase("A")}건 × ${runs("A")}회(정답 정정 후 재측정), C ${ncase("C")}건 × ${runs("C")}회. 끈 조건의 실패에는 결론 없이 끝난 실행 포함`,
      { x: M, y: 6.3, w: 7.0, h: 0.35, fontSize: 12, color: C.accent5 });
  s.addNotes(`각 기술의 기여를 보려고 하나씩 껐습니다. 신호 해석 설명을 빼면 조용한 이상 사건은 ${fmt(pct("A"))}에서 ${fmt(pct("A","no_signal_guide"))}로, 알람 폭주 사건은 ${fmt(pct("C"))}에서 ${fmt(pct("C","no_signal_guide"))}로 떨어졌습니다. 매뉴얼과 사례 검색 도구를 꺼도 ${fmt(pct("A","no_tools"))}로 떨어졌습니다. 반대로 촬영 요청과 도면 검색은 꺼도 떨어지지 않았습니다. 이 사건들의 답이 데이터 안에 있기 때문입니다. 사진의 효과는 이 데이터로는 측정되지 않았고, 그렇게 보고합니다. 모든 기술이 다 효과 있다고 하면 오히려 의심받습니다.`);
}

// ══ 8b. 발견 — Agent가 정답지의 결함을 먼저 짚었다 ═══════════════════════
//   docs/14-data-reuse-finding.md · scripts/91_cross_day_audit.py
{
  const s = content("결과", "Agent가 내 정답지의 결함을 먼저 찾았다",
    "시연을 녹화하다 '오답'을 봤다 — 확인해 보니 틀린 건 정답지였다");
  const A = F.audit;
  const stats = [
    [`${A.dup_index_pct}% → ${A.reused_pct}%`, "선행 라벨이 본 복제 → 실제 재활용 기록", C.accent3],
    [`${A.longest_shared}행${A.longest_shared_capped ? "+" : ""}  vs  ${A.chance_longest}행`, "다른 날과 겹치는 최장 연속 · 실제 vs 순서를 섞은 대조", C.accent1],
    [`${A.clean_rows}행`, `재활용도 복제도 아닌 기록 (전체 ${A.rows.toLocaleString()}행 중)`, C.accent5],
  ];
  stats.forEach(([b, l, col], i) => {
    const y = 1.95 + i * 1.6;
    card(s, M, y, 5.4, 1.42);
    txt(s, b, { x: M + 0.3, y: y + 0.15, w: 4.9, h: 0.7, fontSize: 30, bold: true, color: col });
    txt(s, l, { x: M + 0.3, y: y + 0.88, w: 4.9, h: 0.4, fontSize: 13, color: C.text1 });
  });
  const steps = [
    ["1", "Agent의 결론", "“가압력 하락은 공정 변화가 아니다. 이 구간의 260행이 다른 작업일에 그대로 있다.”"],
    ["2", "오답으로 보였다", "당시 정답은 '센서로는 원인을 특정할 수 없다' — 복제를 뺀 기록은 진짜라고 믿었다"],
    ["3", "확인해 보니 Agent가 맞았다", `복제 라벨 밖 3/25 기록도 ${A.a25_genuine_reused_pct}%가 다른 날과 연속 일치`],
    ["4", "정답만 고치고 다시 측정", "프롬프트는 그대로 — 정답을 안 뒤 Agent를 고치면 튜닝이 된다"],
  ];
  steps.forEach(([n, t, d], i) => {
    const y = 1.95 + i * 1.2;
    badge(s, 6.4, y + 0.05, 0.5, n, i === 2 ? C.accent2 : C.accent5, 15);
    txt(s, t, { x: 7.1, y, w: 5.6, h: 0.4, fontSize: 16, bold: true, color: i === 2 ? C.accent2 : C.text1 });
    txt(s, d, { x: 7.1, y: y + 0.42, w: 5.6, h: 0.7, fontSize: 13, color: C.text1 });
  });
  s.addNotes(`이 프로젝트에서 가장 중요한 장면입니다. 발표 영상을 녹화하려고 실제 사건을 돌렸더니, Agent가 '이건 공정 변화가 아니라 다른 날 기록이 섞인 것'이라고 답했습니다. 당시 제 정답은 '원인을 특정할 수 없다'였기 때문에 오답인 줄 알았습니다. 확인해 보니 선행 프로젝트가 복제로 표시한 건 ${A.dup_index_pct}%뿐이었는데, 실제로는 ${A.reused_pct}%의 기록이 다른 날과 수백 행씩 그대로 겹쳤습니다. 순서를 무작위로 섞으면 겹치는 길이는 ${A.chance_longest}행이 최대라서, 우연이 아닙니다. 그래서 정답을 고쳤고, Agent는 건드리지 않은 채 처음부터 다시 측정했습니다.`);
}

// ══ 9. 기술 구성 ═════════════════════════════════════════════════════
{
  const s = content("결과", "LLM · VLM 기술 10종과 각자의 역할",
    "나열이 아니라 역할 — 끄고 측정한 것과 아직 측정하지 못한 것을 구분한다");
  const techs = [
    ["Agentic 루프", "촬영 요청에서 멈추고 같은 대화로 재개", "구현", C.accent2],
    ["Tool Calling", "시계열 · 매뉴얼 · 도면 · 사례 4종", `측정: A ${fmt(pct("A"))}→${fmt(pct("A", "no_tools"))}`, C.accent2],
    ["Structured Output", "유령 증거 · 인용 없는 결론을 거부", `검증 ${N.verify?.total ?? "–"}항목`, C.accent2],
    ["하이브리드 검색", "BM25 + 벡터 + 리랭커로 매뉴얼 842청크 검색", "구현", C.accent2],
    ["Multimodal RAG", "선으로만 그려진 도면 36장을 VLM 서술", "측정: 효과 없음", C.accent5],
    ["VLM 사진 판독", "범주 판정만 — 다이얼 수치는 제외", "스파이크 168회", C.accent6],
    ["촬영 요청 설계", "가르는 관측 + 사전 선언 해석", "구현 · 웹 E2E · 효과 미측정", C.accent6],
    ["신호 해석 가이드", "측정값 설명만, 결론 지시 금지",
      dSGtag(), C.accent1],
    ["Long-term Memory", "확정 사례를 서명으로 적립 · 재사용", "구현 · 미측정", C.accent5],
    ["LLM-as-Judge", "채점 모델(sonnet)을 진단 모델과 분리", "평가 하네스", C.accent2],
  ];
  const cw = 2.3, ch = 2.25, gx = 0.15, gy = 0.2;
  techs.forEach(([name, role, tag, col], i) => {
    const r = Math.floor(i / 5), c = i % 5;
    const x = M + c * (cw + gx), y = 1.95 + r * (ch + gy);
    card(s, x, y, cw, ch);
    badge(s, x + 0.2, y + 0.2, 0.42, String(i + 1), col, 12);
    txt(s, name, { x: x + 0.2, y: y + 0.75, w: cw - 0.35, h: 0.5, fontSize: 14, bold: true, color: C.text1 });
    txt(s, role, { x: x + 0.2, y: y + 1.25, w: cw - 0.35, h: 0.6, fontSize: 12, color: C.text1 });
    txt(s, tag, { x: x + 0.2, y: y + 1.85, w: cw - 0.35, h: 0.3, fontSize: 11, bold: true, color: col });
  });
  s.addNotes("열 가지 기술을 썼고, 각각 무엇을 하는지와 근거를 같이 적었습니다. 끄고 측정한 것은 측정이라고, 구현만 하고 아직 측정하지 못한 것은 미측정이라고 표시했습니다.");
}

// ══ 10. 평가를 의심하기 ══════════════════════════════════════════════
pres.addSection({ title: "정직성" });
{
  const s = content("정직성", "내 평가가 틀린 곳을 내가 찾았다",
    "평가를 의심했기 때문에 숫자를 믿을 수 있다");
  const bugs = [
    ["정답지가 두 번 틀렸다", `1차: '고압 모드 혼입'은 복제 구간에만 있었다 (>3bar ${F.over3bar_raw_pct[0]}% → ${F.over3bar_genuine_pct[0]}%). 2차: 복제 밖 기록도 ${F.audit.reused_pct}%가 재활용`, "2차는 Agent가 먼저 짚었다 → 정답 정정 후 재측정", C.accent3],
    ["정답이 새고 있었다", "도구 출력에 복제 여부(= Tier C의 정답 라벨)가 그대로 노출", "데이터에서 직접 계산하는 최장공통런으로 교체", C.accent3],
    ["실행끼리 섞이고 있었다", "탐지기 버퍼를 비우지 않아 합성 사건 4건이 똑같은 알람 수(76)", "reset() + 회귀 테스트", C.accent4],
    ["프롬프트가 한쪽에 과적합", "\"데이터 경로를 보라\"(결론 지시)가 C를 고치고 A를 망쳤다", "측정값의 의미만 설명하도록 중립화", C.accent4],
  ];
  bugs.forEach(([t, what, fix, col], i) => {
    const r = Math.floor(i / 2), c = i % 2;
    const x = M + c * 6.15, y = 1.95 + r * 2.15;
    card(s, x, y, 5.95, 1.98);
    badge(s, x + 0.3, y + 0.25, 0.5, "!", col, 16);
    txt(s, t, { x: x + 0.95, y: y + 0.27, w: 4.8, h: 0.45, fontSize: 17, bold: true, color: C.text1 });
    txt(s, what, { x: x + 0.3, y: y + 0.85, w: 5.4, h: 0.6, fontSize: 13, color: C.text1 });
    txt(s, "→ " + fix, { x: x + 0.3, y: y + 1.48, w: 5.4, h: 0.4, fontSize: 13, bold: true, color: C.accent2 });
  });
  card(s, M, 6.3, 12.1, 0.55, { fill: "F7EEE7" });
  txt(s, [{ text: "단일 실행은 믿지 않는다  ", options: { bold: true, color: C.accent1 } },
          { text: `Tier C는 사건 1건이라 같은 조건이 0%↔100%로 뒤집혔다 → ${ncase("C")}건으로 늘려 3회씩 다시 쟀다  ·  설계 검증 ${N.verify?.pass ?? "–"}/${N.verify?.total ?? "–"}`,
            options: { color: C.text1 } }],
      { x: M + 0.3, y: 6.38, w: 11.6, h: 0.4, fontSize: 13, valign: "middle" });
  s.addNotes(`평가를 만들면서 제 평가의 오류를 네 개 찾았습니다. 가장 큰 건 정답지입니다. 두 번 틀렸고, 두 번째는 Agent가 먼저 짚었습니다. 정답이 새던 문제, 실행끼리 섞이던 문제, 프롬프트가 한쪽으로 기울던 문제도 고쳤습니다. 이런 오류가 다시 생기지 않게 설계 의도 ${N.verify?.total ?? 51}개를 코드로 검증합니다.`);
}

// ══ 11. 실패 보고 ════════════════════════════════════════════════════
{
  const s = content("정직성", "측정이 성립하지 않은 실험도 보고한다",
    "사진 '내용'의 효과를 재려던 Tier D는 실패 — 대신 엉뚱한 증거를 거르는 Agent를 발견했다");
  card(s, M, 1.95, 5.5, 4.75);
  txt(s, "Tier D 설계와 결과", { x: M + 0.35, y: 2.15, w: 4.8, h: 0.4, fontSize: 17, bold: true, color: C.text1 });
  txt(s, "공정 데이터가 똑같은 두 사건(냉각수 이상 / 모두 정상)을 만들어 사진만이 둘을 가르게 했다",
      { x: M + 0.35, y: 2.65, w: 4.8, h: 0.8, fontSize: 13, color: C.text1 });
  const td = N.tier_d || {};
  [["Agent가 고른 사진", td.agent_photo], ["무관한 사진", td.random_photo], ["사진 없음", td.no_photo]].forEach(([l, v], i) => {
    const y = 3.6 + i * 0.6;
    txt(s, l, { x: M + 0.35, y, w: 3.0, h: 0.4, fontSize: 14, color: C.text1 });
    txt(s, v ? `${Math.round(v.m1)}%` : "–", { x: M + 3.4, y, w: 1.6, h: 0.4, fontSize: 18, bold: true, color: C.accent3, align: "right" });
  });
  txt(s, [{ text: "원인 — Agent가 아니라 내 설계", options: { bold: true, breakLine: true } },
          { text: "설계자가 정한 '냉각' 가설을 12번 중 0번 떠올림", options: { bullet: true, breakLine: true } },
          { text: "정보이득 지표가 반박 사진에서 오히려 커짐", options: { bullet: true } }],
      { x: M + 0.35, y: 5.45, w: 4.9, h: 1.1, fontSize: 13, color: C.text1 });
  card(s, 6.4, 1.95, 6.3, 4.75, { fill: "EAF5F3", line: C.accent2, lineW: 2 });
  txt(s, "Agent의 결론 (원문 번역)", { x: 6.75, y: 2.15, w: 5.6, h: 0.4, fontSize: 15, bold: true, color: C.accent2 });
  txt(s, "“돌아온 사진은 장착된 전극 팁이 아니라 바닥에 놓인 낱개 전극 팁이라, 두 가설을 가르지 못한다. 장착된 팁 면과 2차 연결부를 직접 확인하라.”",
      { x: 6.75, y: 2.7, w: 5.6, h: 1.6, fontSize: 19, color: C.text1, italic: true });
  txt(s, "인터넷의 제품 사진을 받자, 이 설비를 찍은 사진이 아니라고 판단해 증거로 쓰지 않았다",
      { x: 6.75, y: 4.45, w: 5.6, h: 0.75, fontSize: 14, color: C.text1 });
  txt(s, "→ 엉뚱한 증거를 받으면 알아채고 거른다 (환각 방어의 실제 사례)", { x: 6.75, y: 5.3, w: 5.7, h: 0.7, fontSize: 14, bold: true, color: C.accent2 });
  s.addNotes("실패한 실험도 보고합니다. 사진의 내용이 정답률을 올리는지 재려 했는데 전부 0%였습니다. 원인은 제 설계였습니다. 제가 정한 가설을 Agent가 한 번도 떠올리지 않았고, 지표 정의도 틀렸습니다. 대신 흥미로운 걸 봤습니다. 인터넷의 전극 제품 사진을 주자, Agent가 '이건 이 기계에 달린 전극이 아니다'라고 판단하고 증거로 쓰지 않았습니다.");
}

// ══ 12. 측정해서 설계를 정했다 ═══════════════════════════════════════
{
  const s = content("정직성", "측정해서 설계를 정했다",
    "추측으로 정한 것은 측정이 뒤집었다 — 속도, 사진 판독 범위, 백엔드");
  const st = [
    [`${F.resume_tokens[0].toLocaleString()} → ${F.resume_tokens[1]}`, "스텝당 입력 토큰",
     `매 스텝 새 세션을 열던 것을 대화 이어가기로 — 스텝당 ${F.step_time[0]} → ${F.step_time[1]}`, C.accent2],
    [`${F.spike_fault_binary_pct}% vs ${F.spike_gauge_binary_pct}%`, "같은 사진을 두 번 읽은 일치율",
     "이상 유무(이진)는 안정, 게이지 바늘 판독은 절반이 엇갈림 → 다이얼 판독을 설계에서 제외하고 작업자에게 묻는다", C.accent6],
    ["API 키 없음", "Claude Code 구독으로 운영",
     "claude -p 백엔드. 호출당 비용 환산값은 오버헤드 포함이라 서비스 비용이 아니다", C.accent1],
  ];
  st.forEach(([big, label, desc, col], i) => {
    const x = M + i * 4.1;
    card(s, x, 1.95, 3.8, 3.6);
    txt(s, big, { x: x + 0.35, y: 2.25, w: 3.2, h: 0.8, fontSize: 30, bold: true, color: col });
    txt(s, label, { x: x + 0.35, y: 3.1, w: 3.2, h: 0.4, fontSize: 14, bold: true, color: C.text1 });
    txt(s, desc, { x: x + 0.35, y: 3.65, w: 3.15, h: 1.7, fontSize: 14, color: C.text1 });
  });
  s.addNotes("처음 설계의 많은 부분을 측정이 바꿨습니다. 게이지 바늘 판독은 같은 사진을 두 번 읽혀도 절반이 다르게 나와서 아예 뺐고, 대신 매뉴얼 기준값을 근거로 작업자에게 직접 묻습니다.");
}

// ══ 13. 한계와 계획 ═══════════════════════════════════════════════════
pres.addSection({ title: "마무리" });
{
  const s = content("마무리", "한계와 12/13까지의 계획", "주장의 범위를 먼저 밝힌다");
  const lim = [
    `표본이 작다 — 실측 사건 A ${ncase("A")}건, C ${ncase("C")}건. C의 ${ncase("C")}건은 같은 복제 기록의 다른 구간이라 서로 독립인 고장이 아니다`,
    "Tier B는 합성 — 주 변수 식별만 참고로 본다",
    "이 데이터에는 진짜 공정 이상이 없다 — 실측 사건은 모두 기록 재활용이라 사진 요청의 효과를 재지 못했다",
    "원본 시각이 날짜 단위라 스트림은 교대 시간에 균등 배치한 의사 타임스탬프",
  ];
  const plan = [
    "스트림 계층을 Kafka(Redpanda) + Flink로 이식",
    "DB를 SQLite → Postgres + pgvector로 이전",
    "실제 공정 이상이 담긴 공개 데이터로 사진 요청의 효과 측정",
    "사례 메모리의 효과(루프 길이 · 토큰) 측정",
  ];
  [["한계", lim, C.accent3, "F8E9E8"], ["12/13까지", plan, C.accent2, "EAF5F3"]].forEach(([t, arr, col, fill], i) => {
    const x = M + i * 6.2;
    card(s, x, 1.95, 5.9, 4.75, { fill });
    txt(s, t, { x: x + 0.4, y: 2.15, w: 5.0, h: 0.5, fontSize: 22, bold: true, color: col });
    txt(s, arr.map((a, j) => ({ text: a, options: { bullet: true, breakLine: j < arr.length - 1 } })),
        { x: x + 0.4, y: 2.85, w: 5.2, h: 3.6, fontSize: 15, color: C.text1, paraSpaceAfter: 10 });
  });
  s.addNotes("한계를 먼저 말씀드립니다. 실측 사건 수가 작아 반복 측정으로 보완했습니다. 가장 큰 한계는, 이 데이터의 이상이 전부 기록 재활용이라 진짜 공정 이상이 없다는 점입니다. 그래서 사람에게 사진을 요청하는 기능은 구현과 동작까지만 보였고, 효과는 측정하지 못했습니다. 최종 제출까지 실제 공정 이상이 담긴 데이터로 이 부분을 측정하고, 스트림 인프라를 이식합니다.");
}

// ══ 14. 마무리 ═══════════════════════════════════════════════════════
{
  const s = pres.addSlide({ masterName: "CLOSING_DARK", sectionTitle: "마무리" });
  s.addText("LLM을 답변기가 아니라,\n증거를 의심하는 추론자로", { placeholder: "title" });
  txt(s, "github.com/dlwogud/rootcause-stream", { x: M, y: 4.3, w: 12, h: 0.45, fontSize: 18, color: C.accent1, bold: true });
  txt(s, `모든 수치는 평가 DB에서 재생성  ·  python3 -m eval.report  ·  설계 검증 ${N.verify?.pass ?? "–"}/${N.verify?.total ?? "–"}`,
      { x: M, y: 4.85, w: 12, h: 0.4, fontSize: 14, color: "C9CDD2" });
  s.addNotes("정리하겠습니다. 이 Agent의 가치는 답을 빨리 내는 데보다, 증거를 모으고 의심하는 데 있습니다. 그 덕분에 제 정답지의 결함까지 먼저 찾았습니다. 모든 수치와 발견은 레포에서 재생성할 수 있습니다. 감사합니다.");
}

(async () => {
  await pres.writeFile({ fileName: OUT });
  await applyTheme(OUT, THEME);
  console.log("→", OUT);
})();
