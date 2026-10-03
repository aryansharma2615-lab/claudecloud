#!/usr/bin/env python3
"""calc_v8.py — the SP engineering-data contract (AV v8): load, validate, compute, label.

    python3 calc_v8.py <engineering_data.yaml> [--out eng.json] [--measure MEASURE_ME.md]

Reads the per-design YAML (every value {v, u, src}), merges the CAD facts (out/cad_facts.json),
the slicer facts (out/slicer_facts.json) and the printer tolerance profile, validates against
engineering_schema_v8.json, and writes META.eng for the viewer:

  * every number with its source label   MEASURED · CALC · CAD · SLICER · DATASHEET · ASSUMED · SPEC
  * every §5 check as a tile: value vs limit, formula, inputs; any ASSUMED input -> UNVERIFIED, never PASS
  * a missing required field -> MISSING (and the gate fails)
  * the live model the TEST slider drives (engine_v8.js computes the SAME formulas — verify_av_v9.py
    recomputes both and they must agree to 1 %)
  * the failure ranking ("what breaks first?") and the measurement list sorted by blast radius

Formulas (CALC — shown on tap in the AV):
  gravity torque      tau(theta) = g · Σ m_i · (x_i cos theta − z_i sin theta)        (x, z from the joint axis)
  min-jerk peak accel alpha = 5.774 · dtheta / T^2
  dynamic torque      tau = I · alpha,  I = Σ (I_c + m r^2)
  bending             sigma = M c / I,  I_rect = b h^3 / 12
  shear               tau = 1.5 V / A (rectangle, peak)
  von Mises           sigma_vm = sqrt((Kt sigma)^2 + 3 tau^2)
  safety factor       SF = strength in the loaded direction / sigma_vm   (Z = z_factor × XY)
  deflection          delta = F L^3 / (3 E I)
  stress conc.        Kt = A (r/d)^b, Peterson stepped bar in bending (Shigley Table A-15 power fit)
  thread strip        tau = F / (pi d Le · 0.5)  vs  0.577 · yield (von Mises shear)
  Lewis               sigma = F_t / (b m Y)      Grashof  s + l <= p + q
  grip                N >= m g / (2 mu) × SF     PSU      Σ stall currents <= 80 % of supply
  stack-up            worst = Σ|t|,  RSS = sqrt(Σ t^2)
"""
from __future__ import annotations

import json
import math
import os
import sys

import yaml

HERE = os.path.dirname(os.path.abspath(__file__))
G = 9.80665
KGCM = 98.0665            # N·mm per kgf·cm
SRC = ["MEASURED", "CALC", "CAD", "SLICER", "DATASHEET", "ASSUMED", "SPEC"]
SRC_INFO = {
    "MEASURED": "calipers / scale / bench test",
    "CALC": "formula — tap to see it",
    "CAD": "from the CAD geometry",
    "SLICER": "from real G-code",
    "DATASHEET": "from a published spec",
    "ASSUMED": "not measured yet — on MEASURE_ME",
    "SPEC": "a requirement you set",
}
# Peterson stepped round bar in bending, Kt = A (r/d)^b  (Shigley 9e Table 7-?/Fig A-15-9 power fit)
KT_TABLE = [(1.01, 0.91938, -0.17032), (1.02, 0.96048, -0.17711), (1.03, 0.98061, -0.18381),
            (1.05, 0.98137, -0.19653), (1.07, 0.97527, -0.20958), (1.10, 0.95120, -0.23757),
            (1.20, 0.97098, -0.21796), (1.50, 0.93836, -0.25759), (2.00, 0.90879, -0.28598),
            (3.00, 0.89334, -0.30860), (6.00, 0.87868, -0.33243)]


def kt_step(D, d, r):
    """Peterson Kt for a shoulder step D -> d with fillet r (bending). r/d clamped to the fit's 0.002–0.3."""
    q = max(1.01, min(6.0, D / d))
    for (q0, a0, b0), (q1, a1, b1) in zip(KT_TABLE, KT_TABLE[1:]):
        if q0 <= q <= q1:
            f = (q - q0) / (q1 - q0)
            A, B = a0 + f * (a1 - a0), b0 + f * (b1 - b0)
            break
    rd = max(0.002, min(0.3, r / d))
    return max(1.0, A * rd ** B)


def lewis(Ft, b, m, Y):
    return Ft / (b * m * Y)


def grashof(links):
    s, l = min(links), max(links)
    p_q = sum(links) - s - l
    return s + l <= p_q


def grip_need(m_kg, mu, sf=2.0, a=0.0):
    return m_kg * (G + a) / (2 * mu) * sf


def trans_angle(a, b, c, d, theta_deg):
    """4-bar (crank a, coupler b, rocker c, ground d): transmission angle mu at crank angle theta, degrees"""
    e2 = a * a + d * d - 2 * a * d * math.cos(math.radians(theta_deg))
    return math.degrees(math.acos(max(-1.0, min(1.0, (b * b + c * c - e2) / (2 * b * c)))))


def leadscrew_force(tau_nmm, eta, lead_mm):
    return 2 * math.pi * tau_nmm * eta / lead_mm


def belt_teeth_in_mesh(z_small, d_small, d_big, centre):
    wrap = math.pi - 2 * math.asin((d_big - d_small) / (2 * centre))
    return z_small * wrap / (2 * math.pi)


def minjerk_alpha(dtheta_rad, T):
    return 5.774 * dtheta_rad / (T * T)


def v(x, key=None):
    """value of a {v, src} dict (or a bare number)"""
    if isinstance(x, dict):
        return x.get("v")
    return x


def s(x):
    return x.get("src") if isinstance(x, dict) else None


def lab(val, src, u="", note=None, formula=None):
    o = {"v": val, "u": u, "src": src}
    if note:
        o["note"] = note
    if formula:
        o["formula"] = formula
    return o


def round_sig(x, n=5):
    if x is None or not isinstance(x, (int, float)) or x == 0 or not math.isfinite(x):
        return x
    return round(x, n - 1 - int(math.floor(math.log10(abs(x)))))


# ===================================================================================== load + merge
def load(path):
    root = os.path.dirname(os.path.abspath(path))
    data = yaml.safe_load(open(path, encoding="utf-8"))
    cad = json.load(open(os.path.join(root, "out", "cad_facts.json")))
    sl_p = os.path.join(root, "out", "slicer_facts.json")
    slicer = json.load(open(sl_p)) if os.path.exists(sl_p) else {"parts": {}}
    tp = os.path.join(HERE, "tolerance_profile_" + data["assembly"]["printer"] + ".json")
    prof = json.load(open(tp))
    return data, cad, slicer, prof, root


def validate(data):
    """JSON-Schema validation; returns the list of MISSING required fields (path strings)."""
    missing = []
    try:
        import jsonschema
        schema = json.load(open(os.path.join(HERE, "engineering_schema_v8.json")))
        val = jsonschema.Draft202012Validator(schema)
        for e in sorted(val.iter_errors(data), key=lambda e: list(e.path)):
            where = "/".join(str(p) for p in e.path) or "(root)"
            missing.append({"path": where, "why": e.message[:160]})
    except ImportError:
        missing.append({"path": "(validator)", "why": "pip install jsonschema"})
    return missing


# ===================================================================================== tolerance
def printed_size(prof, cad, kind="hole"):
    """printed size predicted from the profile: coupon fit when measured, else the ASSUMED model"""
    if kind == "rect":
        return [c + prof["rect"]["delta"] for c in cad], prof["rect"]["src"]
    meas = [(c["cad"], c["measured"]) for c in prof.get("coupon", []) if c.get("measured") is not None]
    if len(meas) >= 2:
        meas.sort()
        ds = [(c, m - c) for c, m in meas]
        if cad <= ds[0][0]:
            d = ds[0][1]
        elif cad >= ds[-1][0]:
            d = ds[-1][1]
        else:
            for (c0, d0), (c1, d1) in zip(ds, ds[1:]):
                if c0 <= cad <= c1:
                    d = d0 + (d1 - d0) * (cad - c0) / (c1 - c0)
                    break
        return cad + d, "MEASURED"
    m = prof["model"]
    return cad + m["a"] + m["b"] / cad, m["src"]


def band_of(prof, purpose, clr):
    for b in prof["bands"][purpose]:
        lo, hi = b.get("min", -1e9), b.get("max", 1e9)
        if lo <= clr < hi:
            return {"cls": b["cls"], "label": b["label"], "color": prof["colors"][b["color"]], "tone": b["color"]}
    return {"cls": "?", "label": "?", "color": "#888888", "tone": "red"}


# ===================================================================================== model
class Model:
    """Everything the TEST slider changes, as pure functions of (kg, lever_mm, theta). engine_v8.js mirrors it."""

    def __init__(self, data, cad, slicer):
        self.d, self.cad, self.sl = data, cad, slicer
        P = {k: v(x) for k, x in data["params"].items()}
        self.P = P
        sh = cad["frames"]["shaft"]
        self.o = sh["origin"]
        self.u = cad["frames"]["arm_dir"]          # arm direction at 0° (horizontal)
        self.f = cad["frames"]["front"]            # out of the wall's front face
        mats = data["materials"]
        petg = mats["PETG"]
        self.yield_xy = v(petg["yield_xy"])
        self.zf = v(petg["z_factor"])
        self.E = v(petg["E"])
        act = data["actuators"]["sg90"]
        self.stall_nmm = v(act["stall_kgcm"]) * KGCM
        self.parts = self._mass_props()
        self.moving = set(data["joints"][0]["parts"])
        lc = data["load_cases"][0]
        self.kg0, self.lever0 = v(lc["mass"]), v(lc["lever"])
        self.secs = {x["id"]: x for x in data.get("sections", [])}
        self.fgs = {x["id"]: x for x in data.get("fastener_groups", [])}
        self.tg = data["targets"]

    # ---- mass properties: SLICER grams for printed parts, DATASHEET/ASSUMED for bought, steel density for hardware
    def _mass_props(self):
        out = {}
        dens = {k: v(m["density"]) for k, m in self.d["materials"].items() if "density" in m}
        partsd = {p["id"]: p for p in self.d["parts"]}
        for pid, f in self.cad["parts"].items():
            p = partsd.get(pid)
            vol = f["volume_mm3"]
            if p and p["kind"] == "printed":
                g = self.sl["parts"][pid]["grams"]
                src = "SLICER"
                how = f"G-code filament used ({self.sl['slicer']})"
            elif p and "mass" in p:
                g, src = v(p["mass"]), s(p["mass"])
                how = p["mass"].get("note", "")
            else:          # hardware: CAD volume × steel / brass density
                mat = "brass" if pid.startswith("ins") else "steel"
                g = vol / 1000 * dens[mat]
                src = "CALC"
                how = f"CAD volume {vol:.1f} mm³ × {mat} {dens[mat]} g/cm³"
            out[pid] = {"g": g, "src": src, "com": f["centroid"], "how": how, "vol": vol}
        return out

    def mass_of(self, pid, kg):
        return kg * 1000 if pid == "weight" else self.parts[pid]["g"]

    def com_of(self, pid, lever):
        if pid == "weight":   # the load acts at the lever arm along the arm (the slider moves it)
            u = self.u
            return [self.o[0] + lever * u[0], self.cad["frames"]["load_point"][1], self.o[2] + lever * u[2]]
        return self.parts[pid]["com"]

    def _xz(self, pid, lever):
        """(x along the arm at 0°, z up) from the joint axis"""
        c = self.com_of(pid, lever)
        d = [c[i] - self.o[i] for i in range(3)]
        return sum(d[i] * self.u[i] for i in range(3)), d[2]

    def ahead(self, y, y_ref):
        """distance IN FRONT of a plane through y_ref (front = the wall's outward normal)"""
        return (y - y_ref) * self.f[1]

    # ---- servo holding torque at angle theta (deg, + = arm up), N·mm, signed
    def tau(self, kg, lever, theta):
        t = math.radians(theta)
        n = 0.0
        for pid in self.moving:
            x, z = self._xz(pid, lever)
            n += self.mass_of(pid, kg) / 1000 * G * (x * math.cos(t) - z * math.sin(t))
        return n

    def tau_max(self, kg, lever):
        lo, hi = v(self.d["joints"][0]["limits"])
        best = 0.0
        for th in range(int(lo), int(hi) + 1):
            best = max(best, abs(self.tau(kg, lever, th)))
        return best

    def inertia(self, kg, lever):
        """about the shaft, g·mm² (parts as point masses + their own I about the axis ~ m·(bbox spread)²/12 ignored: CALC point-mass)"""
        I = 0.0
        for pid in self.moving:
            x, z = self._xz(pid, lever)
            I += self.mass_of(pid, kg) * (x * x + z * z)
        return I

    def tau_dyn(self, kg, lever):
        path = self.d["path"]
        keys, sp = path["keys"], path["speed_dps"]
        amax = 0.0
        for a, b in zip(keys, keys[1:]):
            dth = math.radians(abs(b - a))
            T = abs(b - a) / sp
            amax = max(amax, minjerk_alpha(dth, T))
        I_kgm2 = self.inertia(kg, lever) * 1e-9
        return I_kgm2 * amax * 1000, amax          # N·mm, rad/s²

    # ---- sections
    def arm_root(self, kg, lever, r=None):
        S = self.secs["arm_root"]
        x = self.cad["frames"]["arm_root"]["x_from_shaft"]
        d, t, D = v(S["d"]), v(S["t"]), v(S["D"])
        r = v(S["r"]) if r is None else r
        F = kg * G
        # arm self-weight outboard of the root acts at its centroid (conservative: whole arm mass)
        xa, _ = self._xz("arm", lever)
        M = F * max(0.0, lever - x) + self.parts["arm"]["g"] / 1000 * G * max(0.0, xa - x)
        V = F + self.parts["arm"]["g"] / 1000 * G
        I = t * d ** 3 / 12
        c = d / 2
        sig = M * c / I
        kt = kt_step(D, d, r)
        tau = 1.5 * V / (t * d)
        vm = math.sqrt((kt * sig) ** 2 + 3 * tau ** 2)
        sf = self.yield_xy / vm if vm > 0 else float("inf")
        return {"M": M, "V": V, "I": I, "c": c, "sigma": sig, "kt": kt, "tau": tau, "vm": vm, "sf": sf, "x": x, "r": r}

    def hanging(self, kg, lever):
        """everything the wall carries: (mass g, y) list"""
        out = []
        for pid in list(self.moving) + ["servo", "tab0", "tab1"]:
            out.append((self.mass_of(pid, kg), self.com_of(pid, lever)[1]))
        return out

    def wall_root(self, kg, lever):
        S = self.secs["wall_root"]
        b, h, ym = v(S["b"]), v(S["h"]), v(S["y_mid"])
        M = sum(m / 1000 * G * self.ahead(y, ym) for m, y in self.hanging(kg, lever))
        I = b * h ** 3 / 12
        sig = abs(M) * (h / 2) / I
        kt = v(S["kt_bound"])
        vm = kt * sig
        strength = self.yield_xy * self.zf
        return {"M": M, "I": I, "sigma": sig, "kt": kt, "vm": vm, "sf": strength / vm if vm > 0 else float("inf"), "strength": strength}

    def tab_screws(self, kg, lever):
        S = self.fgs["tab_screws"]
        # the servo body sits behind the wall: only what hangs IN FRONT of the tabs pulls them off
        Mx = sum(m / 1000 * G * self.ahead(y, v(S["y_wall"])) for m, y in self.hanging(kg, lever) if self.ahead(y, v(S["y_wall"])) > 0)
        F = max(0.0, Mx) / (v(S["n"]) * v(S["lever"]))
        tau = F / (math.pi * v(S["d"]) * v(S["Le"]) * 0.5)
        allow = 0.577 * self.yield_xy * self.zf
        return {"Mx": Mx, "F": F, "tau": tau, "allow": allow, "sf": allow / tau if tau > 0 else float("inf")}

    def inserts(self, kg, lever):
        S = self.fgs["inserts"]
        Mt = sum(m / 1000 * G * self.ahead(y, v(S["y_edge"])) for m, y in self.hanging(kg, lever) if self.ahead(y, v(S["y_edge"])) > 0)
        F = max(0.0, Mt) / (v(S["n"]) * v(S["arm"]))
        return {"M": Mt, "F": F, "limit": v(S["limit"])}

    def deflection(self, kg, lever):
        S = self.secs["arm_root"]
        x = self.cad["frames"]["arm_root"]["x_from_shaft"]
        L = max(0.0, lever - x)
        I = self.P["arm_t"] * v(S["d"]) ** 3 / 12
        return kg * G * L ** 3 / (3 * self.E * I)

    def at(self, kg=None, lever=None):
        kg = self.kg0 if kg is None else kg
        lever = self.lever0 if lever is None else lever
        th = self.tau_max(kg, lever)
        td, amax = self.tau_dyn(kg, lever)
        ar = self.arm_root(kg, lever)
        arf = self.arm_root(kg, lever, r=v(self.secs["arm_root"]["r_fix"]))
        # the bracket must outlive the servo: arm stress when the load is whatever the servo can hold at stall
        kg_stall = self.kg_at_stall(lever)
        ars = self.arm_root(kg_stall, lever)
        return {"kg": kg, "lever": lever, "tau_hold": th, "frac_hold": th / self.stall_nmm, "tau_dyn": td, "alpha": amax,
                "frac_dyn": (th + td) / self.stall_nmm, "arm": ar, "arm_fix": arf, "wall": self.wall_root(kg, lever),
                "tabs": self.tab_screws(kg, lever), "inserts": self.inserts(kg, lever), "defl": self.deflection(kg, lever),
                "kg_stall": kg_stall, "arm_at_stall": ars}

    def kg_at_stall(self, lever):
        lo, hi = 0.0, 50.0
        for _ in range(60):
            mid = (lo + hi) / 2
            if self.tau_max(mid, lever) > self.stall_nmm:
                hi = mid
            else:
                lo = mid
        return lo

    def kg_break_arm(self, lever, r=None):
        lo, hi = 0.0, 100.0
        for _ in range(60):
            mid = (lo + hi) / 2
            if self.arm_root(mid, lever, r)["sf"] < 1.0:
                hi = mid
            else:
                lo = mid
        return lo


# ===================================================================================== checks
def status_of(would, inputs):
    assumed = [i["k"] for i in inputs if i.get("src") == "ASSUMED"]
    if would == "na":
        return "na"
    if would == "fail":
        return "fail"
    if assumed:
        return "unverified"
    return would


def check(cid, group, label, value, limit, unit, rule, inputs, formula, where=None, note=None, cmp="le"):
    """cmp: le -> value <= limit passes; ge -> value >= limit passes"""
    if rule == "na":
        would = "na"
    elif value is None or limit is None:
        would = "unverified"
    elif cmp == "le":
        would = "pass" if value <= limit else ("warn" if value <= limit * 1.4 else "fail")
    else:
        would = "pass" if value >= limit else ("warn" if value >= limit * 0.7 else "fail")
    st = status_of(would, inputs)
    if value is None or limit is None:
        st = "na" if rule == "na" else "unverified"
    return {"id": cid, "group": group, "label": label, "value": round_sig(value), "limit": round_sig(limit), "unit": unit,
            "status": st, "would": would, "cmp": cmp, "inputs": inputs, "formula": formula, "src": "CALC",
            "assumed": [i["k"] for i in inputs if i.get("src") == "ASSUMED"], "where": where, "note": note or ""}


def inp(k, val, u, src):
    return {"k": k, "v": round_sig(val) if isinstance(val, (int, float)) else val, "u": u, "src": src}


def compute(path):
    data, cad, slicer, prof, root = load(path)
    missing = validate(data)
    M = Model(data, cad, slicer)
    P, pd = data["params"], data
    petg = data["materials"]["PETG"]
    act = data["actuators"]["sg90"]
    tg = data["targets"]
    R = M.at()
    fr = cad["frames"]
    ARMP = fr["arm_root"]["point"]
    WALLP = fr["wall_root"]["point"]
    checks = []

    m_in = lambda pid: inp(f"mass {pid}", M.parts[pid]["g"], "g", M.parts[pid]["src"])
    load_in = [inp("load mass", R["kg"], "kg", "SPEC"), inp("lever arm", R["lever"], "mm", "SPEC")]
    stall_in = inp("SG90 stall", v(act["stall_kgcm"]), "kgf·cm", s(act["stall_kgcm"]))
    # ---- actuators
    checks.append(check("torque_hold", "Actuator", "Holding torque vs SG90 stall (worst pose)", R["frac_hold"] * 100, v(tg["hold_frac"]) * 100, "% stall", "le",
                        load_in + [m_in("arm"), m_in("horn"), stall_in],
                        "τ = g·Σ mᵢ·(xᵢ cosθ − zᵢ sinθ), max over the joint range; ÷ stall", where=fr["shaft"]["origin"]))
    checks.append(check("torque_dyn", "Actuator", "Hold + I·α on the TEST sweep", R["frac_dyn"] * 100, v(tg["dyn_frac"]) * 100, "% stall", "le",
                        load_in + [m_in("arm"), m_in("horn"), stall_in, inp("peak α (min-jerk)", R["alpha"], "rad/s²", "CALC")],
                        "α = 5.774·Δθ/T² ; τ = I·α, I = Σ m r² ; (τ_hold + τ_dyn) ÷ stall", where=fr["shaft"]["origin"]))
    # ---- structure
    ar = R["arm"]
    checks.append(check("sf_arm", "Structure", "Arm root safety factor (XY, Kt sharp)", ar["sf"], v(tg["sf_xy"]), "", "ge",
                        load_in + [inp("PETG yield XY", M.yield_xy, "MPa", s(petg["yield_xy"])), inp("Kt (r 0.2)", ar["kt"], "", "CALC"),
                                   inp("t at root", v(M.secs["arm_root"]["t"]), "mm", "CAD")],
                        "σ = Kt·M·c/I, I = t·d³/12 ; τ = 1.5·V/A ; σ_vm = √(σ² + 3τ²) ; SF = yield / σ_vm", where=ARMP, cmp="ge"))
    ars = R["arm_at_stall"]
    checks.append(check("sf_arm_stall", "Structure", "Bracket outlives the servo: arm SF at SG90 stall", ars["sf"], 1.0, "", "ge",
                        [stall_in, inp("load at stall", R["kg_stall"], "kg", "CALC"), inp("PETG yield XY", M.yield_xy, "MPa", s(petg["yield_xy"]))],
                        "the heaviest load the servo can hold (τ = stall) → arm-root σ_vm → SF must stay > 1", where=ARMP, cmp="ge"))
    wr = R["wall"]
    checks.append(check("sf_wall", "Structure", "Cradle wall root SF (Z — layers pulled apart)", wr["sf"], v(tg["sf_z"]), "", "ge",
                        load_in + [m_in("servo"), inp("PETG yield XY", M.yield_xy, "MPa", s(petg["yield_xy"])), inp("Z factor", M.zf, "", s(petg["z_factor"])),
                                   inp("Kt bound", wr["kt"], "", "ASSUMED")],
                        "σ = Kt·M·c/I, M = Σ m·g·(y − y_mid), I = b·h³/12 ; SF = z·yield / σ", where=WALLP, cmp="ge"))
    tb = R["tabs"]
    checks.append(check("sf_tabs", "Fasteners", "Servo tab screws — thread strip SF", tb["sf"], v(tg["sf_z"]), "", "ge",
                        load_in + [inp("pivot lever", v(M.fgs["tab_screws"]["lever"]), "mm", "ASSUMED"), inp("PETG yield XY", M.yield_xy, "MPa", s(petg["yield_xy"])),
                                   inp("engagement", v(M.fgs["tab_screws"]["Le"]), "mm", "CAD")],
                        "F = Mₓ/(n·lever) ; τ = F/(π·d·Le·0.5) ; allow = 0.577·z·yield", where=cad["fasteners"]["tab0"]["at"], cmp="ge"))
    ins = R["inserts"]
    checks.append(check("insert_pull", "Fasteners", "M3 insert pull-out load (each)", ins["F"], ins["limit"], "N", "le",
                        load_in + [inp("pull-out limit", None, "N", "ASSUMED")],
                        "F = Σ m·g·(y − y_edge)/(n·arm), tipping about the foot front edge", where=cad["fasteners"]["m3a"]["at"],
                        note="no pull-out data — test boss on MEASURE_ME"))
    checks.append(check("defl", "Structure", "Arm sag at the load", R["defl"], v(tg["defl_max"]), "mm", "le",
                        load_in + [inp("PETG E", M.E, "MPa", s(petg["E"]))], "δ = F·L³/(3·E·I)", where=fr["load_point"]))
    tgc = v(petg["tg"])
    checks.append(check("temp", "Material", "Operating temp below Tg − 20 °C", v(tg["temp_op"]), tgc - 20, "°C", "le",
                        [inp("operating", v(tg["temp_op"]), "°C", "SPEC"), inp("PETG Tg", tgc, "°C", s(petg["tg"]))],
                        "T_op ≤ Tg − 20 °C (PETG: no creep flag; PLA under constant load would be)"))
    # ---- electrical
    sup = data["supply"]
    checks.append(check("psu", "Electrical", "Σ stall currents vs 80 % of the supply", v(act["stall_a"]), 0.8 * v(sup["amps"]), "A", "le",
                        [inp("SG90 stall current", v(act["stall_a"]), "A", s(act["stall_a"])), inp("supply", v(sup["amps"]), "A", s(sup["amps"]))],
                        "Σ I_stall ≤ 0.8 · I_supply", note="MB-V2 breadboard module (0.7 A) rejected: one stall eats it"))
    # ---- geometry / DFM (CAD + DATASHEET only -> can PASS for real)
    ii = cad["insert"]
    checks.append(check("insert_cover", "Print / DFM", "Plastic over the insert bore", ii["cover"], 1.4, "mm", "ge",
                        [inp("cover", ii["cover"], "mm", "CAD"), inp("rule", 1.4, "mm", "DATASHEET")], "foot top − (base top + bore depth) ≥ 1.4 (/sp-print-dfm)", cmp="ge",
                        where=cad["features"]["bore_a"]["at"]))
    checks.append(check("insert_engage", "Print / DFM", "M3 thread engagement in the insert", ii["engagement_m3"], 1.5 * 3.0, "mm", "ge",
                        [inp("engagement", ii["engagement_m3"], "mm", "CAD"), inp("rule 1.5·d", 4.5, "mm", "DATASHEET")], "seat + length − insert start ≥ 1.5·d", cmp="ge"))
    checks.append(check("insert_tip", "Print / DFM", "M3 tip clear of the bore end", ii["tip_gap"], 0.0, "mm", "ge",
                        [inp("tip gap", ii["tip_gap"], "mm", "CAD")], "bore end − screw tip > 0", cmp="ge"))
    pw = printed_size(prof, [v(P["sg90_body_l"]) + 2 * v(P["window_clear"]), 1.0], "rect")[0][0]
    pp, ppsrc = printed_size(prof, v(P["pilot_d"]))
    lig_p = v(P["sg90_hole_pitch"]) / 2 - pw / 2 - pp / 2
    checks.append(check("ligament", "Print / DFM", "Tab-hole ligament as printed (CAD " + str(cad["ligament"]) + " mm)", round(lig_p, 4), 1.6, "mm", "ge",
                        [inp("CAD ligament", cad["ligament"], "mm", "CAD"), inp("SG90 hole pitch", v(P["sg90_hole_pitch"]), "mm", "ASSUMED"),
                         inp("hole shrink (profile)", round(v(P["pilot_d"]) - pp, 3), "mm", ppsrc), inp("min wall", 1.6, "mm", "DATASHEET")],
                        "pitch/2 − printed window/2 − printed pilot/2 ≥ 1.60", cmp="ge", where=cad["features"]["pilot0"]["at"],
                        note="CAD alone reads below 1.60 — D4"))
    checks.append(check("sweep", "Motion", "Full-range sweep collisions (−90…+90°)", len(cad["dfm"]["sweep_clashes"]), 0, "hits", "le",
                        [inp("sweep step", 5, "°", "SPEC"), inp("CAD booleans", len(cad["dfm"]["sweep_clashes"]), "", "CAD")],
                        "moving set rotated every 5°, booleaned against every static part"))
    env_ok = all(e["fits"] for e in cad["dfm"]["envelope"].values())
    checks.append(check("envelope", "Print / DFM", "Every printed part fits 220×220×270", 0 if env_ok else 1, 0, "too big", "le",
                        [inp("bed", "220×220×270", "mm", "DATASHEET")], "sorted extents ≤ sorted bed"))
    # ---- mechanisms this design does not have -> N/A tiles (the formulas still live in the engine; verify unit-tests them)
    for cid, label, formula in [("lewis", "Gear tooth bending (Lewis)", "σ = Fₜ/(b·m·Y) ≤ Z strength / 2"),
                                ("grashof", "Linkage Grashof", "s + l ≤ p + q"),
                                ("trans_angle", "Linkage transmission angle", "40° ≤ μ ≤ 140° over the travel"),
                                ("grip", "Grip force", "N ≥ m·g/(2μ) × 2"),
                                ("belt", "Belt teeth in mesh", "≥ 6 teeth"),
                                ("leadscrew", "Leadscrew force", "F = 2π·τ·η / lead"),
                                ("spring", "Spring below solid height", "F = k·x at every pose"),
                                ("prismatic", "Slide anti-racking", "L/W ≥ 1.5 and drive > μ·N")]:
        checks.append(check(cid, "Mechanisms", label, None, None, "", "na", [], formula, note="N/A — no such mechanism in v1"))

    # ---- fits + stack-ups
    fits = []
    for f in data["fits"]:
        fe = cad["features"][f["id"]]
        kind = f["kind"]
        printed, psrc = printed_size(prof, f["cad"], kind)
        if kind == "rect":
            clr = min(p - m for p, m in zip(printed, f["mate_size"])) / 1.0
        else:
            clr = printed - f["mate_size"]
        b = band_of(prof, f["purpose"], clr)
        fits.append({"id": f["id"], "part": f["part"], "label": f["label"], "kind": kind, "at": fe["at"], "axis": fe["axis"],
                     "cad": lab(f["cad"], "CAD", "mm"), "printed": lab([round(x, 3) for x in printed] if kind == "rect" else round(printed, 3), "CALC", "mm",
                                                                       formula=("cad + rect delta" if kind == "rect" else "cad + a + b/cad (profile)") + f" — profile {psrc}"),
                     "comp_src": psrc, "measured": lab(None, "MEASURED", "mm"), "mate": f["mate"], "mate_size": lab(f["mate_size"], f["mate_src"], "mm"),
                     "clearance": lab(round(clr, 3), "CALC", "mm"), "purpose": f["purpose"], "band": b,
                     "size": fe.get("size"), "d": fe.get("d")})
    stack = []
    for st in data["stackups"]:
        nom = sum(l["nominal"] * l["sign"] for l in st["links"])
        wc = sum(abs(l["t"]) for l in st["links"])
        rss = math.sqrt(sum(l["t"] ** 2 for l in st["links"]))
        eats = max(st["links"], key=lambda l: abs(l["t"]))
        w = st["want"]
        ok_wc = nom - wc >= w["min"] and nom + wc <= w["max"]
        ok_rss = nom - rss >= w["min"] and nom + rss <= w["max"]
        inputs = [inp(l["name"], l["nominal"], "mm", l["src"]) for l in st["links"]]
        stack.append({"id": st["id"], "label": st["label"], "nominal": round(nom, 4), "worst": [round(nom - wc, 4), round(nom + wc, 4)],
                      "rss": [round(nom - rss, 4), round(nom + rss, 4)], "eats": eats["name"], "eats_t": eats["t"],
                      "links": st["links"], "want": w, "ok_worst": ok_wc, "ok_rss": ok_rss})
        checks.append(check("stack_" + st["id"], "Fits", "Stack-up: " + st["label"] + " (worst case)", round(nom - wc, 4), w["min"], "mm min", "ge",
                            inputs, "worst = nominal − Σ|tᵢ| ; RSS = nominal − √Σtᵢ²", cmp="ge"))

    # ---- ranking at the default load (the AV re-ranks live)
    rank = rank_at(M, R, cad)

    # ---- per-part display data with source labels
    partsd = {p["id"]: p for p in data["parts"]}
    eparts = {}
    for pid, mp in M.parts.items():
        p = partsd.get(pid, {})
        f = cad["parts"][pid]
        e = {"name": p.get("name", pid), "kind": p.get("kind", "hardware"), "material": p.get("material"),
             "mass": lab(round(mp["g"], 3), mp["src"], "g", note=mp["how"]),
             "com": lab(mp["com"], "CALC", "mm", note="CAD centroid (uniform-density approximation)"),
             "volume": lab(f["volume_mm3"], "CAD", "mm³"), "area": lab(f["area_mm2"], "CAD", "mm²"),
             "bbox": lab([[round(a, 2) for a in f["bbox"][0]], [round(a, 2) for a in f["bbox"][1]]], "CAD", "mm")}
        if pid in slicer["parts"]:
            sp = slicer["parts"][pid]
            e["slicer"] = {"grams": lab(sp["grams"], "SLICER", "g"), "time_min": lab(round(sp["time_s"] / 60, 1), "SLICER", "min"),
                           "layers": lab(sp["layers"], "SLICER", ""), "slicer": slicer["slicer"]}
        if p.get("print"):
            e["print"] = {k: {"v": x["v"], "u": x.get("u", ""), "src": x["src"], "why": x.get("why")} for k, x in p["print"].items()}
        if p.get("measured_mass"):
            e["measured_mass"] = p["measured_mass"]
        if p.get("material") and p["material"] in data["materials"]:
            mt = data["materials"][p["material"]]
            e["mat"] = {k: mt[k] for k in mt if isinstance(mt[k], dict)}
        eparts[pid] = e

    measure = measure_list(data, checks, fits)
    model = {
        "g": G, "kgcm": KGCM, "stall_nmm": M.stall_nmm, "yield_xy": M.yield_xy, "z_factor": M.zf, "E": M.E,
        "shaft": cad["frames"]["shaft"], "arm_dir": fr["arm_dir"], "front": fr["front"], "load_point": fr["load_point"], "arm_root": fr["arm_root"], "wall_root": fr["wall_root"],
        "limits": v(data["joints"][0]["limits"]), "moving": sorted(M.moving),
        "masses": {pid: {"g": mp["g"], "com": mp["com"]} for pid, mp in M.parts.items()},
        "sections": {k: {kk: (v(x) if isinstance(x, dict) else x) for kk, x in S.items()} for k, S in M.secs.items()},
        "fgs": {k: {kk: (v(x) if isinstance(x, dict) else x) for kk, x in S.items()} for k, S in M.fgs.items()},
        "kt_table": KT_TABLE, "path": data["path"], "targets": {k: v(x) for k, x in tg.items()},
        "kg": {"v": M.kg0, "min": 0.0, "max": 5.0, "step": 0.01}, "lever": {"v": M.lever0, "min": 10.0, "max": v(P["arm_len"]), "step": 0.5},
        "arm_t_full": v(P["arm_t"]),
        "break_kg": {"sharp": M.kg_break_arm(M.lever0), "fillet": M.kg_break_arm(M.lever0, v(M.secs["arm_root"]["r_fix"]))},
    }
    eng = {
        "schema": "sp-eng-v8", "assembly": data["assembly"], "sources": SRC_INFO, "missing": missing,
        "parts": eparts, "materials": data["materials"], "actuators": data["actuators"], "supply": data["supply"],
        "fasteners": data["fasteners"], "inserts": data.get("inserts", []), "joints": data["joints"], "targets": tg,
        "load_cases": data["load_cases"], "electronics": data.get("electronics"), "printers": data["printers"],
        "fits": fits, "stackups": stack, "checks": checks, "ranking": rank, "measure": measure, "model": model,
        "tolerance": {"profile": prof["printer"] + " · " + prof["material"], "src": prof["src"], "status": prof["status"],
                      "bands": prof["bands"], "colors": prof["colors"], "model": prof["model"], "rect": prof["rect"],
                      "coupon": prof["coupon"], "why": prof["why"]},
        "slicer": {"name": slicer.get("slicer"), "printer": slicer.get("printer"), "print": slicer.get("print"), "filament": slicer.get("filament")},
        "dfm": {"pass": cad["dfm"]["pass"], "designed": cad["dfm"]["designed_contacts"], "clashes": cad["dfm"]["clashes_at_rest"],
                "sweep": cad["dfm"]["sweep_clashes"], "envelope": cad["dfm"]["envelope"]},
        "at_default": summarize(R),
    }
    return eng, M


def summarize(R):
    return {"kg": R["kg"], "lever": R["lever"], "tau_hold_nmm": round_sig(R["tau_hold"]), "frac_hold": round_sig(R["frac_hold"]),
            "tau_dyn_nmm": round_sig(R["tau_dyn"]), "frac_dyn": round_sig(R["frac_dyn"]), "alpha": round_sig(R["alpha"]),
            "arm_sigma": round_sig(R["arm"]["sigma"]), "arm_kt": round_sig(R["arm"]["kt"]), "arm_vm": round_sig(R["arm"]["vm"]),
            "arm_sf": round_sig(R["arm"]["sf"]), "arm_sf_fix": round_sig(R["arm_fix"]["sf"]), "arm_kt_fix": round_sig(R["arm_fix"]["kt"]),
            "wall_sigma": round_sig(R["wall"]["sigma"]), "wall_sf": round_sig(R["wall"]["sf"]), "tab_F": round_sig(R["tabs"]["F"]),
            "tab_sf": round_sig(R["tabs"]["sf"]), "insert_F": round_sig(R["inserts"]["F"]), "defl": round_sig(R["defl"]),
            "kg_stall": round_sig(R["kg_stall"]), "arm_sf_at_stall": round_sig(R["arm_at_stall"]["sf"])}


def rank_at(M, R, cad):
    fr = cad["frames"]
    items = [
        {"id": "servo", "label": "SG90 stalls (torque)", "sf": M.stall_nmm / max(1e-9, R["tau_hold"]), "where": fr["shaft"]["origin"], "part": "servo",
         "how": "stall ÷ holding torque", "src": "DATASHEET"},
        {"id": "arm", "label": "Arm root snaps (bending, sharp step)", "sf": R["arm"]["sf"], "where": fr["arm_root"]["point"], "part": "arm",
         "how": "yield ÷ σ_vm with Kt", "src": "CALC", "fix": {"r": R["arm_fix"]["r"], "kt_before": R["arm"]["kt"], "kt_after": R["arm_fix"]["kt"],
                                                             "sf_after": R["arm_fix"]["sf"]}},
        {"id": "wall", "label": "Cradle wall root peels (Z)", "sf": R["wall"]["sf"], "where": fr["wall_root"]["point"], "part": "cradle",
         "how": "z·yield ÷ Kt·σ", "src": "CALC"},
        {"id": "tabs", "label": "Tab screws strip out", "sf": R["tabs"]["sf"], "where": cad["fasteners"]["tab0"]["at"], "part": "tab0",
         "how": "0.577·z·yield ÷ thread shear", "src": "CALC"},
    ]
    items.sort(key=lambda x: x["sf"])
    for it in items:
        it["sf"] = round_sig(it["sf"], 4)
    items.append({"id": "inserts", "label": "M3 inserts pull out", "sf": None, "where": cad["fasteners"]["m3a"]["at"], "part": "ins_a",
                  "how": f"{R['inserts']['F']:.2f} N each — no pull-out data", "src": "ASSUMED"})
    return items


MEASURE_HOW = {
    "sg90_": ("calipers", "every SG90 dimension — body L × W × H, tab span, hole pitch, tab height, shaft offset"),
    "PETG": ("datasheet / tensile coupon", "spool brand → its datasheet (or print + pull a dog-bone in XY and Z)"),
    "stall": ("bench test", "SG90 stall torque at 5 V: lever + luggage scale, and stall current with a USB meter"),
    "mass": ("kitchen scale (0.1 g)", "weigh each printed part and the horn"),
    "pivot": ("calipers", "tab edge to screw centre on the real SG90"),
    "Kt": ("design", "keep — or model the fillet and run FreeCAD FEM (CalculiX) offline"),
    "pull-out": ("test boss", "hang weights off an M3 insert in a PETG test boss until it lets go"),
    "supply": ("label", "read the wall adapter's label (V, A)"),
    "coupon": ("calipers", "print the hole coupon, measure 9 holes"),
}


def measure_list(data, checks, fits):
    """every ASSUMED input that blocks a PASS, grouped, sorted by how many checks it unlocks"""
    rows = {}
    def add(key, what, tool, unlocks):
        r = rows.setdefault(key, {"what": what, "tool": tool, "unlocks": set()})
        r["unlocks"] |= set(unlocks)
    for c in checks:
        for k in c["assumed"]:
            if "prints smaller" in k or k.startswith("printer comp") or k.startswith("hole shrink"):
                add("coupon", MEASURE_HOW["coupon"][1], MEASURE_HOW["coupon"][0], [c["id"]])
            elif "SG90" in k and "stall" not in k:
                add("sg90", MEASURE_HOW["sg90_"][1], MEASURE_HOW["sg90_"][0], [c["id"]])
            elif k.startswith("SG90"):
                if "stall current" in k:
                    add("stall_a", "SG90 stall current at 5 V", "USB power meter", [c["id"]])
                elif "stall" in k:
                    add("stall", MEASURE_HOW["stall"][1], MEASURE_HOW["stall"][0], [c["id"]])
                else:
                    add("sg90", MEASURE_HOW["sg90_"][1], MEASURE_HOW["sg90_"][0], [c["id"]])
            elif k.startswith("PETG") or k == "Z factor":
                add("petg", MEASURE_HOW["PETG"][1], MEASURE_HOW["PETG"][0], [c["id"]])
            elif k.startswith("mass"):
                add("mass", MEASURE_HOW["mass"][1], MEASURE_HOW["mass"][0], [c["id"]])
            elif k.startswith("pivot"):
                add("pivot", MEASURE_HOW["pivot"][1], MEASURE_HOW["pivot"][0], [c["id"]])
            elif k.startswith("Kt"):
                add("kt", MEASURE_HOW["Kt"][1], MEASURE_HOW["Kt"][0], [c["id"]])
            elif "pull-out" in k:
                add("pullout", MEASURE_HOW["pull-out"][1], MEASURE_HOW["pull-out"][0], [c["id"]])
            elif k == "supply":
                add("supply", MEASURE_HOW["supply"][1], MEASURE_HOW["supply"][0], [c["id"]])
            else:
                add(k, k, "?", [c["id"]])
    if any(f["comp_src"] == "ASSUMED" for f in fits):
        add("coupon", MEASURE_HOW["coupon"][1], MEASURE_HOW["coupon"][0], ["fit:" + f["id"] for f in fits])
    for p in data["parts"]:
        if p.get("measured_mass") and p["measured_mass"].get("v") is None:
            add("mass", MEASURE_HOW["mass"][1], MEASURE_HOW["mass"][0], ["mass:" + p["id"]])
    out = [{"key": k, "what": r["what"], "tool": r["tool"], "unlocks": sorted(r["unlocks"]), "n": len(r["unlocks"])} for k, r in rows.items()]
    out.sort(key=lambda r: -r["n"])
    return out


def write_measure_md(eng, path):
    L = ["# MEASURE_ME — what to put calipers / a scale on (AV v8, auto-generated)", "",
         f"Assembly: **{eng['assembly']['name']}**. Sorted by blast radius: the top row unlocks the most checks.",
         "Every row is an `ASSUMED` number that keeps a check at UNVERIFIED. Measure → put the value in the YAML with",
         "`src: MEASURED` → rebuild → the tile turns PASS (or FAIL, which is the point).", "",
         "| # | measure | tool | unlocks | checks |", "|---|---|---|---|---|"]
    for i, r in enumerate(eng["measure"], 1):
        L.append(f"| {i} | {r['what']} | {r['tool']} | {r['n']} | {', '.join(r['unlocks'][:8])}{' …' if len(r['unlocks']) > 8 else ''} |")
    L += ["", "## Calipers list (take this to the bench)", ""]
    for i, r in enumerate([r for r in eng["measure"] if r["tool"].startswith("calipers")], 1):
        L.append(f"{i}. {r['what']}")
    open(path, "w", encoding="utf-8").write("\n".join(L) + "\n")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    eng, M = compute(sys.argv[1])
    arg = lambda k: sys.argv[sys.argv.index(k) + 1] if k in sys.argv else None
    out = arg("--out") or os.path.join(os.path.dirname(os.path.abspath(sys.argv[1])), "out", "eng.json")
    json.dump(eng, open(out, "w"), indent=1, default=lambda o: sorted(o) if isinstance(o, set) else str(o))
    if arg("--measure"):
        write_measure_md(eng, arg("--measure"))
    print(json.dumps(eng["at_default"], indent=1))
    print("checks:", {k: sum(1 for c in eng["checks"] if c["status"] == k) for k in ("pass", "warn", "fail", "unverified", "na")})
    print("missing:", eng["missing"])
    for r in eng["ranking"]:
        print(f"  {r['label']:40s} SF {r['sf']}")
