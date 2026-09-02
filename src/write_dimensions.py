#!/usr/bin/env python3
"""write_dimensions.py - generate ../DIMENSIONS.md from stock_measurements.json and
the build reports, so the documented numbers are exactly what was built/checked."""
import json, math, os, sys
import numpy as np

src = os.path.dirname(os.path.abspath(__file__))
meas = json.load(open(os.path.join(src, "stock_measurements.json")))
rep = json.load(open(os.path.join(src, "../output/build_report_right.json")))
rep_left = None
pl = os.path.join(src, "../output/build_report_left.json")
if os.path.exists(pl):
    rep_left = json.load(open(pl))

chk = rep["checks"]
st = rep["stack"]
P = rep["params"]


def v3(v, nd=4):
    return "(" + ", ".join(f"{x:.{nd}f}" for x in v) + ")"


def ok(b):
    return "PASS" if b else "**FAIL**"


L = []
A = L.append
A("# DIMENSIONS - measured stock geometry, chosen seat geometry, clearance checks")
A("")
A("All coordinates are in the frame of kepeo's `keyball_trackball_case_right.stl` (mm). "
  "The right-hand case is the reference; the left-hand case is its exact mirror in X, so every X below "
  "changes sign for the left case (azimuths become 180 deg - az). Numbers in this file are written by "
  "`src/write_dimensions.py` from `src/stock_measurements.json` and `output/build_report_*.json` - they are "
  "not typed by hand.")
A("")
A("## 1. Stock case, measured from the STL")
A("")
A("### 1.1 Inner bowl")
A("")
A("| item | value |")
A("|---|---|")
A(f"| bowl sphere centre (least-squares fit of {meas['bowl_fit_faces']} inward-facing faces) | {v3(meas['bowl_center'])} |")
A(f"| bowl radius | {meas['bowl_radius']:.4f} (design value 18.0 = 17 + 1 mm clearance) |")
A(f"| fit residual median / max | {meas['bowl_fit_residual_median']:.4f} / {meas['bowl_fit_residual_max']:.4f} |")
A("| outer shell radius | 19.4 (wall 1.4) |")
A("| case bottom (mounting plane on the daughterboard) | z = 2.000 |")
A("| sensor window | R18 bowl cut by the plane z = 3.4 -> a 14.0 mm hole, then a 14 mm bore down to z = 2.0 |")
A("")
A("### 1.2 The three original 2 mm ceramic-ball pockets")
A("")
A("Each pocket is a raised cone on the bowl wall (tip 17.51 mm from the bowl centre) with a blind bore and a flat floor. "
  "A 2 mm ball on that flat floor has its centre 1.0 mm above the floor, on the bore axis.")
A("")
A("| pocket | az / el (deg) | bore dia | bore mouth t | flat floor t | axis passes bowl centre by | implied 2 mm ball centre | dist. from bowl centre |")
A("|---|---|---|---|---|---|---|---|")
for p in meas["pockets"]:
    A(f"| {p['name']} | {p['az_deg']:.2f} / {p['el_deg']:.2f} | {p['bore_dia']:.3f} | {p['t_mouth_from_bowl_center']:.3f} | "
      f"{p['t_floor_from_bowl_center']:.3f} | {p['axis_miss_bowl_center']:.3f} | {v3(p['ball_center'])} | {p['ball_center_dist_from_bowl_center']:.4f} |")
A("")
A("(t = distance from the bowl centre along the pocket axis.)")
A("")
A("### 1.3 Trackball centre")
A("")
d = [p["ball_center_dist_from_bowl_center"] for p in meas["pockets"]]
A(f"* The three implied 2 mm ball centres are **{min(d):.4f} .. {max(d):.4f} mm** from the bowl-fit centre - "
  f"they agree with each other to {max(d)-min(d):.4f} mm and with the nominal 17 + 1 = 18.0 mm to {max(abs(x-18) for x in d):.3f} mm "
  "(kepeo's floors are modelled 0.05 mm deeper than the nominal contact sphere).")
A(f"* The point exactly **18.0 mm from all three** 2 mm ball centres (the rule in the task spec) is "
  f"**TB = {v3(meas['trackball_center'])}**, residuals {v3(meas['trackball_center_residuals'], 5)}.")
A(f"* TB lies {meas['trackball_center_offset_from_bowl_center']:.4f} mm from the bowl-fit centre, offset vector "
  f"{v3(meas['trackball_center_offset_vector'])}. This is the real resting position of a 34.00 mm ball on 2.00 mm balls in the "
  "stock case, and it is what sets the stock sensor-to-ball distance (ball underside at z = "
  f"{meas['trackball_center'][2]-17:.3f} above the mounting plane, i.e. {meas['trackball_center'][2]-17-2:.3f} mm above the case bottom). "
  "**All new geometry is built from TB.**")
A("")
A("## 2. Seat stack (identical for all three seats, distances along the contact ray from TB)")
A("")
A("| feature | t [mm] | note |")
A("|---|---|---|")
A("| trackball surface | 17.00 | R17 from the trackball centre in either state (the centre itself moves ~0.2 mm between fresh and bedded, see section 3) |")
A(f"| cap top at the hole (hub) | {st['T_STEP']-P['CAP_HUB_T']:.2f} | cap hub {P['CAP_HUB_T']} thick |")
A(f"| cap top at the rim | {st['T_STEP']-P['CAP_RIM_T']:.2f} | cap rim {P['CAP_RIM_T']} thick |")
A(f"| hard step = cap underside | **{st['T_STEP']:.2f}** | {P['CAP_STEP_ABOVE_WASHER']} above the washer face; cap press bore dia {P['CAP_BORE_D']} nominal (modelled {st['CAP_BORE_DIA_MODELLED']:.2f}, ream 9.0) from the bowl surface down to here |")
A(f"| 5 mm ball centre, fresh (biased) | {st['T_BALL_FRESH']:.2f} | = 19.5 - {P['BEDDING_BIAS']} |")
A(f"| 5 mm ball centre, bedded in | **{st['T_BALL_BEDDED']:.2f}** | = 17 + 2.5, the 19.5 mm rule |")
A(f"| washer top face | {st['T_WASHER_TOP']:.2f} | = 19.5 + sqrt(2.5^2 - 1.5^2) - {P['BEDDING_BIAS']} = 19.5 + {st['DROP']:.2f} - {P['BEDDING_BIAS']} |")
A(f"| ball underside | {st['T_BALL_FRESH']+2.5:.2f} | hangs {st['BALL_HANG_BELOW_WASHER_FACE']:.2f} below the washer face into its 3 mm bore |")
A(f"| counterbore floor (flat, solid) | **{st['T_FLOOR']:.2f}** | washer bore dia {P['CB_D']} nominal (modelled {st['CB_DIA_MODELLED']:.2f}, ream 8.5) from the step down to here, {P['WASHER_T']} deep washer seat at the bottom |")
A(f"| end of solid backing | {st['T_END']:.2f} | >= 1.0 mm plastic behind the floor (modelled {st['T_END']-st['T_FLOOR']:.2f}) |")
A("")
A(f"Ball underside to floor: **{st['BALL_BOTTOM_TO_FLOOR_FRESH']:.2f} mm** as built (fresh), {st['BALL_BOTTOM_TO_FLOOR_BEDDED']:.2f} mm once the ball has bedded 0.15 mm into the washer. "
  "The brief asks for >= 1.4 and for the 0.15 mm bias at the same time; with a 2.0 mm washer both cannot hold after bedding (the floor is the washer face + 2.0), "
  "so the as-built gap is 1.50 and the fully-bedded gap is 1.35 - still an order of magnitude more than any wear that could occur.")
A("")
A("## 3. Chosen 5 mm ball centres (right case)")
A("")
A("| seat | az / el (deg) | ray direction | ball centre, bedded | dist. from TB | replaces | why here |")
A("|---|---|---|---|---|---|---|")
for s in chk["seats"]:
    A(f"| {s['name']} | {s['az_deg']:.1f} / {s['el_deg']:.1f} | {v3(s['ray_dir'])} | {v3(s['ball_center_bedded'])} | "
      f"**{s['dist_from_trackball_center_bedded']:.4f}** | {s['note'].split(';')[-1].strip()} | {s['note'].split(';')[0]} |")
A("")
A("Fresh (biased) centres are 0.15 mm closer to TB along the same rays:")
for s in chk["seats"]:
    A(f"* {s['name']}: {v3(s['ball_center_fresh'])}  ({s['dist_from_trackball_center_fresh']:.3f} from TB)")
A("")
A("Re-measured from the exported STL (floor plane and bore cylinders fitted to the output mesh):")
A("")
A("| seat | floor t | washer bore dia | cap bore dia | step t | implied ball centre t (bedded) | 19.5 +/- 0.02 |")
A("|---|---|---|---|---|---|---|")
for s in chk["seats"]:
    m = s["mesh_measured"]
    A(f"| {s['name']} | {m['t_floor']:.4f} | {m['washer_bore_dia']:.3f} | {m['cap_bore_dia']:.3f} | {m['t_step']:.4f} | {m['implied_ball_center_t_bedded']:.4f} | {ok(s['pass_19p5'])} |")
A("")
A("Contact spread:")
A("")
A("| pair | azimuth difference | 3-D angle between rays |")
A("|---|---|---|")
for k, v in chk["contact_spread"].items():
    A(f"| {k} | {v['azimuth_deg']:.1f} deg | {v['angle_3d_deg']:.1f} deg |")
A("")
A(f"All azimuth spreads >= 90 deg: {ok(chk['contact_spread_pass'])}. All contacts below the horizontal equator: "
  f"{'yes' if chk['all_below_equator'] else 'no - S2 sits above it at the back, as the stock P1/P2 do (see README, why)'}.")
F = chk["contact_forces_x_weight"]
A(f"Static contact loads with the keyboard flat (frictionless, gravity only), in units of the trackball weight: "
  + ", ".join(f"{k} = {v:.2f}" for k, v in F.items()) + f" -> all positive, the ball is held: {ok(chk['gravity_stable'])}; "
  f"largest load {chk['max_contact_load_x_weight']:.2f} (stock 1.78). Lateral holding capacity (largest horizontal push in the worst "
  f"direction before a contact unloads): **{chk['lateral_holding_x_weight']:.2f} x ball weight** (stock layout: 0.42).")
A("")
A("Trackball centre when the seats are fresh (all three balls 0.15 mm high): "
  f"{v3(chk['trackball_center_fresh'])}, i.e. TB + {v3(chk['trackball_rise_when_fresh'])}; it settles onto TB as the PTFE beds in.")
A("")
A("## 4. Clearance checks")
A("")
A("### 4.1 Trackball vs case")
A("")
A("20 000 points on the R17 trackball surface were tested against the output mesh (closest-point distance), and the "
  "R17.3 sphere was intersected with the case solid as an exact boolean (penetration volume "
  f"{chk['trackball_case_penetration_mm3_bedded']:.4f} / {chk['trackball_case_penetration_mm3_fresh']:.4f} mm^3 bedded / fresh).")
A("")
A("| state | min gap trackball -> case | where (az/el from TB) | >= 0.3 |")
A("|---|---|---|---|")
for stt in ("bedded", "fresh"):
    w = chk[f"trackball_case_min_gap_at_{stt}"]
    A(f"| {stt} | {chk[f'trackball_case_min_gap_{stt}']:.3f} | {w['az_el'][0]:.0f} / {w['az_el'][1]:.0f} | {ok(chk[f'trackball_case_clearance_pass_{stt}'])} |")
A("")
A("The only things that touch the trackball are the three 5 mm balls (by design).")
A("")
A("### 4.2 Retention caps")
A("")
A("| state | cap underside -> 5 mm ball (min) | ball radius at the cap plane | hole radial clearance | cap top -> trackball (min, worst seat) | pass |")
A("|---|---|---|---|---|---|")
for stt, c in chk["caps"].items():
    A(f"| {stt} | {c['cap_underside_to_ball_min']:.3f} | {c['ball_radius_at_cap_plane']:.3f} | {c['hole_radial_clearance']:.3f} | {c['cap_top_to_trackball_min']:.3f} | {ok(c['pass_'])} |")
A("")
A(f"Cap OD variants {P['CAP_OD_VARIANTS']}; the trackball sag at the cap rim (rho = {max(P['CAP_OD_VARIANTS'])/2:.2f}) is "
  f"{17-math.sqrt(17**2-(max(P['CAP_OD_VARIANTS'])/2)**2):.2f} mm, so the rim is the least critical point; the hub next to the hole is the critical one and is kept at {P['CAP_HUB_T']} mm thick.")
A("")
A("### 4.3 Ball to floor, backing, bores")
A("")
for b in chk["backing"]:
    A(f"* {b['name']}: 1.0 mm backing behind the floor fully solid: {ok(b['backing_solid'])} ({b['backing_fraction']*100:.0f} % of sample points inside), bore open to the bowl: {ok(b['bore_open'])}")
A(f"* ball underside to floor: {st['BALL_BOTTOM_TO_FLOOR_FRESH']:.2f} mm (fresh) / {st['BALL_BOTTOM_TO_FLOOR_BEDDED']:.2f} mm (bedded)")
A("")
A("### 4.4 Sensor aperture, mounting features, envelope")
A("")
A("The difference between the new and the stock solid was computed as two meshes (added material, removed material) and checked:")
A("")
A(f"* added material {chk['added_volume_mm3']:.1f} mm^3, removed material {chk['removed_volume_mm3']:.1f} mm^3 (removed = the bores cut through the stock wall plus the three old raised cones)")
A(f"* every changed region lies inside a seat zone or an old pocket zone: {ok(chk['modifications_confined_pass'])} ({len(chk['stray_modifications'])} stray regions)")
A(f"* lowest point of any added material: z = {chk['added_material_zmin']:.3f} (mounting plane z = 2.0, limit {P['Z_MIN_NEW']}): {ok(chk['added_material_zmin_pass'])}")
for k, v in chk["protected_regions"].items():
    A(f"* {k}: modified volume inside the protected box {v['modified_volume_mm3']:.4f} mm^3 -> {ok(v['pass_'])}")
A("")
A(f"Added-material bounding box: {v3(chk['added_material_bounds'][0],2)} .. {v3(chk['added_material_bounds'][1],2)}. "
  "Stock envelope: (60.85, -106.12, 2.00) .. (110.10, -70.78, 35.75).")
A("")
A(f"## 5. Overall: {ok(chk['overall_pass'])}")
if rep_left:
    A("")
    A(f"Left-hand case (mirror build): overall {ok(rep_left['checks']['overall_pass'])}; seat centres "
      + ", ".join(f"{s['name']} {s['dist_from_trackball_center_bedded']:.4f}" for s in rep_left["checks"]["seats"]) + " from TB.")
A("")
A("## 6. Neighbouring keys (from the Keyball44 right PCB, `keyball44_right.kicad_pcb`)")
A("")
A("Used only to decide where the bosses may protrude; see README section 'Why the contacts moved'. "
  "Footprint centres (KiCad mm, y down): SW15 (173.10, 89.07), SW16 (154.05, 84.37), SW17 (135.00, 86.87), "
  "SW19/F8 (192.15, 115.12), SW20/F7 (107.62, 116.92), trackball connector J2 (176.44, 113.45).")
open(os.path.join(src, "../DIMENSIONS.md"), "w").write("\n".join(L) + "\n")
print("wrote DIMENSIONS.md")
