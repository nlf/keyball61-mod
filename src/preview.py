#!/usr/bin/env python3
"""preview.py - section views through each seat and 3-D views of the built case (docs/img)."""
import json, math, os, sys
import numpy as np, trimesh, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
import ptfe_seat_case as P

side = sys.argv[1] if len(sys.argv) > 1 else "right"
out = sys.argv[2] if len(sys.argv) > 2 else "../docs/img"
os.makedirs(out, exist_ok=True)
meas = P.load_measurements("stock_measurements.json", side)
Ctb = np.array(meas["trackball_center"]); Cb = np.array(meas["bowl_center"])
new = trimesh.load(f"../output/keyball_ptfe_seat_case_{side}.stl")
stock = trimesh.load(f"../stock/repaired/keyball_trackball_case_{side}_repaired.stl")

def section_plot(ax, mesh, origin, normal, e1, e2, color, lw=0.8):
    s = mesh.section(plane_origin=origin, plane_normal=normal)
    if s is None: return
    for ent in s.entities:
        pts = s.vertices[ent.points] - origin
        ax.plot(pts @ e1, pts @ e2, "-", color=color, lw=lw)

fig, axs = plt.subplots(1, 3, figsize=(21, 7))
for ax, seat in zip(axs, P.SEATS):
    az = seat["az"] if side == "right" else 180 - seat["az"]
    u = P.unit(az, seat["el"])
    # plane containing the ray and the global Z axis
    zdir = np.array([0, 0, 1.0])
    n = np.cross(u, zdir); n /= np.linalg.norm(n)
    e1 = u; e2 = np.cross(n, u)
    section_plot(ax, stock, Ctb, n, e1, e2, "lightgray", 1.5)
    section_plot(ax, new, Ctb, n, e1, e2, "k")
    # trackball, 5 mm ball, washer, cap outlines
    th = np.linspace(0, 2 * np.pi, 200)
    ax.plot(17 * np.cos(th), 17 * np.sin(th), "b--", lw=0.7, label="trackball R17")
    ax.plot(P.T_BALL_FRESH + 2.5 * np.cos(th), 2.5 * np.sin(th), "r-", lw=0.8, label="5 mm ball (fresh)")
    ax.plot(P.T_BALL_BEDDED + 2.5 * np.cos(th), 2.5 * np.sin(th), "r:", lw=0.8, label="5 mm ball (bedded)")
    for sgn in (1, -1):
        ax.add_patch(plt.Rectangle((P.T_WASHER_TOP, sgn * 1.5 if sgn > 0 else -4.25), 2.0, 2.75, fill=False, ec="g", lw=0.8))
        rhos = np.linspace(2.2, P.CAP_OD_NOMINAL / 2, 30)
        top = [P.T_STEP - P.cap_profile_thickness(r) for r in rhos]
        ax.fill_betweenx(sgn * rhos, top, P.T_STEP, color="orange", alpha=0.6)
    ax.set_xlim(14, 27); ax.set_ylim(-8, 8); ax.set_aspect("equal"); ax.grid(True, lw=0.3)
    ax.set_title(f"{seat['name']}  az={az:.0f} el={seat['el']:.0f}   (section along contact ray, +Z up-ish)")
    ax.set_xlabel("distance from trackball centre along ray [mm]")
axs[0].legend(loc="upper left", fontsize=8)
plt.tight_layout(); plt.savefig(os.path.join(out, f"seat_sections_{side}.png"), dpi=80)

fig = plt.figure(figsize=(21, 7))
light = np.array([0.3, 0.5, 0.8]); light /= np.linalg.norm(light)
for i, (el, azv) in enumerate([(35, -60), (25, 200), (-35, 30)]):
    ax = fig.add_subplot(1, 3, i + 1, projection="3d")
    tri = new.vertices[new.faces]
    shade = 0.35 + 0.65 * np.clip(new.face_normals @ light, 0, 1)
    ax.add_collection3d(Poly3DCollection(tri, facecolors=plt.cm.gray(shade), edgecolor="none"))
    lo, hi = new.bounds
    ax.set_xlim(lo[0], hi[0]); ax.set_ylim(lo[1], hi[1]); ax.set_zlim(0, 40)
    ax.set_box_aspect((hi[0]-lo[0], hi[1]-lo[1], 40))
    ax.view_init(elev=el, azim=azv); ax.set_title(f"view elev={el} azim={azv}")
plt.tight_layout(); plt.savefig(os.path.join(out, f"case_views_{side}.png"), dpi=80)

# z-slices to show the bosses relative to the base
fig, axs = plt.subplots(1, 3, figsize=(21, 7))
for ax, z in zip(axs, (2.6, 6.0, 11.0)):
    section_plot(ax, stock, np.array([0, 0, z]), np.array([0, 0, 1.0]), np.array([1.0, 0, 0]), np.array([0, 1.0, 0]), "lightgray", 1.5)
    section_plot(ax, new, np.array([0, 0, z]), np.array([0, 0, 1.0]), np.array([1.0, 0, 0]), np.array([0, 1.0, 0]), "k")
    ax.set_aspect("equal"); ax.grid(True, lw=0.3); ax.set_title(f"z = {z} slice (grey = stock, black = new)")
plt.tight_layout(); plt.savefig(os.path.join(out, f"z_slices_{side}.png"), dpi=80)
print("wrote previews to", out)
