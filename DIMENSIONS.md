# DIMENSIONS - measured stock geometry, chosen seat geometry, clearance checks

All coordinates are in the frame of kepeo's `keyball_trackball_case_right.stl` (mm). The right-hand case is the reference; the left-hand case is its exact mirror in X, so every X below changes sign for the left case (azimuths become 180 deg - az). Numbers in this file are written by `src/write_dimensions.py` from `src/stock_measurements.json` and `output/build_report_*.json` - they are not typed by hand.

## 1. Stock case, measured from the STL

### 1.1 Inner bowl

| item | value |
|---|---|
| bowl sphere centre (least-squares fit of 8819 inward-facing faces) | (77.9986, -90.2820, 20.0019) |
| bowl radius | 17.9940 (design value 18.0 = 17 + 1 mm clearance) |
| fit residual median / max | 0.0010 / 0.0080 |
| outer shell radius | 19.4 (wall 1.4) |
| case bottom (mounting plane on the daughterboard) | z = 2.000 |
| sensor window | R18 bowl cut by the plane z = 3.4 -> a 14.0 mm hole, then a 14 mm bore down to z = 2.0 |

### 1.2 The three original 2 mm ceramic-ball pockets

Each pocket is a raised cone on the bowl wall (tip 17.51 mm from the bowl centre) with a blind bore and a flat floor. A 2 mm ball on that flat floor has its centre 1.0 mm above the floor, on the bore axis.

| pocket | az / el (deg) | bore dia | bore mouth t | flat floor t | axis passes bowl centre by | implied 2 mm ball centre | dist. from bowl centre |
|---|---|---|---|---|---|---|---|
| P1 | -3.07 / 27.32 | 2.076 | 17.510 | 19.047 | 0.208 | (94.1023, -91.0721, 28.1135) | 18.0486 |
| P2 | 123.46 / 8.62 | 2.077 | 17.509 | 19.049 | 0.115 | (68.1219, -75.4004, 22.6002) | 18.0489 |
| P3 | -101.72 / -60.93 | 2.073 | 17.510 | 19.048 | 0.223 | (76.2975, -98.6905, 4.1222) | 18.0489 |

(t = distance from the bowl centre along the pocket axis.)

### 1.3 Trackball centre

* The three implied 2 mm ball centres are **18.0486 .. 18.0489 mm** from the bowl-fit centre - they agree with each other to 0.0004 mm and with the nominal 17 + 1 = 18.0 mm to 0.049 mm (kepeo's floors are modelled 0.05 mm deeper than the nominal contact sphere).
* The point exactly **18.0 mm from all three** 2 mm ball centres (the rule in the task spec) is **TB = (78.1570, -90.0828, 19.8209)**, residuals (0.00000, 0.00000, 0.00000).
* TB lies 0.3123 mm from the bowl-fit centre, offset vector (0.1584, 0.1992, -0.1811). This is the real resting position of a 34.00 mm ball on 2.00 mm balls in the stock case, and it is what sets the stock sensor-to-ball distance (ball underside at z = 2.821 above the mounting plane, i.e. 0.821 mm above the case bottom). **All new geometry is built from TB.**

## 2. Seat stack (identical for all three seats, distances along the contact ray from TB)

| feature | t [mm] | note |
|---|---|---|
| trackball surface | 17.00 | R17 from the trackball centre in either state (the centre itself moves ~0.2 mm between fresh and bedded, see section 3) |
| cap top at the hole (hub) | 17.20 | cap hub 0.65 thick |
| cap top at the rim | 17.35 | cap rim 0.5 thick |
| hard step = cap underside | **17.85** | 3.5 above the washer face; cap press bore dia 9.1 nominal (modelled 8.95, ream 9.0) from the bowl surface down to here |
| 5 mm ball centre, fresh (biased) | 19.35 | = 19.5 - 0.15 |
| 5 mm ball centre, bedded in | **19.50** | = 17 + 2.5, the 19.5 mm rule |
| washer top face | 21.35 | = 19.5 + sqrt(2.5^2 - 1.5^2) - 0.15 = 19.5 + 2.00 - 0.15 |
| ball underside | 21.85 | hangs 0.50 below the washer face into its 3 mm bore |
| counterbore floor (flat, solid) | **23.35** | washer bore dia 8.6 nominal (modelled 8.45, ream 8.5) from the step down to here, 2.0 deep washer seat at the bottom |
| end of solid backing | 24.50 | >= 1.0 mm plastic behind the floor (modelled 1.15) |

Ball underside to floor: **1.50 mm** as built (fresh), 1.35 mm once the ball has bedded 0.15 mm into the washer. The brief asks for >= 1.4 and for the 0.15 mm bias at the same time; with a 2.0 mm washer both cannot hold after bedding (the floor is the washer face + 2.0), so the as-built gap is 1.50 and the fully-bedded gap is 1.35 - still an order of magnitude more than any wear that could occur.

## 3. Chosen 5 mm ball centres (right case)

| seat | az / el (deg) | ray direction | ball centre, bedded | dist. from TB | replaces | why here |
|---|---|---|---|---|---|---|
| S1 | -58.0 / -30.0 | (0.4589, -0.7344, -0.5000) | (87.1060, -104.4042, 10.0709) | **19.5000** | replaces stock P3 | front-right, just under the low front rim (short stub proud of the rim) |
| S2 | 50.0 / 27.0 | (0.5727, 0.6826, 0.4540) | (89.3252, -76.7730, 28.6737) | **19.5000** | replaces stock P1 | back, above the equator on the high back wall, boss stands off the shell above the key row |
| S3 | 158.0 / -30.0 | (-0.8030, 0.3244, -0.5000) | (62.4992, -83.7566, 10.0709) | **19.5000** | replaces stock P2 | back-left at the end of the left wall, clear of the slot |

Fresh (biased) centres are 0.15 mm closer to TB along the same rays:
* S1: (87.0372, -104.2940, 10.1459)  (19.350 from TB)
* S2: (89.2393, -76.8754, 28.6056)  (19.350 from TB)
* S3: (62.6196, -83.8053, 10.1459)  (19.350 from TB)

Re-measured from the exported STL (floor plane and bore cylinders fitted to the output mesh):

| seat | floor t | washer bore dia | cap bore dia | step t | implied ball centre t (bedded) | 19.5 +/- 0.02 |
|---|---|---|---|---|---|---|
| S1 | 23.3500 | 8.450 | 8.950 | 17.8500 | 19.5000 | PASS |
| S2 | 23.3500 | 8.450 | 8.950 | 17.8500 | 19.5000 | PASS |
| S3 | 23.3500 | 8.450 | 8.950 | 17.8500 | 19.5000 | PASS |

Contact spread:

| pair | azimuth difference | 3-D angle between rays |
|---|---|---|
| S1-S2 | 108.0 deg | 117.7 deg |
| S1-S3 | 144.0 deg | 110.9 deg |
| S2-S3 | 108.0 deg | 117.7 deg |

All azimuth spreads >= 90 deg: PASS. All contacts below the horizontal equator: no - S2 sits above it at the back, as the stock P1/P2 do (see README, why).
Static contact loads with the keyboard flat (frictionless, gravity only), in units of the trackball weight: S1 = 1.37, S2 = 0.83, S3 = 1.37 -> all positive, the ball is held: PASS; largest load 1.37 (stock 1.78). Lateral holding capacity (largest horizontal push in the worst direction before a contact unloads): **0.54 x ball weight** (stock layout: 0.42).

Trackball centre when the seats are fresh (all three balls 0.15 mm high): (77.8925, -90.3980, 20.3206), i.e. TB + (-0.2645, -0.3152, 0.4997); it settles onto TB as the PTFE beds in.

## 4. Clearance checks

### 4.1 Trackball vs case

20 000 points on the R17 trackball surface were tested against the output mesh (closest-point distance), and the R17.3 sphere was intersected with the case solid as an exact boolean (penetration volume 0.0000 / 0.0000 mm^3 bedded / fresh).

| state | min gap trackball -> case | where (az/el from TB) | >= 0.3 |
|---|---|---|---|
| bedded | 0.359 | 4 / -5 | PASS |
| fresh | 0.647 | -7 / -0 | PASS |

The only things that touch the trackball are the three 5 mm balls (by design).

### 4.2 Retention caps

| state | cap underside -> 5 mm ball (min) | ball radius at the cap plane | hole radial clearance | cap top -> trackball (min, worst seat) | pass |
|---|---|---|---|---|---|
| fresh | 0.313 | 2.000 | 0.200 | 0.483 | PASS |
| bedded | 0.463 | 1.878 | 0.322 | 0.343 | PASS |

Cap OD variants [9.1, 9.2, 9.3]; the trackball sag at the cap rim (rho = 4.65) is 0.65 mm, so the rim is the least critical point; the hub next to the hole is the critical one and is kept at 0.65 mm thick.

### 4.3 Ball to floor, backing, bores

* S1: 1.0 mm backing behind the floor fully solid: PASS (100 % of sample points inside), bore open to the bowl: PASS
* S2: 1.0 mm backing behind the floor fully solid: PASS (100 % of sample points inside), bore open to the bowl: PASS
* S3: 1.0 mm backing behind the floor fully solid: PASS (100 % of sample points inside), bore open to the bowl: PASS
* ball underside to floor: 1.50 mm (fresh) / 1.35 mm (bedded)

### 4.4 Sensor aperture, mounting features, envelope

The difference between the new and the stock solid was computed as two meshes (added material, removed material) and checked:

* added material 955.2 mm^3, removed material 198.9 mm^3 (removed = the bores cut through the stock wall plus the three old raised cones)
* every changed region lies inside a seat zone or an old pocket zone: PASS (0 stray regions)
* lowest point of any added material: z = 3.058 (mounting plane z = 2.0, limit 2.2): PASS
* base_hole_14mm: modified volume inside the protected box 0.0000 mm^3 -> PASS
* sensor_compartment: modified volume inside the protected box 0.0000 mm^3 -> PASS
* base_ring_and_screw_ears: modified volume inside the protected box -0.0000 mm^3 -> PASS
* sensor_aperture: modified volume inside the protected box 0.0000 mm^3 -> PASS
* finger_slot: modified volume inside the protected box 0.0000 mm^3 -> PASS
* pillar_exterior: modified volume inside the protected box 0.0000 mm^3 -> PASS

Added-material bounding box: (55.50, -111.47, 2.00) .. (96.41, -69.68, 35.62). Stock envelope: (60.85, -106.12, 2.00) .. (110.10, -70.78, 35.75).

## 5. Overall: PASS

Left-hand case (mirror build): overall PASS; seat centres S1 19.5000, S2 19.5000, S3 19.5000 from TB.

## 6. Neighbouring keys (from the Keyball44 right PCB, `keyball44_right.kicad_pcb`)

Used only to decide where the bosses may protrude; see README section 'Why the contacts moved'. Footprint centres (KiCad mm, y down): SW15 (173.10, 89.07), SW16 (154.05, 84.37), SW17 (135.00, 86.87), SW19/F8 (192.15, 115.12), SW20/F7 (107.62, 116.92), trackball connector J2 (176.44, 113.45).
