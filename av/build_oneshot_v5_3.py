"""OneShot Arm v5 -> SP AV engine v5.3: the published v5.2 build + ESP32-CAM bridge wiring + Checks lane.

Run: python av/build_oneshot_v5_3.py  -> av/oneshot_arm_v5_3_artifact.html
Starts from av/engine/viewer_template_motion_v5_3.html (= engine v5.3 carrying the OneShot v5.2 data), adds:
- the ESP32-CAM (camera + Wi-Fi bridge) to the wiring lane: GPIO14 -> UNO D0, UNO D1 -> 1k/2k divider -> GPIO15,
  logic 5 V before the E-stop, common ground (oneshot_v5/WIRING.md), with routed 3D wires appended to the geometry;
- META.checks from the v5 design record (Mem0 2026-10-01/02) and this repo's control stack.
The engine code is untouched.
"""
import base64
import json
import os

import numpy as np
import trimesh

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
TPL = os.path.join(ROOT, "av", "engine", "viewer_template_motion_v5_3.html")
OUT = os.path.join(ROOT, "av", "oneshot_arm_v5_3_artifact.html")
AWG = {22: (0.0530, 7.0, 0.32), 26: (0.134, 2.2, 0.20)}

s = open(TPL).read()
ms = s.find('<script id="meta"'); mb = s.find(">", ms) + 1; me = s.find("</script>", mb)
meta = json.loads(s[mb:me])
gs = s.find('<script id="geo"'); gb = s.find(">", gs) + 1; ge = s.find("</script>", gb)
geo = bytearray(base64.b64decode(s[gb:ge].strip()))

W = meta["wiring"]
uno = next(n for n in W["nodes"] if n["id"] == "uno")
uno["pins"] += [dict(id="d0", label="D0 RX", kind="data"), dict(id="d1", label="D1 TX", kind="data"), dict(id="a0", label="A0", kind="data")]
uno["role"] = (uno.get("role", "") + " Talks to the ESP32-CAM on D0/D1 (unplug D0 while uploading); A0 senses the E-stopped rail.").strip()
esp_at = [-150.0, 95.0, 8.0]
W["nodes"].append(dict(id="esp32cam", label="ESP32-CAM (camera + Wi-Fi)", at=esp_at, schem=[1, 3],
                       role="AI-Thinker ESP32-CAM, off its MB board: /capture JPEG, /stream, /cmd → UNO serial, API key, 3 s dead-man stop. "
                            "Claude drives it from the Mac through oneshot_mcp.py.",
                       pins=[dict(id="tx", label="GPIO14 TX", kind="data"), dict(id="rx", label="GPIO15 RX", kind="data"),
                             dict(id="v", label="5V", kind="power"), dict(id="g", label="GND", kind="ground")]))


def tube(path, r):
    segs = [trimesh.creation.cylinder(radius=max(r, 0.6), segment=[np.array(a, float), np.array(b, float)], sections=6)
            for a, b in zip(path, path[1:]) if np.linalg.norm(np.subtract(b, a)) > 1e-6]
    return trimesh.util.concatenate(segs)


def add_run(rid, label, net, frm, to, kind, awg, amps, path, volts, note, step=11):
    global geo
    L = sum(float(np.linalg.norm(np.subtract(b, a))) for a, b in zip(path, path[1:]))
    ohm_m, chassis, r = AWG[awg]
    ohms = ohm_m * L / 1000
    drop = amps * ohms * 2
    run = dict(id=rid, label=label, net=net, **{"from": frm}, to=to, kind=kind, gauge=f"{awg} AWG", amps=amps, step=step, note=note,
               path=path, part="wire_" + rid, awg=awg, radius=r, length_mm=round(L, 1), conductors=1, ohms=round(ohms, 4),
               drop_v=round(drop, 3), drop_pct=round(100 * drop / volts, 2), chassis_a=chassis, undersized=amps > chassis)
    W["runs"].append(run)
    m = tube(path, r)
    tri = m.vertices[m.faces].reshape(-1, 3)
    lo = tri.min(0); span = np.maximum(tri.max(0) - lo, 1e-3)
    q = np.clip(np.round(((tri - lo) / span * 2 - 1) * 32767), -32767, 32767).astype("<i2").tobytes()
    off = len(geo)
    geo += q
    meta["parts"].append(dict(id="wire_" + rid, label=label, color={"power": "#3987e5", "ground": "#008300", "data": "#d55181"}[kind],
                              group="_wire", step=step, explode=[0, 0, 0], off=off, n=len(tri), lo=[round(float(v), 3) for v in lo],
                              span=[round(float(v), 3) for v in span], tris=len(m.faces), kind="wire", qty=1, bom=False,
                              wire={k: run[k] for k in ("id", "net", "kind", "gauge", "awg", "length_mm", "amps", "ohms", "drop_v",
                                                        "drop_pct", "chassis_a", "undersized", "from", "to")}))


U = uno["at"]
add_run("esp_tx", "ESP32-CAM TX → UNO D0", "UART·ESP→UNO", "esp32cam.tx", "uno.d0", "data", 26, 0.01,
        [esp_at, [-135.0, 70.0, 6.0], U], 5, "3.3 V is enough for the UNO to read HIGH. Unplug it while uploading to the UNO.")
add_run("esp_rx", "UNO D1 → 1k/2k → ESP32-CAM RX", "UART·UNO→ESP", "uno.d1", "esp32cam.rx", "data", 26, 0.01,
        [U, [-132.0, 78.0, 7.0], esp_at], 5, "The 1 kΩ / 2 kΩ divider turns the UNO's 5 V into 3.3 V for GPIO15.")
add_run("esp_v", "Logic 5 V → ESP32-CAM (before the E-stop)", "+5V logic", "psu.v", "esp32cam.v", "power", 22, 0.5,
        [[-190.0, -20.0, 6.0], [-200.0, 40.0, 7.0], [-175.0, 95.0, 8.0], esp_at], 5,
        "Taken BEFORE the E-stop so the camera stays up when the motors are cut; brownouts reboot the ESP32, so never from the UNO pin.")
add_run("esp_g", "ESP32-CAM GND", "GND", "esp32cam.g", "rail.g", "ground", 22, 0.5, [esp_at, [-152.0, 50.0, 6.0], [-150.0, 0.0, 6.0]], 5,
        "One common ground or the serial link floats.")
add_run("sense", "Rail sense → A0 (10k / 100k)", "SENSE·A0", "rail.v", "uno.a0", "data", 26, 0.001, [[-150.0, 0.0, 6.0], [-130.0, 25.0, 6.0], U], 5,
        "Tells the UNO the E-stop is pressed; it then detaches the servos.")
W["note"] = W.get("note", "") + " v5.3: ESP32-CAM bridge on the UNO's D0/D1, logic 5 V before the E-stop, rail sense on A0."

meta["bomExtra"].append(dict(id="esp32cam", label="ESP32-CAM + MB board (camera + Wi-Fi bridge)", qty=1, kind="bought", color="#1f6f8b",
                             cost=dict(each=12.0, est=True, supplier="Amazon.ca (ESP32-CAM + MB)", url="https://www.amazon.ca/s?k=esp32-cam+mb",
                                       checked="2026-10-02", bulk={"10": 9.0, "50": 7.5, "100": 7.0}, have=True, have_note="old ESP32-CAM + MB (Mem0)",
                                       formula="already owned")))
meta["bomExtra"].append(dict(id="divider", label="1 kΩ + 2 kΩ resistors (UART level divider) + 10k/100k (rail sense)", qty=1, kind="bought",
                             color="#1f6f8b", cost=dict(each=0.2, est=True, supplier="ELEGOO kit resistors", url="https://www.amazon.ca/s?k=elegoo+resistor+kit",
                                                        checked="2026-10-02", bulk={"10": 0.1, "50": 0.08, "100": 0.06}, have=True,
                                                        have_note="ELEGOO kit (120 resistors)", formula="already owned")))

meta["checks"] = [
    dict(group="Torque (hold ≤ 50 % of stall)", label="Yaw stepper, worst hold", value=26.4, limit=50, unit="%", status="pass",
         source="OneShot v5 design loop (Mem0 design record 2026-10-01)"),
    dict(group="Torque (hold ≤ 50 % of stall)", label="Shoulder / elbow SG90, worst hold", value=24.1, limit=50, unit="%", status="pass",
         source="OneShot v5 design loop"),
    dict(group="Simulation", label="PyBullet vs hand calc", value=0.2, limit=15, unit="%", status="pass", source="v5 sim (Mem0)"),
    dict(group="CAD", label="DFM clash check", value=0, limit=None, unit="clashes", status="pass", source="v5 DFM harness"),
    dict(group="CAD", label="Screw fit check (this viewer)", value=f"{len(meta['fasteners'])} screws",
         limit=None, status="warn" if any(f['fit'].get('warn') for f in meta['fasteners']) else "pass", source="engine fit lane"),
    dict(group="Motion", label="Pick-and-place path", value="0 dead stops", limit=None, status="pass",
         source="v5.2 firmware L r z straight-line command (Mem0 2026-10-02)", note="11 dead stops in v5.1 → 0"),
    dict(group="Control stack (v5.3)", label="UNO firmware pins = build sheet", value="D5 D6 D3 · D8–D11 · D2 · A0", limit=None,
         status="pass", source="oneshot_v5/uno_arm/uno_arm.ino"),
    dict(group="Control stack (v5.3)", label="UNO + ESP32-CAM compile", value="not run", limit=None, status="warn",
         source="Arduino IDE on the Mac", note="cloud could not download the cores"),
    dict(group="Control stack (v5.3)", label="Calibration (zero, signs, grip)", value="to do", limit=None, status="warn",
         source="oneshot_v5/WIRING.md → Calibrate", note="10 min after the first power-up"),
    dict(group="Electrical", label="Worst voltage drop", value=max(r["drop_pct"] for r in W["runs"]), limit=3.0, unit="%",
         status="pass" if max(r["drop_pct"] for r in W["runs"]) <= 3 else "fail", source="wiring lane"),
]
meta["title"] = "OneShot Arm v5.3"
meta["subtitle"] = meta["subtitle"] + " · ESP32-CAM bridge · engine v5.3"

page = s[:mb] + json.dumps(meta, separators=(",", ":")).replace("</", "<\\/") + s[me:]
gs = page.find('<script id="geo"'); gb = page.find(">", gs) + 1; ge = page.find("</script>", gb)
page = page[:gb] + base64.b64encode(bytes(geo)).decode() + page[ge:]
page = page.replace("<title>OneShot Arm v5.2</title>", "<title>OneShot Arm v5.3</title>", 1)
page = page.replace("<h1>OneShot Arm v5.2</h1>", "<h1>OneShot Arm v5.3</h1>", 1)
open(OUT, "w").write(page)
print("wrote", OUT, f"{len(page) / 1e6:.2f} MB", "runs", len(W["runs"]), "checks", len(meta["checks"]))
