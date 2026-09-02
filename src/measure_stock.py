#!/usr/bin/env python3
"""
measure_stock.py - reverse-engineer the reference geometry of kepeo's
"Keyball Trackball Case" (Thingiverse thing:6215791, CC BY) from the STL.

Outputs stock_measurements.json with:
  * bowl sphere fit (inner R18 bowl) -> "bowl_center", "bowl_radius"
  * the three original 2 mm ceramic-ball pockets: bore axis, bore diameter,
    flat-floor position, implied 2 mm ball centre
  * the trackball centre = point 18.0 mm (17 + 1) from the three implied
    2 mm ball centres (the rule from the task spec), plus the deviation of
    that point from the bowl-fit centre.

Usage: python measure_stock.py [--stl path] [--out json]
"""
import argparse, json, sys
import numpy as np
import trimesh
from scipy.optimize import least_squares
from scipy.spatial import cKDTree
import scipy.sparse as sp
import scipy.sparse.csgraph as csg

TRACKBALL_R = 17.0          # 34 mm trackball
STOCK_BALL_R = 1.0          # 2 mm ceramic balls
STOCK_CONTACT_R = TRACKBALL_R + STOCK_BALL_R   # 18.0


def fit_sphere(P):
    A = np.c_[2 * P, np.ones(len(P))]
    b = (P ** 2).sum(1)
    x, *_ = np.linalg.lstsq(A, b, rcond=None)
    c = x[:3]
    r = np.sqrt(max(x[3] + c @ c, 0.0))
    return c, r, np.abs(np.linalg.norm(P - c, axis=1) - r)


def fit_bowl(m):
    """Fit the inner spherical bowl (inward-facing faces ~R18)."""
    fc, fn = m.triangles_center, m.face_normals
    # coarse Hough search for the centre
    best = None
    lo, hi = m.bounds
    for x in np.arange(lo[0], hi[0], 1.0):
        for y in np.arange(lo[1], hi[1], 1.0):
            for z in np.arange(lo[2], hi[2], 1.0):
                c = np.array([x, y, z])
                d = fc - c
                dist = np.linalg.norm(d, axis=1)
                cosang = (fn * d).sum(1) / np.maximum(dist, 1e-9)
                score = ((cosang < -0.98) & (dist > 15.5) & (dist < 19.5)).sum()
                if best is None or score > best[0]:
                    best = (score, c)
    c0 = best[1]
    for _ in range(6):
        d = fc - c0
        dist = np.linalg.norm(d, axis=1)
        cosang = (fn * d).sum(1) / dist
        sel = np.where((cosang < -0.995) & (dist > 15.5) & (dist < 19.5))[0]
        c, r, res = fit_sphere(fc[sel])
        sel = sel[res < 0.05]
        c, r, res = fit_sphere(fc[sel])
        c0 = c
    return c, r, len(sel), float(np.median(res)), float(res.max())


def find_pockets(m, C):
    """Locate small features on the bowl wall (the raised cones around the
    2 mm ball pockets) by clustering non-radial faces near R18."""
    fc, fn = m.triangles_center, m.face_normals
    d = fc - C
    dist = np.linalg.norm(d, axis=1)
    u = d / dist[:, None]
    cosang = (fn * d).sum(1) / dist
    cand = np.where((dist > 17.3) & (dist < 18.0) & (cosang > -0.98))[0]
    P = fc[cand]
    tree = cKDTree(P)
    pairs = tree.query_pairs(0.6, output_type="ndarray")
    G = sp.coo_matrix((np.ones(len(pairs)), (pairs[:, 0], pairs[:, 1])), shape=(len(P), len(P)))
    n, lab = csg.connected_components(G, directed=False)
    out = []
    for k in range(n):
        idx = np.where(lab == k)[0]
        if len(idx) < 40:
            continue
        Q = P[idx]
        ext = Q.max(0) - Q.min(0)
        if ext.max() > 6:      # not a small pocket
            continue
        uu = Q.mean(0) - C
        uu /= np.linalg.norm(uu)
        out.append(uu)
    return out


def fit_pocket(m, C, u0):
    fc, fn, fa = m.triangles_center, m.face_normals, m.area_faces
    p0 = C + STOCK_CONTACT_R * u0
    near = np.linalg.norm(fc - p0, axis=1) < 2.5
    Fc, N, A = fc[near], fn[near], fa[near]
    t0 = (Fc - C) @ u0
    rho0 = np.linalg.norm((Fc - C) - np.outer(t0, u0), axis=1)
    wall = (np.abs(N @ u0) < 0.25) & (rho0 < 1.5) & (t0 > 17.55) & (t0 < 18.95)
    Nw, Pw = N[wall], Fc[wall]
    w, v = np.linalg.eigh(Nw.T @ Nw)
    dvec = v[:, 0]
    if dvec @ u0 < 0:
        dvec = -dvec

    def resid(x):
        a = x[:3]
        dv = x[3:6] / np.linalg.norm(x[3:6])
        r = x[6]
        wv = Pw - a
        tt = wv @ dv
        perp = wv - np.outer(tt, dv)
        return np.linalg.norm(perp, axis=1) - r

    sol = least_squares(resid, np.r_[p0, dvec, 1.05])
    a = sol.x[:3]
    dvec = sol.x[3:6] / np.linalg.norm(sol.x[3:6])
    if dvec @ u0 < 0:
        dvec = -dvec
    r = float(sol.x[6])
    rms = float(np.sqrt(np.mean(sol.fun ** 2)))
    # flat floor: faces whose normal faces the bowl centre, on the axis
    tA = (Fc - C) @ dvec
    rhoA = np.linalg.norm((Fc - a) - np.outer((Fc - a) @ dvec, dvec), axis=1)
    floor = (N @ dvec < -0.9) & (rhoA < 1.1) & (tA > 18.6) & (tA < 19.6)
    t_floor = float(np.average(tA[floor], weights=A[floor]))
    # rim of the raised cone (mouth of the bore)
    mouth = (rhoA < 1.3)
    t_mouth = float(tA[mouth].min())
    # implied 2 mm ball centre: on the bore axis, 1 mm above the flat floor
    s = (t_floor - STOCK_BALL_R) - ((a - C) @ dvec)
    pc = a + s * dvec
    # how far the bore axis line passes from the bowl centre
    foot = a + ((C - a) @ dvec) * dvec
    return dict(axis_dir=dvec.tolist(),
                az_deg=float(np.degrees(np.arctan2(dvec[1], dvec[0]))),
                el_deg=float(np.degrees(np.arcsin(dvec[2]))),
                bore_dia=2 * r, bore_fit_rms=rms, n_bore_faces=int(wall.sum()),
                t_floor_from_bowl_center=t_floor, t_mouth_from_bowl_center=t_mouth,
                axis_miss_bowl_center=float(np.linalg.norm(foot - C)),
                ball_center=pc.tolist(),
                ball_center_dist_from_bowl_center=float(np.linalg.norm(pc - C)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stl", default="../stock/repaired/keyball_trackball_case_right_repaired.stl")
    ap.add_argument("--out", default="stock_measurements.json")
    a = ap.parse_args()
    m = trimesh.load(a.stl)
    C, R, n, resmed, resmax = fit_bowl(m)
    print(f"bowl: center={np.round(C,4)} R={R:.4f} faces={n} res_med={resmed:.4f} res_max={resmax:.4f}")
    dirs = find_pockets(m, C)
    pockets = [fit_pocket(m, C, u) for u in dirs]
    # sort by azimuth for stable naming
    pockets.sort(key=lambda p: -p["el_deg"])
    for i, p in enumerate(pockets):
        p["name"] = f"P{i+1}"
        print(f"{p['name']}: az={p['az_deg']:.3f} el={p['el_deg']:.3f} bore={p['bore_dia']:.3f} floor_t={p['t_floor_from_bowl_center']:.3f} "
              f"mouth_t={p['t_mouth_from_bowl_center']:.3f} axis_miss={p['axis_miss_bowl_center']:.3f} |ball-C|={p['ball_center_dist_from_bowl_center']:.4f}")
    if len(pockets) != 3:
        sys.exit(f"expected 3 pockets, found {len(pockets)}")
    P = np.array([p["ball_center"] for p in pockets])

    def f(c):
        return np.linalg.norm(P - c, axis=1) - STOCK_CONTACT_R

    sol = least_squares(f, C + np.array([0.3, -0.2, 0.1]))
    Ctb = sol.x
    print(f"trackball center (18.0 from all three 2 mm ball centres): {np.round(Ctb,4)}  residuals={np.round(f(Ctb),5)}  |Ctb-bowl|={np.linalg.norm(Ctb-C):.4f}")
    out = dict(source_stl=a.stl,
               bowl_center=C.tolist(), bowl_radius=float(R), bowl_fit_faces=int(n),
               bowl_fit_residual_median=resmed, bowl_fit_residual_max=resmax,
               pockets=pockets,
               stock_contact_radius=STOCK_CONTACT_R,
               trackball_center=Ctb.tolist(),
               trackball_center_residuals=f(Ctb).tolist(),
               trackball_center_offset_from_bowl_center=float(np.linalg.norm(Ctb - C)),
               trackball_center_offset_vector=(Ctb - C).tolist())
    json.dump(out, open(a.out, "w"), indent=1)
    print("wrote", a.out)


if __name__ == "__main__":
    main()
