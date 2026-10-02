#!/usr/bin/env python3
"""
av_geom.py — geometry layer of the SP assembly-viewer engine.

Everything that turns a config entry into triangles lives here. The viewer
never sees a file path: it gets one flat int16 vertex buffer plus a per-part
(offset, count, lo, span) record, which is why a 1.6 MB page can carry a
quarter of a million vertices and still open on a phone.

Quantisation
------------
Each part is normalised into its OWN bounding box and stored as 3 x int16.
The shader rebuilds it with  p = (q/32767 * 0.5 + 0.5) * span + lo.
Resolution is span/65535 — on a 146 mm housing that is 2.2 um, which is two
orders of magnitude finer than a 0.4 mm nozzle can place plastic. It is not
lossy in any sense that matters to a printed part.
"""
from __future__ import annotations

import math
import os

import numpy as np
import trimesh

# Facet count for generated primitives. 32 keeps a bought-in stand-in (motor
# can, pipe stub) cheap: 128 triangles instead of the thousands a real STL of
# the same object would cost, and nobody inspects the flats on a placeholder.
PRIM_SECTIONS = 32

Q_MAX = 32767.0


# ---------------------------------------------------------------------------
# primitives — stand-ins for bought parts we have no STL for
# ---------------------------------------------------------------------------
def _prim(spec: dict) -> trimesh.Trimesh:
    t = spec["type"]
    at = np.asarray(spec.get("at", [0, 0, 0]), dtype=float)

    if t == "box":
        m = trimesh.creation.box(extents=spec["size"])
    elif t == "cylinder":
        m = trimesh.creation.cylinder(
            radius=spec["r"], height=spec["h"], sections=PRIM_SECTIONS)
    elif t == "sphere":
        m = trimesh.creation.icosphere(subdivisions=2, radius=spec["r"])
    elif t == "compound":
        return trimesh.util.concatenate([_prim(s) for s in spec["parts"]])
    else:
        raise ValueError(f"unknown primitive type {t!r}")

    # every primitive is authored about its own centre, then moved by `at`
    m.apply_translation(at)
    return m


# ---------------------------------------------------------------------------
# transforms
# ---------------------------------------------------------------------------
def apply_transform(mesh: trimesh.Trimesh, ops) -> trimesh.Trimesh:
    """Apply an ordered list of ops. Order is the list order — a rotate after a
    translate is not the same part, and silently reordering them is how a
    viewer ends up disagreeing with the CAD."""
    for op in ops or []:
        if "t" in op:
            mesh.apply_translation(np.asarray(op["t"], dtype=float))
        elif "rx" in op:
            mesh.apply_transform(trimesh.transformations.rotation_matrix(
                math.radians(op["rx"]), [1, 0, 0]))
        elif "ry" in op:
            mesh.apply_transform(trimesh.transformations.rotation_matrix(
                math.radians(op["ry"]), [0, 1, 0]))
        elif "rz" in op:
            mesh.apply_transform(trimesh.transformations.rotation_matrix(
                math.radians(op["rz"]), [0, 0, 1]))
        elif "s" in op:
            s = op["s"]
            s = [s, s, s] if isinstance(s, (int, float)) else s
            mesh.apply_scale(s)
        else:
            raise ValueError(f"unknown transform op {op!r}")
    return mesh


def tube(path, radius=1.0, sections=8, cap=True) -> trimesh.Trimesh:
    """Sweep a circular section along a polyline — a wire, a hose, a cable run.

    Frames are carried along the path by PARALLEL TRANSPORT rather than rebuilt
    from a fixed "up" vector at each point. The fixed-up version is the obvious
    one and it fails the moment a run goes vertical: the reference direction
    becomes parallel to the tangent, the frame flips, and the tube turns itself
    inside out for one segment. Transport has no such singularity.

    At each interior point the ring uses the AVERAGED tangent of the two
    adjoining segments, which mitres the corner instead of letting the tube
    pinch shut on the inside of a bend.

    8 sections is deliberate: a 1 mm wire is 3-4 px on screen, nobody counts its
    facets, and 11 runs at 8 sections cost about a thousand triangles total.
    """
    pts = [np.asarray(p, dtype=float) for p in path]
    # drop consecutive duplicates, which would produce a zero-length tangent
    clean = [pts[0]]
    for p in pts[1:]:
        if np.linalg.norm(p - clean[-1]) > 1e-9:
            clean.append(p)
    if len(clean) < 2:
        raise ValueError("tube() needs at least two distinct points")
    P = np.array(clean)
    n = len(P)

    seg = P[1:] - P[:-1]
    seg_t = seg / np.linalg.norm(seg, axis=1)[:, None]

    # per-point tangent: averaged across the joint, so corners mitre
    tan = np.zeros_like(P)
    tan[0] = seg_t[0]
    tan[-1] = seg_t[-1]
    for i in range(1, n - 1):
        v = seg_t[i - 1] + seg_t[i]
        L = np.linalg.norm(v)
        tan[i] = seg_t[i] if L < 1e-9 else v / L

    # initial normal: any axis not parallel to the first tangent
    a = np.array([0.0, 0.0, 1.0])
    if abs(np.dot(a, tan[0])) > 0.9:
        a = np.array([1.0, 0.0, 0.0])
    nrm0 = np.cross(tan[0], a)
    nrm0 /= np.linalg.norm(nrm0)

    normals = [nrm0]
    for i in range(1, n):
        prev_t, cur_t = tan[i - 1], tan[i]
        v = np.cross(prev_t, cur_t)
        s = np.linalg.norm(v)
        if s < 1e-9:                       # collinear, frame carries unchanged
            normals.append(normals[-1])
            continue
        axis = v / s
        ang = math.atan2(s, float(np.dot(prev_t, cur_t)))
        R = trimesh.transformations.rotation_matrix(ang, axis)[:3, :3]
        m = R @ normals[-1]
        m -= np.dot(m, cur_t) * cur_t      # re-orthogonalise against drift
        normals.append(m / np.linalg.norm(m))

    verts, faces = [], []
    for i in range(n):
        t = tan[i]
        u = normals[i]
        v = np.cross(t, u)
        for k in range(sections):
            th = 2 * math.pi * k / sections
            verts.append(P[i] + radius * (math.cos(th) * u + math.sin(th) * v))
    for i in range(n - 1):
        for k in range(sections):
            k2 = (k + 1) % sections
            a0 = i * sections + k
            b0 = i * sections + k2
            a1 = (i + 1) * sections + k
            b1 = (i + 1) * sections + k2
            # wound so the radial normal points OUT: with a right-handed
            # (u, v, t) frame, (a0,a1,b1) comes out facing inward, which the
            # back-face cull then renders as a hollow shell
            faces.append([a0, b1, a1])
            faces.append([a0, b0, b1])
    if cap:
        for (idx, flip) in ((0, True), (n - 1, False)):
            c = len(verts)
            verts.append(P[idx])
            for k in range(sections):
                k2 = (k + 1) % sections
                a0 = idx * sections + k
                b0 = idx * sections + k2
                faces.append([c, b0, a0] if flip else [c, a0, b0])

    m = trimesh.Trimesh(vertices=np.array(verts), faces=np.array(faces),
                        process=False)
    return m


def polyline_length(path) -> float:
    """Run length in mm, straight through the points."""
    P = np.asarray(path, dtype=float)
    if len(P) < 2:
        return 0.0
    return float(np.linalg.norm(P[1:] - P[:-1], axis=1).sum())


def transform_matrix(ops) -> np.ndarray:
    """The same op list as a single 4x4. The viewer needs the INVERSE of this to
    get from assembly coordinates back to the part's own STL frame, which is
    what a downloaded STL and a bed layout are both expressed in."""
    m = np.eye(4)
    for op in ops or []:
        if "t" in op:
            t = np.eye(4); t[:3, 3] = op["t"]
        elif "rx" in op:
            t = trimesh.transformations.rotation_matrix(math.radians(op["rx"]), [1, 0, 0])
        elif "ry" in op:
            t = trimesh.transformations.rotation_matrix(math.radians(op["ry"]), [0, 1, 0])
        elif "rz" in op:
            t = trimesh.transformations.rotation_matrix(math.radians(op["rz"]), [0, 0, 1])
        elif "s" in op:
            s = op["s"]
            s = [s, s, s] if isinstance(s, (int, float)) else s
            t = np.diag([s[0], s[1], s[2], 1.0])
        else:
            raise ValueError(f"unknown transform op {op!r}")
        m = t @ m
    return m


def col_major(m: np.ndarray):
    """numpy row-major 4x4 -> the flat column-major list WebGL wants."""
    return [round(float(x), 6) for x in m.T.reshape(-1)]


def load_part_mesh(part: dict, base_dir: str) -> trimesh.Trimesh:
    """Config entry -> a mesh in ASSEMBLY coordinates."""
    if "stl" in part:
        path = part["stl"]
        if not os.path.isabs(path):
            path = os.path.join(base_dir, path)
        m = trimesh.load_mesh(path, process=False)
        if isinstance(m, trimesh.Scene):
            m = trimesh.util.concatenate(list(m.geometry.values()))
    elif "primitive" in part:
        m = _prim(part["primitive"])
    else:
        raise ValueError(f"part {part.get('id')!r} has neither stl nor primitive")
    return apply_transform(m, part.get("transform"))


def source_mesh(part: dict, base_dir: str) -> trimesh.Trimesh:
    """Mesh in its own PRINT coordinates — i.e. straight out of the STL, before
    the assembly transform. This is what goes on the bed, not what is drawn in
    the exploded view."""
    if "stl" in part:
        path = part["stl"]
        if not os.path.isabs(path):
            path = os.path.join(base_dir, path)
        m = trimesh.load_mesh(path, process=False)
        if isinstance(m, trimesh.Scene):
            m = trimesh.util.concatenate(list(m.geometry.values()))
        return m
    return _prim(part["primitive"])


# ---------------------------------------------------------------------------
# quantise + pack
# ---------------------------------------------------------------------------
def quantise(mesh: trimesh.Trimesh):
    """-> (int16 array [n,3], lo, span). Vertices come out triangle-soup: no
    index buffer. Indexing would save ~35% but costs a second buffer, a second
    attribute binding and a per-part element offset; at this size the flat soup
    is the simpler, faster thing."""
    v = mesh.vertices[mesh.faces].reshape(-1, 3).astype(np.float64)
    lo = v.min(axis=0)
    hi = v.max(axis=0)
    span = np.maximum(hi - lo, 1e-6)
    # Full-range mapping: u=0 -> -32768, u=1 -> +32767. The shader reads these
    # as SIGNED NORMALIZED, where GL defines -32768 and -32767 to both clamp to
    # -1.0, so the low end still decodes exactly to `lo`.
    q = np.rint((v - lo) / span * 65535.0) - 32768.0
    q = np.clip(q, -32768.0, Q_MAX).astype(np.int16)
    return q, lo, span


def pack(entries):
    """entries: [(part_id, mesh)] -> (bytes, {id: {off, n, lo, span, tris}})"""
    blob = bytearray()
    rec = {}
    for pid, mesh in entries:
        q, lo, span = quantise(mesh)
        rec[pid] = {
            "off": len(blob),                      # BYTE offset; shader /6
            "n": int(q.shape[0]),                  # vertex count
            "lo": [round(float(x), 4) for x in lo],
            "span": [round(float(x), 4) for x in span],
            "tris": int(q.shape[0] // 3),
        }
        blob += q.tobytes()
    return bytes(blob), rec


# ---------------------------------------------------------------------------
# physical facts the BOM and the bed check need
# ---------------------------------------------------------------------------
def mesh_facts(mesh: trimesh.Trimesh) -> dict:
    """Volume via the divergence theorem. trimesh signs it from the winding, so
    an inside-out STL reports negative — abs() would hide a real defect, so we
    keep the sign and let the caller flag it."""
    try:
        vol = float(mesh.volume)
    except Exception:
        vol = 0.0
    ext = mesh.extents
    return {
        "volume_mm3": round(vol, 2),
        "extents": [round(float(x), 3) for x in ext],
        "tris": int(len(mesh.faces)),
        "watertight": bool(mesh.is_watertight),
    }


def oriented(mesh: trimesh.Trimesh, rot) -> trimesh.Trimesh:
    """Copy of the mesh rotated into its print orientation and dropped so its
    lowest facet sits on z = 0, centred in XY. rot is [rx, ry, rz] degrees."""
    m = mesh.copy()
    rx, ry, rz = (rot or [0, 0, 0])
    for ang, ax in ((rx, [1, 0, 0]), (ry, [0, 1, 0]), (rz, [0, 0, 1])):
        if ang:
            m.apply_transform(trimesh.transformations.rotation_matrix(
                math.radians(ang), ax))
    lo = m.bounds[0]
    hi = m.bounds[1]
    m.apply_translation([-(lo[0] + hi[0]) / 2, -(lo[1] + hi[1]) / 2, -lo[2]])
    return m
