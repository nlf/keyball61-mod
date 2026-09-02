#!/usr/bin/env python3
"""layout_search.py - feasibility map for the three seat positions against the real obstacles
(sensor compartment in the pillar, Keyball61 switches/keycaps, mounting plane, slot, aperture).
Seat = boss cylinder along the contact ray from TB: t in [17.4, T_END], radius BOSS_R."""
import json, itertools, math, sys
import numpy as np
import ptfe_seat_case as P

meas = json.load(open("stock_measurements.json"))
TB = np.array(meas["trackball_center"]); Cb = np.array(meas["bowl_center"])
BOSS_R = float(sys.argv[1]) if len(sys.argv) > 1 else 5.5
KEYBOARD = sys.argv[2] if len(sys.argv) > 2 else "61"
KEYCAP_Z = float(sys.argv[3]) if len(sys.argv) > 3 else 13.0   # STL z of the keycap skirt bottom (fully pressed), PCB top is z=2

# STL <-> KiCad (right side): board plane at STL x~105 sits on the socket J2
if KEYBOARD == "61":
    J2 = (178.471, 132.545); sw = {"SW21": (175.11, 108.17), "SW22": (156.06, 103.47), "SW23": (137.01, 105.97),
                                   "SW27": (194.16, 134.22), "SW28": (111.452, 134.017), "SW24": (117.96, 108.47)}
    pcb_edge_y = 150.759
else:
    J2 = (176.440797, 113.450119); sw = {"SW15": (173.104426, 89.070516), "SW16": (154.054427, 84.370516), "SW17": (135.004427, 86.870516),
                                         "SW19": (192.154426, 115.120515), "SW20": (107.620426, 116.920516)}
    pcb_edge_y = 133.661
X0 = J2[0] - 105.0; Y0 = J2[1] - 90.3          # x_k = x_s + X0 ; y_k = Y0 - y_s
def k2s(xk, yk): return np.array([xk - X0, Y0 - yk])

# obstacles as axis-aligned boxes in the STL frame [xmin,xmax,ymin,ymax,zmin,zmax]
obst = {}
obst["sensor compartment (board+lens+header)"] = [96.7, 106.5, -101.6, -79.0, 2.0, 32.0]
obst["hex aperture / sensor window"] = [94.9, 97.0, -93.0, -87.5, 17.5, 25.5]
obst["mounting plane (z<2.2)"] = [-1e3, 1e3, -1e3, 1e3, -1e3, 2.2]
for name, (xk, yk) in sw.items():
    cx, cy = k2s(xk, yk)
    obst[f"{name} switch housing"] = [cx - 7.8, cx + 7.8, cy - 7.8, cy + 7.8, 2.0, 13.6]
    obst[f"{name} keycap"] = [cx - 9.3, cx + 9.3, cy - 9.3, cy + 9.3, KEYCAP_Z, 24.0]
# finger slot hull (from the stock mesh) as a box
obst["finger slot"] = [67.0, 74.6, -76.3, -71.2, 11.5, 24.0]
for n, b in obst.items():
    if "SW" in n and "keycap" in n: print(f"  {n}: STL x {b[0]:.1f}..{b[1]:.1f} y {b[2]:.1f}..{b[3]:.1f}")
print(f"keyboard {KEYBOARD}: ball centre in KiCad = ({TB[0]+X0:.1f}, {Y0-TB[1]:.1f}); PCB front edge at STL y = {Y0-pcb_edge_y:.1f}")

def boss_points(u, r=BOSS_R, t0=17.4, t1=P.T_END):
    a = np.array([1.0, 0, 0]) if abs(u[0]) < 0.9 else np.array([0, 1.0, 0])
    e1 = np.cross(u, a); e1 /= np.linalg.norm(e1); e2 = np.cross(u, e1)
    pts = []
    for t in np.linspace(t0, t1, 15):
        rr = r - P.BOSS_END_CHAMFER if t > t1 - P.BOSS_END_CHAMFER + 1e-6 else r   # end chamfer
        for th in np.linspace(0, 2 * np.pi, 24, endpoint=False):
            pts.append(TB + t * u + rr * (np.cos(th) * e1 + np.sin(th) * e2))
        pts.append(TB + t * u)
    return np.array(pts)

def hits(pts, b):
    return np.any((pts[:, 0] > b[0]) & (pts[:, 0] < b[1]) & (pts[:, 1] > b[2]) & (pts[:, 1] < b[3]) & (pts[:, 2] > b[4]) & (pts[:, 2] < b[5]))

def feasible(az, el):
    u = P.unit(az, el); pts = boss_points(u)
    # only the part of the boss outside the stock bowl wall matters for external obstacles: points with |p-Cb|>18
    ext = pts[np.linalg.norm(pts - Cb, axis=1) > 18.0]
    bad = [n for n, b in obst.items() if hits(ext, b)]
    return bad

azs = np.arange(-180, 180, 5); els = np.arange(-45, 46, 1)
feas = {}
for az in azs:
    for el in els:
        bad = feasible(az, el)
        if not bad: feas[(int(az), int(el))] = True
print("feasible (az -> el range):")
for az in azs:
    e = [el for el in els if (int(az), int(el)) in feas]
    if e: print(f"  az {az:5d}: el {min(e)} .. {max(e)}")

# rim elevation of the stock wall per azimuth (contact must be below the rim to be on the wall)
def rim_el(az):
    tab = {-175: -47, -165: -47.6, -155: -45.6, -145: -42, -135: -37.2, -125: -32.7, -115: -31.2, -105: -31.3, -95: -32.9, -85: -34.6, -75: -34.7, -65: -32.5, -55: -26.8, -45: -13.8, -35: 48.9, -25: 53.6, -15: 55.6, -5: 56.1, 5: 55.9, 15: 55.7, 25: 54.3, 35: 53.4, 45: 51.7, 55: 49.9, 65: 47.6, 75: 46.2, 85: 44, 95: 42, 105: 40.1, 115: 38.9, 125: 37.4, 135: 35.8, 145: 32.3, 155: 25.5, 165: -34.9, 175: -43.4}
    k = min(tab, key=lambda a: abs(((a - az + 180) % 360) - 180)); return tab[k]

def holding(us):
    """max lateral push (in units of ball weight) the three contacts can resist in the worst direction"""
    N = np.array([-u for u in us]).T
    best = 1e9
    for phi in np.linspace(0, 2 * np.pi, 72, endpoint=False):
        d = np.array([np.cos(phi), np.sin(phi), 0])
        lo, hi = 0.0, 5.0
        for _ in range(30):
            mid = (lo + hi) / 2
            F = np.linalg.solve(N, np.array([0, 0, 1.0]) + mid * d)
            if np.all(F > 0): lo = mid
            else: hi = mid
        best = min(best, lo)
    return best

# triples on a coarse grid; holding capacity only for the best by min azimuth gap
coarse = [k for k in feas if k[0] % 10 == 0 and k[1] % 3 == 0 and k[1] <= 0]
rows = []
for a, b, c in itertools.combinations(coarse, 3):
    azl = sorted([a[0], b[0], c[0]])
    gaps = [azl[1] - azl[0], azl[2] - azl[1], 360 - (azl[2] - azl[0])]
    if max(gaps) >= 180 or min(gaps) < 60: continue
    onwall = sum(1 for s in (a, b, c) if s[1] <= rim_el(s[0]) - 15)
    rows.append((min(gaps), onwall, (a, b, c), gaps))
rows.sort(key=lambda r: (-r[0], -r[1]))
print(f"\n{len(rows)} spanning triples; best by min azimuth gap:")
shown = 0
for r in rows[:400]:
    us = [P.unit(*s) for s in r[2]]
    h = holding(us)
    F = np.linalg.solve(np.array([-u for u in us]).T, np.array([0, 0, 1.0]))
    print(f"  min gap {r[0]:3d} gaps {r[3]} on-wall {r[1]} holding {h:.2f} loads {np.round(F,2)} seats {r[2]}")
    shown += 1
    if shown >= 25: break
for name, trip in (("stock", [(-3.07, 27.32), (123.46, 8.62), (-101.72, -60.93)]), ("previous", [(12, -25), (153, -28), (-110, -32)])):
    us = [P.unit(*s) for s in trip]; print(f"{name}: holding {holding(us):.2f}", [feasible(*s) for s in trip])
