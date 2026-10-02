"""Static sag at the tool under the 1.5 kg hold (rule: <= 1 mm, Prompt A Phase 2). Rigid-body sims can't see this.

Run: python sim/stiffness.py  -> appended to sim/SIM_REPORT.md by sim/sim_check.py
Model: column = cantilever from the X carriage carrying the arm's moment; upper arm + forearm = cantilevers
loaded by everything outboard. Bearings, wheels and printed-joint compliance are NOT included (they add more),
so treat the result as a lower bound. Section properties computed here; material E values are ASSUMED.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "cad"))
from params import L1, L2  # noqa: E402

G = 9.81
PAY, HAND, W_MOTOR, FOREARM, ELBOW = 1.5, 0.30, 0.35, 0.25, 0.25    # kg (hand body+jaws printed ~0.3 at 45 % infill)
MANDREL = 0.06
E = {"PETG": 2.0e9, "PETG-CF": 4.5e9, "aluminium": 69e9}            # Pa, ASSUMED (printed E along the layers)
COLUMN_I = {"2040 V-slot, bending about its 20 mm side (lean BOM as drawn)": 0.70e-8,
            "2040 V-slot turned 90° (40 mm side toward the printers)": 2.77e-8,
            "4040 V-slot": 6.9e-8, "4080 V-slot strong side": 42e-8}                                    # m^4, ASSUMED catalogue values -> verify
SHOULDER_H = 0.40                                                    # m from the X carriage to the shoulder (plate pose)


def u_channel(b, h, t):
    """Open-bottom U: top web b×t + two side walls t×(h-t). Returns I about the horizontal centroid axis (m^4)."""
    a1, y1 = b * t, t / 2
    a2, y2 = 2 * t * (h - t), t + (h - t) / 2
    yb = (a1 * y1 + a2 * y2) / (a1 + a2)
    i = b * t ** 3 / 12 + a1 * (yb - y1) ** 2 + 2 * t * (h - t) ** 3 / 12 + a2 * (yb - y2) ** 2
    return i * 1e-12


def closed_box(b, h, t):
    return (b * h ** 3 - (b - 2 * t) * (h - 2 * t) ** 3) / 12 * 1e-12


def sag(EI_ua, EI_fa, EI_col):
    """Vertical deflection at the payload (m), arm stretched horizontally."""
    l1, l2 = L1 / 1000, L2 / 1000
    # forearm cantilever from the elbow: payload at l2+mandrel, hand at l2, own weight at l2/2
    Fp, Fh, Ff = PAY * G, (HAND + W_MOTOR * 0) * G, FOREARM * G
    a = l2 + MANDREL
    d_fa = Fp * a ** 3 / (3 * EI_fa) + Fh * l2 ** 3 / (3 * EI_fa) + Ff * (l2 / 2) ** 2 * (3 * a - l2 / 2) / (6 * EI_fa)
    # upper arm: shear + moment from the forearm at its tip, rotation carries to the payload
    F_tip = (PAY + HAND + W_MOTOR + FOREARM + ELBOW) * G
    M_tip = (PAY * a + HAND * l2 + FOREARM * l2 / 2 - W_MOTOR * 0.045) * G
    d_ua = F_tip * l1 ** 3 / (3 * EI_ua) + M_tip * l1 ** 2 / (2 * EI_ua)
    th_ua = F_tip * l1 ** 2 / (2 * EI_ua) + M_tip * l1 / EI_ua
    # column: the whole arm's moment at the shoulder tilts it
    M_sh = M_tip + F_tip * l1 + 0.45 * G * l1 / 2
    th_col = M_sh * SHOULDER_H / EI_col
    reach = l1 + a
    return {"forearm bend": d_fa, "upper-arm bend": d_ua + th_ua * a, "column tilt": th_col * reach}


def report():
    rows = []
    cases = [
        ("Lean as drawn: U-channel 50×36×3.2 PETG, 2040 column on its weak side",
         E["PETG"] * u_channel(50, 36, 3.2), E["PETG"] * u_channel(44, 36, 3.2),
         E["aluminium"] * list(COLUMN_I.values())[0]),
        ("Same arm, 2040 turned 90°", E["PETG"] * u_channel(50, 36, 3.2), E["PETG"] * u_channel(44, 36, 3.2),
         E["aluminium"] * list(COLUMN_I.values())[1]),
        ("Closed box (cover screwed + glued) 50×36, PETG-CF, 4040 column",
         E["PETG-CF"] * closed_box(50, 36, 3.2), E["PETG-CF"] * closed_box(44, 36, 3.2), E["aluminium"] * 6.9e-8),
        ("**Fix: closed box 50×60 ×3.2 PETG-CF + 20×20×1.5 alu spine, 4040 column**",
         E["PETG-CF"] * closed_box(50, 60, 3.2) + E["aluminium"] * (20 ** 4 - 17 ** 4) / 12 * 1e-12,
         E["PETG-CF"] * closed_box(44, 50, 3.2) + E["aluminium"] * (20 ** 4 - 17 ** 4) / 12 * 1e-12,
         E["aluminium"] * 6.9e-8),
        ("**Fix B (plain PETG, PICK): upper arm closed box 50×60 + 2× 25×25×2 alu tubes stacked; forearm 44×50 + 1× 20×20×1.5; 4080 column**",
         E["PETG"] * closed_box(50, 60, 3.2) + E["aluminium"] * (2 * (25 ** 4 - 21 ** 4) / 12 + 2 * (25 ** 2 - 21 ** 2) * 12.5 ** 2) * 1e-12,
         E["PETG"] * closed_box(44, 50, 3.2) + 2 * E["aluminium"] * (20 ** 4 - 17 ** 4) / 12 * 1e-12,
         E["aluminium"] * 42e-8),
    ]
    out = ["## Static sag at the tool, 1.5 kg held at full reach (rule ≤ 1 mm)\n",
           "Beam theory, joints/bearings/wheels assumed rigid (real sag is higher). E: PETG 2.0 GPa, PETG-CF 4.5 GPa, "
           "aluminium 69 GPa; V-slot inertias from catalogue values (verify).\n",
           "| Build | Forearm | Upper arm | Column tilt | **Total** | ≤ 1 mm? |", "|---|---|---|---|---|---|"]
    for name, ua, fa, col in cases:
        d = sag(ua, fa, col)
        tot = sum(d.values()) * 1000
        out.append(f"| {name} | {d['forearm bend']*1000:.2f} | {d['upper-arm bend']*1000:.2f} | {d['column tilt']*1000:.2f} | "
                   f"**{tot:.2f} mm** | {'✓' if tot <= 1.0 else '✗'} |")
    out.append("\nSag is static and repeatable, so the planner also subtracts a payload-dependent Z offset "
               "(known payload: empty / plate / spool) and the wrist camera closes the last millimetre on AprilTags. "
               "The structural fix keeps that correction small enough to trust.")
    return "\n".join(out)


if __name__ == "__main__":
    print(report())
