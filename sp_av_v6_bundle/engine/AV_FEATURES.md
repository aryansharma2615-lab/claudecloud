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
