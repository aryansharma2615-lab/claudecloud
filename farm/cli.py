"""Operator commands, run on the farm PC by a human (not reachable by Claude).

  python -m farm.cli status
  python -m farm.cli library-add h2s path\\to\\bracket.3mf --name "Bracket v3"
  python -m farm.cli library-list
  python -m farm.cli capture-reference h2s          # bed must be EMPTY
  python -m farm.cli set-roi h2s X Y W H            # bed region in the camera image
  python -m farm.cli actions                        # last 20 actions (audit log)
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from .config import load_settings
from .library import add_file
from .mcp_server import build_service


def main() -> None:
    ap = argparse.ArgumentParser(prog="farm")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("status")
    a = sub.add_parser("library-add")
    a.add_argument("printer", choices=["h2s", "ender"])
    a.add_argument("path", type=Path)
    a.add_argument("--name")
    sub.add_parser("library-list")
    c = sub.add_parser("capture-reference")
    c.add_argument("printer", choices=["h2s", "ender"])
    r = sub.add_parser("set-roi")
    r.add_argument("printer", choices=["h2s", "ender"])
    for k in "xywh":
        r.add_argument(k, type=int)
    sub.add_parser("actions")
    args = ap.parse_args()

    settings = load_settings()
    svc = build_service(settings)

    if args.cmd == "status":
        time.sleep(3)  # let MQTT deliver the first report
        print(json.dumps(svc.farm_status("cli"), indent=1, default=str))
    elif args.cmd == "library-add":
        entry = add_file(svc.store, settings.library_dir, args.printer, args.path, args.name)
        print(f"added {entry['file_id']}  {entry['name']}  plates={sorted(entry['plates'])}")
    elif args.cmd == "library-list":
        for f in svc.store.list_files():
            print(f"{f['file_id']}  {f['printer']:5}  {f['name']}  plates={sorted(f['plates'])}")
    elif args.cmd == "capture-reference":
        if input(f"Is the {args.printer} bed EMPTY and the plate seated? [y/N] ").lower() != "y":
            return
        img = svc._bed_photo(args.printer)
        out = settings.vision_dir / f"{args.printer}_empty.jpg"
        out.write_bytes(img)
        print(f"saved {out}")
    elif args.cmd == "set-roi":
        out = settings.vision_dir / f"{args.printer}_roi.json"
        out.write_text(json.dumps({"x": args.x, "y": args.y, "w": args.w, "h": args.h}))
        print(f"saved {out}")
    elif args.cmd == "actions":
        for ts, user, tool, params, outcome, detail in svc.store.recent_actions():
            print(time.strftime("%m-%d %H:%M:%S", time.localtime(ts)), user, tool, params, outcome, detail)


if __name__ == "__main__":
    main()
