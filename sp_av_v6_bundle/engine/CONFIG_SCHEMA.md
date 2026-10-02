# AV config schema

One JSON file per product. `build_av.py` turns it into one self-contained HTML
viewer plus the plated 3MF files.

```bash
python3 ~/Claude/AV/build_av.py av_config.json out.html
python3 ~/Claude/AV/verify_av.py out.html --shots ./shots
```

**The rule:** if shipping a new product would need an edit to
`viewer_template.html`, the schema is missing a field. Add the field.

---

## Top level

| field | type | required | what it does |
|---|---|---|---|
| `title` | string | ✅ | header `<h1>` and `<title>` |
| `subtitle` | string |  | small mono line beside the title |
| `description` | string |  | `<meta name=description>` |
| `slug` | string |  | filename stem for the 3MF. Defaults to the config filename |
| `base_dir` | string |  | where relative `stl:` paths resolve from. Defaults to the config's folder |
| `groups` | object |  | `{"key": "Group heading"}`. Orders the parts list. A part's `group` must be a key here |
| `printer` | object |  | see **Printer** |
| `materials` | object |  | see **Materials** |
| `machine_rate_per_h` | number |  | $/hour for printed-part costing. `0` excludes machine time |
| `currency` | string |  | prefix on every money figure, e.g. `"CAD $"` |
| `price_note` | string |  | footnote under the BOM. Put FX rates and assumptions here |
| `explode_scale` | number |  | multiplies each part's `explode` vector. Default `16` |
| `home` | object |  | `{"yaw": -0.95, "pitch": 0.36}` starting camera, radians |
| `centre` | `[x,y,z]` |  | orbit target. Computed from the bounding box if omitted |
| `steps` | array |  | see **Steps**. Omit and the Build tab hides itself |
| `fasteners` | array |  | see **Fasteners**. Omit and the Bolts button hides itself |
| `wiring` | object |  | see **wiring**. Omit and the Wiring tab hides itself |
| `parts` | array | ✅ | see **Parts** |
| `bom_extra` | array |  | BOM lines with no geometry — screws, inserts, electronics |

---

## Printer

Ships with exactly one profile. Bed size is a value so a future machine is a
one-line change, not a rewrite.

```json
"printer": {
  "name": "Creality Ender 3 S1 Pro",
  "x": 220.0, "y": 220.0, "z": 270.0,
  "nozzle": 0.4,
  "gap": 8.0,
  "margin": 5.0,
  "sequential": false,
  "flow_mm3s": 8.0
}
```

| field | meaning |
|---|---|
| `x`,`y`,`z` | build volume, mm. Anything bigger is flagged **red** as a design bug |
| `gap` | clearance between neighbours when auto-arranging, mm |
| `margin` | keep-out from the bed edge, mm |
| `sequential` | **`false` for the SP machine, and that is not a placeholder.** The Ender 3 S1 Pro with Creality Print has one gantry and slices the plate as a single job — every object rises together, the toolhead never crosses a finished part, so part height and neighbour spacing carry no crash risk. Set `true` only for a machine that genuinely prints one object to full height before starting the next; that switches on the hazard audit and makes `gantry`/`skirt` meaningful |
| `gantry` | vertical clearance under the X gantry. **Only used when `sequential: true`.** Measure it on the machine — nozzle tip to the lowest point of the gantry |
| `skirt` | radius of the toolhead footprint around the nozzle. **Only used when `sequential: true`** |
| `flow_mm3s` | effective volumetric throughput used to estimate print time when the config gives no `time_min`. Include travel and acceleration losses |

---

## Materials

Density is physics, so grams and print time are computed whether or not anyone
has priced the spool. **Omit `price` and the BOM line renders `TBD`** — never a
guess.

```json
"materials": {
  "PETG": {
    "density": 1.27, "spool_g": 1000,
    "price": 24.99,
    "supplier": "Digitmakers.ca",
    "url": "https://www.digitmakers.ca/collections/petg-1-75-mm",
    "checked": "2026-09-13"
  },
  "PLA": { "density": 1.24, "spool_g": 1000 }
}
```

Open-frame machine: **PLA / PETG / TPU only. No ASA, no ABS.**

---

## Parts

```json
{
  "id": "housing",
  "label": "Gearbox housing",
  "color": "#5d6d7e",
  "group": "struct",
  "step": 4,
  "kind": "printed",
  "qty": 1,
  "material": "PETG",
  "note": "The whole box is sized backwards from one number…",
  "explode": [0, 0, 0],
  "stl": "stl/05_gearbox_housing.stl",
  "transform": [{"t": [0, 0, 8.0]}],
  "mates": ["plate", "wheel", "bulkhead", "lid"],
  "print": {
    "rot": [0, 0, 0],
    "layer": 0.24, "walls": 4, "infill": 25, "support": "none",
    "orientation": "Open side up, floor on the bed."
  }
}
```

| field | required | notes |
|---|---|---|
| `id` | ✅ | unique; referenced by `mates`, `fasteners[].part`, plates |
| `label` | ✅ | shown on pins, rows, BOM |
| `color` | ✅ | `#rrggbb`. Also the BOM swatch and the pin's edge stripe |
| `group` | | key into `groups` |
| `step` | | which build step it arrives at. Drives the timeline |
| `kind` | | `"printed"` or `"bought"`. Printed parts get plates, print settings, STL download |
| `qty` | | **printed parts with `qty: 2` are packed twice on the bed.** Default `1` |
| `material` | | key into `materials`. Printed parts only |
| `note` | | the one place prose is allowed. Shown in the caption strip and inspector |
| `explode` | | direction vector, multiplied by `explode_scale` and the slider |
| `bom` | | `false` removes the part from the BOM (context geometry like a pipe stub) |
| `mates` | | part ids. Rendered as tappable chips that jump to that part |
| `cost` | | see **Cost**. Overrides the computed printed-part cost |

### Geometry — exactly one of

**`stl`** — path, relative to `base_dir`:
```json
"stl": "stl/05_gearbox_housing.stl"
```

**`primitive`** — a cheap stand-in for a bought part you have no STL for.
`at` is the primitive's **centre**. Cylinders run along Z.
```json
"primitive": {"type": "compound", "parts": [
  {"type": "cylinder", "r": 18.5, "h": 68, "at": [0, 0, 0]},
  {"type": "box", "size": [11, 11, 18], "at": [0, 0, 8]}
]}
```
Types: `box` (`size`), `cylinder` (`r`,`h`), `sphere` (`r`), `compound` (`parts`).

### `transform` — applied in list order

```json
"transform": [{"rx": 90}, {"t": [0, 0, -17]}]
```
Ops: `t` (translate `[x,y,z]`), `rx`/`ry`/`rz` (degrees), `s` (scale, number or
`[x,y,z]`). **Order is the list order** — rotate-then-translate is not the same
part as translate-then-rotate, so nothing gets silently reordered.

### `print` — printed parts only

| field | meaning |
|---|---|
| `rot` | `[rx,ry,rz]` degrees to lay the part on the bed. The packer may add a further 90° about Z on its own to make it fit |
| `layer`,`walls`,`infill`,`support` | shown as chips in the inspector; `walls` and `infill` also drive the filament estimate |
| `orientation` | one line explaining **why** it prints that way up |
| `grams`,`time_min` | supply real sliced numbers and they win over the estimate |

---

## Steps

```json
"steps": [
  {"n": 4, "title": "Gearbox housing down over it",
   "caption": "Four M4 through into the plate…",
   "tool": "3 mm hex",
   "spec": "4× M4×12 into M4 inserts · 2.5 N·m",
   "time": "5 min"}
]
```

The legacy v1 shape `[[n, "title", "body"], …]` is still accepted.
Parts and fasteners appear on a step automatically via their own `step` field.

---

## Fasteners

Every entry becomes an arrow callout in the 3D view and a chip in the owning
part's inspector. **Derive `at` from the CAD constants** — see
`SmartValve/v3_viewer/make_av_config.py` for the pattern.

```json
{"id": "m4_-1-1", "label": "M4×12",
 "spec": "socket cap + M4 heat-set insert",
 "qty": 1, "at": [-30.0, -30.0, 11.2],
 "part": "housing", "step": 4,
 "gid": "M4×12 · housing to plate",
 "note": "Through the 3.2 mm housing floor into an M4 brass insert…"}
```

| field | meaning |
|---|---|
| `at` | position in assembly coordinates. Moves with `part`'s explode offset |
| `part` | the part it belongs to; hidden when that part is hidden |
| `step` | hidden in the timeline until that step |
| `gid` | group label — the inspector collapses same-`gid` entries into `4× M4×12` |

---

## Cost

Attach to a part (`parts[].cost`) or a `bom_extra` line.

```json
"cost": {
  "each": 53.99,
  "est": true,
  "supplier": "Pololu 4745",
  "url": "https://www.pololu.com/product/4745",
  "checked": "2026-09-13",
  "bulk": {"10": 49.67, "50": 45.70, "100": 42.04},
  "formula": "Published USD breaks 1/$38.95, 5/$35.83 … × 1.3862 = CAD …"
}
```

- **Omit `cost` entirely** and the line renders `TBD`, is excluded from every
  total, and is listed in the build report. That is the correct behaviour for
  anything unsourced. Do not put a number you cannot link to.
- `bulk` missing a break falls back to `each`.
- `est: true` prints a small `est` flag next to the figure.
- `formula` is rendered verbatim in the inspector so the number can be argued
  with instead of believed. Put the derivation and the assumptions in it.

Printed parts with a priced material get `cost` computed automatically:

```
grams  = shell(surface area × walls × nozzle) + infill% × remaining volume, × density
each   = grams × $/g  +  minutes/60 × machine_rate_per_h
```

---

## bom_extra

BOM lines with no geometry.

```json
{"id": "ins_m3", "label": "M3 heat-set insert (brass)", "qty": 9,
 "kind": "bought", "color": "#c9a227", "cost": { … }}
```

---

## wiring — the electronics lane

Optional. Omit it and the Wiring tab removes itself.

```json
"wiring": {
  "volts": 12,
  "note": "Lengths are the routed polyline, not straight line.",
  "colors": {"power":"#3987e5","ground":"#008300",
             "data":"#d55181","motor":"#c98500"},
  "nodes": [
    {"id":"drv", "label":"H-bridge driver", "at":[44,12,85], "schem":[1,0],
     "role":"Four switches in an H around the motor…",
     "pins":[{"id":"vin","label":"VIN","kind":"power"},
             {"id":"out1","label":"OUT1","kind":"motor"}]}
  ],
  "runs": [
    {"id":"mot_a", "label":"Motor drive A", "net":"M+",
     "from":"drv.out1", "to":"motor.m+",
     "kind":"motor", "gauge":"18 AWG", "amps":5.5, "step":7,
     "path":[[48,6,86],[52,2,82],[55,-30,72],[55,-30,58],[49,-99,32.2]],
     "note":"The lid has no pass-through there yet."}
  ]
}
```

### nodes

| field | meaning |
|---|---|
| `id` | referenced by `runs[].from` / `.to` as `"node.pin"` |
| `at` | position in assembly coordinates — where the part physically is |
| `schem` | `[col, row]` on the schematic grid. Keep it dense; a row holding one node in the far column leaves a dead band |
| `role` | one line shown when you tap the node. **Spell out the abbreviation** — this is where a reader learns what an H-bridge is |
| `pins` | `{id, label, kind}`. `kind` colours the pin dot |

### runs

| field | meaning |
|---|---|
| `net` | the short net name (`+12V`, `GND`, `M+`, `IN1`). **Direct-labels the schematic edge** — this is the secondary encoding that makes the palette legal, so it is not optional |
| `kind` | `power` / `ground` / `data` / `motor` — picks the colour and the filter group |
| `gauge` | `"18 AWG"`. Drives the real drawn diameter, resistance and the ampacity check |
| `amps` | the current the run actually carries. **Use the stall figure, not the running figure** — a jammed motor is the case the wire has to survive |
| `path` | polyline in assembly coordinates, swept into a tube at the wire's true insulated diameter. Length is computed from it |
| `step` | the build step at which the run is made |

Computed for you and shown in the UI: length, resistance, voltage drop (absolute
and %), and an `undersized` flag when `amps` exceeds the gauge's chassis rating.
The AWG table in `build_av.py` is the standard's own numbers, not estimates.

---

## Worked example

`~/Claude/SmartValve/v3_viewer/av_config.json` is a complete, shipping config —
14 parts, 8 steps, 18 fastener callouts, 4 plates. It is **generated** by
`make_av_config.py`, which pulls every coordinate from the CAD source so the
viewer cannot drift away from the parts. Copy that pattern: hand-write the
editorial content, compute the geometry.

---

## Engine v7 fields (all optional — every one has a default from what configs already carry)

Build with `build_av_v7.py` (same arguments as `build_av.py`). It passes the new part fields
through; wiring nodes and runs already pass through whole. A config with none of these builds
exactly as before and still gets every v7 feature from the defaults.

### Parts

| field | default | what it does |
|---|---|---|
| `insert` | `{dir: explode direction, dist: max(18, |explode|·explode_scale·1.25)}` | how the part flies in when its Build step plays. `dir` is the direction it travels **from** (unit vector, assembly coords), `dist` in mm |
| `finish` | from `material` / `kind` (see below) | shading: `matte` · `gloss` · `satin` · `plastic` · `steel` · `brass` · `metal` |
| `screw` | (project builders emit it) | `{axis, at, len, role, host}` — `axis` is the drive direction, `at` the head. On its step the screw drives in along `axis` while turning (2–6 visual turns); `role: "nut"` threads on from the far side |

Finish defaults: printed PLA → matte, PETG → gloss, TPU → satin; `kind: "screw"` → steel;
id/label containing *insert* or *brass* → brass; bearings / shafts / rails / nuts → steel;
motors → metal; any other bought part → plastic; wires → satin.

```json
{"id": "servo", "kind": "bought", "finish": "plastic",
 "explode": [0, -2.0, 0.6], "insert": {"dir": [0, -1, 0], "dist": 50}}
```

### Top level

| field | default | what it does |
|---|---|---|
| `plate_dir` | folder of `plateFile`, or `<project>/av/plates` | the folder the plate panel's **On the Mac** card points at |
| `project_dir` | the parts' `stlPath` up to `/out/` | the project root used to build that path |

### wiring.nodes

| field | default | what it does |
|---|---|---|
| `connector` | inferred from the label (servo → *JR servo 3-pin · 2.54 mm*, 28BYJ-48 → *JST-XH 5-pin*, UNO/ESP32 → *Dupont 2.54 mm header*, PSU → *Screw terminal*, pot / sensor → *Solder joint*, …) | the connector chip on the node's card and on each run's end |
| `supply` | first node whose id/label says psu / supply / charger / adapter / battery; rating parsed from "… 4 A …" in its label or role | `{volts, amps}` — the supply the power budget is checked against |
| `stall_a` | the `amps` of the node's single power run | the worst-case current this load draws (stall, not running) |

### wiring.nodes[].pins

| field | default | what it does |
|---|---|---|
| `order` | array order | pin number on the connector (1 = pin 1) |
| `color` | a colour word in the label ("SIG orange", "+5V red/GND brn") → the part library (SG90/MG90S: brown GND · red +5 V · orange SIG; 28BYJ-48: blue · pink · yellow · orange · red) → convention (power red, ground black) → shown **unset** | lead colour. A name (`"orange"`) or `#rrggbb`. An array gives one colour per conductor |
| `wires` | — | `[{label, color}]` — several conductors behind one pin, in order. Use it for the SG90's moved potentiometer: `[{"label":"END 1","color":"white"},{"label":"WIPER","color":"yellow"},{"label":"END 2","color":"green"}]` |

A pin label like `pot pads ×3` / `3 pins` without `wires` shows three numbered conductors
(END 1 · WIPER · END 2 for a pot) with colour **unset** — the verifier warns, it does not guess.

### wiring.runs

| field | default | what it does |
|---|---|---|
| `ends` | each end's node `connector` | `{from: {connector, color}, to: {connector, color}}` — the connector actually used at each end of this run |
| `dir` | power flows away from the supply, ground back to it, a data run flows from the controller (UNO / ESP32 / driver) | `"to"` = current/signal flows from → to, `"from"` = the reverse. Drives the flow animation |

Worked example: `examples/v7_demo/av_config.json` uses every field above.
