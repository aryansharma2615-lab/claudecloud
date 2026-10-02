#!/usr/bin/env python3
"""build_av_v7.py — build_av.py, carried forward to engine v7 without editing it.

    python3 build_av_v7.py av_config.json out.html

Loads build_av.py, applies anchored source patches (each asserted exactly once), and runs it:

* parts pass through the new v7 fields (and `screw`, which project builders already emit): `insert` {dir, dist} (how the part flies in on its
  build step) and `finish` (matte / gloss / satin / plastic / steel / brass / metal shading).
  build_av.py copies a whitelist of part fields into the page, so without this they never
  reach the viewer.
* top level `plate_dir` / `project_dir` -> META.plateDir / META.projectDir (the plate panel's
  "On the Mac" path; by default it is derived from the parts' stlPath).
* the template defaults to viewer_template_motion_v7.html (override: AV_TEMPLATE=path).

Wiring nodes and runs already pass through whole, so node `connector` / `supply` / `stall_a`,
pin `color` / `order` / `wires` and run `ends` / `dir` need no builder change.
"""
import os
import sys
import types

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "build_av.py")


def sub(s, old, new, count=1):
    n = s.count(old)
    assert n == count, f"anchor found {n}x (want {count}): {old[:80]!r}"
    return s.replace(old, new)


def load():
    s = open(SRC, encoding="utf-8").read()
    s = sub(s, 'TEMPLATE = os.path.join(HERE, "viewer_template.html")',
            'TEMPLATE = os.environ.get("AV_TEMPLATE") or os.path.join(HERE, "viewer_template_motion_v7.html")')
    s = sub(s, '"fast": p.get("fast", []),',
            '"fast": p.get("fast", []),\n            "insert": p.get("insert"), "finish": p.get("finish"), "screw": p.get("screw"),')
    s = sub(s, '"currency": cfg.get("currency", "$"),',
            '"currency": cfg.get("currency", "$"),\n        "plateDir": cfg.get("plate_dir"), "projectDir": cfg.get("project_dir"),')
    # the Motion templates carry __META__ / __GEO__ and a hard-coded title (project builders swapped them)
    s = sub(s, '.replace("__AV_GEO__", base64.b64encode(blob).decode("ascii")))',
            '.replace("__AV_GEO__", base64.b64encode(blob).decode("ascii"))\n'
            '            .replace("__META__", json.dumps(meta, separators=(",", ":")).replace("</", "<\\\\/"))\n'
            '            .replace("__GEO__", base64.b64encode(blob).decode("ascii"))\n'
            '            .replace("<title>OneShot Arm v3</title>", "<title>" + esc_html(cfg["title"]) + "</title>")\n'
            '            .replace("<h1>OneShot Arm v3</h1>", "<h1>" + esc_html(cfg["title"]) + "</h1>")\n'
            '            .replace("Parallelogram arm · 4 × MG90S · no spring, no wrist servo", esc_html(cfg.get("subtitle", ""))))')
    s = s.replace('if __name__ == "__main__":', 'if __name__ == "__build_av_main__":')
    mod = types.ModuleType("build_av_v7")
    mod.__file__ = SRC
    sys.path.insert(0, HERE)
    exec(compile(s, SRC, "exec"), mod.__dict__)
    return mod


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    B = load()
    B.build(sys.argv[1], out_html=sys.argv[2] if len(sys.argv) > 2 else None)
