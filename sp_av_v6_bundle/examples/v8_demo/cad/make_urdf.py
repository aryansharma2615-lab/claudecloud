#!/usr/bin/env python3
"""URDF + SRDF + SDF for the Servo Mount, from the SAME CAD + mass data the AV uses, then a PyBullet check.

    python3 cad/make_urdf.py   -> out/servo_mount_v1.urdf, .srdf, .sdf, out/SIM_REPORT.json

Links: base_link (base, cradle, servo, inserts, M3s, tab screws — all fixed) and arm_link (horn, arm,
horn screw, load pin + test mass). One revolute joint `shaft` at the CAD shaft axis, limits ±90°,
effort = SG90 stall (DATASHEET), velocity = 60° / 0.1 s. Inertials: mass from slicer / datasheet,
COM from CAD, inertia tensor from the STL at uniform density m/V (parallel-axis combined per link).
PyBullet check: (1) the load point FK from the URDF matches the AV's joint rotation within 1 mm at
every path key; (2) inverse-dynamics gravity torque matches calc_v8 within 1 % at three loads.
"""
import json
import math
import os
import sys
import xml.etree.ElementTree as ET

import numpy as np
import trimesh

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OUT = os.path.join(ROOT, "out")
sys.path.insert(0, os.path.join(ROOT, "..", "..", "engine"))
import calc_v8  # noqa: E402

ENG, M = calc_v8.compute(os.path.join(ROOT, "engineering_data_servo_mount_v1.yaml"))
cad = json.load(open(os.path.join(OUT, "cad_facts.json")))
ARM = ["horn", "arm", "horn_screw", "weight"]
BASE = [p for p in cad["parts"] if p not in ARM]
o = np.array(cad["frames"]["shaft"]["origin"])        # mm
axis = cad["frames"]["shaft"]["axis"]
LIM = [math.radians(a) for a in ENG["model"]["limits"]]
EFFORT = ENG["model"]["stall_nmm"] / 1000             # N·m
VEL = math.radians(60) / 0.1


def link_inertial(pids, origin_mm, kg_load):
    """combined mass (kg), COM (m, in link frame), inertia about COM (kg m²)"""
    ms, cs, Is = [], [], []
    for pid in pids:
        mesh = trimesh.load(os.path.join(OUT, "stl", pid + ".stl"))
        g = M.mass_of(pid, kg_load)
        m = g / 1000.0
        if pid == "weight":   # the test mass acts at the load point (lever = load hole)
            c = np.array(cad["frames"]["load_point"])
            Ic = np.zeros((3, 3))
        else:
            c = np.array(M.parts[pid]["com"])
            vol = abs(mesh.volume)
            Ic = np.array(mesh.moment_inertia) * (g / vol) * 1e-9 if vol > 0 else np.zeros((3, 3))   # g·mm² -> kg·m²
        ms.append(m); cs.append((c - origin_mm) / 1000.0); Is.append(Ic)
    mt = sum(ms)
    ct = sum(m * c for m, c in zip(ms, cs)) / mt
    It = np.zeros((3, 3))
    for m, c, Ic in zip(ms, cs, Is):
        d = c - ct
        It += Ic + m * (np.dot(d, d) * np.eye(3) - np.outer(d, d))
    return mt, ct, It


def urdf(kg_load=None):
    kg_load = ENG["model"]["kg"]["v"] if kg_load is None else kg_load
    r = ET.Element("robot", name="servo_mount_v1")
    def link(name, pids, origin):
        L = ET.SubElement(r, "link", name=name)
        m, c, I = link_inertial(pids, origin, kg_load)
        inr = ET.SubElement(L, "inertial")
        ET.SubElement(inr, "origin", xyz=" ".join(f"{x:.6f}" for x in c), rpy="0 0 0")
        ET.SubElement(inr, "mass", value=f"{m:.6f}")
        ET.SubElement(inr, "inertia", ixx=f"{I[0,0]:.3e}", ixy=f"{I[0,1]:.3e}", ixz=f"{I[0,2]:.3e}",
                      iyy=f"{I[1,1]:.3e}", iyz=f"{I[1,2]:.3e}", izz=f"{I[2,2]:.3e}")
        for pid in pids:
            for tag in ("visual", "collision"):
                vv = ET.SubElement(L, tag, name=f"{pid}_{tag[0]}")
                ET.SubElement(vv, "origin", xyz=" ".join(f"{-x/1000:.6f}" for x in origin), rpy="0 0 0")
                g = ET.SubElement(vv, "geometry")
                ET.SubElement(g, "mesh", filename=f"stl/{pid}.stl", scale="0.001 0.001 0.001")
        return m
    link("base_link", BASE, np.zeros(3))
    link("arm_link", ARM, o)
    # massless frame at the load hole — 1 mg, never 1 kg (PyBullet default trap)
    lp = ET.SubElement(r, "link", name="load_point")
    inr = ET.SubElement(lp, "inertial")
    ET.SubElement(inr, "mass", value="0.000001")
    ET.SubElement(inr, "inertia", ixx="1e-12", ixy="0", ixz="0", iyy="1e-12", iyz="0", izz="1e-12")
    j = ET.SubElement(r, "joint", name="shaft", type="revolute")
    ET.SubElement(j, "parent", link="base_link"); ET.SubElement(j, "child", link="arm_link")
    ET.SubElement(j, "origin", xyz=" ".join(f"{x/1000:.6f}" for x in o), rpy="0 0 0")
    ET.SubElement(j, "axis", xyz=" ".join(str(a) for a in axis))
    ET.SubElement(j, "limit", lower=f"{LIM[0]:.5f}", upper=f"{LIM[1]:.5f}", effort=f"{EFFORT:.4f}", velocity=f"{VEL:.3f}")
    jf = ET.SubElement(r, "joint", name="load_point_fixed", type="fixed")
    ET.SubElement(jf, "parent", link="arm_link"); ET.SubElement(jf, "child", link="load_point")
    lpnt = np.array(cad["frames"]["load_point"]) - o
    ET.SubElement(jf, "origin", xyz=" ".join(f"{x/1000:.6f}" for x in lpnt), rpy="0 0 0")
    ET.indent(r)
    return ET.tostring(r, encoding="unicode")


def srdf():
    r = ET.Element("robot", name="servo_mount_v1")
    g = ET.SubElement(r, "group", name="arm")
    ET.SubElement(g, "joint", name="shaft")
    gs = ET.SubElement(r, "group_state", name="level", group="arm")
    ET.SubElement(gs, "joint", name="shaft", value="0")
    ET.SubElement(r, "end_effector", name="load", parent_link="arm_link", group="arm")
    ET.SubElement(r, "disable_collisions", link1="base_link", link2="arm_link", reason="Adjacent")
    ET.SubElement(r, "disable_collisions", link1="arm_link", link2="load_point", reason="Adjacent")
    ET.indent(r)
    return ET.tostring(r, encoding="unicode")


def sdf(u):
    """SDF 1.7 from the URDF (same frames, same inertials)"""
    R = ET.fromstring(u)
    s = ET.Element("sdf", version="1.7")
    m = ET.SubElement(s, "model", name="servo_mount_v1")
    for L in R.findall("link"):
        l = ET.SubElement(m, "link", name=L.get("name"))
        if L.get("name") == "arm_link":
            ET.SubElement(l, "pose").text = R.find("joint/origin").get("xyz") + " 0 0 0"
        if L.get("name") == "load_point":
            arm_xyz = np.array([float(x) for x in R.find("joint/origin").get("xyz").split()])
            lp = np.array([float(x) for x in R.findall("joint")[1].find("origin").get("xyz").split()])
            ET.SubElement(l, "pose").text = " ".join(f"{x:.6f}" for x in arm_xyz + lp) + " 0 0 0"
        ii = L.find("inertial")
        if ii is not None:
            I = ET.SubElement(l, "inertial")
            org = ii.find("origin")
            ET.SubElement(I, "pose").text = (org.get("xyz") if org is not None else "0 0 0") + " 0 0 0"
            ET.SubElement(I, "mass").text = ii.find("mass").get("value")
            it = ET.SubElement(I, "inertia")
            for k in ("ixx", "ixy", "ixz", "iyy", "iyz", "izz"):
                ET.SubElement(it, k).text = ii.find("inertia").get(k)
        for tag in ("visual", "collision"):
            for vv in L.findall(tag):
                e = ET.SubElement(l, tag, name=vv.get("name"))
                ET.SubElement(e, "pose").text = vv.find("origin").get("xyz") + " 0 0 0"
                gm = ET.SubElement(ET.SubElement(e, "geometry"), "mesh")
                ET.SubElement(gm, "uri").text = vv.find("geometry/mesh").get("filename")
                ET.SubElement(gm, "scale").text = vv.find("geometry/mesh").get("scale")
    j = ET.SubElement(m, "joint", name="shaft", type="revolute")
    ET.SubElement(j, "parent").text = "base_link"; ET.SubElement(j, "child").text = "arm_link"
    ax = ET.SubElement(j, "axis"); ET.SubElement(ax, "xyz").text = " ".join(str(a) for a in axis)
    lim = ET.SubElement(ax, "limit")
    for k, val in (("lower", LIM[0]), ("upper", LIM[1]), ("effort", EFFORT), ("velocity", VEL)):
        ET.SubElement(lim, k).text = f"{val:.5f}"
    jf = ET.SubElement(m, "joint", name="load_point_fixed", type="fixed")
    ET.SubElement(jf, "parent").text = "arm_link"; ET.SubElement(jf, "child").text = "load_point"
    ET.indent(s)
    return ET.tostring(s, encoding="unicode")


def sim_check():
    import pybullet as pb
    rep = {"fk": [], "tau": [], "ok": True}
    for kg in (0.0, 0.2, 0.5):
        path = os.path.join(OUT, f"_sim_{kg}.urdf")
        open(path, "w").write(urdf(kg))
        cid = pb.connect(pb.DIRECT)
        pb.setGravity(0, 0, -calc_v8.G)
        rid = pb.loadURDF(path, useFixedBase=True, flags=pb.URDF_USE_INERTIA_FROM_FILE)
        for th in (path_keys := ENG["model"]["path"]["keys"]):
            q = math.radians(th)
            pb.resetJointState(rid, 0, q)
            pos = np.array(pb.getLinkState(rid, 1, computeForwardKinematics=True)[4]) * 1000
            # the AV: rotate the CAD load point about the shaft axis by +theta (Rodrigues, right-hand — same as the engine)
            lp = np.array(cad["frames"]["load_point"]) - o
            k = np.array(axis, float) / np.linalg.norm(axis)
            av = o + lp * math.cos(q) + np.cross(k, lp) * math.sin(q) + k * np.dot(k, lp) * (1 - math.cos(q))
            err = float(np.linalg.norm(pos - av))
            if kg == 0.2:
                rep["fk"].append({"deg": th, "err_mm": round(err, 6)})
            rep["ok"] &= err < 1.0
            tq = pb.calculateInverseDynamics(rid, [q], [0.0], [0.0])[0] * 1000   # N·mm
            hc = M.tau(kg, ENG["model"]["lever"]["v"], th)
            rel = abs(abs(tq) - abs(hc)) / max(abs(hc), 1e-6)
            rep["tau"].append({"kg": kg, "deg": th, "pybullet_nmm": round(tq, 4), "calc_nmm": round(hc, 4), "rel": round(rel, 6)})
            if abs(hc) > 1e-3:
                rep["ok"] &= rel < 0.01
        pb.disconnect(cid)
        os.remove(path)
    return rep


if __name__ == "__main__":
    u = urdf()
    open(os.path.join(OUT, "servo_mount_v1.urdf"), "w").write(u)
    open(os.path.join(OUT, "servo_mount_v1.srdf"), "w").write(srdf())
    open(os.path.join(OUT, "servo_mount_v1.sdf"), "w").write(sdf(u))
    for f in ("urdf", "srdf", "sdf"):
        ET.parse(os.path.join(OUT, f"servo_mount_v1.{f}"))       # parses
    rep = sim_check()
    json.dump(rep, open(os.path.join(OUT, "SIM_REPORT.json"), "w"), indent=1)
    worst_fk = max(r["err_mm"] for r in rep["fk"])
    worst_tau = max(r["rel"] for r in rep["tau"] if abs(r["calc_nmm"]) > 1e-3)
    print(f"URDF/SRDF/SDF parse OK · FK worst {worst_fk:.2e} mm · ID torque worst {worst_tau*100:.3f} % · {'PASS' if rep['ok'] else 'FAIL'}")
