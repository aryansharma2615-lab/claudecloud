# ADR-008: AV v8 stays one self-contained WebGL2 file; v8 is a patch module, not a rewrite

**Status:** Accepted · **Date:** 2026-10-03 · **Deciders:** Shawarma (SP)

## Context
v8 adds a guided LOAD → FIT → SECURE → TEST mode, live hand calcs and a stress heatmap. The original
brief floated a Next.js/React + three.js + cannon-es rewrite. Constraints: the AV must publish as a Claude
artifact (one HTML, scripts only from cdnjs / jsdelivr / unpkg, no localStorage reliance, 390 px phones),
zero regression on v7 … v7.4, and the verifier suite (v3 → v7.4 gates) must keep passing.

## Decision
Keep the engine as **one hand-written WebGL2 HTML file**. v8 = `patch_engine_v8.py` (anchored patches, each
asserted once) + `engine_v8.js` / `engine_v8.css` inlined before BOOT → `viewer_template_motion_v8.html`.
A Vercel page, if wanted, is a copy of the same built file plus SEO text (stretch) — never a second codebase.

## Options considered

### A. Patch module on the v7.4 single-file engine ✅
| Dimension | Assessment |
|---|---|
| Complexity | Low–Med: wrap named functions (`draw`, `goTab`, `showChecks`, `navTap` …) |
| Cost | 1 session; every legacy gate re-runs unchanged |
| Scalability | Fine to ~50k triangles default (+ LOD) on a phone |
| Team familiarity | Same mechanism as v7 → v7.4 |
| Artifact pipeline | Works as-is (`capabilities: {downloads: true}`) |

**Pros:** zero regression risk you can't measure; no build step; offline; tiny attack surface.
**Cons:** one big file; closure-private state means test hooks must be explicit (`window.__avV8`).

### B. Next.js / React + three.js rewrite
| Dimension | Assessment |
|---|---|
| Complexity | High: re-implement Motion lane, BVH collision, wiring, plates, build sheet |
| Cost | Weeks; every v3 → v7.4 gate rewritten |
| Artifact pipeline | Breaks (bundler, multiple files, npm) |

**Pros:** component model, ecosystem (RoomEnvironment HDRI, drei). **Cons:** throws away the proven engine and its proofs.

## Trade-off
The value of v8 is *engineering truth* (sources, calcs, tolerances), not a new renderer. A rewrite would spend
the session re-earning v7 instead of adding v8. The single file is also what makes the AV shareable in one tap.

## Module boundaries inside engine_v8.js
| Block | Owns | Talks to the core through |
|---|---|---|
| R39 numbers | `num8 / srcEl / statusPill` — every number + its source | DOM only |
| R44 live model | `calc8` = line-for-line mirror of `calc_v8.Model` | `META.eng.model` (read-only) |
| R41 tolerance | `printed8 / band8 / fits8` — profile → colour | `META.eng.tolerance` |
| Shader hooks | heat + wireframe **second program** (built lazily), hover tint | patched `draw` lines, `prog`/`uni` swap |
| Overlays | caliper, rings, SECURE chips, load arrow | `drawMotionOverlays` wrapper |
| Phases | `setPhase / enterPhase`, panels, hash | `goTab`, `openSheet`, `hashNow`, `applyHash` wrappers |
| Inspector / tree / BOM | engineering card, parts tree, OWNED $0 | `renderInspector`, `pickPart`, `showBom` wrappers |
| Verifier hooks | `window.__avV8` | — |

## Consequences
- Easier: every future ratchet is another patch; the gate chain grows (`verify_av_v9.py` runs v3 → v7.4 first).
- Harder: shader features must not slow the base program (lesson: SwiftShader paid ~15 % for unused branches → heat/wire moved to a second program; v8 now ≥ v7.4 fps on the same model).
- Revisit when a design needs > 100k triangles default or real FEA meshes (then: baked per-vertex colours, still in-file).

## Action items
1. [x] `patch_engine_v8.py` + `engine_v8.js/.css` → `viewer_template_motion_v8.html`
2. [x] `verify_av_v9.py` (all earlier gates + v8 gates)
3. [ ] Optional: Vercel copy of `servo_mount_v8.html` + SEO text
