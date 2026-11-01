# Mechanical review

**Historical v0.1 review.** The later one-clip/domelike lid, slotted floor,
thicker shell and component bays are described in [decisions](decisions.md),
[drop-in layout](drop-in-layout.md) and [current validation](validation.md).
The findings below retain the reasons for changes and unresolved physical tests.

Source review, 2026-10-24: `cad/parameters.scad`, `cad/feeder.scad`, vendored rowing `enclosure/sensor/sensor.scad`, its README and `openscad/libraries/edges.scad`. **Early prototype; no exports or physical tests were run for this review.** Dimensions below are nominal source geometry, not measurements of prints.

Latest user addition: the top enclosure must contain retained-air honeycomb insulation. The primary agent is implementing sealed cavities in the lid/upper shell with solid opening, hinge and catch lands, plus a coupon. Proposed 0.8 mm skins, 12 mm cells and 0.8 mm webs are provisional. This addition was in progress at review time; the geometry inspection below predates those new cavities. The review **does include** the current bed-level sector flange (`flange_z=0`), lowered hub (`tray_z-2`), drive (`tray_z-6`) and recessed pickup lip.

## What is actually modelled

**Review follow-up:** the CAD now includes sealed honeycomb geometry and an
insulation coupon. The drive now has a 40.5 mm-radius shoulder supporting the
hub at Z=96 mm, a blind shaft-tip socket with a 1 mm roof, and two hub finger
tabs. A provisional 28 mm motor body with an 18 mm shaft puts its fixed face at
Z=82 mm, clear of the rotating drive. These address the nominal datum/handling
omissions in findings 2; actual fit, retention and loaded handling are untested.
The historical findings below describe the reviewed revision where indicated.
The deck now has 0.5 mm radial shell clearance and an integral shell ledge at
Z=80 mm. Its print-quarter seams are rotated 15° between cartridge sites, so
the prototype no longer cuts cooling pockets in half. Quarter retention/joints
and cold-cartridge support remain unresolved.

| Assembly | Present | Status / limit |
|---|---|---|
| Food tray | Four quarter sectors, three bowls each; 1.2 mm floor, 16 mm depth, rounded plan and floor transitions | Useful prototype geometry. Continuous bowl walls avoid a liquid-bearing assembly seam; loaded rigidity, capacity and cleaning are untested. |
| Lift-off drive | Broad 12-dog coupling with one wider master dog; through-socket hub, four rectangular sector lugs and lifting lip | Positive torque geometry, not reduction gearing. The hub and sectors are loose axial assemblies, not a captured carrier. |
| Closure | Imported IMU hinge/catch/clip geometry, feeder lid opening, 110° illustrated open pose | Reused functional mechanism geometry; feeder-scale fit, loads and motion not verified. Upstream coupons test the original straight-wall mechanism. |
| Cooling deck | 18 mm slab with central recess and twelve cap/TEC/sink pockets; a quarter print orientation | Packaging coupon, not a completed insulating/support assembly. Low-density infill is a slicer proposal. |
| Cooling equipment | Twelve caps, TEC blocks and 40 × 40 × 40 mm sink blocks; central 120 × 120 × 25 mm fan block | Envelopes only: no real fins, clamps, compliant interfaces, attachment, wiring or duct. |
| Enclosure / motor | 300 mm shell, vents, integral feet, short NEMA17 and shaft blocks | Packaging only: no printable shell/lid division, base floor, deck ledge, motor mount, electronics retention or service cartridge. |

## Priority findings

### 1. Establish the support and compression load paths

- **Original finding, nominal geometry addressed:** the deck floated in the shell. The follow-up adds 0.5 mm clearance and a support ledge (see above). The full deck shown in assembly still conceals the unjoined 0.6 mm gaps between printable quarters; retention is unresolved.
- **Cold caps have essentially no independent seat.** The through TEC opening is 41.2 mm wide; the cap is 41.28 mm. That leaves only **0.04 mm nominal overlap per edge** at the top-pocket shoulder, far below a credible printed ledge and less than the cap's lateral clearance. Treat the cap as needing a supported cartridge, not as resting securely in this pocket.
- Cap tops and deck top are both at Z=98 mm. Tray weight and sliding loads therefore can reach the caps and TEC stack unless a separate structural load path bypasses the ceramic. No clamp, preload control or cap-height adjustment exists. A raised cap snags/loads the thin tray; a recessed cap loses contact. Twelve sites magnify flatness and assembly variation.
- Screwless assembly still needs flat thermal interfaces, controlled compression and a supported metal/spring load path. No screwless clamp design is present. Printed warm hooks alone should not be assumed to maintain TEC compression; use actual component guidance and bench evidence.
- **Original split-pocket finding addressed in layout:** deck quarter seams now lie at 15/105/195/285°, between cap sites. Joint keys, moisture barriers and cartridge support still need space beside the pockets.

### 2. Lift-off coupling needs an axial datum and usable handling

- **Original datum finding addressed in CAD:** hub lip underside/top are Z=96/97.7 mm; recess floor Z=95.7; sector underside Z=98. The new drive shoulder now supplies the nominal axial support for the 0.3 mm pickup clearance.
- **Original motor-face contact addressed in CAD:** the provisional fixed motor face is now Z=82 mm and the blind drive socket seats on its shaft tip. The D bore still has clearance, not a demonstrated friction fit. Pulling the tray must leave the drive on the shaft; retention remains a fit-test dependency.
- Four lugs transmit torque at radius 52 mm; their tops nominally engage only about 3.7 mm into the 4 mm sector flanges, including the top chamfer. The lower lip can lift all sectors, but there is no positive axial capture, outer tie or handling grip. A loaded carrier may tilt, lift off a lug or flex during removal; demonstrate a level tool-free lift and individual sector washing.
- The master dog uniquely clocks **hub to drive**, not the four identical sectors to the hub. Reordered sectors can change portion order by 90°. Provide an intelligible starting reference/sector marking if portion sequence matters.
- Broad coupling diameter spreads tooth load; it does **not** reduce required motor torque. Measure startup drag after a cold humid dwell and a full 30° travel across the deck/cap boundaries. Use `T = F × r` with a measured tangential force and radius, then include acceleration and jam limits. Do not select from holding torque alone. Motor mounting, index/home feedback and parked-position retention are absent.

### 3. Dry joints are a layout intention, not moisture isolation

- Each bowl is continuous; quarter seams lie between bowls and lugs lie inside the food ring. This is a good basis for disassembly without liquid-tight structural joints.
- However, spills can enter the 0.6 mm sector seams and inner flange/lug holes. The cold-cap perimeter, wire notches, split deck and open drive well provide paths toward the motor and warm base. There is no catch area, drain path, drip barrier or penetration seal.
- Specify a removable washable spill surface and dry mechanical/electrical separation before treating the enclosure as usable. Avoid hidden water-filled infill or joints that require dismantling twelve thermal stacks for routine cleaning.
- A 1.2 mm printed liquid-contact floor and rounded corners are prototypes for leak/cleanability trials, not proof of a durable hygienic surface. Test leaks, food residue removal and the actual intended washing temperature; establish material/finish choices separately. Inspect both faces of every sector and the lug pockets after washing.

### 4. Feeding access and closure need full-size trials

- One 26° rounded wedge, inset by 2 mm, forms the lid opening. Its middle is only roughly 40–45 mm wide; it narrows toward the centre. The outer lid overhang further limits approach. Try the full-size opening with the actual cat rather than inferring access from cavity volume.
- Food floor is Z=99.2 mm and lid top Z=126.4 mm: access down to the floor is about **27.2 mm**, although the bowl is only 16 mm deep. The 2 mm rim-to-lid clearance also needs a spill/wipe and moving-edge check.
- The source reuses the small IMU's approximately 30 mm-wide hinge and 1.75 mm filament-pin convention on a 300 mm lid. Upstream fit history does not establish adequate hinge/root strength, sag, clip force or pin wear for this lever arm. The feeder's curved roots and two-clip arrangement require their own checks.
- Only `hinge_knuckles()` is imported into the feeder assembly: the upstream **hinge opening stop is not included**. `open_angle=110` is a display pose, not a physical stop or a hold-open feature. Add a supported open position and verify stability with the lid raised.
- Pins are not instantiated in the feeder preview. Upstream uses inserted, heat-headed filament with running clearance; define pin insertion/removal access and how the hinged lid is cleaned. Reusing heat-headed pins does not make the lid routinely detachable without a separate design.

### 5. Printing, exposed edges and thermal packaging remain incomplete

- A sector is bounded by roughly 140 × 140 mm and a deck quarter by 146 × 146 mm before brim; hub/drive/coupons are smaller. These are source bounds, not mesh validation. The full 300 mm shell and lid exceed the 180 mm bed and have no split/join/export implementation.
- Tray/flange undersides share Z=0, helping flat printing. The thin broad floor still needs a flatness/leak coupon. Inverted deck-quarter printing puts the chilled face on the bed, but stepped cartridge cutouts need slicer inspection for bridges and unsupported ledges.
- Proposed 0.8 mm skins and 5–8% infill are not encoded air-cell geometry or proven insulation. Low infill must still support the sliding plane, cartridge joints and seals without creep or moisture entry.
- For the new upper-enclosure honeycomb, verify closed cell boundaries at the feed opening, rim, split joints and hardware roots. Inspect roof bridging over the proposed 12 mm cells, especially with 0.8 mm skins; retained air requires continuous skins after printing and washing. Keep solid load-bearing lands around the hinge/catches and assess lid stiffness with the actual cavity pattern. A closed CAD void is not proof of an airtight print or a measured insulation value.
- Bowl mouths, exterior rims and dog tops have explicit edge treatments. Subtracted inner bores, lug holes, flange edges, vent cuts and some imported features do not automatically inherit those chamfers. Catalogue cap edges likewise need inspection. Preserve engagement lands while completing the exposed-edge requirement.
- Twelve sink blocks fit a ring as envelopes; a central fan block is not a distribution system. There is no defined inlet/exhaust separation, fin orientation, cleaning access, guarded underside, wire/connector volume or separation of warm air from the food space. Easier sourcing may reduce metal fabrication while increasing clamp/wiring/maintenance count; assess that tradeoff explicitly.

## Next evidence to obtain

1. Actual stock cap/TEC/sink dimensions and one supported, sealed, screwless cartridge coupon, including controlled cap height and an independent structural load path.
2. One sector + hub/drive fit trial: leak/cleaning check, flatness, grip, loaded lifting and reliable release that leaves the drive on the motor.
3. Full-size opening/hinge mock-up: cat access, loaded lid sweep, pin access, hold-open support, clip operation and stability. Reuse upstream coupons first, then validate feeder-specific roots and loads.
4. Loaded cold/humid breakaway and running torque, including cap transitions; position sensing and stopped-tray behaviour. Record conditions and measured values.
5. Complete small-printer joint layout and washable/dry separation; then relate mechanical contact measurements to the separate [thermal model](thermal-model.md).

These are unresolved prototype interfaces, not claims that the chosen user architecture cannot work.
