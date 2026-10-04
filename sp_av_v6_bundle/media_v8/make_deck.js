const pptxgen = require("pptxgenjs");
const path = require("path");
const SK = "/root/.claude/skills/synced/99122024-1353-4aee-bba7-39b338c4f5c7_640a665a-5549-4210-ae00-9fdfd1891b49/pptx/scripts/apply_theme.js";
const { applyTheme } = require(SK);
const SH = "/home/user/claudecloud/sp_av_v6_bundle/shots_v8/servo_mount/";
const OUT = "/home/user/claudecloud/sp_av_v6_bundle/media_v8/AV_v8_demo_deck.pptx";

const THEME = { name: "Shawarma Prints", headFontFace: "Arial", bodyFontFace: "Arial",
  colors: { dk1: "141413", lt1: "FFFFFF", dk2: "26292D", lt2: "E8E6E0", accent1: "FF6B35", accent2: "2A78D6",
            accent3: "0CA30C", accent4: "FAB219", accent5: "D03B3B", accent6: "8A8F98", hlink: "FF6B35", folHlink: "C2410C" } };

(async () => {
  const pres = new pptxgen();
  pres.layout = "LAYOUT_16x9";               // 10 x 5.625 in
  pres.theme = { headFontFace: THEME.headFontFace, bodyFontFace: THEME.bodyFontFace };
  pres.author = "Shawarma Prints"; pres.title = "AV v8 demo";
  const C = pres.SchemeColor;
  const foot = { text: "Shawarma Prints · Designed in Vaughan, ON · Prototyped on Ender 3 S1 Pro · Toronto, Canada",
                 options: { x: 0.5, y: 5.25, w: 9, h: 0.25, fontSize: 9, color: C.background2, margin: 0 } };
  pres.defineSlideMaster({ title: "SP_DARK", background: { color: THEME.colors.dk1 },
    objects: [{ text: foot }],
    slideNumber: { x: 9.2, y: 5.25, w: 0.4, h: 0.25, fontSize: 9, color: "8A8F98" },
    placeholders: [] });
  pres.defineSlideMaster({ title: "SP_CONTENT", background: { color: THEME.colors.dk1 },
    objects: [{ text: foot },
              { placeholder: { options: { name: "title", type: "title", x: 0.5, y: 0.3, w: 9, h: 0.7, fontSize: 30, bold: true, color: C.background1, margin: 0 }, text: "" } }],
    slideNumber: { x: 9.2, y: 5.25, w: 0.4, h: 0.25, fontSize: 9, color: "8A8F98" } });

  /* 1 — title */
  pres.addSection({ title: "AV v8" });
  let s = pres.addSlide({ masterName: "SP_DARK", sectionTitle: "AV v8" });
  s.addText("AV v8", { x: 0.5, y: 0.6, w: 4.3, h: 0.5, fontSize: 18, bold: true, color: C.accent1, margin: 0, isTextBox: true, objectName: "kicker" });
  s.addText("See if it fits, bolts up and holds — before you print it", { x: 0.5, y: 1.15, w: 4.3, h: 1.9, fontSize: 32, bold: true, color: C.background1, margin: 0, valign: "top", isTextBox: true, objectName: "headline" });
  s.addText("Shawarma Servo Mount v1 · LOAD → FIT → SECURE → TEST · one link, every number with its source", { x: 0.5, y: 3.25, w: 4.3, h: 0.9, fontSize: 14, color: C.background2, margin: 0, valign: "top", isTextBox: true, objectName: "sub" });
  s.addImage({ path: SH + "v8_test_1280_dark.png", x: 5.0, y: 0.55, w: 4.6, h: 2.875, rounding: false, objectName: "hero" });
  s.addText("TEST phase: 2.0 kg on the arm — the SG90 stalls first (red), the arm root carries the stress.", { x: 5.0, y: 3.5, w: 4.6, h: 0.5, fontSize: 11, color: "8A8F98", margin: 0, isTextBox: true, objectName: "caption" });
  s.addNotes("v8 adds a guided four-phase mode on top of everything v7 did. The point: every number on screen says where it came from, and the load test is a real hand calculation, cross-checked by PyBullet.");

  /* 2 — the four phases */
  pres.addSection({ title: "Phases" });
  s = pres.addSlide({ masterName: "SP_CONTENT", sectionTitle: "Phases" });
  s.addText("Four taps tell the whole story", { placeholder: "title" });
  const ph = [["LOAD", "load", "mass + print time, from G-code"], ["FIT", "fit", "holes coloured by how YOUR printer prints"],
              ["SECURE", "secure", "auto-build: 240 °C inserts, screws from their side"], ["TEST", "test", "drag the load, see what breaks first"]];
  ph.forEach(([lab, f, cap], i) => {
    const x = 0.5 + i * 2.3;
    s.addImage({ path: SH + `v8_${f}_390_dark.png`, x: x + 0.2, y: 1.15, w: 1.6, h: 3.46, objectName: "shot_" + f });
    s.addText(`${i + 1}  ${lab}`, { x, y: 4.62, w: 2.0, h: 0.3, fontSize: 14, bold: true, color: C.accent1, margin: 0, align: "center", isTextBox: true, objectName: "lab_" + f });
    s.addText(cap, { x, y: 4.9, w: 2.0, h: 0.3, fontSize: 10, color: C.background2, margin: 0, align: "center", isTextBox: true, objectName: "cap_" + f });
  });
  s.addNotes("Each phase is a URL: the hash carries the phase, camera, explode, section cut and load, so a client opens exactly what you saw.");

  /* 3 — the servo is the fuse */
  pres.addSection({ title: "Physics" });
  s = pres.addSlide({ masterName: "SP_CONTENT", sectionTitle: "Physics" });
  s.addText("The servo is the fuse", { placeholder: "title" });
  const st = [["0.51 kg", "SG90 stalls", "1.8 kgf·cm DATASHEET ÷ 35 mm lever", "D03B3B"],
              ["2.24 kg", "arm root snaps, sharp step", "Kt 2.43 (Peterson) · CALC", "FAB219"],
              ["4.05 kg", "with a 2 mm fillet", "Kt 1.34 · CALC", "0CA30C"],
              ["0.10 %", "PyBullet vs hand calc", "inverse-dynamics torque", "2A78D6"]];
  st.forEach(([big, lab, src, col], i) => {
    const x = 0.5 + i * 2.3;
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y: 1.3, w: 2.1, h: 2.6, fill: { color: "26292D" }, line: { color: "3A3D42", width: 1 }, rectRadius: 0.12, objectName: "card" + i });
    s.addText(big, { x: x + 0.15, y: 1.5, w: 1.8, h: 0.9, fontSize: 32, bold: true, color: col, margin: 0, isTextBox: true, objectName: "big" + i });
    s.addText(lab, { x: x + 0.15, y: 2.45, w: 1.8, h: 0.7, fontSize: 14, bold: true, color: C.background1, margin: 0, valign: "top", isTextBox: true, objectName: "lab" + i });
    s.addText(src, { x: x + 0.15, y: 3.2, w: 1.8, h: 0.6, fontSize: 10, color: "8A8F98", margin: 0, valign: "top", isTextBox: true, objectName: "src" + i });
  });
  s.addText("The cheap part gives up first, safely — the bracket outlives the servo by 4.4× (arm SF at stall).", { x: 0.5, y: 4.2, w: 9, h: 0.5, fontSize: 14, italic: true, color: C.background2, margin: 0, isTextBox: true, objectName: "take" });
  s.addNotes("Torque = force × distance. 5 kg at 35 mm is 17.5 kgf·cm, almost ten times the SG90's stall, so the servo stalls long before the printed arm breaks. The fillet is margin.");

  /* 4 — what the AV caught */
  pres.addSection({ title: "Findings" });
  s = pres.addSlide({ masterName: "SP_CONTENT", sectionTitle: "Findings" });
  s.addText("Caught before a gram was printed", { placeholder: "title" });
  const fd = [["Tips over", "CoG 8.0 mm outside the base with 200 g → base under the load: 12.1 mm inside", "0CA30C"],
              ["Pilot too tight", "Ø1.5 prints Ø1.13 (split risk) → Ø1.8 CAD prints Ø1.48: a clean M2 bite", "0CA30C"],
              ["SG90 may not fit", "datasheets disagree by 0.8 mm → worst-case window −0.10 mm: calipers first", "D03B3B"]];
  fd.forEach(([h, t, col], i) => {
    const y = 1.2 + i * 1.25;
    s.addShape(pres.shapes.OVAL, { x: 0.5, y: y + 0.12, w: 0.42, h: 0.42, fill: { color: col }, line: { color: col }, objectName: "dot" + i });
    s.addText(h, { x: 1.1, y, w: 3.6, h: 0.4, fontSize: 18, bold: true, color: C.background1, margin: 0, isTextBox: true, objectName: "fh" + i });
    s.addText(t, { x: 1.1, y: y + 0.42, w: 3.8, h: 0.7, fontSize: 12, color: C.background2, margin: 0, valign: "top", isTextBox: true, objectName: "ft" + i });
  });
  s.addImage({ path: SH + "v8_fit_rings.png", x: 5.2, y: 1.2, w: 4.3, h: 2.69, objectName: "rings" });
  s.addText("FIT: rings coloured from the printer's tolerance profile (green snug · yellow running · red sloppy/tight).", { x: 5.2, y: 3.95, w: 4.3, h: 0.5, fontSize: 10, color: "8A8F98", margin: 0, isTextBox: true, objectName: "rcap" });
  s.addNotes("Two of these were fixed in CAD. The third needs real calipers on a real SG90: until then the tile honestly reads FAIL on ASSUMED inputs.");

  /* 5 — next */
  pres.addSection({ title: "Next" });
  s = pres.addSlide({ masterName: "SP_CONTENT", sectionTitle: "Next" });
  s.addText("Measure three things, then sell it", { placeholder: "title" });
  s.addText([{ text: "Caliper the SG90: body, tab span, hole pitch", options: { bullet: true, breakLine: true } },
             { text: "Print + measure the hole coupon (9 holes, 46 min)", options: { bullet: true, breakLine: true } },
             { text: "Weigh the parts; read the spool's datasheet", options: { bullet: true } }],
            { x: 0.5, y: 1.25, w: 4.4, h: 1.8, fontSize: 16, color: C.background1, paraSpaceAfter: 8, margin: 0, valign: "top", isTextBox: true, objectName: "measure" });
  s.addText("11 UNVERIFIED tiles turn PASS or FAIL — both are useful.", { x: 0.5, y: 3.1, w: 4.4, h: 0.5, fontSize: 12, italic: true, color: "8A8F98", margin: 0, isTextBox: true, objectName: "mnote" });
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: 5.3, y: 1.25, w: 4.2, h: 2.6, fill: { color: "FF6B35" }, line: { color: "FF6B35" }, rectRadius: 0.12, objectName: "offer" });
  s.addText("AV for your build", { x: 5.55, y: 1.45, w: 3.7, h: 0.45, fontSize: 18, bold: true, color: "141413", margin: 0, isTextBox: true, objectName: "oh" });
  s.addText([{ text: "$450 — LOAD + FIT + SECURE", options: { breakLine: true } }, { text: "$1,200 — + TEST, checks, MEASURE_ME", options: { breakLine: true } },
             { text: "First one free for a testimonial" }],
            { x: 5.55, y: 2.0, w: 3.7, h: 1.6, fontSize: 14, color: "141413", paraSpaceAfter: 6, margin: 0, valign: "top", isTextBox: true, objectName: "ot" });
  s.addNotes("Agency 3D microsites run $3,000–8,000; basic viewers from ~$400. SP's edge is the engineering proof, not the turntable.");

  await pres.writeFile({ fileName: OUT });
  await applyTheme(OUT, THEME);
  console.log("written", OUT);
})().catch(e => { console.error(e); process.exit(1); });
