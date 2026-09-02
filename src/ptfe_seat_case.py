#!/usr/bin/env python3
"""
ptfe_seat_case.py - parametric PTFE-seat bearing upgrade for kepeo's
"Keyball Trackball Case" (Thingiverse thing:6215791, CC BY 4.0).

Replaces the three static 2 mm ceramic balls with three 5 mm chrome-steel
balls, each resting in the inner edge of a 3 x 8.5 x 2 mm PTFE washer.

Everything geometric is derived from the parameters at the top of this file
and from stock_measurements.json (written by measure_stock.py).

Pipeline
  1. load the repaired stock STL, the measured trackball centre and the
     measured stock pocket axes
  2. build the tool solids (bosses, bores, pocket plugs/shaves) in CadQuery
  3. mesh booleans with manifold3d  -> output STL   (source of truth)
  4. B-rep booleans with OpenCascade -> output STEP  (same tool solids)
  5. caps (3 OD variants) and a test coupon           -> STEP + STL
  6. geometric acceptance checks                      -> build_report.json

Run:  python ptfe_seat_case.py [--side right|left] [--no-step] [--out ../output]
"""
import argparse
import json
import math
import os
import sys
import time

import numpy as np
import trimesh
import cadquery as cq
import manifold3d as m3d

# ---------------------------------------------------------------------------
#  PARAMETERS  (mm, degrees)
# ---------------------------------------------------------------------------
TRACKBALL_D = 34.0          # chromed steel trackball
BALL_D = 5.0                # 5 mm chrome-steel support balls (G25)
WASHER_ID = 3.0             # uxcell PTFE washer 3 x 8.5 x 2
WASHER_OD = 8.5
WASHER_T = 2.0

CONTACT_R = TRACKBALL_D / 2 + BALL_D / 2      # 19.5: 5 mm ball CENTRE distance from trackball centre
BEDDING_BIAS = 0.15         # washer face modelled this much closer to the trackball (PTFE beds in)

# Contact positions on the CONTACT_R sphere, in the STL frame of the RIGHT-hand
# case (az measured in the XY plane from +X towards +Y, el above the XY plane).
# Stock pockets were at (az,el) = (-3.1,+27.3), (123.5,+8.6), (-101.7,-60.9).
# A 24.5 mm deep seat stack cannot go anywhere the stock pockets are: the right
# side (az -45..+45) is the sensor compartment (the Keyball sensor board stands
# vertically inside the "pillar"), the row of switches behind the ball blocks
# az 45..140 below the equator, and the mounting plane limits the front to
# el >= -32. The contact triangle is therefore rotated so that one contact sits
# above the equator at the back (as in the stock case) - see layout_search.py.
SEATS = [
    dict(name="S1", az=-58.0,  el=-30.0, note="front-right, just under the low front rim (short stub proud of the rim); replaces stock P3"),
    dict(name="S2", az=50.0,   el=27.0,  note="back, above the equator on the high back wall, boss stands off the shell above the key row; replaces stock P1"),
    dict(name="S3", az=158.0,  el=-30.0, note="back-left at the end of the left wall, clear of the slot; replaces stock P2"),
]

# seat stack, distances measured along the contact ray from the trackball centre
BOSS_D = 11.0               # local boss cylinder
BOSS_BLEND = 1.5            # 45 deg flare where the boss meets the outer shell
BOSS_END_CHAMFER = 0.5
BACKING_MIN = 1.0           # solid plastic behind the counterbore floor
BACKING_EXTRA = 0.15        # a little more than the minimum
CB_D = WASHER_OD + 0.1      # 8.6 washer counterbore (nominal)
CAP_BORE_D = 9.1            # cap press bore (nominal) - must exceed the washer OD so the washer can be inserted
PRINT_UNDERSIZE = 0.15      # all press bores modelled this much under nominal; ream to size
CAP_STEP_ABOVE_WASHER = 3.5 # hard step (cap seat) this far above the washer top face
BORE_START = 15.0           # bores are cut from well inside the bowl (open towards the trackball)

# retention cap (ring)
CAP_HOLE_D = 4.4
CAP_OD_NOMINAL = 9.2
CAP_OD_VARIANTS = [9.1, 9.2, 9.3]
CAP_RIM_T = 0.5             # thickness at the outer rim
CAP_HUB_T = 0.65            # thickness at the hole (spec allows up to 0.85; 0.65 keeps >=0.3 to the trackball)
CAP_HUB_R = 2.9             # hub flat extends to this radius, then chamfers down to CAP_RIM_T at CAP_CHAMFER_R
CAP_CHAMFER_R = 3.7

# test coupon
COUPON_OD = 14.0
COUPON_CAP_BORE_DEPTH = 1.0

# safety envelope for new material (STL frame): the stock case bottoms on the
# daughterboard at z = 2.0; nothing new may go below this.
Z_MIN_NEW = 2.2
CLEARANCE_MIN = 0.3

REMOVE_STOCK_POCKETS = True   # plug the old 2 mm bores and shave the raised cones flush with the R18 bowl
POCKET_PLUG_R = 1.15
POCKET_SHAVE_R = 2.6

# The stock case has a flat (the pillar wall) inside the bowl at x = 95.4 that is only 0.24 mm from
# the trackball once the ball rests at its true centre TB. Everything closer than this to the
# trackball surface (in both the fresh and the bedded state) is trimmed away; only that flat is affected.
ENVELOPE_CLEARANCE = 0.35

# the finger slot in the back-left wall (az/el window, right-hand frame) - used to keep the plug of
# the old P2 pocket, which broke into the slot's corner, out of the slot
SLOT_AZ_WINDOW = (100.0, 127.0)
SLOT_EL_WINDOW = (-28.0, 13.0)

STOCK_BOWL_R = 18.0          # inner bowl of the stock case
STOCK_SHELL_R = 19.4         # outer shell of the stock case

# ---------------------------------------------------------------------------
#  derived seat stack
# ---------------------------------------------------------------------------
RING_R = WASHER_ID / 2
BALL_R = BALL_D / 2
DROP = math.sqrt(BALL_R ** 2 - RING_R ** 2)               # 2.0: ball centre above the washer's inner edge
T_BALL_BEDDED = CONTACT_R                                  # 19.5
T_BALL_FRESH = CONTACT_R - BEDDING_BIAS                    # 19.35
T_WASHER_TOP = CONTACT_R + DROP - BEDDING_BIAS             # 21.35
T_FLOOR = T_WASHER_TOP + WASHER_T                          # 23.35
T_STEP = T_WASHER_TOP - CAP_STEP_ABOVE_WASHER              # 17.85
T_END = T_FLOOR + BACKING_MIN + BACKING_EXTRA              # 24.5
T_FLARE0 = 19.0                                            # flare starts inside the shell wall
CB_R_MODEL = (CB_D - PRINT_UNDERSIZE) / 2
CAPBORE_R_MODEL = (CAP_BORE_D - PRINT_UNDERSIZE) / 2
BOSS_R = BOSS_D / 2


def unit(az, el):
    az, el = math.radians(az), math.radians(el)
    return np.array([math.cos(el) * math.cos(az), math.cos(el) * math.sin(az), math.sin(el)])


def az_el(u):
    return math.degrees(math.atan2(u[1], u[0])), math.degrees(math.asin(u[2]))


def V(p):
    return cq.Vector(float(p[0]), float(p[1]), float(p[2]))


# ---------------------------------------------------------------------------
#  measurements
# ---------------------------------------------------------------------------
def load_measurements(path, side):
    m = json.load(open(path))
    if side == "left":
        # the stock left case is the mirror (x -> -x) of the right one
        def mx(p):
            return [-p[0], p[1], p[2]]
        m["bowl_center"] = mx(m["bowl_center"])
        m["trackball_center"] = mx(m["trackball_center"])
        for p in m["pockets"]:
            p["axis_dir"] = mx(p["axis_dir"])
            p["ball_center"] = mx(p["ball_center"])
            p["az_deg"], p["el_deg"] = az_el(np.array(p["axis_dir"]))
    return m


# ---------------------------------------------------------------------------
#  B-rep tools (CadQuery)
# ---------------------------------------------------------------------------
def cyl(r, t0, t1, C, u):
    return cq.Solid.makeCylinder(r, t1 - t0, V(C + t0 * u), V(u))


def cone(r0, r1, t0, t1, C, u):
    return cq.Solid.makeCone(r0, r1, t1 - t0, V(C + t0 * u), V(u))


def sphere(r, C):
    return cq.Solid.makeSphere(r, V(C), angleDegrees1=-90, angleDegrees2=90, angleDegrees3=360)


def big_box_below(z):
    return cq.Solid.makeBox(1000, 1000, 1000, V(np.array([-500, -500, z - 1000])))


def seat_tools(C, u, Cbowl):
    """Return dict of B-rep solids for one seat along ray u from trackball centre C."""
    body = cyl(BOSS_R, STOCK_BOWL_R - 1.0, T_END - BOSS_END_CHAMFER, C, u)
    body = body.fuse(cone(BOSS_R, BOSS_R - BOSS_END_CHAMFER, T_END - BOSS_END_CHAMFER, T_END, C, u))
    flare = cone(BOSS_R + BOSS_BLEND, BOSS_R, T_FLARE0, T_FLARE0 + BOSS_BLEND, C, u)
    # the flare only lives outside the stock shell surface; the boss never intrudes into the R18 bowl
    flare = flare.cut(sphere(STOCK_SHELL_R, Cbowl))
    body = body.fuse(flare).cut(sphere(STOCK_BOWL_R, Cbowl)).cut(big_box_below(Z_MIN_NEW))
    cap_bore = cyl(CAPBORE_R_MODEL, BORE_START, T_STEP, C, u)
    washer_bore = cyl(CB_R_MODEL, BORE_START, T_FLOOR, C, u)
    return dict(boss=body, cap_bore=cap_bore, washer_bore=washer_bore)


def wall_feature_hull(stock, Cbowl, az_window, el_window, side, exclude_axes=(), t_in=17.0, t_out=20.5):
    """Convex hull of a through-wall feature (the finger slot): its wall faces are the faces between
    the two shell spheres whose normals are tangential; their vertices are extended radially."""
    fc, fn = stock.triangles_center, stock.face_normals
    d = fc - Cbowl
    dist = np.linalg.norm(d, axis=1)
    u = d / dist[:, None]
    az = np.degrees(np.arctan2(u[:, 1], u[:, 0]))
    if side == "left":
        az = 180.0 - az
        az = (az + 180) % 360 - 180
    el = np.degrees(np.arcsin(u[:, 2]))
    cosang = (fn * d).sum(1) / dist
    sel = (dist > STOCK_BOWL_R + 0.05) & (dist < STOCK_SHELL_R - 0.05) & (np.abs(cosang) < 0.3) & \
          (az > az_window[0]) & (az < az_window[1]) & (el > el_window[0]) & (el < el_window[1])
    # the old P2 pocket bore broke into the slot's corner: its bore walls must not be part of the slot hull
    for ax in exclude_axes:
        t = d @ ax
        rho = np.linalg.norm(d - np.outer(t, ax), axis=1)
        sel &= ~((rho < POCKET_PLUG_R + 0.6) & (t > STOCK_BOWL_R - 1.0))
    verts = stock.vertices[np.unique(stock.faces[sel])]
    dv = verts - Cbowl
    uu = dv / np.linalg.norm(dv, axis=1)[:, None]
    pts = np.r_[Cbowl + t_in * uu, Cbowl + t_out * uu]
    return trimesh.convex.convex_hull(pts)


def pocket_tools(Cbowl, dvec, t_floor):
    plug = cyl(POCKET_PLUG_R, STOCK_BOWL_R - 0.4, t_floor + 0.25, Cbowl, dvec)
    shave = cyl(POCKET_SHAVE_R, STOCK_BOWL_R - 2.0, STOCK_BOWL_R + 0.02, Cbowl, dvec).intersect(sphere(STOCK_BOWL_R, Cbowl))
    return dict(plug=plug, shave=shave)


# ---------------------------------------------------------------------------
#  mesh helpers (manifold3d)
# ---------------------------------------------------------------------------
def solid_to_trimesh(solid, tol=0.003, ang=0.03):
    verts, tris = solid.tessellate(tol, ang)
    v = np.array([[p.x, p.y, p.z] for p in verts], dtype=float)
    f = np.array(tris, dtype=np.int64)
    tm = trimesh.Trimesh(v, f, process=True)
    if not tm.is_watertight:
        import pymeshfix
        mf = pymeshfix.MeshFix(np.asarray(tm.vertices, dtype=float), np.asarray(tm.faces, dtype=np.int64))
        mf.repair(joincomp=True, remove_smallest_components=False)
        tm = trimesh.Trimesh(np.asarray(mf.points), np.asarray(mf.faces), process=True)
    if tm.volume < 0:
        tm.invert()
    return tm


def tm_to_manifold(tm):
    man = m3d.Manifold(m3d.Mesh(vert_properties=np.asarray(tm.vertices, dtype=np.float32),
                                tri_verts=np.asarray(tm.faces, dtype=np.uint32)))
    if man.status() != m3d.Error.NoError:
        raise RuntimeError(f"non-manifold mesh: {man.status()}")
    return man


def manifold_to_tm(man):
    mesh = man.to_mesh()
    # keep manifold3d's output as is (it is manifold by construction; it may contain a few zero-area
    # T-junction triangles, which is why proximity queries use clean_for_proximity())
    return trimesh.Trimesh(np.asarray(mesh.vert_properties)[:, :3], np.asarray(mesh.tri_verts), process=True)


def clean_for_proximity(tm):
    """copy without zero-area faces (they produce NaN in closest-point queries)"""
    c = tm.copy()
    c.update_faces(c.nondegenerate_faces())
    c.remove_unreferenced_vertices()
    return c


# ---------------------------------------------------------------------------
#  OCC helpers (STEP route)
# ---------------------------------------------------------------------------
def trimesh_to_occ_solid(tm):
    from OCP.BRepBuilderAPI import BRepBuilderAPI_Sewing, BRepBuilderAPI_MakeSolid, BRepBuilderAPI_MakePolygon, BRepBuilderAPI_MakeFace
    from OCP.gp import gp_Pnt
    from OCP.TopoDS import TopoDS
    from OCP.TopAbs import TopAbs_SHELL
    from OCP.TopExp import TopExp_Explorer
    Vv, F = tm.vertices, tm.faces
    sew = BRepBuilderAPI_Sewing(1e-4)
    for f in F:
        poly = BRepBuilderAPI_MakePolygon(gp_Pnt(*Vv[f[0]]), gp_Pnt(*Vv[f[1]]), gp_Pnt(*Vv[f[2]]), True)
        sew.Add(BRepBuilderAPI_MakeFace(poly.Wire(), True).Face())
    sew.Perform()
    sh = sew.SewedShape()
    ex = TopExp_Explorer(sh, TopAbs_SHELL)
    shells = []
    while ex.More():
        shells.append(TopoDS.Shell_s(ex.Current()))
        ex.Next()
    if len(shells) != 1:
        raise RuntimeError(f"sewing produced {len(shells)} shells")
    solid = cq.Solid(BRepBuilderAPI_MakeSolid(shells[0]).Solid())
    if solid.Volume() < 0:
        solid = cq.Solid(solid.wrapped.Reversed())
    return solid


def unify(shape):
    from OCP.ShapeUpgrade import ShapeUpgrade_UnifySameDomain
    u = ShapeUpgrade_UnifySameDomain(shape.wrapped, True, True, True)
    u.Build()
    return cq.Solid(u.Shape())


# ---------------------------------------------------------------------------
#  caps and coupon
# ---------------------------------------------------------------------------
def cap_profile_thickness(rho):
    """cap thickness (mm) as a function of radius, thickening towards the hole"""
    if rho <= CAP_HUB_R:
        return CAP_HUB_T
    if rho >= CAP_CHAMFER_R:
        return CAP_RIM_T
    f = (rho - CAP_HUB_R) / (CAP_CHAMFER_R - CAP_HUB_R)
    return CAP_HUB_T + f * (CAP_RIM_T - CAP_HUB_T)


def make_cap(od):
    """Cap ring, axis = +Z, underside (the face that bottoms on the step) at z=0,
    thickness grows towards -Z? No: the cap sits with its underside at z=0 and
    its top at z = -thickness in the seat frame (towards the trackball). For a
    stand-alone part we build it hole-up: underside at z=0, top at +thickness."""
    r_hole = CAP_HOLE_D / 2
    r_out = od / 2
    pts = [(r_hole, 0.0), (r_out, 0.0), (r_out, CAP_RIM_T), (CAP_CHAMFER_R, CAP_RIM_T),
           (CAP_HUB_R, CAP_HUB_T), (r_hole, CAP_HUB_T)]
    wp = cq.Workplane("XZ").polyline(pts).close().revolve(360, (0, 0, 0), (0, 1, 0))
    return wp


def make_coupon():
    """One full seat stack in a printable puck: cap bore, step, washer bore, floor,
    backing. Axis +Z, floor-side down (prints with the bores opening upward)."""
    top = T_STEP - COUPON_CAP_BORE_DEPTH          # coupon top face along the ray
    h = T_END - top
    puck = cq.Workplane("XY").circle(COUPON_OD / 2).extrude(h)
    # an orientation flat + a small "R" marker is not needed; keep it simple
    z_step = h - (T_STEP - top)                    # measured from the bottom (back face)
    z_floor = h - (T_FLOOR - top)
    puck = (puck.faces(">Z").workplane().hole(2 * CAPBORE_R_MODEL, depth=h - z_step)
                .faces(">Z").workplane().hole(2 * CB_R_MODEL, depth=h - z_floor))
    return puck, dict(height=h, cap_bore_depth=h - z_step, washer_bore_depth=h - z_floor,
                      backing=z_floor)


# ---------------------------------------------------------------------------
#  checks
# ---------------------------------------------------------------------------
def fibonacci_sphere(n):
    i = np.arange(n) + 0.5
    phi = np.arccos(1 - 2 * i / n)
    theta = np.pi * (1 + 5 ** 0.5) * i
    return np.c_[np.cos(theta) * np.sin(phi), np.sin(theta) * np.sin(phi), np.cos(phi)]


def solve_trackball_center(ball_centers, R, guess):
    from scipy.optimize import least_squares
    P = np.asarray(ball_centers)
    sol = least_squares(lambda c: np.linalg.norm(P - c, axis=1) - R, guess)
    return sol.x


def contact_forces(us):
    """Static equilibrium of the trackball under gravity (-Z) on three frictionless
    contacts with unit outward directions us (from trackball centre to ball centre).
    Returns the contact forces in units of the trackball weight."""
    N = np.array([-u for u in us]).T           # contact normals pointing into the ball
    F = np.linalg.solve(N, np.array([0, 0, 1.0]))
    return F


def holding_capacity(us):
    """largest horizontal push (in units of the trackball weight), in the worst direction, that the
    three contacts can resist before one of them unloads (stock case: 0.42)"""
    N = np.array([-u for u in us]).T
    worst = 1e9
    for phi in np.linspace(0, 2 * np.pi, 72, endpoint=False):
        d = np.array([np.cos(phi), np.sin(phi), 0.0])
        lo, hi = 0.0, 5.0
        for _ in range(30):
            mid = (lo + hi) / 2
            F = np.linalg.solve(N, np.array([0, 0, 1.0]) + mid * d)
            if np.all(F > 0):
                lo = mid
            else:
                hi = mid
        worst = min(worst, lo)
    return worst


def measure_seat_from_mesh(tm, C, u):
    """Re-measure one built seat from the output mesh: floor plane and washer-bore radius."""
    fc, fn, fa = tm.triangles_center, tm.face_normals, tm.area_faces
    d = fc - C
    t = d @ u
    rho = np.linalg.norm(d - np.outer(t, u), axis=1)
    floor = (fn @ u < -0.999) & (rho < CB_R_MODEL - 0.1) & (np.abs(t - T_FLOOR) < 0.5)
    t_floor = float(np.average(t[floor], weights=fa[floor])) if floor.any() else float("nan")
    wall = (np.abs(fn @ u) < 0.01) & (t > T_STEP + 0.3) & (t < T_FLOOR - 0.3) & (rho < CB_R_MODEL + 0.3)
    r_bore = float(np.median(rho[wall])) if wall.any() else float("nan")
    capw = (np.abs(fn @ u) < 0.01) & (t > T_STEP - 0.4) & (t < T_STEP - 0.05) & (rho > CB_R_MODEL + 0.1) & (rho < CAPBORE_R_MODEL + 0.3)
    r_cap = float(np.median(rho[capw])) if capw.any() else float("nan")
    step = (fn @ u < -0.999) & (rho > CB_R_MODEL) & (rho < CAPBORE_R_MODEL) & (np.abs(t - T_STEP) < 0.3)
    t_step = float(np.average(t[step], weights=fa[step])) if step.any() else float("nan")
    return dict(t_floor=t_floor, washer_bore_dia=2 * r_bore, cap_bore_dia=2 * r_cap, t_step=t_step,
                implied_ball_center_t_fresh=t_floor - WASHER_T - DROP,
                implied_ball_center_t_bedded=t_floor - WASHER_T - DROP + BEDDING_BIAS)


def inside_points(tm, pts, chunk=1500):
    """point-in-solid test via closest surface point and its face normal (no ray casting:
    trimesh's ray-based contains() needs gigabytes on a 77k-face mesh)."""
    from trimesh.proximity import closest_point
    out = np.empty(len(pts), dtype=bool)
    for i in range(0, len(pts), chunk):
        p = pts[i:i + chunk]
        cp, d, tid = closest_point(tm, p)
        out[i:i + chunk] = ((p - cp) * tm.face_normals[tid]).sum(1) < 0
    return out


def gap_points_to_mesh(tm, pts, chunk=1500):
    """unsigned distance of points to the (cropped) mesh surface, chunked to bound memory.
    The sign is not needed for the trackball check: the R17.3 containment test below catches penetration."""
    from trimesh.proximity import closest_point
    out = np.empty(len(pts))
    for i in range(0, len(pts), chunk):
        _, d, _ = closest_point(tm, pts[i:i + chunk])
        out[i:i + chunk] = d
    return out


# ---------------------------------------------------------------------------
#  main build
# ---------------------------------------------------------------------------
def build(side, outdir, do_step=True, meas_path="stock_measurements.json", stock_dir="../stock/repaired"):
    t_start = time.time()
    os.makedirs(outdir, exist_ok=True)
    meas = load_measurements(meas_path, side)
    Cbowl = np.array(meas["bowl_center"])
    Ctb = np.array(meas["trackball_center"])
    stock_path = os.path.join(stock_dir, f"keyball_trackball_case_{side}_repaired.stl")
    stock = trimesh.load(stock_path)
    assert stock.is_watertight, "stock mesh must be watertight (run the repair first)"
    report = dict(side=side, params=dict(
        TRACKBALL_D=TRACKBALL_D, BALL_D=BALL_D, WASHER_ID=WASHER_ID, WASHER_OD=WASHER_OD, WASHER_T=WASHER_T,
        CONTACT_R=CONTACT_R, BEDDING_BIAS=BEDDING_BIAS, BOSS_D=BOSS_D, BOSS_BLEND=BOSS_BLEND, CB_D=CB_D,
        CAP_BORE_D=CAP_BORE_D, PRINT_UNDERSIZE=PRINT_UNDERSIZE, CAP_STEP_ABOVE_WASHER=CAP_STEP_ABOVE_WASHER,
        CAP_HOLE_D=CAP_HOLE_D, CAP_OD_NOMINAL=CAP_OD_NOMINAL, CAP_OD_VARIANTS=CAP_OD_VARIANTS,
        CAP_RIM_T=CAP_RIM_T, CAP_HUB_T=CAP_HUB_T, CAP_HUB_R=CAP_HUB_R, CAP_CHAMFER_R=CAP_CHAMFER_R,
        Z_MIN_NEW=Z_MIN_NEW, REMOVE_STOCK_POCKETS=REMOVE_STOCK_POCKETS, ENVELOPE_CLEARANCE=ENVELOPE_CLEARANCE),
        stack=dict(DROP=DROP, T_BALL_FRESH=T_BALL_FRESH, T_BALL_BEDDED=T_BALL_BEDDED, T_WASHER_TOP=T_WASHER_TOP,
                   T_FLOOR=T_FLOOR, T_STEP=T_STEP, T_END=T_END, CB_DIA_MODELLED=2 * CB_R_MODEL,
                   CAP_BORE_DIA_MODELLED=2 * CAPBORE_R_MODEL, BALL_BOTTOM_TO_FLOOR_FRESH=T_FLOOR - (T_BALL_FRESH + BALL_R),
                   BALL_BOTTOM_TO_FLOOR_BEDDED=T_FLOOR - (T_BALL_BEDDED + BALL_R),
                   BALL_HANG_BELOW_WASHER_FACE=(T_BALL_FRESH + BALL_R) - T_WASHER_TOP),
        stock=dict(bowl_center=Cbowl.tolist(), bowl_radius=meas["bowl_radius"], trackball_center=Ctb.tolist(),
                   trackball_center_offset_from_bowl_center=meas["trackball_center_offset_from_bowl_center"],
                   pockets=meas["pockets"]))

    # --- seats
    seats = []
    for s in SEATS:
        az = s["az"] if side == "right" else 180.0 - s["az"]
        u = unit(az, s["el"])
        seats.append(dict(name=s["name"], az=az, el=s["el"], u=u, note=s["note"],
                          ball_center_bedded=(Ctb + T_BALL_BEDDED * u), ball_center_fresh=(Ctb + T_BALL_FRESH * u)))
    print("seats:")
    for s in seats:
        print(f"  {s['name']}: az={s['az']:.2f} el={s['el']:.2f} ball centre (bedded) {np.round(s['ball_center_bedded'],4)}")

    # trackball centre while the seats are fresh (all three balls BEDDING_BIAS closer to TB)
    Ctb_fresh = solve_trackball_center([s["ball_center_fresh"] for s in seats], TRACKBALL_D / 2 + BALL_R, Ctb)

    # --- B-rep tools
    print("building tool solids ...")
    tools = [seat_tools(Ctb, s["u"], Cbowl) for s in seats]
    ptools = []
    if REMOVE_STOCK_POCKETS:
        for p in meas["pockets"]:
            ptools.append(pocket_tools(Cbowl, np.array(p["axis_dir"]), p["t_floor_from_bowl_center"]))
    envelope = [sphere(TRACKBALL_D / 2 + ENVELOPE_CLEARANCE, c) for c in (Ctb, Ctb_fresh)]
    slot_hull_tm = wall_feature_hull(stock, Cbowl, SLOT_AZ_WINDOW, SLOT_EL_WINDOW, side,
                                     exclude_axes=[np.array(p["axis_dir"]) for p in meas["pockets"]])

    # --- mesh booleans
    print("mesh booleans (manifold3d) ...")
    t0 = time.time()
    M = tm_to_manifold(stock)
    M_slot = tm_to_manifold(slot_hull_tm)
    for pt in ptools:
        M = M + (tm_to_manifold(solid_to_trimesh(pt["plug"])) - M_slot)
    for pt in ptools:
        M = M - tm_to_manifold(solid_to_trimesh(pt["shave"]))
    for tl in tools:
        M = M + tm_to_manifold(solid_to_trimesh(tl["boss"]))
    for tl in tools:
        M = M - tm_to_manifold(solid_to_trimesh(tl["cap_bore"]))
        M = M - tm_to_manifold(solid_to_trimesh(tl["washer_bore"]))
    for c in (Ctb, Ctb_fresh):
        # 256 segments: chord sagitta 0.0013 mm at R17.35, far below the clearance being enforced
        M = M - m3d.Manifold.sphere(TRACKBALL_D / 2 + ENVELOPE_CLEARANCE, 256).translate(c.tolist())
    final = manifold_to_tm(M)
    final_clean = clean_for_proximity(final)
    print(f"  done in {time.time()-t0:.1f}s: faces={len(final.faces)} manifold={M.status()} bodies={final.body_count} volume={final.volume:.1f} (stock {stock.volume:.1f})")
    stl_path = os.path.join(outdir, f"keyball_ptfe_seat_case_{side}.stl")
    final.export(stl_path)
    report["case_stl"] = os.path.basename(stl_path)
    report["case_volume_mm3"] = float(final.volume)
    report["case_mesh_manifold"] = str(M.status())
    report["case_mesh_bodies"] = int(final.body_count)
    report["stock_volume_mm3"] = float(stock.volume)

    # --- checks -------------------------------------------------------------
    chk = {}
    # 1. ball centres at CONTACT_R from the trackball centre (design + re-measured from the mesh)
    seat_checks = []
    for s, tl in zip(seats, tools):
        mm = measure_seat_from_mesh(final_clean, Ctb, s["u"])
        d_bedded = float(np.linalg.norm(s["ball_center_bedded"] - Ctb))
        seat_checks.append(dict(name=s["name"], az_deg=s["az"], el_deg=s["el"], ray_dir=s["u"].tolist(), note=s["note"],
                                ball_center_bedded=s["ball_center_bedded"].tolist(), ball_center_fresh=s["ball_center_fresh"].tolist(),
                                dist_from_trackball_center_bedded=d_bedded,
                                dist_from_trackball_center_fresh=float(np.linalg.norm(s["ball_center_fresh"] - Ctb)),
                                mesh_measured=mm,
                                pass_19p5=abs(d_bedded - CONTACT_R) <= 0.02 and abs(mm["implied_ball_center_t_bedded"] - CONTACT_R) <= 0.02))
    chk["seats"] = seat_checks
    # angular spread
    spreads = {}
    for i in range(3):
        for j in range(i + 1, 3):
            a, b = seats[i], seats[j]
            daz = abs((a["az"] - b["az"] + 180) % 360 - 180)
            ang3d = math.degrees(math.acos(np.clip(a["u"] @ b["u"], -1, 1)))
            spreads[f"{a['name']}-{b['name']}"] = dict(azimuth_deg=daz, angle_3d_deg=ang3d)
    chk["contact_spread"] = spreads
    chk["contact_spread_pass"] = all(v["azimuth_deg"] >= 90 for v in spreads.values())
    chk["all_below_equator"] = all(s["el"] < 0 for s in seats)      # informational: the stock case has two contacts above it
    F = contact_forces([s["u"] for s in seats])
    chk["contact_forces_x_weight"] = dict(zip([s["name"] for s in seats], F.tolist()))
    chk["gravity_stable"] = bool(np.all(F > 0))
    chk["max_contact_load_x_weight"] = float(F.max())
    chk["lateral_holding_x_weight"] = float(holding_capacity([s["u"] for s in seats]))
    chk["loads_pass"] = bool(np.all(F > 0) and F.max() <= 2.0)

    # 2. trackball centre in the fresh (biased) state
    chk["trackball_center_bedded"] = Ctb.tolist()
    chk["trackball_center_fresh"] = Ctb_fresh.tolist()
    chk["trackball_rise_when_fresh"] = (Ctb_fresh - Ctb).tolist()
    chk["trackball_center_vs_stock_derived"] = 0.0     # we build from the stock-derived centre itself
    chk["trackball_center_vs_bowl_fit_center"] = float(np.linalg.norm(Ctb - Cbowl))

    # 3. trackball vs case clearance (both states)
    dirs = fibonacci_sphere(20000)
    # only faces near the trackball can be the closest ones: crop the mesh (speed + memory)
    near = np.linalg.norm(final_clean.triangles_center - Ctb, axis=1) < TRACKBALL_D / 2 + 4.0
    crop = final_clean.submesh([np.where(near)[0]], append=True)
    for state, c in (("bedded", Ctb), ("fresh", Ctb_fresh)):
        pts = c + (TRACKBALL_D / 2) * dirs
        gap = gap_points_to_mesh(crop, pts)
        i = int(np.argmin(gap))
        # penetration test (exact, boolean): the R(17 + clearance) sphere must not intersect the case solid
        pen = (M ^ m3d.Manifold.sphere(TRACKBALL_D / 2 + CLEARANCE_MIN - 0.002, 256).translate(c.tolist())).volume()
        chk[f"trackball_case_min_gap_{state}"] = float(gap.min())
        chk[f"trackball_case_min_gap_at_{state}"] = dict(point=pts[i].tolist(), az_el=list(az_el(dirs[i])))
        chk[f"trackball_case_penetration_mm3_{state}"] = float(pen)
        chk[f"trackball_case_clearance_pass_{state}"] = bool(gap.min() >= CLEARANCE_MIN and pen < 1e-6)

    # 4. caps: clearance to the seated 5 mm ball and to the trackball (2-D, rotationally symmetric)
    rhos = np.linspace(CAP_HOLE_D / 2, max(CAP_OD_VARIANTS) / 2, 400)
    cap_chk = {}
    for state, tb, cc in (("fresh", T_BALL_FRESH, Ctb_fresh), ("bedded", T_BALL_BEDDED, Ctb)):
        # underside at T_STEP (flat); ball surface (towards the trackball) at tb - sqrt(R^2 - rho^2)
        ball_surf = np.where(rhos < BALL_R, tb - np.sqrt(np.clip(BALL_R ** 2 - rhos ** 2, 0, None)), np.inf)
        gap_ball = float(np.min(ball_surf - T_STEP))
        # ball radial clearance through the hole at the underside plane
        r_ball_at_step = math.sqrt(max(BALL_R ** 2 - (tb - T_STEP) ** 2, 0))
        # cap top (towards trackball) at T_STEP - thickness(rho); trackball surface along the ray, offset by
        # the fresh-state shift of the trackball centre (projected on this seat's ray, worst case over seats)
        gaps_tb = []
        for s in seats:
            shift = float((cc - Ctb) @ s["u"])
            tb_surf = shift + np.sqrt((TRACKBALL_D / 2) ** 2 - rhos ** 2)   # distance from Ctb along ray
            cap_top = T_STEP - np.array([cap_profile_thickness(r) for r in rhos])
            gaps_tb.append(float(np.min(cap_top - tb_surf)))
        cap_chk[state] = dict(cap_underside_to_ball_min=gap_ball, ball_radius_at_cap_plane=r_ball_at_step,
                              hole_radial_clearance=CAP_HOLE_D / 2 - r_ball_at_step,
                              cap_top_to_trackball_min=min(gaps_tb),
                              pass_=(gap_ball >= CLEARANCE_MIN and min(gaps_tb) >= CLEARANCE_MIN and CAP_HOLE_D / 2 > r_ball_at_step))
    chk["caps"] = cap_chk
    chk["cap_pass"] = all(v["pass_"] for v in cap_chk.values())

    # 5. difference to stock must be confined to the seat zones / old pockets; protected regions untouched
    added = manifold_to_tm(M - tm_to_manifold(stock))
    removed = manifold_to_tm(tm_to_manifold(stock) - M)
    chk["added_volume_mm3"] = float(added.volume) if len(added.faces) else 0.0
    chk["removed_volume_mm3"] = float(removed.volume) if len(removed.faces) else 0.0
    chk["added_material_bounds"] = added.bounds.tolist() if len(added.faces) else None
    # lowest genuinely new surface: added-material vertices farther than 0.25 mm from any stock surface
    # (this ignores hairline slivers where a boss fills a crevice between two stock walls)
    if len(added.faces):
        from trimesh.proximity import closest_point
        stock_clean = clean_for_proximity(stock)
        av = added.vertices
        dist_stock = np.empty(len(av))
        for i in range(0, len(av), 2000):
            _, dist_stock[i:i + 2000], _ = closest_point(stock_clean, av[i:i + 2000])
        newv = av[np.nan_to_num(dist_stock, nan=1.0) > 0.25]
        chk["added_material_zmin"] = float(newv[:, 2].min())
        chk["added_material_zmin_pass"] = bool(newv[:, 2].min() >= Z_MIN_NEW - 1e-3)
    else:
        chk["added_material_zmin"] = None
        chk["added_material_zmin_pass"] = True

    def in_zone(p):
        for s in seats:
            d = p - Ctb
            t = d @ s["u"]
            rho = np.linalg.norm(d - t * s["u"])
            if BORE_START - 0.5 <= t <= T_END + 0.5 and rho <= BOSS_R + BOSS_BLEND + 0.5:
                return True
        for pk in meas["pockets"]:
            dv = np.array(pk["axis_dir"])
            d = p - Cbowl
            t = d @ dv
            rho = np.linalg.norm(d - t * dv)
            if 15.5 <= t <= 19.6 and rho <= POCKET_SHAVE_R + 0.3:
                return True
        return False

    stray = []
    for name, dm in (("added", added), ("removed", removed)):
        if len(dm.faces) == 0:
            continue
        for body in dm.split(only_watertight=False):
            if body.volume < 1e-6:
                continue
            c = body.centroid
            if not in_zone(c):
                stray.append(dict(kind=name, centroid=c.tolist(), volume=float(body.volume), bounds=body.bounds.tolist()))
    chk["stray_modifications"] = stray
    chk["modifications_confined_pass"] = len(stray) == 0

    # protected regions (STL frame, right side; mirrored for left): base ring + sensor window, screw ears,
    # hex nut pocket in the pillar wall, the finger slot, the pillar itself must not lose material.
    def box_tm(xmin, xmax, ymin, ymax, zmin, zmax):
        if side == "left":
            xmin, xmax = -xmax, -xmin
        b = np.array([[xmin, ymin, zmin], [xmax, ymax, zmax]])
        return trimesh.creation.box(extents=b[1] - b[0], transform=trimesh.transformations.translation_matrix((b[0] + b[1]) / 2))

    def zcyl_tm(cx, cy, r, z0, z1):
        return trimesh.creation.cylinder(radius=r, height=z1 - z0, sections=256,
                                         transform=trimesh.transformations.translation_matrix([cx, cy, (z0 + z1) / 2]))
    # the pillar's outer envelope: convex hull of the stock faces on the pillar side of the bowl
    pil_sel = (stock.triangles_center[:, 0] > 96.0) if side == "right" else (stock.triangles_center[:, 0] < -96.0)
    pillar_hull = trimesh.convex.convex_hull(stock.vertices[np.unique(stock.faces[pil_sel])])
    protected = dict(
        base_hole_14mm=zcyl_tm(Cbowl[0], Cbowl[1], 6.95, 1.9, 3.42),
        # the sensor board stands vertically inside the pillar: lens + chip + board + header live here
        sensor_compartment=box_tm(96.7, 106.5, -101.6, -79.0, 1.9, 32.0),
        base_ring_and_screw_ears=manifold_to_tm(tm_to_manifold(box_tm(Cbowl[0] - 12, Cbowl[0] + 13.5, Cbowl[1] - 11, Cbowl[1] + 11, 1.9, 3.3))
                                                - tm_to_manifold(zcyl_tm(Cbowl[0], Cbowl[1], 7.05, 1.8, 3.4))),
        sensor_aperture=box_tm(94.9, 97.0, -93.0, -87.5, 17.5, 25.5),
        finger_slot=manifold_to_tm(tm_to_manifold(slot_hull_tm) - tm_to_manifold(solid_to_trimesh(sphere(STOCK_BOWL_R, Cbowl)))),
        pillar_exterior=manifold_to_tm(tm_to_manifold(box_tm(96.5, 111.0, -105.0, -76.0, 1.9, 37.0)) - tm_to_manifold(pillar_hull)),
    )
    # the three old pocket zones are intended modifications (plug + cone shave); the P3 pocket sits where
    # the shell merges into the base ring, so its plug legitimately fills a bore inside that region
    pocket_zone = None
    for pk in meas["pockets"]:
        z = tm_to_manifold(solid_to_trimesh(cyl(POCKET_SHAVE_R + 0.3, 15.5, 19.6, Cbowl, np.array(pk["axis_dir"]))))
        pocket_zone = z if pocket_zone is None else pocket_zone + z
    prot_res = {}
    for name, region in protected.items():
        if pocket_zone is not None:
            region = manifold_to_tm(tm_to_manifold(region) - pocket_zone)
        vol = 0.0
        for dm in (added, removed):
            if len(dm.faces) == 0:
                continue
            inter = manifold_to_tm(tm_to_manifold(dm) ^ tm_to_manifold(region))
            vol += float(inter.volume) if len(inter.faces) else 0.0
        prot_res[name] = dict(bounds=region.bounds.tolist(), modified_volume_mm3=vol, pass_=vol < 1e-2)
    chk["protected_regions"] = prot_res
    chk["protected_regions_pass"] = all(v["pass_"] for v in prot_res.values())

    # 6. backing behind each floor is solid; bores are open towards the trackball
    back_ok = []
    for s in seats:
        u = s["u"]
        # orthonormal frame
        a = np.array([1.0, 0, 0]) if abs(u[0]) < 0.9 else np.array([0, 1.0, 0])
        e1 = np.cross(u, a); e1 /= np.linalg.norm(e1); e2 = np.cross(u, e1)
        pts = []
        for t in np.linspace(T_FLOOR + 0.05, T_FLOOR + BACKING_MIN - 0.05, 8):
            for r in np.linspace(0, CB_R_MODEL, 6):
                for th in np.linspace(0, 2 * np.pi, 16, endpoint=False):
                    pts.append(Ctb + t * u + r * (np.cos(th) * e1 + np.sin(th) * e2))
        inside = inside_points(final_clean, np.array(pts))
        # open path: points on the axis from the bowl to the floor must be outside the solid
        axis_pts = np.array([Ctb + t * u for t in np.linspace(T_STEP - 1.0, T_FLOOR - 0.05, 40)])
        open_ = ~inside_points(final_clean, axis_pts)
        back_ok.append(dict(name=s["name"], backing_solid=bool(inside.all()), backing_fraction=float(inside.mean()),
                            bore_open=bool(open_.all())))
    chk["backing"] = back_ok
    chk["backing_pass"] = all(b["backing_solid"] and b["bore_open"] for b in back_ok)

    chk["overall_pass"] = all([all(s["pass_19p5"] for s in seat_checks), chk["contact_spread_pass"],
                               chk["gravity_stable"], chk["loads_pass"], chk["trackball_case_clearance_pass_bedded"], chk["trackball_case_clearance_pass_fresh"],
                               chk["cap_pass"], chk["added_material_zmin_pass"], chk["modifications_confined_pass"],
                               chk["protected_regions_pass"], chk["backing_pass"]])
    report["checks"] = chk
    print("checks:")
    print(f"  contact loads x weight: {chk['contact_forces_x_weight']}  max {chk['max_contact_load_x_weight']:.2f}  lateral holding {chk['lateral_holding_x_weight']:.2f}")
    for k in ["contact_spread_pass", "all_below_equator", "gravity_stable", "loads_pass", "trackball_case_clearance_pass_bedded",
              "trackball_case_clearance_pass_fresh", "cap_pass", "added_material_zmin_pass", "modifications_confined_pass",
              "protected_regions_pass", "backing_pass", "overall_pass"]:
        print(f"  {k}: {chk[k]}")
    for s in seat_checks:
        print(f"  {s['name']}: |ball-C|={s['dist_from_trackball_center_bedded']:.4f} mesh floor t={s['mesh_measured']['t_floor']:.4f} "
              f"-> implied bedded centre t={s['mesh_measured']['implied_ball_center_t_bedded']:.4f} washer bore {s['mesh_measured']['washer_bore_dia']:.3f} cap bore {s['mesh_measured']['cap_bore_dia']:.3f} pass={s['pass_19p5']}")
    print(f"  trackball-case min gap: bedded {chk['trackball_case_min_gap_bedded']:.3f} fresh {chk['trackball_case_min_gap_fresh']:.3f}")
    print(f"  caps: {json.dumps(cap_chk)}")
    print(f"  added zmin {chk['added_material_zmin']}, stray mods {len(stray)}, protected " + json.dumps({k: (round(v['modified_volume_mm3'], 4), v['pass_']) for k, v in prot_res.items()}))

    # --- caps and coupon --------------------------------------------------------
    for od in CAP_OD_VARIANTS:
        cap = make_cap(od)
        base = os.path.join(outdir, f"cap_ring_OD{od:.1f}_hole{CAP_HOLE_D:.1f}")
        cq.exporters.export(cap, base + ".step")
        cq.exporters.export(cap, base + ".stl", tolerance=0.002, angularTolerance=0.05)
    coupon, cinfo = make_coupon()
    cq.exporters.export(coupon, os.path.join(outdir, "test_coupon_seat.step"))
    cq.exporters.export(coupon, os.path.join(outdir, "test_coupon_seat.stl"), tolerance=0.002, angularTolerance=0.05)
    report["coupon"] = cinfo

    # --- STEP of the case (OpenCascade B-rep booleans with the same tools) -------------
    if do_step:
        print("STEP route: sewing stock mesh into an OCC solid ...")
        t0 = time.time()
        occ = trimesh_to_occ_solid(stock)
        try:
            occ = unify(occ)
        except Exception as e:
            print("  unify failed (continuing):", e)
        print(f"  solid: valid={occ.isValid()} volume={occ.Volume():.1f} ({time.time()-t0:.1f}s)")
        wp = cq.Workplane().add(occ)
        slot_occ = trimesh_to_occ_solid(slot_hull_tm)
        for pt in ptools:
            wp = wp.union(cq.Workplane().add(pt["plug"]).cut(cq.Workplane().add(slot_occ)))
        for pt in ptools:
            wp = wp.cut(cq.Workplane().add(pt["shave"]))
        for tl in tools:
            wp = wp.union(cq.Workplane().add(tl["boss"]))
        for tl in tools:
            wp = wp.cut(cq.Workplane().add(tl["cap_bore"])).cut(cq.Workplane().add(tl["washer_bore"]))
        for env in envelope:
            wp = wp.cut(cq.Workplane().add(env))
        res = wp.val()
        print(f"  booleans done ({time.time()-t0:.1f}s): valid={res.isValid()} volume={res.Volume():.1f} (mesh route {final.volume:.1f})")
        step_path = os.path.join(outdir, f"keyball_ptfe_seat_case_{side}.step")
        cq.exporters.export(wp, step_path)
        report["case_step"] = os.path.basename(step_path)
        report["case_step_volume_mm3"] = float(res.Volume())
        report["case_step_size_MB"] = os.path.getsize(step_path) / 1e6
        print(f"  wrote {step_path} ({report['case_step_size_MB']:.1f} MB, {time.time()-t0:.1f}s)")

    report["build_seconds"] = time.time() - t_start
    json.dump(report, open(os.path.join(outdir, f"build_report_{side}.json"), "w"), indent=1, default=float)
    print(f"total {report['build_seconds']:.0f}s; overall_pass={chk['overall_pass']}")
    return report


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--side", default="right", choices=["right", "left"])
    ap.add_argument("--out", default="../output")
    ap.add_argument("--no-step", action="store_true")
    ap.add_argument("--measurements", default="stock_measurements.json")
    ap.add_argument("--stock-dir", default="../stock/repaired")
    a = ap.parse_args()
    r = build(a.side, a.out, do_step=not a.no_step, meas_path=a.measurements, stock_dir=a.stock_dir)
    sys.exit(0 if r["checks"]["overall_pass"] else 1)
