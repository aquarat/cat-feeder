# Cold-air plenum CAD study (D35)

**Status: packaging/geometry study, 2026-10-25; rev 2 on 2026-10-26** (hot-side
baffles, more vent area, 70 × 60 mm cold sinks, blower moved, TARK thickness,
sloped pockets, following [plenum sizing](plenum-sizing.md)). Envelopes are provisional,
not selected parts. Clearance and mesh checks pass for the modelled geometry.
Airflow, sealing, drainage, frost, rolling drag and cooling are **not tested**.
The direct-contact design (D19) remains the default build and is unchanged.

Related: [decisions D32–D36](decisions.md), [plenum thermal study](plenum-thermal.md), [plenum sizing](plenum-sizing.md),
[2026-10-25 review](review-2026-10-25.md), [drop-in layout](drop-in-layout.md),
[cable harness and D34 card fit](harness.md) (2026-10-26).


## Reproduce

```sh
bash scripts/export_plenum.sh          # card models, harness, access report, plenum parts, checks, views → build/plenum/
python3 scripts/check_mesh.py --plenum # → build/plenum/geometry-report.json
```

`cooling_concept` in [parameters](../cad/parameters.scad) selects the concept;
the script passes `-D 'cooling_concept="plenum"'`. Plenum geometry is in
[plenum.scad](../cad/plenum.scad). Unchanged prints (tray sectors, hub, drive,
clip, closure coupons) come from `scripts/export.sh`. The direct build was
re-exported after the refactor: identical triangle counts, volumes and bounds,
13/13 mesh checks and 44/44 clearance checks pass.

## Arrangement

| Item | Study geometry | Status |
| --- | --- | --- |
| Air channel | 15 mm between deck top (Z102) and tray underside (Z117), radial R63.5–R141 | Thermal study assumed 12 mm × 80 mm; re-run with 15 mm |
| Channel walls | Inner ring R61.5–63.5 to 1 mm below tray; outer lip R141–143.5 rising 3 mm beside the tray rim | Labyrinth only; 1 mm gaps not sealed |
| Cooling sites | 4 at 0/90/180/270°, R100. Serving position (270°) is a site | — |
| Cold stack | Hot sink top Z83.5 → 40 × 40 × 4.2 Adaptive ADV-127-135200-S TEC (final D34 BOM; was 4.7 mm TARK-class) → 40 × 40 × 6.3 aluminium spacer through the deck → **Alutronic PR 411** cold sink cut to 46 mm along the flow: 74.5 radial × 46 × 22, 3 mm base, 13 fins (`pl_cold_sink = [74.5,46]`, centred 1.25 mm outboard). Its inner face clears the inner wall by 0.5 mm and its corners reach R140.4, inside the R140.5 check. It sits in the unchanged 76 × 64 mm pocket, clipped at R140.5. The thermal model (`thermal/plenum_cad.py` `cold_slots`) counts bypass only over the fin tips, at the radial side gaps and under the base. The extra 18 mm of pocket length along the flow is in series, not a bypass, so the pocket stays as the thermal results assumed | [Sizing](plenum-sizing.md) (sim): R_cold 1.81 K/W with 93 % of the air through the fins. Quote from Alutronic required |
| Hot sinks | **Alutronic PR 614** cut to 70 mm: 70 radial × 75 tangential × 45 (`pl_hot_sink = [70,75,45]`, 2026-10-26; was 70 × 70). Sits on floor posts with L guides, under the deck. The tangential guide legs are kept at the outer corners only; at the inner corners the baffle ends now locate the sink, since those legs would hit the baffles. Floor aprons close the route under each inner face. Thermostat clips use `pl_fin = [1.4,2.2]` (estimate from the drawing) | [Sizing](plenum-sizing.md) (sim): R_hot 0.667 K/W |
| Hot-side baffles | Four drop-in 2 mm printed plates (47 × 55.3 mm; `pl_baffle_end` 23.5, so the ends stop 0.5 mm short of the 75 mm sink faces, as before) on the diagonals at 78 mm from the axis. Floor rails seat them and the deck holds them down. Legs straddle the fan corners. An open-top slot, 23 mm wide from Z59 (harness study; was 11 mm from Z70.5), takes the bridge arm and the [modelled harness](harness.md) above and below the arm | Forces fan air through the fins. ~800 mm² leakage estimated, not measured. Open slot area around the leads is ~1120 mm² in total [estimate]. The coordinator put the 20 mm version at ~1.7 W of TEC power (R_hot 0.645 → 0.674 K/W) and accepted it without a comb; 23 mm adds ~240 mm² more, roughly 2.5 W extrapolated |
| Vents | Intake slots 4.2 mm wide (×1.2 area); second slit row at Z32–54 (×2 total), kept solid ±9° round the inlet grommet | Slot area from CAD; flow is an estimate |
| Blower | 51.11 × 51.11 × 15 (RS PRO ODB5115-12HB: 4.2 CFM / 124 Pa, below the ≥4.5 CFM / 167 Pa target), recessed 57 mm upstream and 14 mm inboard of the serving site, inlet down into a 7 mm well with an upstream intake opening; discharges CCW straight into the serving-site fins | Fits the 52 mm recess (0.45 mm per side); duct shape simplified |
| Tray support | 7 × 608 bearings as rim rollers at R131 on 8 mm printed axles, in open-top U notches of deck-integral cheeks | Tray inner edge rests on the hub lip, so the motor shaft carries an estimated ~4 N axial load. Check the motor rating |
| Drainage | Each cold pocket floor falls 1.5 mm outward to a drain at R138.5, with a 2 mm collar round the TEC window. A Ø5 silicone tube pushes 5 mm up into a Ø4.6 socket under the pocket and runs down beside the hot sink, ending 6 mm above an evaporation basin | Push-fit grip untested |
| Evaporation basins (D37) | Four drop-in printed arcs (123 × 21 × 6 mm), R137.5–145.3, ±25° behind each hot sink, in the exhaust stream. Each has a lobe under the tube drip and notches round the sink guides. A standpipe (overflow 3.3 mm above the basin floor, ~2 mL per basin) fits over a floor stub whose bore drains through the floor. Notches in the deck ledge let each basin lift straight out with the deck removed | ~26 cm² water surface; passive evaporation ~10 g/day (hand estimate) |
| Electronics (D33/D34) | DPS5005 bay 41 × 79 × 43 at 135°. Three [D34 cards](d34-controller.md), 81 × 47 mm, stand vertically at 45° (ctrl), 225° (pwr) and 315° (tec). Each card plane is tangential, with its solder face 133 mm from the axis and its components facing inward. Since 2026-10-26 the cards are generated from the KiCad boards and `parts3d.json` (`cad/d34_cards.scad`): bodies, solder tails, mated plugs and lead exits. The 36 mm envelope is kept as a fallback assertion. Floor rails grip the lower 3 mm band. A printed U-cap (86 × 11 × 4.4 mm) grips the upper band; its end tabs drop into shell posts and the deck holds it down. The 24 V inlet is a Kycon KPJX-PM-4S power-DIN socket at 247°, Z42, held by a printed snap-peg keeper instead of M2.5 screws (see [harness](harness.md)) | Free bay per diagonal is 44 × 85 × 51 mm (CAD-checked). Lead routes, device mounts and hand access are modelled and checked; see [harness](harness.md) |
| Off-card devices ([harness](harness.md)) | Printed thermostat fin J-clips ×4 for RS PRO T24A060ASF2-15. The envelope comes from the Multicomp T23 drawing; With the 75 mm PR 614 faces, the placements are:
  - T0 and T270: rotated 66° at x −8.4.
  - T90: level at x −7.4; its clip carries the hot-sink DS18B20.
  - T180: vertical (90°) at x −6 with its tabs soldered, because flag receptacles there graze pwr J8's grip zone. Sealed deck bores for the blower lead and two SMD DS18B20 chamber probes. Room-air probe in a floor boss. Hall post on the motor bridge, with a magnet in a `plenum_drive` variant. Reed in the rim with a magnet in the lid. Snap-in panel pod in a front-right wall pocket. Basin-full pin clip. TEC lead grooves in the deck underside | Positions are `pl_` parameters. Sink fin geometry, the DPS rear layout and most device sizes are estimates |
| Motor bridge | Removable X-bridge on four diagonal posts at R89 | Printable, 136.5 mm square |
| Deck | 18 mm, 4 quarters split at 40/130/220/310° (clear of sites, rollers and blower), printed underside down | 145.2 × 145.2 × 36 mm per quarter |
| Height | Shell 138.5 mm (direct: 123.5 mm); food rim Z134 | Inside the brief's 135–145 mm rim range |

## Checks (2026-10-26, harness revision)

93 plenum clearance checks pass [checked] (boards bef910cab0df, PR 614 / PR 411 sinks, inlet snubber; 2026-10-27). The 45 non-repeated checks are:

- deck against the shell, cold stacks, hot sinks, blower and rollers;
- top-loading sweeps of the hot sinks, bays, fan, baffles, basins, fin clips,
  basin probe, room probe, card caps and the generated card bodies, with the
  deck removed;
- the motor bridge, which now carries the hall post, against all equipment;
- the baffles against the shell, internals, equipment, motor bridge and deck;
- the basins against the shell, internals, equipment and baffles;
- the D34 card models with mated plugs against the baffles, basins, sinks,
  fan, motor, bridge, DPS, drains, devices, mounts and deck. A fallback
  check keeps them inside the old 36 mm envelope;
- the devices and mounts against the shell, sinks (with the first fin gap
  open for the clips), baffles, basins, fan, bridge, DPS, drains and deck.
  The cold-zone probes sit only in their sealed bores;
- the lid magnet against the shell, and the hall sensor and post against the
  drive;
- the inlet snubber (RC across the Kycon pins, in the counterbore) against the
  keeper, socket and wall;
- the harness tubes and inline bodies against every solid group, tray and
  lid included.

The repeated groups make up the other 51:

- 21 hand-access checks, one per plug (8 mm grip criterion; the unused spare tec J7 has no plug and passes trivially): the grip and approach volume must be
  clear of the enclosure, devices, mounts and the other cards;
- the lid opening from 0 to 110° (12);
- tray rotation from 0 to 30° against the deck, fins, blower, cold probes,
  hall sensor, motor bridge, shell and lid (7);
- rollers touching only at the tray datum (7).

The harness checker passes all 32 leads. Its analytic checks cover bend
radius, lead-out, hot-sink and fan clearance, the zones, water, approximate
solids and slot fill; see [harness](harness.md).

The plenum printed parts are closed, connected, on the bed and within
170 mm [checked]:

| Part | Size (mm) | Print |
|---|---|---:|
| Deck quarter | 145.2 × 145.2 × 36 | |
| Motor bridge, with the hall post | 136.5 × 136.5 × 35.4 | |
| Baffle | 47 × 55.3 × 2 | 4 |
| Basin | 123 × 21 × 6 | 4 |
| Card cap | 86 × 11 × 4.4 | 3 |
| Fin clip, 66° (T0, T270) | 35.3 × 5.1 × 43.4 | 2 |
| Fin clip, 90° (T180, soldered tabs) | 24.8 × 5.1 × 40.5 | 1 |
| Sensor clip, level (T90) | 34.1 × 8.1 × 42.3 | 1 |
| Fin clip, level (spare variant) | 34.1 × 5.1 × 35.8 | 0 |
| Inlet keeper (Kycon) | 16.2 × 27.2 × 7.5 | 1 |
| Basin probe clip | 13.7 × 10.9 × 8 | 1 |
| Panel pod | 25.6 × 21.6 × 9.3 | 1 |
| Plenum drive, with the magnet pocket | 81 × 81 × 9 | |

Shell height is unchanged at 138.5 mm.

The direct build re-exported byte-identical after the harness work: 16 STL
hashes match, with 13/13 mesh checks and 44/44 clearance checks passing.

Views are in `build/plenum/preview/`:

- opened, closed, exploded and section;
- plenum_deck, loading and underside;
- harness (perspective) and harness_top (orthographic, deck removed);
- bay_45, bay_135, bay_225 and bay_315 close-ups;
- cold_pocket: a section through the serving site (PR 411 in its pocket, spacer, TEC, PR 614).

## Known gaps and risks

1. **Sink capacity** — addressed in rev 2 per [plenum sizing](plenum-sizing.md)
   (estimates): baffled hot sinks ~0.65 K/W, 70 × 60 mm cold sinks ~1.24 K/W,
   4 × TARK at ~44–47 W. Remaining risks: real sink products, installed fan and
   blower flow, and baffle leakage. All need measuring.
2. **Air leakage at the 1 mm lip gaps, tray seams and drive bore.** The hub area is
   open to the hot bay through the drive bore. Warm, moist air can reach the
   channel inner gap. Needs a hub labyrinth or seal (no foam).
3. **Window sealing:** 0.6 mm gap round each spacer to the hot bay. Use a
   silicone sealant bead, per the no-foam rule.
4. **Frost and defrost:** meltwater path is modelled, not proven. Pocket floors
   slope 1.5 mm to the drain and tubes push-fit into the deck (rev 2). Frost on
   4 mm-pitch cold fins will cut loop flow; the defrost interval is unknown.
   Estimated frost is ~3–15 g/day at 0.002–0.01 L/s leakage and 40–70 % RH,
   rising to ~26–55 g/day for a leaky 0.05 L/s chamber (heat_balance latent term,
   estimate). The owner chose evaporation basins (D37). The hand estimate assumes
   a water surface near the ~18 °C wet-bulb temperature of ~30 °C exhaust,
   Δρ_v ≈ 5 g/m³, h_m ≈ 0.01 m/s and 26 cm², giving ~10 g/day. That covers the
   tight-to-nominal cases. Above it the standpipes overflow through the floor,
   so water only drips under the feeder with a leaky lid in a humid room.
   Evaporation rate, mould and cleaning interval are untested.
10. **Hub-area leakage:** the route over the inner wall (1 mm) and down past the
   hub lip into the drive bore is a two-stage labyrinth with no seal. Sealing it
   would change the hub and tray, which are shared with the direct build, so it
   is deferred until leakage or frost is measured.
5. **Rolling drag** is estimated to be small, but is unmeasured. The owner expects
   no practical issue (stepper torque, low-friction PETG, 608 rollers), so it is
   an observation for the prototype, not a design driver. Sector seam gaps (0.6 mm)
   pass over the rollers. Bearing corrosion in cold, humid air is unknown; prefer stainless.
6. **Blower** inlet and outlet are envelope-level. A real 5015 outlet is offset to one
   side, and the candidate is 51.7 mm square against the 50 mm envelope.
9. ~~Wiring past the baffles~~ — modelled 2026-10-26 ([harness](harness.md)).
   The leads share the widened 23 mm slots. The coordinator accepted the
   extra leakage (~1.7 W at 20 mm, ~2.5 W extrapolated at 23 mm), so no comb.
7. ~~Thermal study geometry differs~~ — re-run on 15 × 77.5 mm and four sites in
   [plenum sizing](plenum-sizing.md) (2026-10-26).
8. Crescent PCB seat, cradles and 12-site supports are direct-mode only. The D34
   cards fit the plenum bays (above). Card heights come from `parts3d.json`,
   whose shapes are tagged datasheet, footprint or estimate; there are no
   vendor 3D models. Hand access is clear of the enclosure. Plug spacing on
   the cards leaves 12 of 21 plugs needing an extraction tool under the 8 mm
   grip criterion ([harness](harness.md)).
