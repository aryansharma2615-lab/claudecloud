"""FarmHand rail-SCARA: job-path feasibility + collision sweep against the printers (Phase 2 first pass).

Run: python sim/paths.py   -> sim/PATHS_REPORT.md
World frame: x along the table (left -> right), y toward the back wall, z up, table top z = 0.
The robot's J1 axis runs along the line y = 0 (rail is behind it at y = -115). Printer fronts at y = FACE.
Every station number marked ASSUMED waits on Shawarma's measurements; the point of this file is that
re-running it with real numbers re-checks every job in one command.
"""
import math
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "cad"))
from params import L1, L2, H2S, ENDER  # noqa: E402

# ---------------- station (ASSUMED) ----------------
FACE = 101.0                    # printer front faces (table depth 750 - H2S depth 514 - rail/robot strip)
H2S_X0 = -100.0                 # H2S left side
H2S_X1 = H2S_X0 + H2S["w"]
H2S_AP = dict(x0=H2S_X0 + 20, x1=H2S_X1 - 20, z0=40, z1=560)   # door aperture (ASSUMED)
H2S_HINGE = (H2S_X0, FACE)      # door hinged on the LEFT (ASSUMED, question 3)
DOOR_W, DOOR_T = H2S["w"] - 20, 12
HANDLE = dict(r=DOOR_W - 30, z=300)                            # handle 30 mm from the free edge (ASSUMED)
PLATE = dict(w=355.0, d=346.5, front_y=FACE + 60, cx=(H2S_X0 + H2S_X1) / 2)   # 60 mm door-to-plate (ASSUMED)
Z_PLATE = 250.0                 # bed commanded to this hand-off height (ASSUMED, gcode_line)
SCREEN = dict(x=H2S_X0 + 70, z=560)                            # front top-left (research), tilt ignored
ENDER_X0 = H2S_X1 + 100
ENDER_X1 = ENDER_X0 + ENDER["w"]
ENDER_SHEET = dict(w=235.0, d=235.0, cx=(ENDER_X0 + ENDER_X1) / 2, front_y=FACE - 10, z=100.0)  # bed slung forward
FLEX_STATION = (1180.0, -40.0)  # where full plates go (right end of the table)

# ---------------- robot (from cad/build_parts.py) ----------------
UA = dict(z0=62, z1=122, hw=25, tail=75)          # 60 mm closed box (stiffness Fix B)          # upper arm, relative to the shoulder height Zs
FA = dict(z0=10, z1=60, hw=22, tail=65)
HAND = dict(z0=-44, z1=-4, hx=90, hy=33)
JAW_Z0 = -149                                    # jaw tips
GRIP_DZ = -134                                   # plate plane when held
STYLUS = dict(lx=69, ly=45, z=-26)               # tip in hand frame (horizontal, points along hand +y)
ZS_MIN, ZS_MAX = 215.0, 950.0                    # shoulder height range from the column (CAD)
COLUMN = dict(dx0=-40, dx1=0, y0=-125, y1=-105)  # relative to J1 x
J1_LIM, J2_LIM = 140.0, 140.0                    # planning limits = hard stops (150/145) minus a 10/5° margin
REACH_MARGIN = 20.0                              # never plan the arm fully stretched
CLEAR = 8.0                                      # required clearance, mm


# ---------------- geometry helpers ----------------
def box(x0, x1, y0, y1, z0, z1, name):
    return (min(x0, x1), max(x0, x1), min(y0, y1), max(y0, y1), min(z0, z1), max(z0, z1), name)


def inside(p, b, c=CLEAR):
    return b[0] - c < p[0] < b[1] + c and b[2] - c < p[1] < b[3] + c and b[4] - c < p[2] < b[5] + c


def h2s_obstacles(door_phi=None):
    t = 15
    ap = H2S_AP
    obs = [box(H2S_X0, H2S_X0 + t, FACE, FACE + H2S["d"], 0, H2S["h"], "H2S left wall"),
           box(H2S_X1 - t, H2S_X1, FACE, FACE + H2S["d"], 0, H2S["h"], "H2S right wall"),
           box(H2S_X0, H2S_X1, FACE + H2S["d"] - t, FACE + H2S["d"], 0, H2S["h"], "H2S back"),
           box(H2S_X0, H2S_X1, FACE, FACE + H2S["d"], H2S["h"] - t, H2S["h"] + 226, "H2S top + AMS"),
           box(H2S_X0, H2S_X1, FACE, FACE + t, 0, ap["z0"], "H2S sill"),
           box(H2S_X0, H2S_X1, FACE, FACE + t, ap["z1"], H2S["h"], "H2S header"),
           box(H2S_X0, ap["x0"], FACE, FACE + t, 0, H2S["h"], "H2S left jamb"),
           box(ap["x1"], H2S_X1, FACE, FACE + t, 0, H2S["h"], "H2S right jamb"),
           box(PLATE["cx"] - 170, PLATE["cx"] + 170, PLATE["front_y"] + 4, FACE + H2S["d"] - 40, Z_PLATE - 40, Z_PLATE - 1.5, "H2S bed"),
           box(H2S_X0 + 20, H2S_X1 - 20, FACE + H2S["d"] - 120, FACE + H2S["d"] - 20, ap["z1"] - 80, ap["z1"], "H2S parked toolhead")]
    if door_phi is not None:
        obs += door_boxes(door_phi)
    return obs


def door_boxes(phi_deg, n=40):
    """The open door as a chain of small boxes along its slab (it is a rotated plate)."""
    hx, hy = H2S_HINGE
    ux, uy = math.cos(math.radians(phi_deg)), -math.sin(math.radians(phi_deg))
    out = []
    for i in range(n):
        s0, s1 = DOOR_W * i / n, DOOR_W * (i + 1) / n
        xa, ya, xb, yb = hx + ux * s0, hy + uy * s0, hx + ux * s1, hy + uy * s1
        out.append(box(min(xa, xb) - DOOR_T / 2, max(xa, xb) + DOOR_T / 2, min(ya, yb) - DOOR_T / 2,
                       max(ya, yb) + DOOR_T / 2, H2S_AP["z0"], H2S_AP["z1"] + 20, "H2S door"))
    return out


def ender_obstacles():
    return [box(ENDER_X0, ENDER_X1, FACE + 60, FACE + 400, 0, 80, "Ender base"),
            box(ENDER_X0, ENDER_X0 + 40, FACE + 200, FACE + 240, 0, ENDER["h"], "Ender left upright"),
            box(ENDER_X1 - 40, ENDER_X1, FACE + 200, FACE + 240, 0, ENDER["h"], "Ender right upright"),
            box(ENDER_X0, ENDER_X1, FACE + 200, FACE + 240, ENDER["h"] - 40, ENDER["h"], "Ender top bar"),
            box(ENDER_X0 + 40, ENDER_X1 - 40, FACE + 180, FACE + 260, 240, 300, "Ender X gantry (raised to Z 250)"),
            box(ENDER_SHEET["cx"] - 120, ENDER_SHEET["cx"] + 120, ENDER_SHEET["front_y"] + 3, ENDER_SHEET["front_y"] + 235,
                ENDER_SHEET["z"] - 30, ENDER_SHEET["z"] - 1.5, "Ender bed")]


def table_obstacles():
    return [box(-200, 1400, -400, 750, -60, 0, "table top")]


# ---------------- kinematics ----------------
def ik(X, wx, wy, elbow=+1):
    """Wrist (wx, wy) for J1 at (X, 0). Returns (t1, t2) in degrees, t1 from +y, or None if unreachable."""
    dx, dy = wx - X, wy
    r2 = dx * dx + dy * dy
    c2 = (r2 - L1 * L1 - L2 * L2) / (2 * L1 * L2)
    if abs(c2) > 1:
        return None
    t2 = elbow * math.acos(c2)
    a = math.atan2(dx, dy)                           # angle from +y, positive toward +x
    b = math.atan2(L2 * math.sin(t2), L1 + L2 * math.cos(t2))
    return math.degrees(a - b), math.degrees(t2)


def fk(X, t1, t2):
    a1 = math.radians(t1)
    a12 = math.radians(t1 + t2)
    e = (X + L1 * math.sin(a1), L1 * math.cos(a1))
    w = (e[0] + L2 * math.sin(a12), e[1] + L2 * math.cos(a12))
    return (X, 0.0), e, w


def seg_points(p, q, hw, z0, z1, tail=0.0, step=12.0):
    dx, dy = q[0] - p[0], q[1] - p[1]
    L = math.hypot(dx, dy)
    ux, uy = dx / L, dy / L
    nx, ny = -uy, ux
    pts = []
    s = -tail
    while s <= L + 1e-6:
        for w in (-hw, 0, hw):
            for z in (z0, (z0 + z1) / 2, z1):
                pts.append((p[0] + ux * s + nx * w, p[1] + uy * s + ny * w, z))
        s += step
    return pts


def rect_points(cx, cy, th, x0, x1, y0, y1, z, step=15.0):
    c, s = math.cos(th), math.sin(th)
    pts = []
    x = x0
    while x <= x1 + 1e-6:
        y = y0
        while y <= y1 + 1e-6:
            pts.append((cx + c * x - s * y, cy + s * x + c * y, z))
            y += step
        x += step
    return pts


def robot_points(X, Zs, t1, t2, th, plate=None, stylus=False):
    """Sample points of everything that moves. th = hand yaw (rad, 0 = hand x along world x)."""
    j1, e, w = fk(X, t1, t2)
    pts = [("upper arm", p) for p in seg_points(j1, e, UA["hw"], Zs + UA["z0"], Zs + UA["z1"], UA["tail"])]
    pts += [("forearm", p) for p in seg_points(e, w, FA["hw"], Zs + FA["z0"], Zs + FA["z1"], FA["tail"])]
    for z in (Zs + HAND["z0"], Zs + HAND["z1"]):
        pts += [("hand", p) for p in rect_points(w[0], w[1], th, -HAND["hx"], HAND["hx"], -HAND["hy"], HAND["hy"], z, 20)]
    for jx in (-30, 30):
        for z in (Zs + JAW_Z0, Zs + (JAW_Z0 - 30) / 2):
            pts += [("jaw", p) for p in rect_points(w[0], w[1], th, jx - 7, jx + 7, -9, 9, z, 7)]
    if plate:
        pw, pd = plate
        pts += [("held plate", p) for p in rect_points(w[0], w[1], th, -pw / 2, pw / 2, 28, 28 + pd, Zs + GRIP_DZ)]
    if stylus:
        c, s = math.cos(th), math.sin(th)
        lx, ly = STYLUS["lx"], STYLUS["ly"]
        pts.append(("stylus tip", (w[0] + c * lx - s * ly, w[1] + s * lx + c * ly, Zs + STYLUS["z"])))
    return pts


def column_box(X):
    return box(X + COLUMN["dx0"], X + COLUMN["dx1"], COLUMN["y0"], COLUMN["y1"], 0, 1040, "own Z column")


# ---------------- a job = list of (X, Zs, wrist x, wrist y, hand yaw deg, carrying plate?, contact_ok set) ----------------
def lerp(a, b, n):
    return [tuple(a[k] + (b[k] - a[k]) * i / n if isinstance(a[k], float) else a[k] for k in range(len(a))) for i in range(n + 1)]


def check_pose(X, Zs, wx, wy, yaw, plate, stylus, elbow, obs, allow, margin=REACH_MARGIN):
    """Returns (ok, clearance, issues, (t1, t2))."""
    sol = ik(X, wx, wy, elbow)
    if sol is None:
        return False, -1e9, [f"unreachable wrist ({wx:.0f}, {wy:.0f}) from X={X:.0f}"], None
    t1, t2 = sol
    issues = []
    if math.hypot(wx - X, wy) > L1 + L2 - margin:
        issues.append("reach margin")
    if abs(t1) > J1_LIM or abs(t2) > J2_LIM:
        issues.append(f"joint limit: J1 {t1:.0f}°, J2 {t2:.0f}°")
    if not (ZS_MIN <= Zs <= ZS_MAX):
        issues.append(f"Z out of travel: {Zs:.0f}")
    worst = 1e9
    own = column_box(X)
    for part, p in robot_points(X, Zs, t1, t2, math.radians(yaw), plate, stylus):
        for b in obs + ([own] if part == "held plate" else []):
            if b[6] in allow.get(part, ()):
                continue
            if inside(p, b):
                issues.append(f"{part} hits {b[6]}")
            else:
                worst = min(worst, max(b[0] - p[0], p[0] - b[1], b[2] - p[1], p[1] - b[3], b[4] - p[2], p[2] - b[5]))
    return not issues, worst, issues, (t1, t2)


X_GRID = [x * 20.0 for x in range(-12, 58)]          # rail travel -240 .. 1140 (ASSUMED table span)


def run_job(name, waypoints, obstacles_fn, allow=None, steps=12, fixed_first=True, margin=REACH_MARGIN):
    """Each waypoint: (X or None, Zs, wrist x, wrist y, yaw, plate, stylus). X None = planner picks the rail
    position; at every sample the planner keeps the clean (X, elbow) closest to the previous one."""
    allow = allow or {}
    samples = []
    for a, b in zip(waypoints, waypoints[1:]):
        for i in range(steps + 1):
            f = i / steps
            samples.append(tuple((a[k] + (b[k] - a[k]) * f) if isinstance(a[k], float) and isinstance(b[k], float) else a[k]
                                 for k in range(7)))
    prev, hits, worst, reach, zs, jr, xs = None, [], 1e9, [], [], [], []
    traj = []
    if fixed_first and all(smp[0] is None for smp in samples):     # one rail stop for the whole job, if one exists
        for el in (1, -1):
            for x in sorted(X_GRID, key=lambda v: abs(v - (samples[0][2] - 250))):
                if all(check_pose(x, *smp[1:], el, obstacles_fn(smp) + table_obstacles(), allow, margin)[0] for smp in samples[::3]):
                    samples = [(x,) + smp[1:] for smp in samples]
                    prev = (x, el)
                    break
            if prev:
                break
    for idx, (X, Zs, wx, wy, yaw, plate, stylus) in enumerate(samples):
        obs = obstacles_fn((X, Zs, wx, wy, yaw, plate, stylus)) + table_obstacles()
        cands = [X] if X is not None else sorted(X_GRID, key=lambda x: abs(x - (prev[0] if prev else wx - 250)))
        best = None
        for el in ([prev[1], -prev[1]] if prev else [1, -1]):
            for x in cands:
                ok, clr, iss, sol = check_pose(x, Zs, wx, wy, yaw, plate, stylus, el, obs, allow, margin)
                if ok and clr >= 0:
                    best = (x, el, clr, sol)
                    break
            if best:
                break
        if best is None:
            ok, clr, iss, sol = check_pose(cands[0], Zs, wx, wy, yaw, plate, stylus, prev[1] if prev else 1, obs, allow)
            hits += [f"sample {idx}: wrist ({wx:.0f}, {wy:.0f}, Zs {Zs:.0f}): " + "; ".join(dict.fromkeys(iss))]
            continue
        x, el, clr, sol = best
        if prev and abs(x - prev[0]) > 200 and (plate or wy > FACE - 40):   # repositioning outside, empty-handed, is fine
            hits.append(f"sample {idx}: rail jump {prev[0]:.0f} → {x:.0f} mm (needs a re-plan, not a straight move)")
        prev = (x, el)
        worst = min(worst, clr)
        reach.append(math.hypot(wx - x, wy)); zs.append(Zs); jr.append(sol); xs.append(x)
        traj.append((x, Zs, sol[0], sol[1], yaw, el))
    return dict(name=name, n=len(samples), hits=hits, clear=worst if worst < 1e9 else 0,
                reach=(min(reach), max(reach)) if reach else (0, 0), zs=(min(zs), max(zs)) if zs else (0, 0),
                j1=(min(j[0] for j in jr), max(j[0] for j in jr)) if jr else (0, 0),
                j2=(min(j[1] for j in jr), max(j[1] for j in jr)) if jr else (0, 0),
                x=(min(xs), max(xs)) if xs else (0, 0), traj=traj)


def main():
    # ---------------- the jobs ----------------
    jobs = []

    # 1. H2S plate swap (door already open at 170°): grip the shoe tab, peel, pull straight out past the robot's side
    PX = PLATE["cx"]
    X_P = PX - 260.0                                   # robot parks beside the plate path, so the plate clears its own column
    tab_y = PLATE["front_y"] - 14
    zs_g = Z_PLATE - GRIP_DZ                           # shoulder height that puts the plate plane at the bed
    out_y = FACE - 12 - 28 - PLATE["d"]                # plate's back edge 12 mm clear of the door plane
    wp = [(None, zs_g + 25, PX, FACE - 60, 0.0, None, False),
          (None, zs_g + 25, PX, tab_y, 0.0, None, False),
          (None, zs_g + 3, PX, tab_y, 0.0, None, False),            # jaws down around the tab (plate still on the bed)
          (None, zs_g + 8, PX, tab_y, 0.0, (PLATE["w"], PLATE["d"]), False),   # peel 8 mm off the magnets
          (None, zs_g + 8, PX, out_y, 0.0, (PLATE["w"], PLATE["d"]), False),   # straight out through the door
          (None, zs_g + 60, PX, out_y, 0.0, (PLATE["w"], PLATE["d"]), False)]
    ALLOW_PLATE = {"held plate": ("H2S bed",), "jaw": ("H2S bed",)}   # sliding on the bed is the job
    jobs.append(run_job("H2S plate pull (door open 170°)", wp, lambda i: h2s_obstacles(170.0), allow=ALLOW_PLATE, margin=10.0))
    jobs.append(run_job("H2S plate insert (reverse)", list(reversed(wp)), lambda i: h2s_obstacles(170.0), allow=ALLOW_PLATE, margin=10.0))

    # 2. H2S door: grip the handle, swing it along its arc, the rail carriage tracks the door so the column stays clear
    def door_wp(phi):
        hx, hy = H2S_HINGE
        a = math.radians(phi)
        wx = hx + HANDLE["r"] * math.cos(a) - 60 * math.sin(a)      # hand 60 mm off the slab (handle standoff, ASSUMED), on its outer (robot) side
        wy = hy - HANDLE["r"] * math.sin(a) - 60 * math.cos(a)
        rail_cross = hx + (hy - COLUMN["y1"]) / math.tan(a) if 0 < phi < 180 and abs(math.tan(a)) > 1e-6 else -1e9
        X = max(wx + 120.0, rail_cross - COLUMN["dx0"] + 40.0 if phi < 90 else wx + 120.0)
        return (None, HANDLE["z"] + 20.0, wx, wy, -phi, None, False)


    def door_push_wp(phi, r=140.0, off=55.0):
        """Hand on the door's INNER face, r mm from the hinge, pushing it open (like a person's palm)."""
        hx, hy = H2S_HINGE
        a = math.radians(phi)
        wx = hx + r * math.cos(a) + off * math.sin(a)
        wy = hy - r * math.sin(a) + off * math.cos(a)
        return (None, HANDLE["z"] + 20.0, wx, wy, -phi, None, False)


    DOOR_PULL_END = 40
    door_pull = [door_wp(float(p)) for p in range(0, DOOR_PULL_END + 1, 5)]
    jobs.append(run_job(f"H2S door: pull by the handle 0→{DOOR_PULL_END}°", door_pull,
                        lambda smp: h2s_obstacles(None) + door_boxes(-smp[4])[:-2], steps=8, fixed_first=False,
                        allow={"jaw": ("H2S door",)}))
    door_push = [door_push_wp(float(p)) for p in range(DOOR_PULL_END, 171, 10)]
    jobs.append(run_job(f"H2S door: push from inside {DOOR_PULL_END}→170°", door_push,
                        lambda smp: h2s_obstacles(None) + door_boxes(-smp[4])[:-2], steps=8, fixed_first=False,
                        allow={"hand": ("H2S door",)}))      # the back of the hand is touching the glass on purpose

    # 3. H2S screen tap (fallback job): stylus horizontal, pointing at the screen face
    c_y = FACE - CLEAR + 2 - STYLUS["ly"]   # tip ends 2 mm into the clearance band = touching the glass
    wp = [(None, SCREEN["z"] - STYLUS["z"], SCREEN["x"] - STYLUS["lx"], c_y - 60, 0.0, None, True),
          (None, SCREEN["z"] - STYLUS["z"], SCREEN["x"] - STYLUS["lx"], c_y, 0.0, None, True)]
    jobs.append(run_job("H2S screen tap (door closed)", wp, lambda i: h2s_obstacles(None),
                        allow={"stylus tip": ("H2S header", "H2S left jamb")}))

    # 4. Ender sheet swap: bed slung forward, lift the sheet by its tab, carry it out to the front
    EX = ENDER_SHEET["cx"]
    X_E = EX - 260.0
    etab = ENDER_SHEET["front_y"] - 14
    ezs = ENDER_SHEET["z"] - GRIP_DZ
    wp = [(None, ezs + 25, EX, etab - 80, 0.0, None, False),
          (None, ezs + 25, EX, etab, 0.0, None, False),
          (None, ezs + 3, EX, etab, 0.0, None, False),
          (None, ezs + 40, EX, etab, 0.0, (ENDER_SHEET["w"], ENDER_SHEET["d"]), False),
          (None, ezs + 40, EX, etab - 150, 0.0, (ENDER_SHEET["w"], ENDER_SHEET["d"]), False)]
    jobs.append(run_job("Ender sheet lift + carry out", wp, lambda i: ender_obstacles(), allow={"held plate": ("Ender bed",), "jaw": ("Ender bed",)}))

    # 5. Carry the H2S plate to the flex station along the rail
    wp = [(None, zs_g + 60, PX, out_y, 0.0, (PLATE["w"], PLATE["d"]), False),
          (None, zs_g + 60, FLEX_STATION[0], out_y, 0.0, (PLATE["w"], PLATE["d"]), False)]
    jobs.append(run_job("Carry H2S plate to the flex station (rail move)", wp, lambda i: h2s_obstacles(170.0) + ender_obstacles(), steps=30, fixed_first=False))

    # ---------------- report ----------------
    lines = ["# FarmHand — job paths vs printers (generated by `sim/paths.py`)\n",
             "First-pass kinematic sweep: every job is sampled along straight-line moves, inverse kinematics solved at "
             f"each sample, and ~1–2k points on the arm, hand, jaws and held plate tested against box models of the "
             f"H2S (walls, door aperture, bed, parked toolhead, AMS on top, **the door slab at its real angle**), the Ender "
             f"(base, uprights, raised gantry, bed), the table and the robot's own column. Required clearance {CLEAR:.0f} mm. "
             "**Station dimensions are ASSUMED** (see the top of the script) until measured.\n",
             "| Job | Samples | Result | Min clearance | Rail X used | Wrist reach used | Shoulder height | J1 range | J2 range |",
             "|---|---|---|---|---|---|---|---|---|"]
    for j in jobs:
        res = "✓ clean" if not j["hits"] else f"**{len(j['hits'])} issue(s)**"
        lines.append(f"| {j['name']} | {j['n']} | {res} | {j['clear']:.0f} mm | {j['x'][0]:.0f}…{j['x'][1]:.0f} | {j['reach'][0]:.0f}–{j['reach'][1]:.0f} mm "
                     f"(max {L1 + L2:.0f}) | {j['zs'][0]:.0f}–{j['zs'][1]:.0f} mm | {j['j1'][0]:.0f}…{j['j1'][1]:.0f}° | "
                     f"{j['j2'][0]:.0f}…{j['j2'][1]:.0f}° |")
    for j in jobs:
        if j["hits"]:
            lines.append(f"\n**{j['name']}** — first issues:\n")
            lines += [f"- {h}" for h in j["hits"][:8]]
    open(os.path.join(os.path.dirname(__file__), "PATHS_REPORT.md"), "w").write("\n".join(lines) + "\n")
    print("\n".join(lines))
    return jobs


if __name__ == "__main__":
    main()
