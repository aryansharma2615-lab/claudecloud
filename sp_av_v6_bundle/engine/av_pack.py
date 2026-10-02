#!/usr/bin/env python3
"""
av_pack.py — bed layout for the print-orientation view and the 3MF export.

MaxRects bin-packing, best-short-side-fit, 90-degree rotation allowed. Not
optimal — optimal 2D packing is NP-hard and nobody is shipping a thousand
plates — but it is deterministic, which matters more here: the same config must
always produce the same plate, or the 3MF you sliced yesterday is not the one
you get today.

SEQUENTIAL PRINTING — OFF BY DEFAULT, AND OFF FOR SP
---------------------------------------------------
The hazard audit below only applies to machines that print one object to full
height before starting the next ("print by object" / sequential mode). The SP
machine is a Creality Ender 3 S1 Pro driven by Creality Print: ONE gantry, and
the whole plate prints together layer by layer. The toolhead never travels over
a finished part, so part height and neighbour spacing carry no crash risk, and
`printer.gantry` / `printer.skirt` are meaningless on it.

So audit_plate() is a no-op unless the config sets `printer.sequential: true`.
It stays in the engine because a future enclosed/multi-tool machine may want it,
but shipping a red "the gantry will hit them" box on hardware that cannot do
that is worse than shipping no box at all — it trains you to ignore the red.

WHAT IT CATCHES WHEN IT IS ON:

  1. HEIGHT — a finished part taller than the clearance under the X gantry gets
     struck by the gantry on a later pass. The part comes off the bed, or the
     hotend crashes and the print is over.
  2. SKIRT — even below gantry height, the toolhead itself (fan shroud, Sprite
     Pro extruder body) is a fat cylinder around the nozzle. A neighbour inside
     that radius gets clipped by the shroud before the gantry is ever a factor.

So the packer records, per plate, the tallest part and the tightest centre
spacing, and the viewer paints both in red when they are violated.
"""
from __future__ import annotations


class _Bin:
    """MaxRects, best-short-side-fit, rotation allowed.

    Shelf packing was the first attempt and it packed badly here: three parts
    are ~146 mm wide, each claimed a full-width shelf, and the 60 mm strip left
    above it went to waste — SmartValve came out 1/1/1/8 across four plates.
    MaxRects keeps free space as a list of overlapping maximal rectangles
    instead of rows, so that leftover strip stays usable: 7/3/1/1 for the same
    twelve objects.

    Note it is STILL four plates. The binding constraint is not the packer, it
    is that housing, lid and shell are each 146 mm wide and 118-140 mm deep, so
    no two of them share a 220 x 220 bed in any orientation. That is a fact
    about the product, and no packing algorithm will argue it away.
    """

    def __init__(self, w, h):
        self.free = [(0.0, 0.0, w, h)]
        self.used = []

    def insert(self, w, h):
        best = None
        for (fx, fy, fw, fh) in self.free:
            for (iw, ih, rot) in ((w, h, False), (h, w, True)):
                if iw > fw + 1e-9 or ih > fh + 1e-9:
                    continue
                # best short side fit: leave the tidiest leftover
                short = min(fw - iw, fh - ih)
                long_ = max(fw - iw, fh - ih)
                key = (short, long_)
                if best is None or key < best[0]:
                    best = (key, fx, fy, iw, ih, rot)
        if best is None:
            return None
        _, x, y, iw, ih, rot = best
        rect = (x, y, iw, ih)
        self.used.append(rect)
        self._split(rect)
        self._prune()
        return (x, y, iw, ih, rot)

    def _split(self, r):
        rx, ry, rw, rh = r
        out = []
        for f in self.free:
            fx, fy, fw, fh = f
            if rx >= fx + fw or rx + rw <= fx or ry >= fy + fh or ry + rh <= fy:
                out.append(f)                       # no overlap, keep whole
                continue
            if rx > fx:
                out.append((fx, fy, rx - fx, fh))
            if rx + rw < fx + fw:
                out.append((rx + rw, fy, fx + fw - (rx + rw), fh))
            if ry > fy:
                out.append((fx, fy, fw, ry - fy))
            if ry + rh < fy + fh:
                out.append((fx, ry + rh, fw, fy + fh - (ry + rh)))
        self.free = [f for f in out if f[2] > 1e-6 and f[3] > 1e-6]

    def _prune(self):
        keep = []
        for i, a in enumerate(self.free):
            if not any(i != j and _contains(b, a) for j, b in enumerate(self.free)):
                keep.append(a)
        self.free = keep


def _contains(a, b):
    return (a[0] <= b[0] + 1e-9 and a[1] <= b[1] + 1e-9
            and a[0] + a[2] >= b[0] + b[2] - 1e-9
            and a[1] + a[3] >= b[1] + b[3] - 1e-9)


def pack_plates(items, bed_x, bed_y, gap=8.0, margin=5.0):
    """items: [{"id":str, "w":float, "d":float, "h":float}] in bed millimetres.

    Returns (plates, placed) where
      plates = [{"idx":1, "parts":[id,...], "warn":[str,...]}]
      placed = {id: {"x":cx, "y":cy, "plate":n, "fits":bool, "rot":bool}}
    x/y are the part CENTRE in bed coordinates, bed centred on the origin.
    `rot` means the packer turned it 90 degrees about Z to make it fit.

    Clearance is handled by inflating every part by `gap` and inflating the bin
    by the same amount, so the gap between two neighbours is exactly `gap` and
    the gap to the bed edge is exactly `margin`.
    """
    usable_x = bed_x - 2 * margin
    usable_y = bed_y - 2 * margin

    def fits_either(it):
        return ((it["w"] <= usable_x and it["d"] <= usable_y) or
                (it["d"] <= usable_x and it["w"] <= usable_y))

    oversize = [it for it in items if not fits_either(it)]
    fitting = [it for it in items if fits_either(it)]

    # biggest first — a large part placed late has nowhere to go
    order = sorted(fitting, key=lambda i: (-max(i["w"], i["d"]), -i["w"] * i["d"]))

    plates, placed = [], {}
    bins, bin_parts = [], []

    for it in order:
        iw, ih = it["w"] + gap, it["d"] + gap
        pos = None
        for bi, b in enumerate(bins):
            pos = b.insert(iw, ih)
            if pos:
                break
        if not pos:
            bins.append(_Bin(usable_x + gap, usable_y + gap))
            bin_parts.append([])
            bi = len(bins) - 1
            pos = bins[bi].insert(iw, ih)
            if not pos:                       # cannot happen, fits_either passed
                oversize.append(it)
                continue
        x, y, pw, ph, rot = pos
        placed[it["id"]] = {
            "x": round(margin + x + pw / 2 - bed_x / 2, 3),
            "y": round(margin + y + ph / 2 - bed_y / 2, 3),
            "plate": bi + 1,
            "fits": True,
            "rot": bool(rot),
        }
        bin_parts[bi].append(it["id"])

    for i, ids in enumerate(bin_parts):
        plates.append({"idx": i + 1, "parts": list(ids), "warn": []})

    # Parts that cannot go on the bed at all are still shown — parked at the
    # origin of plate 1 and flagged red. Hiding a design bug is not a feature.
    for it in oversize:
        placed[it["id"]] = {"x": 0.0, "y": 0.0, "plate": 1, "fits": False, "rot": False}
        if not plates:
            plates.append({"idx": 1, "parts": [], "warn": []})
        plates[0]["parts"].append(it["id"])

    if not plates:
        plates.append({"idx": 1, "parts": [], "warn": []})
    return plates, placed


def audit_plate(plate, items_by_id, placed, gantry, skirt, sequential=False):
    """Fill plate["warn"] with the print-by-object hazards on this plate.

    No-op unless `sequential` — see the module docstring. Still records maxH so
    the UI can show plate height; just no hazard claims.
    """
    ids = plate["parts"]
    warn = []
    if not sequential:
        plate["warn"] = []
        plate["minGap"] = None
        plate["tallCount"] = 0
        plate["maxH"] = round(max([items_by_id[i]["h"] for i in ids], default=0.0), 1)
        return plate
    tall = [i for i in ids
            if items_by_id[i]["h"] > gantry and placed[i]["fits"]]
    # The viewer renders its own gantry warning and names the offending parts,
    # so emitting a second, vaguer copy here just stacks two red boxes saying
    # the same thing. Record the fact; let the UI phrase it.
    plate["tallCount"] = len(tall)
    # tightest centre-to-centre spacing vs the toolhead skirt
    worst = None
    for a in range(len(ids)):
        for b in range(a + 1, len(ids)):
            ia, ib = ids[a], ids[b]
            if not (placed[ia]["fits"] and placed[ib]["fits"]):
                continue
            # clearance between footprint rectangles, not centres: two long
            # thin parts side by side are fine even though their centres are close
            dx = abs(placed[ia]["x"] - placed[ib]["x"]) \
                 - (items_by_id[ia]["w"] + items_by_id[ib]["w"]) / 2
            dy = abs(placed[ia]["y"] - placed[ib]["y"]) \
                 - (items_by_id[ia]["d"] + items_by_id[ib]["d"]) / 2
            clear = max(dx, dy)
            if worst is None or clear < worst:
                worst = clear
    if worst is not None and worst < skirt:
        warn.append(
            f"Tightest neighbour gap is {worst:.0f} mm, inside the {skirt:g} mm "
            f"toolhead skirt radius — the fan shroud will clip a finished "
            f"neighbour if you print by object.")
    plate["warn"] = warn
    plate["minGap"] = None if worst is None else round(worst, 1)
    plate["maxH"] = round(max([items_by_id[i]["h"] for i in ids], default=0.0), 1)
    return plate
