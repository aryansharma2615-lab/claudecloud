#!/usr/bin/env python3
"""build_av_v8.py — build_av_v7.py carried forward to engine v8, without editing build_av.py.

    python3 build_av_v8.py av_config.json out.html

On top of v7 (insert / finish / screw / plate_dir / project_dir, Motion __META__ / __GEO__):

* `eng` (top level)       a path to engineering_data_<assembly>.yaml -> calc_v8.compute() -> META.eng
                          (every number source-labelled, checks, fits, stack-ups, live TEST model, ranking,
                          measurement list). Or `eng_json`: a ready dict (test coupons, other tools).
* `motion` (top level)    passes straight through to META.motion (project builders used to splice it)
* `checks` (top level)    META.checks (v7.2 tiles), passes through
* parts[].mass            {g, com, how} -> Motion loads + CoG
* parts[].stl_hi          a finer tessellation of the same part -> META part.lod {off, n, lo, span, tris};
                          the viewer swaps it in when you zoom past 2× (default view stays light)
* `brand`                 {accent, loader, footer} — SP defaults
* template defaults to viewer_template_motion_v8.html (override: AV_TEMPLATE=path)
"""
import json
import os
import sys
import types

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import build_av_v7 as V7  # noqa: E402

SP_BRAND = {"accent": "#FF6B35", "loader": "Shawarma Prints · Designed in Vaughan, ON",
            "footer": "Prototyped on Ender 3 S1 Pro · Toronto, Canada"}


def sub(s, old, new, count=1):
    n = s.count(old)
    assert n == count, f"anchor found {n}x (want {count}): {old[:80]!r}"
    return s.replace(old, new)


def load():
    s = open(V7.SRC, encoding="utf-8").read()
    # ---- everything v7 did (same anchors, asserted once each) ----
    s = sub(s, 'TEMPLATE = os.path.join(HERE, "viewer_template.html")',
            'TEMPLATE = os.environ.get("AV_TEMPLATE") or os.path.join(HERE, "viewer_template_motion_v8.html")')
    s = sub(s, '"fast": p.get("fast", []),',
            '"fast": p.get("fast", []),\n            "insert": p.get("insert"), "finish": p.get("finish"), "screw": p.get("screw"),'
            '\n            "mass": p.get("mass"), "bomLink": p.get("bom_link"),'
            '\n            "lod": ({k: rec[p["id"] + "__hi"][k] for k in ("off", "n", "lo", "span", "tris")} if p["id"] + "__hi" in rec else None),')
    s = sub(s, '"currency": cfg.get("currency", "$"),',
            '"currency": cfg.get("currency", "$"),\n        "plateDir": cfg.get("plate_dir"), "projectDir": cfg.get("project_dir"),'
            '\n        "motion": cfg.get("motion"), "checks": cfg.get("checks", []), "eng": cfg.get("_eng"),'
            '\n        "brand": cfg.get("brand"),')
    s = sub(s, '.replace("__AV_GEO__", base64.b64encode(blob).decode("ascii")))',
            '.replace("__AV_GEO__", base64.b64encode(blob).decode("ascii"))\n'
            '            .replace("__META__", json.dumps(meta, separators=(",", ":"), allow_nan=False).replace("<", "\\\\u003c"))\n'
            '            .replace("__GEO__", base64.b64encode(blob).decode("ascii"))\n'
            '            .replace("<title>OneShot Arm v3</title>", "<title>" + esc_html(cfg["title"]) + "</title>")\n'
            '            .replace("<h1>OneShot Arm v3</h1>", "<h1>" + esc_html(cfg["title"]) + "</h1>")\n'
            '            .replace("Parallelogram arm · 4 × MG90S · no spring, no wrist servo", esc_html(cfg.get("subtitle", ""))))')
    # ---- v8: the fine LOD meshes ride in the same buffer, after every part ----
    s = sub(s, '    blob, rec = G.pack(meshes)',
            '    for p in cfg["parts"]:\n'
            '        if p.get("stl_hi"):\n'
            '            meshes.append((p["id"] + "__hi", G.load_part_mesh({**p, "stl": p["stl_hi"]}, base)))\n'
            '    blob, rec = G.pack(meshes)')
    s = s.replace('if __name__ == "__main__":', 'if __name__ == "__build_av_main__":')
    mod = types.ModuleType("build_av_v8")
    mod.__file__ = V7.SRC
    exec(compile(s, V7.SRC, "exec"), mod.__dict__)
    return mod


def prepare(cfg_path):
    """resolve `eng` (YAML -> calc_v8) and `brand`, write a resolved copy next to the config"""
    cfg = json.load(open(cfg_path, encoding="utf-8"))
    base = os.path.dirname(os.path.abspath(cfg_path))
    if cfg.get("eng"):
        import calc_v8
        eng, _ = calc_v8.compute(os.path.join(base, cfg["eng"]))
        cfg["_eng"] = json.loads(json.dumps(eng, allow_nan=False, default=lambda o: sorted(o) if isinstance(o, set) else str(o)))
    elif cfg.get("eng_json"):
        cfg["_eng"] = cfg["eng_json"]
    cfg["brand"] = {**SP_BRAND, **(cfg.get("brand") or {})}
    cfg.setdefault("slug", os.path.splitext(os.path.basename(cfg_path))[0])   # never named after the temp file below
    out = os.path.join(base, "." + os.path.basename(cfg_path) + ".resolved.json")
    json.dump(cfg, open(out, "w", encoding="utf-8"))
    return out


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    B = load()
    resolved = prepare(sys.argv[1])
    try:
        B.build(resolved, out_html=sys.argv[2] if len(sys.argv) > 2 else None)
    finally:
        os.remove(resolved)
