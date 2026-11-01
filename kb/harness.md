# Plenum cable harness and D34 card fit (D34/D35)

**Status (2026-10-26, redesigned D34 cards, source hash 49de0a823799; earlier pass decb7e396781): CAD geometry
study, machine-checked, not built.** Labels used below:

- **[checked]**: verified by an automated check on the current files
  (OpenSCAD solid interference, the harness checker, or mesh checks).
- **[estimate]**: a hand or catalogue value, not yet confirmed.
- **[untested]**: needs a physical trial.

A modelled route is not a measured loom. No lead has been cut, crimped or
fitted.

Related pages: [plenum CAD](plenum-cad.md), [D34 controller](d34-controller.md),
[D34 sourcing](d34-sourcing.md), [D34 files and pinouts](../electronics/d34/README.md),
[plenum sizing](plenum-sizing.md) and [decisions D32–D37](decisions.md).

## Reproduce

```sh
bash scripts/export_plenum.sh          # cards, harness, access, parts, views, 92 checks
python3 scripts/check_mesh.py --plenum # printable meshes → build/plenum/geometry-report.json
```

The script runs these steps in order, and stops on any failure:

1. `scripts/gen_d34_cards.py` builds the card models from each card's
   `.kicad_pcb` and `design.json`, plus `electronics/d34/parts3d.json`
   (schema `d34-parts3d/1`). That file supplies bodies, solder tails, mated
   plugs/modules and lead exits. Each record is re-anchored to the current
   footprint. The generator falls back to KiCad plus the catalogue when a
   part's kind or rotation changed, and reports a stale file.
   - Side-entry plugs (pwr J2 MSTB): it takes the wire side whose `cable`
     keep-clear box is free of other parts. That is the −v side, toward the
     clip edge; the +v side hits F1/F2.
2. `scripts/harness.py` gets every port and the key geometry from OpenSCAD.
   It then resolves `cad/harness.json`, fillets each corner and runs the
   analytic checks. It also checks every lead against its pre-crimped or
   device-lead source, and writes the routes, `report.json` and
   `cutlist.csv`/`.md` under `build/plenum/harness/`.
3. `part="access_report"` and `scripts/access_order.py` produce the
   per-plug access verdicts in `build/plenum/harness/access.txt`.
4. The script exports parts and views, then runs `part="checks"`. Every
   check asserts.

`scripts/harness_report.sh` is a non-asserting per-lead collision
diagnostic.

## Card models

- **Placement.** Generated in `cad/d34_cards.scad`, in each card frame:
  x = 131.4 − w, y = 40.5 − u, z = 75 − v (u right, v down, w out of the
  component side, as in `parts3d.json`).
- **Lead exits.** Lead exits use the `parts3d` face centre and direction;
  any direction is supported.
- **Checks [checked].**
  - Cards with mated plugs against the rails, posts, caps, baffles, basins,
    sinks, fan, motor, bridge, DPS, drains, devices and deck.
  - Top-loading sweep of the bodies.
  - The old 36 mm envelope stays as a fallback assertion.

### Hand access to unplug [checked]

**Criterion.** This is changed from 12 mm all round, which the parts agent
showed is impossible on 81 × 47 cards. A plug is **finger-removable** if,
in one grip mode, all of the following hold:

- 8 mm of clearance on both gripped faces;
- swept along the withdrawal travel + 5 mm, plus a vertical approach from
  above (deck and caps removed);
- that whole volume is free of the enclosure, devices, mounts, other cards
  and its own card's parts and still-mated plugs, in the unplug order shown.

Grip modes are **pinch** (across the plug's narrow dimension) or **ends**
(across its long dimension). Otherwise the plug is flagged **extraction
tool required**. For XH, VH and fan plugs that means tweezers or an
extraction tool on the housing. For Mini-Fit, press the latch and pull by
the housing.

**Asserted.** All 20 plugs in use have an access volume clear of the
enclosure, devices, mounts and other cards.

**Reported** (`access.txt`, after the PR 614 change): 9 plugs are
finger-removable and 11 need a tool, because of their own card's parts within
8 mm. The spare tec J7 is unused.

| Card | Plug | Order, grip | Result |
|---|---|---|---|
| d34-ctrl | J1 | 1. ends | finger-removable (8 mm clear) |
| d34-ctrl | J2 | 2. pinch | finger-removable (8 mm clear) |
| d34-ctrl | J4 | 3. pinch | extraction tool required (own card's parts within 8 mm, 272 mm3) |
| d34-ctrl | J3 | 4. ends | finger-removable (8 mm clear) |
| d34-ctrl | J6 | 5. pinch | extraction tool required (own card's parts within 8 mm, 327 mm3) |
| d34-ctrl | J11 | 6. pinch | extraction tool required (own card's parts within 8 mm, 18 mm3) |
| d34-pwr | J8 | 1. pinch | finger-removable (8 mm clear) |
| d34-pwr | J4 | 2. ends | finger-removable (8 mm clear) |
| d34-pwr | J6 | 3. ends | finger-removable (8 mm clear) |
| d34-pwr | J9 | 4. ends | finger-removable (8 mm clear) |
| d34-pwr | J2 | 5. pinch | extraction tool required (own card's parts within 8 mm, 156 mm3) |
| d34-pwr | J3 | 6. pinch | extraction tool required (own card's parts within 8 mm, 130 mm3) |
| d34-pwr | J1 | 7. ends | extraction tool required (own card's parts within 8 mm, 162 mm3) |
| d34-tec | J6 | 1. pinch | finger-removable (8 mm clear) |
| d34-tec | J5 | 2. ends | finger-removable (8 mm clear) |
| d34-tec | J1 | 3. pinch | extraction tool required (own card's parts within 8 mm, 154 mm3) |
| d34-tec | J2 | 4. pinch | extraction tool required (own card's parts within 8 mm, 185 mm3) |
| d34-tec | J9 | 5. pinch | extraction tool required (own card's parts within 8 mm, 45 mm3) |
| d34-tec | J3 | 6. ends | extraction tool required (own card's parts within 8 mm, 179 mm3) |
| d34-tec | J4 | 7. pinch | extraction tool required (own card's parts within 8 mm, 143 mm3) |
| d34-tec | J7 | - | unused spare: no plug in this harness |

**Board delta bef910cab0df (2026-10-27).** All checks re-run against the
regenerated `parts3d.json`:

- **tec card:**
  - The new bottom-right parts (TL431 U1, BC327 Q6, R11/R13/R14/R15), the
    vertical R1/R2 and D5/D8, and the moved Q1/R3/Q3/D7 clear the bay.
  - Q4/Q5 moved to y 26.9. T270 clears Q5 and the new parts by more than
    1 mm, including the card's top-loading sweep.
- **ctrl card:** D9 (6.5 mm) is under the DevKit. The tallest part under
  the module is still D2 at 8.0 mm, inside the ≤8 mm rule; the module
  underside is at 8.5 mm.
- **tec J7** is still unused. If it were ever populated it would need a
  tool:
  - Pinch grip: the polyfuses intrude 195 mm³ and T270 176 mm³ into the
    8 mm grip zone.
  - Ends grip: T270 intrudes 306 mm³.
- **Reverse-brick snubber** (Vishay MRS25 2.2 Ω in series with a 1 µF film
  cap, across the Kycon +24 V / 0 V pins) sits inside the inlet
  counterbore, behind the keeper plate:
  - The cap (7.2 × 4.6 × 9 mm, WIMA MKS2-class [estimate]) stands radially
    in the +y side pocket; the resistor is in the −y pocket.
  - It clears the wall by ≥0.5 mm, the socket body by 0.6 mm and the
    keeper plate by 0.3 mm.
  - New asserted check: "inlet snubber / keeper, socket, shell wall".
  - View: `build/plenum/preview/inlet_snubber.png`.
  - Fit the snubber before pushing the keeper home.

**Sinks changed (2026-10-26, PR 614 hot / PR 411 cold).** Each hot sink face
moved 2.5 mm into the bays, so the thermostats were re-placed (all in
`pl_tstats`):

- **T0 and T270:** 66° at x −8.4.
- **T90:** level at x −7.4; it now carries the hot-sink DS18B20 on
  `plenum_sensor_clip`. That lead, W21, now crosses the 45° and 225° slots
  to the bus-B Y-splice.
- **T180:** vertical (90°) at x −6 with its **tabs soldered**, since the
  sourcing note allows that instead of flags. With flags, every orientation
  that clears the pwr card's parts grazed pwr J8's 8 mm grip zone. Its
  print is `plenum_fin_clip_90`.

Leads re-routed for the new geometry: W16 (blower inline re-angled away from
the 270 sink), W02, W23, W28 and W32. W02 then needs 310 mm, which is longer
than the 300 mm pre-crimped XH lead, so it is now hand-crimped from loose SXH
contacts like W01.

**Redesign (49de0a823799).** The new tall tec parts were checked:

| Part | Height | Card position |
|---|---:|---|
| RXEF050 polyfuses ×3 | 13.7 mm | below J7 |
| IRLZ44N TO-220 ×2 | 20.6 mm | — |
| C1 | 13 mm | — |
| R26 | — | ctrl |
| D2 | — | ctrl, under the DevKit |
| C9 | — | pwr |

- **T270:** the level clip at x+11 collided with Q5 (TO-220, 1.3 mm). T270 is
  now rotated 66° at x−7, like T0 and T180. That is the only
  `parameters.scad` change in this pass (`pl_tstats`).
- **tec J7** (the spare FAN3 output) is **unused**: no harness lead plugs
  into it. It is modelled unmated and excluded from the asserted access
  checks. The rule is data-driven: any card connector no lead uses.
- **If J7 is ever populated, it needs an extraction tool.**
  - Pinch grip: the polyfuses below it intrude 195 mm³ into the 8 mm grip,
    and T270's flags graze the envelope (11 mm³, about 1 mm).
  - Ends grip: blocked by T270 and the J6 plug.
  - Reach it from above with tweezers.
- Every other plug, and the cards with mated plugs, clear the bays: the
  rails, posts, baffles, sinks, devices and harness all pass.

## Off-card devices and tool-free mounts

Positions are `pl_` parameters in [parameters.scad](../cad/parameters.scad);
the geometry is in [plenum.scad](../cad/plenum.scad). No mount uses a screw.

| Item | Mount / position | Status |
|---|---|---|
| DPS5005 | 135° bay; rear IN/OUT terminals and comm header on the inner face | Terminal layout UNVERIFIED (assumed OUT y+8.5, IN y+19, COM y−24) |
| TEC ×4: Adaptive ADV-127-135200-S, 40 × 40 × **4.2** mm (`pl_tec_t` = 4.2; the spacer grows to 6.3 mm) | Leads leave the inner edge in a 4 × 6.5 mm deck-underside groove (silicone bead), into the drive bore, to junctions JT1/JT2 | 350 mm AWG20 leads; the 74–84 mm routes use them with margin |
| Thermostats ×4: RS PRO T24A060ASF2-15, envelope from the Multicomp **T23** sibling drawing (`pl_tstat_env`: flange 30.3 × 21 × 0.4, body Ø16.1 × 9.6, 19.3 mm to the tab ends, tabs 16.2 mm apart) | Printed J-clip hooks under the outer fin's bottom edge, leg in the first fin gap. A thin plate holds the flange flat on the fin; the body passes through. TE 2-520129-2 flags point up. T0 and T270 are rotated 66° (`plenum_fin_clip_66`). T90 is level and carries the hot-sink DS18B20 TO-92 (`plenum_sensor_clip`). T180 is vertical with soldered tabs (`plenum_fin_clip_90`). These placements keep the tabs out of the ctrl J2, pwr J8 and card zones and the tec Q5/J7 zone | The real part's size is unpublished: re-measure and adjust `pl_tstat_env`; the clips regenerate. Fin dimensions are from the PR 614 drawing (1.4 / 2.2 mm, estimate) |
| Blower: RS PRO ODB5115-12HB, **51.11** × 51.11 × 15 mm | Unchanged recess. Lead through a Ø4.5 sealed deck bore (serving-site x18, y−44) to a JST SM inline under the deck | Its wire lead length is unknown |
| Chamber-air / near-serving probes: DFRobot SEN0511 | Sealed deck bores at 58° R70 and 305° R72, 12 mm proud. Cut tails to JST SM inline pairs (Adafruit 1663) | — |
| Room-air probe (SEN0511) | Floor boss at 199.4° R127.5, tip 10 mm below the floor | — |
| Home sensor: **DRV5033AJQLPG** (omnipolar) | TO-92 on a post of the motor bridge's 45° arm. Ø6×3 magnet in the `plenum_drive` shoulder, 3 mm gap | Field strength untested |
| Lid reed (KSK-1A66) and basin-full pins | Rim slot at 286.5° (wall channel), magnet in the lid. Pin clip on basin 90. Both leads share **ctrl J4 (XH-4 SENSE)** | — |
| Panel pod (5 mm LED + B3F tact switch) | Snap-in pod in a wall pocket at 292.5°, Z112 | — |
| **24 V inlet: Kycon KPJX-PM-4S** power-DIN socket for the MEAN WELL GST160A24-R7B brick | At 247°, Z42:<br>- flange in a 1.2 mm outside pocket;<br>- body through a 3 mm wall web (Ø12.4 hole);<br>- an inside counterbore.<br>The drawn M2.5 screws are replaced by a printed **keeper** (`plenum_inlet_keeper`): a plate with two split, barbed pegs. The pegs pass through the web and snap through the flange's Ø2.3 holes, to remove by squeezing the barbs. Pigtail: pins 1+4 → +24 V, 2+3 → 0 V, one 18 AWG wire per pole to pwr J1 | Socket body Ø12 behind the flange is [estimate]; check the barb snap on a print |

## Harness model

`cad/harness.json` lists **34 leads**. Each lead starts and ends at a port
(card plug lead exit, device lead exit), a junction (JT1/JT2 TEC pairs, YA/YB
1-Wire Y-splices) or an inline-connector end.

**Bend policy.**

- Tied bundles bend at ≥ 4 × bundle diameter (PVC) or 3 × (silicone).
- Sheathed probe cables bend at 4 × their diameter.
- Leads made of separate wires (`loose`) bend per wire. This covers the XH
  links, which are built from individual pre-crimped leads; the DPS, TEC,
  inlet and stepper wires; the fan and blower; and the reed, panel and hall
  leads. Tie them only on straight runs.

**Levels and slots.**

- Baffle slots are now **23 mm wide** (`pl_baffle_slot` 11.5) and open from
  Z59. The 4-wire 18 AWG TEC feed (Ø6.1) needs ±7.75 mm lanes beside the
  motor post.
- Lower lanes run under the bridge arm (Z60–69); upper lanes run over it
  (Z79–80.5).

**Slot fill [checked].**

| Slot | Fill |
|---|---:|
| 45 | 0.14 |
| 135 | 0.14 |
| 225 | 0.23 |
| 315 | 0.31 |

**Leakage [estimate].** Open slot area totals about 1120 mm²:
303 / 305 / 272 / 242 mm² at 45° / 135° / 225° / 315°. That is about
240 mm² more than the 20 mm slots the coordinator assessed at ~1.7 W of
TEC power. Scaling that estimate linearly gives roughly 2.5 W; no slot comb
per the coordinator. This is an extrapolation, not a new simulation.

**Servicing.** Card plugs are unplugged in place. Cold-zone leads have JST
SM inline pairs under the deck, with 80 mm of slack so a deck quarter can
lift 60 mm. The TEC sinks come out by unplugging the Mini-Fit wire-to-wire
pairs at JT1/JT2 and pulling the thermostat flags.

**Checks [checked].** All 34 leads pass:

- bend radius and straight lead-out;
- hot-sink margin (≥ 3 mm, or ≥ 1 mm / contact for rated leads);
- ≥ 3 mm above the fan blades;
- ≥ 3 mm from the drive and tray;
- under the deck, except leads in grooves and bores;
- water: basin rim + 5 mm, drip paths 6 mm, floor 3 mm;
- approximate solids.

Seven OpenSCAD solid checks of every tube and inline body also pass.

**Not checked:** abrasion at slot and arm edges (fit a sleeve), current or
temperature rise, EMC, strain relief, and vibration over the fan.

### Cut list and pre-crimped lead lengths

Pre-crimped sources are from [D34 sourcing](d34-sourcing.md):

| Source | Length | Contacts |
|---|---:|---|
| JST XH | 300 mm | both ends, or cut in half for 150 mm board ends |
| JST VH | 300 mm | both ends, or cut in half for 150 mm board ends |
| Molex Mini-Fit 215341-1113 | 225 mm | one end |
| Adafruit SM pairs | 163 mm | — |

"EXTEND" means the board-end lead is shorter than the cut length: solder on
a heat-shrunk extension of the stated length.
"TOO SHORT" means a both-ends lead is shorter than the route: order a
custom length or crimp loose contacts.

Model route total 4.21 m; cut total 5.81 m. Full table:
`build/plenum/harness/cutlist.md` / `.csv`.

| Lead | Ends | Wire | Cut (mm) | Source | Lead used → length check |
|---|---|---|---:|---|---|
| W01 ctrl-pwr link | ctrl J1 JST XHP-11 → pwr J9 JST XHP-11 | 11 × 26 AWG pvc_thin | 335 | hand-crimped | loose JST SXH-001T-P0.6 contacts, hand-crimped (Engineer PA-09) → made to length (no pre-crimped lead) |
| W02 ctrl-tec link | ctrl J2 JST XHP-12 → tec J9 JST XHP-12 | 12 × 26 AWG pvc_thin | 290 | pre-crimped | JST 01SXHSXH-26L300 (300 mm, contact both ends) → OK: 290 of 300 mm |
| W03 12 V pwr to tec | pwr J3 JST VHR-3N → tec J1 JST VHR-3N | 3 × 20 AWG silicone | 290 | pre-crimped | JST 01SVHSVH-20L-300 (300 mm, contact both ends) → OK: 290 of 300 mm |
| W04 DPS input | pwr J2 Phoenix MSTB 2,5/2-ST-5,08 → DPS5005 IN+/IN- screw terminals (ferrules) | 2 × 18 AWG silicone | 275 | made to length (soldered/screw) | Phoenix MSTB 2,5/2-ST-5,08 screw plug + 18 AWG silicone (no crimp) → made to length (no pre-crimped lead) |
| W05 DPS output to relays | DPS5005 OUT+/OUT- screw terminals → tec J2 Mini-Fit 6 (pins 1 and 4 only) | 2 × 18 AWG pvc | 290 | pre-crimped | Molex 215341-1115 (450 mm, 18 AWG, one end crimped); fallback 225 mm + soldered extension → OK: 290 of 450 mm |
| W06 TEC feed to JT1 | tec J3 Molex 39-01-2040 Mini-Fit 4 → JT1: Mini-Fit 2-way receptacles (39-01-2020); pins 3-4 continue as W07 | 4 × 18 AWG pvc | 100 | pre-crimped | Molex 215341-1113 (225 mm, 18 AWG, one end crimped) → OK: 100 of 225 mm |
| W07 TEC string 2 JT1-JT2 | JT1 (pass-through of tec J3 pins 3-4) → JT2: Mini-Fit 2-way receptacles (continuation of tec J3 pins 3-4) | 2 × 18 AWG pvc | 105 | pre-crimped | Molex 215341-1113 (225 mm, 18 AWG, one end crimped) → OK: 195 of 225 mm |
| W08 TEC270 pigtail | TEC270 ADV-127 leads (350 mm) → Mini-Fit 2-way plug (39-01-3023), pin contacts from 226197-3114 | 2 × 20 AWG pvc | 90 | device lead + crimp | device leads 350 mm + pin contact from Molex 226197-3114 (cut in half) → OK: 90 of 340 mm |
| W09 TEC0 pigtail | TEC0 ADV-127 leads (350 mm) → Mini-Fit 2-way plug (39-01-3023), pin contacts from 226197-3114 | 2 × 20 AWG pvc | 100 | device lead + crimp | device leads 350 mm + pin contact from Molex 226197-3114 (cut in half) → OK: 100 of 340 mm |
| W10 TEC90 pigtail | TEC90 ADV-127 leads (350 mm) → Mini-Fit 2-way plug (39-01-3023), pin contacts from 226197-3114 | 2 × 20 AWG pvc | 100 | device lead + crimp | device leads 350 mm + pin contact from Molex 226197-3114 (cut in half) → OK: 100 of 340 mm |
| W11 TEC180 pigtail | TEC180 ADV-127 leads (350 mm) → Mini-Fit 2-way plug (39-01-3023), pin contacts from 226197-3114 | 2 × 20 AWG pvc | 90 | device lead + crimp | device leads 350 mm + pin contact from Molex 226197-3114 (cut in half) → OK: 90 of 340 mm |
| W12 DPS UART | DPS5005 comm header (type UNVERIFIED) → ctrl J11 JST XHP-4 | 3 × 26 AWG pvc_thin | 280 | cut | JST 01SXHSXH-26L300, cut near one end (~290 mm usable) → OK: 280 of 290 mm |
| W13 stepper | 17HS08 motor connector (JST PH-6 class, cable assembly) → pwr J8 JST VHR-4N | 4 × 26 AWG pvc | 190 | cut | JST 01SVHSVH-20L-300, cut near one end (~290 mm usable) → OK: 190 of 290 mm |
| W14 hot-side fan | NF-A12x25 lead (+ NA-EC1 extension if short) → tec J5 4-pin fan header (switched DC, no PWM) | 4 × 24 AWG pvc | 100 | device lead | NF-A12x25 own lead (~200 mm; NA-SEC extension in the box) → OK: 100 of 200 mm |
| W15 blower deck pigtail | RS PRO ODB5115-12HB blower wire leads → JST SM 3-way plug (SMP-03V-BC) | 3 × 26 AWG pvc | 70 | made to length (soldered/screw) | blower wire leads (length UNVERIFIED) + Adafruit 1663 SM pigtail → made to length (no pre-crimped lead) |
| W16 blower harness | Adafruit 1663 JST SM 3-way receptacle lead (163 mm, 22 AWG) → tec J6 fan header (switched DC, no PWM) | 3 × 26 AWG pvc_thin | 310 | spliced | Noctua NA-EC1 300 mm extension (female into tec J6) + one solder junction to the Adafruit 1663 SM pigtail (163 mm) → OK: 310 of 463 mm |
| W17 chamber probe tail | DFRobot SEN0511 SMD probe cable (1 m, cut) → JST SM 3-way plug | probe cable Ø3.5 | 50 | device lead | probe cable 1000 mm + Adafruit 1663 SM pigtail → OK: 50 of 1000 mm |
| W18 chamber probe harness | JST SM 3-way receptacle → Y-splice YA (bus A), soldered + heat-shrink | 3 × 26 AWG pvc_thin | 155 | pre-crimped | Adafruit 1663 JST SM receptacle lead (163 mm) to the Y-splice → OK: 155 of 163 mm |
| W19 near-serving probe tail | DFRobot SEN0511 SMD probe cable (1 m, cut) → JST SM 3-way plug | probe cable Ø3.5 | 50 | device lead | probe cable 1000 mm + Adafruit 1663 SM pigtail → OK: 50 of 1000 mm |
| W20 near-serving probe harness | JST SM 3-way receptacle → Y-splice YA (bus A), soldered + heat-shrink | 3 × 26 AWG pvc_thin | 135 | pre-crimped | Adafruit 1663 JST SM receptacle lead (163 mm) to the Y-splice → OK: 135 of 163 mm |
| W21 hot-sink probe | DS18B20 TO-92 on the T180 clip (soldered to the leads, heat-shrunk) → Y-splice YB (bus B), soldered + heat-shrink | 3 × 26 AWG silicone | 55 | made to length (soldered/screw) | 26 AWG silicone to the TO-92, soldered both ends → made to length (no pre-crimped lead) |
| W22 room-air probe | DFRobot SEN0511 SMD probe through the floor boss → Y-splice YB (bus B), soldered + heat-shrink | probe cable Ø3.0 | 75 | device lead | probe cable 1000 mm → OK: 75 of 1000 mm |
| W23 thermostat loop: tec J4.1 to T270 | tec J4 JST VHR-2N pin 1 (+12 V) → RS PRO T24A060ASF2-15 T270 6.3 mm flag receptacle | 1 × 22 AWG silicone | 105 | cut | JST 01SVHSVH-20L-300, cut near one end (~290 mm usable) → OK: 105 of 290 mm |
| W24 thermostat loop: T270 to T0 | RS PRO T24A060ASF2-15 T270 flag receptacle → RS PRO T24A060ASF2-15 T0 flag receptacle | 1 × 22 AWG silicone | 250 | made to length (soldered/screw) | 20 AWG silicone, TE 2-520129-2 flags crimped (ratchet crimper) or soldered both ends → made to length (no pre-crimped lead) |
| W25 thermostat loop: T0 to T90 | RS PRO T24A060ASF2-15 T0 flag receptacle → RS PRO T24A060ASF2-15 T90 flag receptacle | 1 × 22 AWG silicone | 95 | made to length (soldered/screw) | 20 AWG silicone, TE 2-520129-2 flags crimped (ratchet crimper) or soldered both ends → made to length (no pre-crimped lead) |
| W26 thermostat loop: T90 to T180 | RS PRO T24A060ASF2-15 T90 flag receptacle → RS PRO T24A060ASF2-15 T180 flag receptacle | 1 × 22 AWG silicone | 275 | made to length (soldered/screw) | 20 AWG silicone, TE 2-520129-2 flags crimped (ratchet crimper) or soldered both ends → made to length (no pre-crimped lead) |
| W27 thermostat loop: T180 to tec J4.2 | RS PRO T24A060ASF2-15 T180 flag receptacle → tec J4 JST VHR-2N pin 2 (return to K1) | 1 × 22 AWG silicone | 265 | cut | JST 01SVHSVH-20L-300, cut near one end (~290 mm usable) → OK: 265 of 290 mm |
| W28 lid reed switch | reed switch leads (sealed in the rim slot) → ctrl J4 JST XHP-4 SENSE (LID pins, shared with W30) | 2 × 26 AWG pvc_thin | 325 | hand-crimped | loose JST SXH-001T-P0.6 contacts, hand-crimped (Engineer PA-09) → made to length (no pre-crimped lead) |
| W29 panel LED + button | panel pod (5 mm LED, 6x6 tact switch) → ctrl J6 JST XHP-5 | 5 × 26 AWG pvc_thin | 300 | hand-crimped | loose JST SXH-001T-P0.6 contacts, hand-crimped (Engineer PA-09) → made to length (no pre-crimped lead) |
| W30 basin-full probe | two stainless pins in the basin 90 clip → ctrl J4 JST XHP-4 SENSE (LEAK pins, shared with W28) | 2 × 26 AWG pvc_thin | 110 | cut | JST 01SXHSXH-26L300, cut near one end (~290 mm usable) → OK: 110 of 290 mm |
| W31 home hall sensor | TI DRV5033AJQLPG TO-92 on the bridge post → ctrl J3 JST XHP-3 | 3 × 26 AWG pvc_thin | 165 | cut | JST 01SXHSXH-26L300, cut near one end (~290 mm usable) → OK: 165 of 290 mm |
| W32 24 V inlet pigtail | Kycon KPJX-PM-4S pins 1+4 (+24 V), 2+3 (0 V), soldered → pwr J1 Molex 39-01-2020 Mini-Fit 2 | 2 × 18 AWG pvc | 115 | pre-crimped | Molex 215341-1113 (225 mm, 18 AWG, one end crimped) → OK: 115 of 225 mm |
| W33 1-Wire bus A tail | Y-splice YA (chamber + near-serving probes) → pwr J4 JST XHP-3 (1-Wire A) | 3 × 26 AWG pvc_thin | 135 | cut | JST 01SXHSXH-26L300, cut near one end (~290 mm usable) → OK: 135 of 290 mm |
| W34 1-Wire bus B tail | Y-splice YB (hot-sink + room probes) → pwr J6 JST XHP-3 (1-Wire B) | 3 × 26 AWG pvc_thin | 60 | cut | JST 01SXHSXH-26L300, cut near one end (~290 mm usable) → OK: 60 of 290 mm |

## Findings for the electronics and parts work

**Lead plan (design agent, 2026-10-26).** All 34 leads fit their sources;
none needs an extension. Source type per lead is in the table above:

- **Pre-crimped:** whole pre-crimped leads, contacts at both ends.
- **Cut:** a 300 mm pre-crimped lead cut near one end (~290 mm usable).
  Used for W12, W13, W23, W27, W30, W31, W33 and W34.
- **Hand-crimped:** loose SXH contacts with an Engineer PA-09. Used for
  W01 (335 mm), W28 and W29.
- **Spliced:** W16 is a Noctua NA-EC1 300 mm extension, soldered to the
  Adafruit SM pigtail.
- **Device lead:** the TEC, fan and probe leads.
- **Made to length:** soldered or screw terminals.

Specific leads:

- **W05** uses the Molex 215341-1115 (450 mm). Fallback: 225 mm plus a
  soldered extension.
- **Bus-A Y-splice YA** moved into the central zone, beside the probes'
  inline connectors (225 frame x26). That shortens W18/W20 to ≤163 mm. The
  W33 tail now runs through the 225 slot to pwr J4.
- **Fan headers J5/J6** now carry switched DC, not PWM. The leads are
  unchanged.

Other findings:

- **pwr J2 MSTB:** insert the plug with the wires toward the clip edge;
  the other side fouls F1/F2.
- **Hand access:** 12 of 20 used plugs need an extraction tool under the
  8 mm criterion. J7 is unused and would also need one (see above).
- **DPS5005:** confirm the rear terminal order and position, and the comm
  header.
- **Thermostat calibration:** the T24A060 opens at 60 °C mid-fin, which
  reads cooler than the sink base. Calibrate on the bench.

## Remaining uncertainties

- **Unpublished sizes.**
  - T24A060 thermostat;
  - Kycon body diameter;
  - DPS rear layout;
  - real hot-sink fin pitch;
  - NF-A12x25 and blower lead positions.
- **Slot leakage** above the assessed 1.7 W (estimate about 2.5 W).
- **Hall gap field.**
- **Basin-pin false trips.**
- **How real loose wires lie** compared with the modelled centrelines.
