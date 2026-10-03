# SP assembly-viewer engine v2 — features

Shared infrastructure for every Shawarma Prints hardware project. A new product
supplies **a config file**, never a new viewer and never an edited template.

```
~/Claude/AV/
  viewer_template.html   all 12 features, zero project content
  build_av.py            config JSON + STLs  ->  one self-contained HTML
  av_geom.py             mesh load / transform / int16 quantise / pack
  av_pack.py             MaxRects bed layout + print-by-object hazard audit
  export_3mf.py          core-spec 3MF writer, reader and bed audit
  verify_av.py           drives the built page in a real browser and proves it
  CONFIG_SCHEMA.md       every field, with a worked example
```

Files are one-per-viewer, no build step, no npm, **no CDN** — WebGL2 is written
by hand, so the page works offline on a phone beside the printer.

---

## The features

### 1. Build timeline scrubber
Play / step / scrub through the assembly. Parts not yet fitted are absent;
already-fitted parts stay on screen, dimmed, so you never lose your bearings.
Each step carries a tool, a torque-or-fit spec, and a one-line caption.
**Config:** `steps[]` with `tool` / `spec`; a part joins a step via `part.step`.
Omit `steps` and the Build tab removes itself.

### 2. Part inspector
Tap a part → material, print settings, size, triangle count, the *why* note,
tappable mating parts, its fasteners (collapsed by `gid` into `4× M4×12`), cost
with the derivation, and the slicer handoff.
**Config:** `parts[].material`, `.print`, `.mates`, `.note`.

### 3. Live BOM drawer
Qty, each, line, ×100, supplier link, running total, and a ×1 / ×10 / ×50 / ×100
KPI row. A horizontal bar chart ranks where the money actually goes.
Bidirectional highlight: tap a row → the part selects in 3D; select in 3D → the
row scrolls into view.
**Config:** `parts[].cost`, `bom_extra[]`, `materials`, `machine_rate_per_h`.
**Unsourced lines render `TBD`, are excluded from every total, and are listed in
the build report.** There is no code path that invents a price.

### 4. Section / cut-plane
X, Y or Z, with a flip. Culling comes off while cutting so you see the inside,
back faces are tinted so a cut reads as machined material rather than "the model
is hollow", and the readout is in millimetres of assembly coordinate.
**Config:** always on.

### 5. Measurement
Tap two features → distance in mm plus the ΔX/ΔY/ΔZ components. CPU raycast
against the real triangles (Möller–Trumbore, AABB prefiltered, meshes decoded to
float lazily). Snaps to the nearest facet corner within 3.5 % of the part
diagonal — a measurement between two arbitrary points on a face is almost never
what you meant; between two corners it always is.
**Config:** always on.

### 6. View presets
Iso / Front / Top / Right / Exploded / Collapsed, one tap, animated, shortest way
round the yaw circle. Respects `prefers-reduced-motion`.
**Config:** `home` sets what Iso means.

### 7. Fastener callouts
Arrow annotations at every bolt with size and length (`M3×12`), leader lines back
to the hole, hidden until their step arrives, and hidden with their parent part.
**Config:** `fasteners[]`. Omit it and the Bolts button removes itself.
Derive `at` from the CAD constants — see `make_av_config.py`.

### 8. Print-orientation view
Every printed part as it sits on the bed, inside a drawn 220 × 220 × 270 volume
with a 20 mm grid and the gantry-clearance plane marked. Parts that do not fit
are flagged **red**. Real STL bounding boxes throughout — a part is measured, not
assumed. `qty: 2` puts two on the bed.
**Config:** `printer`, `parts[].print.rot`, `parts[].qty`.

### 9. Mobile-first
Reviewed on an iPhone next to the printer:
- Every control ≥ 44 px on its short side (the range sliders are 44 px of grab
  height over a 6 px track — the hit area is the target, not the ink).
- Panels are bottom sheets with a drag-to-dismiss handle.
- **The dock stays above the sheet**, so switching panels is one tap, not
  dismiss-then-tap.
- **The projection skews upward by the fraction of stage the sheet covers**, so
  the step you are reading about is never behind the panel describing it.
- Zero hover-only interactions — verified, the harness counts `:hover` rules.
- Above 900 px the same DOM becomes a docked right rail.

### 10. 90 % visual / 10 % words
Every panel leads with the picture or the number. Text is labels, chips and
captions. The only prose is the per-part *why* note and the print-by-object
hazard warnings, both capped and both load-bearing.

### 11. Slicer handoff
Per printed part: **Download STL** (binary STL rebuilt from the viewer mesh in
its own source orientation) and **Copy slicer command**, which puts
`open -a "Creality Print" <abs path>` on the clipboard. Clipboard API with an
`execCommand` fallback for `file://` Safari. **Zero network calls** — a published
artifact cannot reach the local machine, so nothing tries.

### 12. 3MF plate export
See below.

### 13. Wiring & electronics lane
The harness in two linked views.

**In 3D** every run is a real swept tube on its real routed path, drawn at its
true insulated diameter — 18 AWG really is 1.72 mm on screen. The enclosure
x-rays so you can see which wall a run is cable-tied to instead of watching it
float in space. Tubes are packed into the same int16 buffer as every other part
and carry `kind:"wire"`, so picking, ghosting, isolate and section work on a
cable run without a line of special-case code. Cost: 880 triangles for eleven
runs.

**In 2D** a pinout schematic — node boxes with pin rows, coloured pin dots, and
orthogonally routed edges. Tap a node for what it *is*, in plain words.

**Linked both ways.** Tap a run in the list, an edge in the schematic, or the
tube itself in 3D: it lights in all three, the other runs ghost, and the caption
gives gauge, length, current, resistance and voltage drop.

Per run the engine computes length from the routed polyline, DC resistance,
voltage drop absolute and as a % of the bus, and flags any run whose current
exceeds its gauge's chassis rating. The AWG table is the standard's own numbers.

**Colour is never the only encoding.** Wire kinds use slots 1–4 of the
`/dataviz` reference categorical theme in its fixed order, and every schematic
edge is direct-labelled with its net name (`+12V`, `M+`, `SIG`). That label is
load-bearing, not decoration: the dark steps land in the 6–8 CVD floor band,
which is legal *only* with secondary encoding. The obvious palette — red for
power, amber for motor — was measured at **CVD ΔE 1.3 under deuteranopia**,
i.e. the same colour to a red-green colourblind reader. Run the validator.

**Config:** a top-level `wiring` block. See `CONFIG_SCHEMA.md`.

### 14. Motion
**Auto-explode intro.** On load the assembly flies apart, holds long enough to
read, and settles home — about two seconds, with a slow yaw drift so it reads as
a solid object rather than a picture that grew. It answers "how many parts is
this and how do they stack" before anyone touches a control. **Any** input kills
it instantly (pointer, wheel, key, touch); an animation you cannot interrupt is
a loading screen. Skipped entirely under `prefers-reduced-motion`.

**Every camera move is eased.** One `animate()` with cubic easing and
shortest-way-round yaw, and a `glide()` wrapper that every mode change routes
through — entering a step, a plate, a wire trace, or Reset. Direct `cam.dist =`
assignment is what made those snap. The two places still assigning directly are
the pointer drag and wheel, which must follow the finger frame-for-frame; easing
a drag feels like lag, not polish.

A newer move cancels the one in flight (`animGen`), so overlapping rAF loops
can never both call `draw()` in the same frame. That bug was real and cost 12
fps before it was caught.

**The intro holds the fps floor on its own terms.** It is the heaviest
continuous render in the artifact, so it starts on the **bottom** resolution
rung rather than waiting for the tuner to discover the problem — the tuner steps
every 500 ms and the whole animation is 2000 ms, so it would have finished
before the ramp arrived. Resolution is also least noticeable while nothing is
holding still; it recovers to full on the first settled frame, which is the
frame anyone actually studies.

| intro fps (SwiftShader) | before | after |
|---|---|---|
| iPhone 390 × 844 | 30.3 | **42.4** |
| desktop 1280 × 860 | 28.6 | **38.7** |
| iPad 1024 × 1366 | — | **32.8** |

Also fixed along the way: `offsetWidth` was read for every callout pin on every
frame — a read-write-read layout thrash. Pin widths are now cached and
invalidated only when the text or class changes.

### 15. Printable build sheet + deep links
**One-click build sheet.** `⎙ Build sheet (PDF)` in the Build panel captures a
render per step off the live canvas, assembles a print document and calls
`window.print()`. No PDF library — the browser already has print-to-PDF, and a
`@media print` stylesheet *is* the exporter. No npm, no CDN, ~0 kB added.

Contents: cover with an exploded hero render and eight stat tiles → full BOM
table with live links → one block per step (render, tool, torque/fit spec,
caption, its parts, its fasteners) → fastener schedule → wiring schedule.

Two details that matter:
- Renders are captured with `draw()` and `toDataURL()` in the **same
  synchronous task**, which keeps the WebGL back buffer readable without paying
  for `preserveDrawingBuffer` on every frame of normal use.
- Capture temporarily forces the **light** token set. A dark-theme render prints
  as a black rectangle that soaks a cartridge. The viewer's own theme is
  restored in a `finally`, so a mid-capture throw cannot strand it.

The whole capture runs inside `try/finally` and restores camera, explode, mode,
step, selection and theme exactly — verified by string-comparing `__avState()`
before and after.

**Deep links.** `#step=4` · `#part=housing` · `#wire=mot_a` · `#plate=2` ·
`#tab=bom`. The hash is written back on every state change with
`replaceState`, **never** `pushState` — the hash records where you *are*, and
turning Back into a per-tap undo is not what a Back button means. A deep link
skips the intro: someone sent that link to show a specific thing. `⧉` in the
sheet header copies the link to the current view.

---

## 3MF and the print-by-object warning

> **Sequential printing is OFF for SP hardware.** The Ender 3 S1 Pro driven by
> Creality Print has one gantry and slices the plate as a single job: every
> object rises together, layer by layer, and the toolhead never travels across a
> finished part. Part height and neighbour spacing therefore carry **no crash
> risk** on this machine, and the hazard audit below is gated behind
> `printer.sequential` (default `false`). It stays in the engine for a future
> machine that genuinely prints one object at a time.

`build_av.py` writes one core-spec 3MF **per plate** plus a combined file with
every part (plates offset along +Y so they do not overlap). The page can also
build a plate's 3MF **in the browser** — welded on the int16 grid the geometry
already lives on, DEFLATE via `CompressionStream` with a STORED fallback, no
network.

Each part is a **separate named object with real coordinates**, not one merged
mesh and not one file per part. That is the whole reason this is 3MF: STL is an
anonymous triangle soup with no units and no object boundaries.

**Deliberately no vendor metadata.** Plate assignment and print-sequence flags
are vendor extensions; Creality Print, OrcaSlicer and Bambu Studio each store
them differently and none of it is in the core spec. A guess at Creality's
namespace would produce a file that *looks* right and imports wrong.
**So: turn on print-by-object in the slicer yourself.**

### And then read the red box, because this is where prints die

Sequential print-by-object on an **open-frame bedslinger** means the gantry
sweeps horizontally across parts that are already finished. Two failure modes:

1. **Gantry height.** A finished part taller than the clearance under the X
   gantry gets struck on a later pass. The part comes off the bed, or the hotend
   crashes and the job is over. Config value `printer.gantry`.
2. **Toolhead skirt.** Even below gantry height, the fan shroud and Sprite Pro
   extruder body form a fat cylinder around the nozzle. A neighbour inside that
   radius gets clipped before the gantry is ever a factor. Config value
   `printer.skirt`.

The packer records the tallest part and the tightest neighbour gap on every
plate; the viewer paints both in red and **names the offending parts**.

> `printer.gantry: 25` and `printer.skirt: 45` are conservative placeholders.
> **Measure them on the actual machine** — nozzle tip to the lowest point of the
> gantry, and nozzle to the widest point of the shroud — before trusting a
> sequential job. Too low costs you a plate; too high costs you a crash.

### Bed packing
MaxRects, best-short-side-fit, 90° rotation allowed, biggest part first.
Shelf packing was the first attempt and it packed badly: three SmartValve parts
are ~146 mm wide, each claimed a full-width shelf, and the 60 mm strip above it
went to waste — 1/1/1/8 across four plates. MaxRects keeps free space as
maximal rectangles instead of rows: **7/3/1/1** for the same twelve objects.

Still four plates, and that is not the packer's fault: housing, lid and shell
are each 146 mm wide and 118–140 mm deep, so no two of them share a 220 × 220
bed in any rotation. That is a fact about the product. Deterministic — the same
config always produces the same plate.

---

## Performance

**Measured, not assumed.** `window.__avBench(ms)` runs a continuous orbit and
reports fps, median and p95 frame time, pixel count and the GL renderer string.
`verify_av.py` calls it at a 390 px viewport; pressing **f** shows the same
number live in-page.

SmartValve v3 — 14 parts, 65 948 triangles, 1.13 MB of int16 geometry:

| | fps | median frame |
|---|---|---|
| first working build | 28.6 | 35.0 ms |
| **shipping** | **45.7** | **21.6 ms** |

> These are **SwiftShader** numbers — headless Chromium fell back to software
> rasterisation, so this is a CPU-rendered floor, not an iPhone figure. A real
> GPU has far more headroom. The floor is the useful number: if it clears 30 fps
> with no GPU at all, the phone is fine.

### Rungs used

Only **rung 1**, and in its good form:

**Rung 1 — devicePixelRatio.** Rather than capping DPR globally, the engine does
**dynamic resolution scaling**: full resolution on still frames, reduced
resolution only *while you are dragging*, auto-tuned from measured frame time
down the ladder 2 → 1.5 → 1.25 → 1 and back up again. Tuning only fires on a run
of slow frames and at most twice a second, so one hitch cannot permanently drop
the quality. This bought 28.6 → 45.7 fps while *improving* the still image,
which is the thing you actually look at.

Rungs **2–5 were not needed and were not used**:
- antialiasing is still **on** — the flat-shaded CAD look leans on it
- ghosts still render **transparent** (`GHOST_OPAQUE` exists as rung 3 if ever
  needed)
- no shadows were ever drawn, so there was nothing to drop
- **no mesh was decimated.** Triangle counts are exactly what the CAD exported

Cheap by construction, before any rung: int16 quantised positions at 6 bytes a
vertex, no normals (the fragment shader recovers a flat facet normal from screen
derivatives), no index buffer, on-demand rendering with no idle rAF loop, and
GPU colour-id picking.

---

## Verification

`verify_av.py OUT.html --shots DIR` drives the real page in Chromium at
390 × 844 and fails the build on:

- any console error or page error
- horizontal overflow (children of intentional scrollers excluded)
- **clipped text** — content wider than its own box, which `scrollWidth` on the
  document never catches
- v1 behaviour regressions: orbit, explode, tap-to-identify, ghost, isolate
- any view preset that does not move the camera
- a section slider that changes no pixels
- a measurement that yields no distance
- a timeline that does not advance on next or on play
- **any part off screen at full explode** (`__avOffscreen()` projects all eight
  bbox corners of every visible part)
- BOM lines that do not sum to the rendered total

and reports fps, touch-target sizes, `:hover` rule count, and screenshots of
every panel. `build_av.py` additionally reopens every 3MF it wrote and checks
object counts, bed containment and pairwise overlap on every build.

---

## Geometry pipeline

```
STL / primitive  ->  transform  ->  per-part int16 quantise  ->  concat  ->  base64
```

Each part is normalised into **its own** bounding box as 3 × int16; the shader
rebuilds it with `p = (q/32767 × 0.5 + 0.5) × span + lo`. Resolution is
`span/65535` — 2.2 µm on a 146 mm housing, two orders of magnitude finer than a
0.4 mm nozzle can place plastic.

A `uModel` matrix is what lets one vertex buffer serve both views: the assembly
passes a translation (the explode offset), the bed passes
`T_place · T_drop · R_print · A⁻¹`, precomputed per instance by `build_av.py`.

**v1 parity was proved, not assumed.** The rebuilt pipeline reproduces v1's
embedded buffer at identical byte offsets, vertex counts and bounding boxes for
all 14 parts; 99.5 % of components are bit-identical and the rest differ by
exactly one quantisation LSB (≈ 2 µm) from a rounding-mode difference in the
original, now-missing build script.

---

## Engine change 2026-09-18 — downloads work inside a published artifact

**Project that hit it:** SmartCount v2.2.

Published as a Claude artifact, the `⤓ 3MF` and per-part STL buttons were
**inert**: the artifact viewer sandbox never grants a page download permission,
so `<a download>` (blob: and data: hrefs included) silently does nothing. The
button looked like it worked. The publisher warns about this, which is how it
was caught.

`saveBlob()` — the single chokepoint both exports already routed through — now
tries the platform `downloads` capability first and falls back to the anchor.
The capability's extension allowlist has **no `.stl` and no `.3mf`**, but both
are legal inside a `.zip` and the page already ships `buildZip()` for the 3MF
itself, so in an artifact the file is offered zipped under its own name.

Outside an artifact (`window.claude` absent) the path is byte-for-byte the old
one, so `verify_av.py` is unaffected — confirmed PASS on both sides of the
change.

**Publishing requirement:** an artifact that wants working export buttons must
be published with `capabilities: {downloads: true}`.

**Still open upstream:** `bom: false` is documented in `CONFIG_SCHEMA.md` as
removing a part from the BOM, but `build_av.py:416` only uses it to suppress the
*TBD report* line — the row still renders in the UI. SmartCount v2.2 worked
around it by pricing board-mounted parts at $0.00 with the reason, which is the
existing SP convention for kit-included parts.

---

## 2026-10-01 — OneShot v4 ratchet (engine v2 + Motion → `viewer_template_motion_v4.html`, verifier → `verify_av_v2.py`)

Source of truth for the patch: `patch_engine.py` (each edit asserts its anchor
exists exactly once, so a changed engine fails loudly). Base = the Motion-lane
engine extracted from the published OneShot v3 build (`viewer_template_motion.html`,
now also kept here).

* **R1 physics — gear efficiency.** A coupling may carry `eta`; the Load tab's
  virtual-work servo torque is divided by it. A geared servo's bar now includes
  the ratio AND the stage friction.
* **R2 BOM — HAVE / BUY.** `cost.have` (from the SP parts inventory) → tiles
  "To buy now / Already own / Filament + time", a Buy·Have·Print filter, a status
  chip per row, `[BUY]/[HAVE]/[PRINT]` on the printed build sheet.
* **R3 UI — steppers read "motor N°", not "servo N°".**
* **R4 schematic — channel router.** One vertical track per edge, crossings
  minimised (exact count, greedy insert + swap passes), gap widens to fit,
  same-column runs loop on the right edge, labels on the arriving pin. v3 drew
  every run between two columns on one x.
* **R5 physics — loop closure stays on its branch.** Passive angles wrap into
  range, big jumps are walked in ≤ 4° continuation steps from a consistent state
  (`makeState(q, pay, from)`), path frames seed from the previous frame. Without
  it 41 / 200 random poses solved onto the crossed anti-parallelogram branch
  silently (hand tilted 179°); with it 0 / 200.
* **verify_av_v2.py.** Theme check compares AFTER with BEFORE (v1 demanded
  `data-theme="dark"`, which a page that never set the attribute could not pass —
  the v3 page fails v1 too). Adds: no two runs on one vertical track; Motion
  gates — Load vs the config's independent calc (≤ 15 %), τ = −dU/dθ, BVH vs brute
  force, no tunnelling, grip (contact, stall, squeeze ≥ need), demo path (peak ≤
  rules.max, 0 collisions), drag fps, framing.
* **Display LOD** (project side, `cad/display_lod.py`): the viewer draws meshes
  built at half polygon count (inscribed → never a false collision), print STL
  stays full-res. 33 % fewer triangles, worst deviation 0.075 mm.

Known: software-WebGL fps in the headless container is 20–25 for v3 and v4 alike;
not a regression, the gate needs a GPU to mean anything.

---

## 2026-10-01 — OneShot v5 ratchet (`viewer_template_motion_v5.html`, `patch_engine_v5.py`)

* **R6 physics — multi-output gear trains.** A pinion that drives two racks (a parallel
  gripper) moves its jaws through COUPLINGS, not the kinematic tree. `subtreeOf(pinion)`
  held only the pinion, so the grip test said "never touches", the Path closed the jaws
  straight through the cube without grasping it, and the contact chip named the wrong
  part. New helper `drivenParts(id)` = the driver's subtree + the subtrees of every
  joint coupled to it; used by the grip test, the path grasp and the contact chip.
  Proved on OneShot v5: grip contact at 0.03° with 1.7° preload, demo path 0 collisions.
* Prismatic coupled joints (rack jaws, `units: "mm"`, `couple.ratio` in mm per degree)
  confirmed working end-to-end in Motion, Load, Grip and Path.
* The AV path check caught a real defect: an M2×8 gripper tab screw tip poking into the
  cube's descent path → M2×6 (OneShot D131).
* Open: yaw-drag fps on software WebGL fell to ~2 fps with v5's enclosed base (one big
  mesh around the turret defeats BVH pruning) — split large enclosing parts.

---

## 2026-10-01 — OneShot v5.2 ratchet (`viewer_template_motion_v5_2.html`, `patch_engine_v5_2.py`, `verify_av_v3.py`)

* **R7a motion — through-moves.** A path key `{through: [q1, q2, …], param?, dur?}` is ONE move
  through its via points: one minimum-jerk time-scaling over the whole polyline, so the robot
  never stops at a via. `param: "even"` gives every via the same share of the path parameter
  (matches a straight-line executor whose IK points are evenly spaced in mm); `dur` sets the time.
  OneShot v5.2 feeds IK points every 1 mm and the firmware `L` command's own timing rule, so the
  AV and the robot run the same profile (lift 1.16 s in both).
* **R7b lint — mid-move stops.** Consecutive q-keys with the same label are one move cut into
  hops, and each hop is rest-to-rest, so the arm stops dead between them. Shawarma saw OneShot
  v5's lift "struggling to go up" — it was 3 hops with 2 dead stops, not servo load (12–28 % of
  stall). New "Mid-move stops" tile on the Path tab; `__avMotion.path()` returns `deadStops` and
  per-through-move `minRatio` (slowest interior speed ÷ peak).
* **verify_av_v3.py** = v2 + gates: 0 dead stops; every through-move minRatio > 0.05.
  Proved both ways: the old v5 path built on the new engine reports 11 dead stops (FAIL); the
  v5.2 path reports 0 with minRatio 0.235–0.269 (PASS).
* Lesson for the config generator: never chain same-label joint keys to fake a straight line —
  emit one through-move.

---

## 2026-10-02 — OneShot v6 ratchet (`viewer_template_motion_v6.html`, `patch_engine_v6.py`)

* **R8a physics — gear trains are felt by the servo.** `loads()` used virtual work only when the
  mechanism had closed loops; otherwise it summed r × F over the servo's kinematic SUBTREE. A servo
  that drives its load through a gear COUPLING (planetary: sun → carrier → lever) has nothing in its
  subtree, so it would have read ~0 kg·cm with a weight on the lever. Now any servo that drives a
  coupling is loaded by virtual work (nudge the servo, every coupled joint follows, τ = −dU/dθ ÷ η).
  Proved on the OneShot v6 planetary bench: Load tab vs an independent Σ m·g·x ÷ 4 ÷ η 0.6 at three
  lever angles, err ≤ 0.01 %. Regression: the v5.2 arm build re-verified PASS on the v6 engine.
* **R8b physics/UI — the Load formula line says why** (loops and/or a gear train) and quotes the
  stage's real η (0.6 for a printed planetary) instead of a hard-coded 0.9.
* Planetary in the motion block, no engine change needed: carrier `couple.ratio = 1/N` to the sun,
  each planet a child of the carrier with `ratio = −(Zs/Zp)(1 − 1/N)` (spin RELATIVE to the carrier),
  feedback gears `ratio = −(1/N)(Z1/Z2)`. `mesh` exempts one pair, `touch` the other.
* The AV path check caught a real bench defect: the hanging test weight met the stand at −40° with
  a 64 mm lever → lever 96 mm, test hole 90 mm, sweep −15° … +40°.

---

## 2026-10-02 — engine v7 ratchet (`viewer_template_motion_v7.html`, `patch_engine_v7.py` + `engine_v7.js/.css`, `verify_av_v4.py`, `build_av_v7.py`)

Built in the cloud on `sp-av-v7` from this bundle's v6. `patch(html)` upgrades a built v6 page in place,
which is how the regression refs were made. Proved on three builds — OneShot v6 bench, OneShot v5.2 arm
(v5.2 → v6 → v7) and `examples/v7_demo` (every new config field) — all `verify_av_v4.py` **PASS**
(every v3 gate + every v7 gate, 0 console errors). Screens: `shots_v7/` (390 + 1280 px, light + dark).

* **R10 nav — CAD-grade camera.** The camera is `target + PAN` seen from (yaw, pitch, dist); orbit-about-
  the-pick, zoom-to-cursor and pinch all move PAN and one other number so the picked point keeps its pixel —
  exact for both projections. Right / middle / shift drag and two fingers pan; a CSS-3D **view cube**
  (6 face buttons; the outer 28 % bands of a face pick its 12 edges and 8 corners, so the targets stay
  thumb-sized); **Fit** (F), **double-tap a part = fit it**, **Persp / Ortho** (5); keys 1 / 3 / 7 front /
  right / top, Ctrl = opposite, 0 iso, 9 flip. Presets, Reset, steps, plates and the wiring view route their
  pan through the same eased `animate()`. Gates: cube 6/6 views exact (face, edge, corner, from the real
  cube's pixels); pan moves the target 72–94 mm with every model matrix byte-identical; zoom-to-cursor
  0.10 px (persp **and** ortho); orbit pivot 0.0 px; CDP two-finger pinch 0.0 px; double-tap fit puts the
  whole bbox on screen (bench ring housing 74 → 276 px wide).
* **R11 look — CAD viewport.** Key + fill + rim lights over a sky/ground hemisphere; per-material shading
  (PLA matte, PETG gloss, TPU satin, bought plastic, steel screws/bearings, brass inserts, `finish` overrides);
  screen-space **silhouette + crease + part-seam** lines from a normal/id + depth pass; a **soft contact
  shadow** (256² height map from under the ground, separable blur, re-rendered only when a part moves);
  MSAA kept. Found by the fps gate: edges every drag frame and a 13-tap blur every frame cost ~6 ms →
  edges now draw on the still frame only (same rule as the DPR tuner) and the blur runs once per pose.
  fps (SwiftShader, best of 2, same machine): bench **41.9 vs v6 42.1**, arm **33.5 vs 34.0**, demo **60.6 vs 60.6**.
* **R12 build — every step plays.** Parts fly in along `insert` (default = their explode vector), screws drive
  in along their axis while turning (nuts thread on from the far side), staggered; ▷/❚❚, scrub and ↺ per step;
  ▶ now plays the whole build step by step (each step waits for its animation). At u = 1 the engine returns the
  untouched base matrix, so the end pose is **bit-exact** (gate: max |Δ| = 0 on every step — 9 bench, 12 arm,
  5 demo). The build sheet wraps `buildSheet` with no-anim / no-pan / persp, so it stays static.
* **R13 wiring — detailed.** One connector card per node: pins in order, every conductor with its colour
  (config → label words → part library: SG90 brown/red/orange, 28BYJ-48 blue/pink/yellow/orange/red →
  convention → *unset*, never guessed); a pair pin ("+5V/GND") sends its GND lead to the far end's ground
  pin; connector per end; gauge · A · ΔV chips on every run; **power budget** (sum of load stall currents vs the
  supply rating, 80 % line) + **common ground** (union-find over ground runs and power pairs); tracing a run
  animates flow on the 3D tube and the schematic edge (power away from the supply, ground back, data from
  the controller). Bench: 0.70 A of 2.4 A, common ground ✓; arm: 2.34 A of 4 A ✓. The moved-pot leads show as
  END 1 · WIPER · END 2 and stay **unset** until `pins[].wires` names their colours (the demo does).
* **R14 3MF — honest.** Inside an artifact the button reads "3MF · zipped by the viewer — tap to unzip" and
  the platform gets a .zip (gate stubs `window.claude`); locally it stays the direct .3mf. The plate panel's
  **On the Mac** card shows `…/av/plates/<slug>_all_plates_plate<N>.3mf` + the all-plates file, with copy,
  open-in-slicer and reveal-in-Finder commands.
* **R15 UI.** Fit / Persp / Edges / Spin (turntable) in the tool rail; tool buttons 44 px on phones (were 36);
  the cube shrinks to ⅔ while the sheet is up on a phone; `prefers-reduced-motion` turns off fly-ins, cube
  moves, flow dashes, the turntable and the cube transition.
* `build_av_v7.py` — runs `build_av.py` through anchored source patches (never edits it): passes `insert`,
  `finish`, `screw`, `plate_dir`, `project_dir`, and fills the Motion template's `__META__` / `__GEO__`.
* Known: fps is SwiftShader in a container — a floor, not a phone. The v3 orbit bench inside the same run read
  29.9 fps on the arm (v6 page: same band); the v7 gate's best-of-2 read 33.5 vs v6 34.0.

---

## 2026-10-02 — engine v7.1 → v7.4 (same session; `patch_engine_v7_1/2/3/4.py`, `engine_v7_N.js/.css`, verifiers v5 → v8)

Each step patches the previous template and its verifier runs every earlier gate first.
Proved on the OneShot v6 bench, the OneShot v5.2 arm and `examples/v7_demo` (numbers below).

* **R16 wires as SP wires them (v7.1).** Shawarma: "no specific colours have been used" — kit jumpers.
  Colour order is now config → factory lead (label / library) → **carried along the run** from a
  factory lead → red/black convention → **any colour · tag it**. Ranges ("D8–11", "IN1–4") and
  "5-pin" plugs expand to one row per wire; a generic `MOTOR` pin mating the 28BYJ plug takes its 5
  colours; "brn" reads "brown"; a door button is "Dupont / solder tab", not a screw terminal.
  Arm: UNO D5/D6/D3 → **orange via lead**, ULN2003 motor socket → blue/pink/yellow/orange/red, 0 unset.
* **R17 explode traces · R18 part search · R19 bench checklist (device-local) · R20 Snap PNG + wire
  cut-list CSV (straight through the artifact allowlist, no zip) · R21 long-press peek · R22 scale
  bar · R23 camera in the ⧉ link · R24 Focus mode + haptics (v7.1).**
* **R25–R28 Checks tab (v7.2).** The v5.3 line's `META.checks` tiles, plus: **clash scan** (all
  intersecting facet pairs via the Motion BVH, sorted clash / by design / contact — same pair set as
  the brute-force sweep), **centre of gravity** (= an independent Σ m·x over META to 0.00 mm) with its
  footprint and the static **tip angle** atan(margin / height), and the **Ø tool** (3 rim taps).
* **R29–R32 (v7.3).** **Gap** tool and **Tight gaps** report (BVH distance = brute-force all-triangle
  distance to 1e-6 mm; flush < 0.005 mm counts as touching; a printed pair under 0.2 mm is a print
  risk) — CHECKPOINT's open "Stage 4 clearance callouts". **BOM CSV** (sums to the tab's total).
  **Section handle** (exact in ortho, under the finger in persp).
* **R33–R37 (v7.4).** ∠ angle tool, view history ◀ ▶ ([ ]), swipe between build steps, "wire to buy"
  per gauge, "?" key map.
* **Fixes found by the gates:** overlays that wrote `style.display` every frame now write only on
  change (`showEl`); the scale bar only writes when its numbers move; the long-press test leaves the
  wiring view first (ghosts cannot be picked). **The fps gate is now the median of 5 interleaved runs**:
  the same v6 bench page read 35.2 / 36.5 / 49.1 fps in one sitting (the DPR tuner sometimes steps down
  mid-bench), so best-of-N rewarded luck, not the engine.

**Findings for Shawarma (OneShot v6 bench):**
- Clash: ring housing × SG90 (cuts in ≤ 4.5 mm), torque lever × test weight (≤ 4.3 mm).
- Print-risk gaps < 0.2 mm on printed pairs: ring housing ↔ carrier 0.10, sun ↔ carrier 0.10,
  ring housing ↔ planets 0.118–0.119, horn ↔ sun 0.137, pot gear ↔ pot 0.064 mm — the planetary
  stage will likely bind as printed: open to ≥ 0.2 mm or print-in-place with a tested clearance.
- Tips over at 8.7° of tilt with the weight on the lever (CoG 12.8 mm inside the footprint, 83 mm up).

**Proof (final run, v7.3 pages, every layer v3 → v7.3):** OneShot v6 bench PASS (fps median of 5: 42.7 vs v6 37.3);
OneShot v5.2 arm PASS (36.1 vs 36.7). The demo run was still going at hand-off.
**v7.4 (R33–R37) is built and has its verifier (`verify_av_v8.py`), but has NOT been run yet: next step.**

---

## 2026-10-03 — engine v8 ratchet (`viewer_template_motion_v8.html`, `patch_engine_v8.py` + `engine_v8.js/.css`, `calc_v8.py`, `build_av_v8.py`, `verify_av_v9.py`)

Built in the cloud on `sp-av-v8` from v7.4. Guided **LOAD → FIT → SECURE → TEST** over the existing tabs, and an
**engineering-data contract** behind every number. Demo: `examples/v8_demo` — Shawarma Servo Mount v1 (SG90 bracket,
build123d CAD, PrusaSlicer G-code, URDF/SRDF/SDF + PyBullet check) + a hole-coupon test-print AV.

* **R38 phases.** A stepper over the tabs; each phase is a URL-hash state (`#phase=test&kg=…&lev=…&sec=…&xr=1&cam=…`).
  Leaving through the dock ends the phase. Gate: every phase restored from the hash alone in a fresh page.
* **R39 source labels.** Every engineering number is `value · unit · SOURCE` (MEASURED · CALC · CAD · SLICER ·
  DATASHEET · ASSUMED · SPEC); CALC carries its formula. Gate: DOM scan of every v8 panel / overlay — 0 unlabelled
  numerals (229 labelled numbers across LOAD, FIT, SECURE, TEST, Checks, inspector).
* **R40 caliper** (animated jaws, snapped points). Gate: reads the base plate's 80.00 mm front edge to 0.01 mm.
* **R41 tolerance rings** on every hole / window, coloured from `tolerance_profile_<printer>.json` (coupon fit when
  measured, ASSUMED model until then). Gate: ring colours = Python `band_of`; recolouring the profile in the page
  recolours the rings.
* **R42 stack-ups** (worst case + RSS, contribution bars, "eats most") + a CAD → printed → measured → class calculator.
* **R43 SECURE**: auto-plays the sequence; insert iron temperature and screw torque chips with their source.
* **R44 TEST**: load slider (kg + lever) → CALC stress heatmap (σ_vm ÷ strength, servo τ ÷ stall), torque meter,
  stall warning, τ(θ) chart, load arrow; the test weight's mass feeds the Motion lane. Gates: JS model = `calc_v8.Model`
  at 6 load cases (worst 2e-16 relative); Motion lane r × F = hand calc (0.7035 kgf·cm both); PyBullet inverse dynamics
  = hand calc within 0.10 %.
* **R45 what breaks first** (sorted SF, fly-to, fillet fix Kt 2.43 → 1.34: arm breaks at 2.24 kg sharp vs 4.05 kg
  filleted; SG90 stalls at 0.51 kg — the servo is the fuse).
* **R46 X-ray + true wireframe** (barycentric edges from gl_VertexID on the triangle soup). **R47 capped section**
  (flat hatched cap; gate: the pixel inside the cut = the cap colour).
* **R48 parts tree** drawer (bottom sheet < 768 px) + engineering card in the inspector. **R49 Share View.**
  **R50 STL per part + Send to slicer (3MF).** **R51 BOM OWNED $0.** **R52 perf HUD + LOD** (13.8k default, 41.3k
  past 2× zoom). **R53 checks contract** (26 tiles; ASSUMED input → UNVERIFIED, missing field → MISSING; MEASURE_ME).
* **R54 fix:** v7.4's view-history gate had never run; it failed (◀ returned to a pre-Reset view). Fixed; v7.4 gates
  now PASS on all three builds.
* **R55 build steps** draw at interaction resolution with the clock clamped to 50 ms/frame — the servo mount's steps
  5–10 finished in 3–4 frames on SwiftShader (gate: "nothing moved mid-animation"); now every step moves and lands
  bit-exact. **R56** CSS variables cached. **R57** interaction-resolution ladder gains a 0.75× rung + double step when
  frames run > 50 ms (arm: v8 21.9 fps vs v6 21.1 vs v7.4 19.2, same machine, interleaved).
* **Shader lesson:** a uniform branch costs both sides on SwiftShader — heat + wireframe in the base program cost
  ~15 % fps. They live in a second program used only when on; v8 ≥ v7.4 fps on the same model.
* **Found by the AV on the demo part (fixed in CAD):** the CoG gate showed the mount tipping forward with 200 g on the
  arm (CoG 8.0 mm outside the footprint) → base extended under the load: 12.1 mm inside, tips past 14.6°.

**Proof (clean sequential run):** servo mount — every v3 → v7.4 gate + every v8 gate **PASS** (v7 fps gate 34.7 vs v6
floor 30.1; v8 orbit 31.5 fps at 390 px). OneShot v6 bench and v5.2 arm upgraded to v8 (`refs_v8/`): every functional
gate PASS; **FAIL only on the absolute 30 fps floor** — bench 29.6 (v6 page 30.9), arm 21.3 (v6 page 20.8). A container
limit, not a v8 regression (ratio to v6: 0.96× / 1.02×). Screens: `shots_v8/` (390 + 1280 px, dark + light, all phases).
