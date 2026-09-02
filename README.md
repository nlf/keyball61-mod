# Keyball 34 mm trackball case - PTFE-seat bearing upgrade

A remix of **kepeo's "Keyball Trackball Case"** (Thingiverse thing:6215791) that
replaces the three static 2 mm ceramic balls with three **5 mm chrome-steel balls
resting in the inner edge of thick PTFE washers**. The 34 mm ball rolls on the
steel balls; the steel balls slide on the PTFE ring, which cuts stiction with a
heavy (chromed steel, 160 g class) trackball. The PMW3360 sensor-to-ball distance
of the stock case is preserved exactly.

![seat sections](docs/img/seat_sections_right.png)
![case views](docs/img/case_views_right.png)

## Attribution and license

* Original design: **Keyball Trackball Case** by **kepeo**,
  <https://www.thingiverse.com/thing:6215791>, licensed
  **Creative Commons - Attribution (CC BY)**. The unmodified source STLs and
  kepeo's README/license text from the Thingiverse download are kept in
  `stock/original/`. Only the 34 mm / three-ceramic-ball case is used - not the
  Type D bearing case and not the 25 mm variants.
* This remix (everything in `src/`, `output/`, the docs) is also released under
  **CC BY 4.0**. Attribute kepeo for the case and this repository for the
  PTFE-seat modification.
* The Keyball61 and Keyball44 PCB layouts and the sensor-board gerbers
  (Yowkees/keyball) were used only to locate the neighbouring switches and the
  sensor board relative to the case.

## What is in the repository

| path | what |
|---|---|
| `src/ptfe_seat_case.py` | **parametric source** (CadQuery + manifold3d). All parameters at the top: ball diameter, washer ID/OD/thickness, contact radius, bedding bias, per-seat contact angles, boss size, bore undersize, cap dimensions. |
| `src/measure_stock.py` | reverse-engineers the stock STL: bowl sphere, the three 2 mm pockets, the trackball centre. Writes `src/stock_measurements.json`. |
| `src/layout_search.py` | obstacle model (sensor compartment, switches/keycaps from the KiCad files, mounting plane, slot, aperture) and the seat-triple search that produced the layout; `python layout_search.py 5.5 61` or `.. 44`. |
| `src/write_dimensions.py`, `src/preview.py` | generate `DIMENSIONS.md` and the pictures from the build report. |
| `output/keyball_ptfe_seat_case_right.stl` / `.step.zip` | modified right-hand case. The STEP is a B-rep with true cylinders/planes for the seats on top of the faceted stock body; at 54 MB it is stored zipped (12 MB), unzip before use |
| `output/keyball_ptfe_seat_case_left.stl` / `.step.zip` | mirrored left-hand case (same build, mirrored inputs) |
| `output/cap_ring_OD9.1_hole4.4.*`, `..OD9.2..`, `..OD9.3..` | retention caps, three OD variants for press-fit selection (STEP + STL) |
| `output/test_coupon_seat.*` | one full seat stack (cap bore + step + washer bore + floor + backing) in a 14 mm puck, to dial in the fit before printing the case |
| `output/build_report_*.json` | every number the checks produced |
| `DIMENSIONS.md` | measured stock coordinates, the three chosen ball centres, all clearance results |
| `stock/original/` | kepeo's files as downloaded; `stock/repaired/` the same meshes made watertight (14 sliver triangles on the rim top re-triangulated, volume change 0.03 %) |

## Bill of materials

| qty | part | link |
|---|---|---|
| 3 | PTFE washer 3 mm ID x 8.5 mm OD x 2 mm thick (uxcell) | <https://www.amazon.com/dp/B08CD8TGF1> |
| 3 | 5 mm chrome steel ball, G25 (AISI 52100) | any bearing-ball supplier, e.g. <https://www.amazon.com/s?k=5mm+chrome+steel+ball+G25> |
| 1 | 34 mm trackball (chromed steel or stock POM) | - |
| 3 (optional) | printed retention cap (`output/cap_ring_OD9.2_hole4.4.stl`, or the 9.1 / 9.3 variant that fits) | this repo |
| 1 | printed case (`output/keyball_ptfe_seat_case_right.stl`) | this repo |
| 2 | the stock M1.7 flat-head tapping screws that hold the Keyball case to the daughterboard | Keyball kit |

Nothing else, nothing glued. PTFE cannot be bonded; every part is retained
mechanically (washer pressed into its counterbore, ball captive under the
optional cap, cap pressed against a hard step).

## The 19.5 mm rule (read this before editing anything)

The sensor distance is fixed by where the trackball rests, and the trackball
rests where its three support contacts put it.

* Stock: three 2 mm balls, each with its centre **17 + 1 = 18.0 mm** from the
  trackball centre. `measure_stock.py` finds the three stock pocket floors and
  solves for the point that is 18.0 mm from all three implied 2 mm ball
  centres. That point, **TB = (78.157, -90.083, 19.821)** in the STL frame, is the
  trackball centre. (It is 0.31 mm from the geometric centre of the R18 bowl,
  because kepeo's pocket floors are 0.05 mm deeper than nominal - see
  `DIMENSIONS.md` section 1.3. The bowl is only a clearance surface; the
  contacts define the ball position, so TB is used.)
* New: three 5 mm balls, so each ball **centre must be 17 + 2.5 = 19.5 mm from TB**.
  Every seat feature is a distance along the "contact ray" (the line from TB
  through the ball centre), perpendicular to that ray:

| t from TB | feature |
|---|---|
| 17.00 | trackball surface (contact point) |
| 17.85 | hard step, cap underside (3.5 above the washer face) |
| 19.35 / **19.50** | 5 mm ball centre, fresh / bedded-in |
| 21.35 | washer top face: 19.5 + sqrt(2.5^2 - 1.5^2) = 19.5 + 2.0, minus the 0.15 bias |
| 23.35 | flat, solid counterbore floor (washer 2.0 thick) |
| >= 24.35 | 1.0 mm solid plastic behind the floor |

If you change the ball, the washer or the bias, change the parameters in
`src/ptfe_seat_case.py` and rebuild; the script recomputes the stack and
re-verifies every ball centre against 19.5 +/- 0.02. Never move a washer
floor by hand: 0.1 mm at the floor is 0.1 mm at the sensor.

**Bedding-in bias.** A fresh PTFE edge yields ~0.1-0.2 mm during the first
days of use, which lowers the ball toward the sensor. The washer floor is
therefore modelled **0.15 mm high** (washer face at 21.35 instead of 21.50).
New seats put the trackball ~0.2 mm high; it settles to the stock height as the
PTFE beds in. Expect the cursor feel to change slightly over the first days -
that is the seats bedding in, not a fault.

## Why the contacts moved (and where they are now)

Designed and checked for the **Keyball61**; the Keyball44 uses the same sensor
board and the same case, and the layout clears its keys too.

Two things about the stock case decide where a 24.5 mm deep seat stack can go:

* **The "pillar" is the sensor compartment.** The Keyball sensor board stands
  vertically in a 7-pin socket on the main PCB; the pillar houses it, the lens
  and chip sit in front of it, and the hex-shaped opening in the pillar wall is
  the **sensor aperture** (the PMW3360 looks sideways at the ball, not up from
  below - the 14 mm hole in the base is just a hole). From the case sections the
  compartment (x 96.7..106.5, the full 22.6 mm board width, z 6..30) is
  completely full, so nothing may enter it. That blocks az -45..+45 at every
  elevation.
* **The mounting plane** (z = 2, the case bottoms on the main PCB) limits any
  seat to el >= -32, and the switch housings of the row behind the ball (SW21
  and SW22 on the 61, SW15/SW16 on the 44) block az 45..140 below the equator.

What is left below the equator is a 165 deg arc from the back-left round the
front, and three contacts have to span more than 180 deg or the ball is not
held. `src/layout_search.py` models the compartment, the switches and keycaps
(from the KiCad files), the mounting plane, the slot and the aperture, and
searches all seat triples. The stock case solves the same problem by putting
two of its three contacts *above* the equator (az/el -3/+27 and 123/+9) and
the third steeply below (-102/-61); the steep one is impossible for a deep
seat, so the triangle is rotated the other way:

| seat | az / el | where the boss goes | replaces |
|---|---|---|---|
| S1 | -58 / -30 | front-right, just under the low front rim; the top of the 11 mm boss stands ~4 mm proud of the rim as a short stub, in front of the pillar and clear of the sensor compartment | stock P3 |
| S2 | +50 / +27 | back, on the high back wall **above the equator**; the boss stands off the outside of the shell above the key row behind the ball (its underside is ~4 mm above the keycap tops, it never enters the compartment) | stock P1 |
| S3 | +158 / -30 | back-left at the end of the left wall, clear of the finger slot and the SW23/SW24 keycaps | stock P2 |

Azimuth spread 108 / 108 / 144 deg (all >= 90), all three ball centres 19.5 mm
from TB. With the keyboard flat the contacts carry 1.37 / 0.83 / 1.37 of the
ball weight (stock: 0.86 / 1.08 / 1.78) and the largest horizontal push the
ball takes before a contact unloads is 0.54 x its weight (stock layout 0.42) -
the rotated triangle holds the ball at least as well as the stock one. The
brief asked for all contacts below the equator; that is geometrically
impossible on this keyboard, and S2 above the equator is the same trick
kepeo's case already uses.

The three now-unused stock pockets (raised cone + 2.08 mm bore) are shaved
flush with the R18 bowl and plugged, so the bowl is a clean sphere again
(`REMOVE_STOCK_POCKETS = True`; set to `False` to keep them). The plug of the
old P2 pocket is clipped to the slot volume, so the finger slot the pocket had
broken into keeps its exact stock outline. kepeo's case also carries a small
external boss behind each ceramic pocket; the one behind P2 is a square bump
beside the slot on the outside of the shell and is shaved flush (the P1 one is
buried in the pillar wall, the P3 one merges into the base ring, both stay). Verified on the output mesh: no
surface closer than 17.998 mm to the bowl centre remains at any old pocket,
and probe spheres along all three old bore axes are 100 % inside solid.

![bowl map](docs/img/bowl_map_stock_vs_new.png)

The oblong through-slot in the back-left wall (az 102-125, 4 x 12 mm) is
kepeo's stock feature and is left exactly as it was. Mapped onto the PCB it
sits under the rear corner of the keycap behind it (SW23 on the 61, SW17 on
the 44), which is consistent with a keycap clearance notch; treat that as a
plausible reading, not a confirmed one. The hex-shaped opening in the pillar
wall is the sensor aperture and is untouched (the trackball-envelope trim
above only skims the flat around it).

One more small change to the stock body: the flat face of the pillar wall
that shows inside the bowl at x = 95.4 is only 0.24 mm from the trackball once
the ball rests at its true centre TB (0.40 mm in kepeo's model, where the ball
is drawn at the bowl centre). The case is therefore trimmed with a sphere of
R17.35 around TB (and around the fresh-state centre), which takes at most
0.11 mm off that flat and touches nothing else, so the 0.3 mm clearance holds
everywhere (`ENVELOPE_CLEARANCE`).

The sensor aperture and compartment, the base ring and its 14 mm hole, the two
screw ears, the finger slot and the pillar are byte-for-byte the stock geometry: the checks
compute the added/removed material and verify that none of it lies in those
regions (`DIMENSIONS.md` 4.4). The case mounts to the stock daughterboard
exactly as before.

## Seat geometry (per seat)

* Local boss: 11 mm cylinder along the contact ray from the bowl wall out to
  t = 24.5, with a 1.5 mm 45 deg flare that starts where its wide end meets the
  R19.4 outer shell (so it is joined to the shell all the way round) and a
  0.5 mm chamfer on the end. It never intrudes inside the R18 bowl.
* Cap bore: **9.1 mm nominal, modelled 8.95, ream with a 9.0 mm drill**, from the
  bowl surface down to the hard step at t = 17.85.
* Washer bore: **8.6 mm nominal, modelled 8.45, ream with an 8.5 mm drill**, from
  the step down to the flat floor at t = 23.35. The washer is pressed 3.35 mm
  down this bore until it bottoms on the floor; the bottom 2.0 mm is its seat.
  The floor is solid (no through hole) with >= 1.0 mm of plastic behind it.

**Deviation from the brief - cap bore 9.1 instead of 8.1.** The 8.5 mm washer
has to get to its floor through the cap bore, so the cap bore must be wider
than the washer, and the cap must be wider than the cap bore. An 8.1 mm cap
bore above an 8.6 mm washer bore cannot be assembled (the floor is solid, so
the washer cannot come from behind). Every other number of the brief is kept;
the caps are 9.1 / 9.2 / 9.3 mm OD (nominal 9.2) for the 9.0 mm reamed bore,
i.e. the same 0.1-0.3 mm interference range the brief intended.

## Retention caps

Ring, hole 4.4 mm, OD 9.2 nominal (variants 9.1 / 9.2 / 9.3), 0.5 mm thick at
the rim, thickening to 0.65 mm at the hole with a chamfer between rho 2.9 and
3.7. The cap presses into the 9.0 mm bore until it **bottoms on the step** at
t = 17.85 - the step sets the height, not friction. It keeps the 5 mm ball
captive when the trackball is lifted out and never touches anything in use:

* cap underside to the seated 5 mm ball: 0.31 mm (fresh) / 0.46 mm (bedded);
  ball underside to the pocket floor 1.50 mm (fresh) / 1.35 mm (bedded)
* cap hole vs ball: the ball is 4.0 mm across at the cap plane, hole 4.4
* cap top to the trackball: >= 0.3 mm at the hub, ~1.1 mm at the rim (the
  34 mm ball sags 0.63 mm at rho 4.6)

Caps are optional; the seat works without them (the ball then just lifts out
with the trackball if you turn the case over).

## Assembly order

1. Ream the bores if needed: 8.5 mm drill for the washer bores, 9.0 mm drill for
   the cap bores (twist the drill by hand, do not power it; PLA/PETG melt).
   Use the coupon to find out whether your printer needs the reaming at all.
2. **Washer**: push a PTFE washer into each washer bore, flat, until it bottoms
   on the floor (a 6 mm dowel or the shank of a 6 mm drill works as a pusher).
3. **Ball**: drop a 5 mm ball into each washer. It sits in the 3 mm bore of the
   washer, 0.5 mm below the washer face.
4. **Cap** (optional): press the cap that fits (try 9.2 first) into the cap bore,
   hole over the ball, until it stops on the step. It must not rock; if it
   goes in loose use the 9.3, if it needs force use the 9.1.
5. Mount the case on the daughterboard with the stock screws, drop in the
   trackball.

The seats bed in **~0.1-0.2 mm over the first days**; the floors are biased
0.15 mm high for that. Do not "fix" a slightly high ball on day one.

## Printing

* Case: print in the stock orientation (flat base down, as kepeo's STL is
  oriented). The three bores are near-horizontal blind holes (S1/S3 axes 30 deg
  below horizontal, S2 27 deg above); their upper side is a small bridge and
  the S2 boss overhangs the shell at the back. Either enable
  supports inside the three bores, or print without and clean the ceiling of
  each bore with the reamer - the counterbore floors are steep walls and print
  clean either way. 0.4 nozzle, 0.12-0.16 mm layers, 4+ perimeters (the boss
  walls are 0.95-1.2 mm).
* Caps: print flat, **hole up**, 0.1-0.12 mm layers, one at each OD.
* Coupon: prints as a puck with the bores opening upward (no support). Use it
  to test washer press fit, ball seating and cap press fit before printing the
  case.
* All press bores are modelled 0.15 mm under nominal for FDM shrink; ream to
  8.5 / 9.0.

## Rebuilding

```
pip install cadquery manifold3d trimesh numpy scipy rtree pymeshfix networkx matplotlib
cd src
python measure_stock.py                 # -> stock_measurements.json
python ptfe_seat_case.py --side right   # -> ../output (STL + STEP + caps + coupon + report), exit 1 if a check fails
python ptfe_seat_case.py --side left
python write_dimensions.py              # -> ../DIMENSIONS.md
python preview.py right                 # -> ../docs/img
```

The build fails (non-zero exit) if any acceptance check fails: ball centres
19.5 +/- 0.02 from TB, trackball >= 0.3 mm from the case everywhere, cap
clearances, solid backing, added material above the mounting plane, and no
change to the protected stock regions.
