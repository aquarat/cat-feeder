# Bottom fan and hot-side airflow

**2026-10-24 — dimensional review and lumped sizing, not CFD or a physical test.**
Read with [decisions](decisions.md), [drop-in internals](drop-in-layout.md),
[BOM](../BOM.md) and [thermal model](thermal-model.md).

## Recommendation for the next prototype

Use the **120 × 120 × 25 mm upward-blowing fan**, add a **2 mm-high printed
under-fan sealing skirt**, and move the wall exhausts into **Z58–80 mm**.
Preserve exhaust area by doubling the slit count. Enlarge the bottom slit field
within the existing fan footprint. Test this simple arrangement before adding
individual ducts. It encourages flow through the exposed lower sink region;
it does **not** establish equal flow through twelve sinks.

| Proposed change | Concrete bounds / rationale |
|---|---|
| Under-fan skirt | Square ring **118 mm outside, 114 mm inside**, wall 2 mm, **Z28–30**; centred on the fan. Union into the floor and existing corner seats. Top meets the stationary fan inlet frame, not blades. Verify actual Noctua frame/pad contact with a coupon. |
| Bottom intake | Two columns centred X=±28, slot length 50, Z25–28 through the 3 mm floor. Integrated CAD uses **17 equally spaced Y centres from −47 to +47**, width **3.5 mm**: 34 slots, **59.36 cm²** analytic throat area. Moving the proposed ±48 mm endpoints inward preserves **0.95 mm** nominal land to corner seats after the 0.3 mm easing. |
| Side exhaust | **120 slots**, 3 mm wide × **22 mm high**, angular pitch **3°**, bottom **Z58**, top **Z80**. Rounded-corner throat area **78.70 cm²**. At inner radius 146, circumferential pitch ≈7.64 mm, leaving ≈4.64 mm webs. |
| Isolation / ledge | Keep **Z80–81 solid**, deck ledge **Z81–84** intact, and wall above it unvented. Keep the deck, cartridge perimeter and drive penetration as the hot/cold boundary; a solid outer wall alone does not seal those interfaces. |
| Baffles above fan | None in the first trial. The bridge begins at Z56, only **1 mm** above the fan top: there is no room for an ordinary full-width outlet funnel. |

These recommendations are integrated into the v0.3 CAD, with the intake endpoint
adjustment above. See [geometry validation](validation.md) for the regenerated
mesh/loading evidence. The fan-inlet coupon reproduces the revised floor cuts,
seats and skirt; it is not a measurement of fan sealing or flow.
The inlet skirt stays below the fan and within its footprint, does not bridge
electrical bays, and preserves fan removal after lifting the motor bridge.
Use the existing floor seats/guides; no screws or foam. It is a leakage-reduction
contact, not a promised airtight gasket. Rounded fan corners, moulded frame
reliefs and anti-vibration pads may require the ring outline to follow the real
stationary contact land. Do not raise the fan to obtain compression: the bridge
clearance is already only 1 mm.

## Geometry basis and likely bypasses

Inspected `cad/parameters.scad`, `cad/feeder.scad` (`shell`, `deck`) and
`cad/internals.scad`, plus the linked KB. At inspection, the older cap-based
sink was Z55–95. This review evaluates the owner's **cap-removal revision**:

- Floor top Z28; fan Z30–55; motor bridge Z56–62.8; motor bottom Z58.
- Twelve 40 mm-square sinks centred at radius 105; **40 mm-high allowance
  Z58–98**, TEC Z98–102; deck Z84–102, ledge Z81–84.
- Body radius 158, bore radius 146; electronics at Z29.5–44.5 maximum.
- Original wall slots: 60 × 3 × 44, Z34–78. Original bottom slots:
  26 × 50 × 3. Both have 0.7 mm rounded plan corners; floor cuts are eased.

The sinks are **around**, not directly over, the fan's swept disc: their inner
radial face is at 85 mm, beyond even the nominal 60 mm fan radius. Air must rise,
turn radially and spread around the motor and bridge. Likely weaknesses:

1. **Fan recirculation:** the open 2 mm floor gap connects the pressurised
   equipment space back to the suction side. Its gross perimeter opening is
   up to `4 × 120 × 2 = 960 mm²` (9.6 cm²), before subtracting corner seats.
   That is about a quarter of the original intake area; area alone cannot
   predict the leak fraction. The low skirt closes this short path.
2. **Low side escape:** original exhaust starts at Z34, 24 mm below the revised
   sink tips. Air can go beneath the sinks straight to the wall. Raising the
   exhaust removes this direct low outlet, while retaining access below sinks.
3. **Around-sink bypass:** gaps between cartridges and the outer annulus remain
   easier routes than dense fins. Raising slots is not a substitute for a duct
   seal, and sink guides/boards make the split asymmetric.
4. **Dead upper fins:** sink material above Z84 lies inside deck recesses with
   only about 1 mm nominal side clearance in the inspected CAD. Most useful
   crossflow must be below the deck, not through that narrow pocket clearance.
5. **External re-ingestion:** preserve the 25 mm feet and a clear hard underside;
   test near the intended wall/corner because warm exhaust can return beneath
   the appliance. No carpet or filter performance is assumed.

Do not extend the wall slots above the ledge to chase the TEC at Z98: this would
cut the insulated cold-boundary wall rather than create a useful fin channel.
Do not add a fixed annular shelf across the board/sink insertion paths. If
testing later shows concentrated bypass, trial **removable, local cartridge
side cheeks**, floor-seat supported and lifted with the cartridge. Determine
their geometry from the purchased sink first; a full sealed manifold is not
justified by the present evidence.

## Stock sink is a significant interface choice

The BOM's [Fischer ICK S 40 × 40 × 20 / RS 674-4835](https://uk.rs-online.com/web/p/heatsinks/6744835)
is a **pin-fin** sink, not the 40 mm-high block drawn by CAD. Supplier text gives
40 × 40 × 20 mm, **3.5 mm base**, approximately 29 g and 3.5 K/W catalogue thermal
resistance. [TME's exact product](https://www.tme.eu/en/details/icks40x40x20/heatsinks/fischer-elektronik/ick-s-40-x-40-x-20/)
corroborates dimensions/base thickness; [Texim](https://www.texim-europe.com/product/electromechanical-devices/cooling/heatsinks-for-processors-and-led/detail/icks40x40x20-fis)
explicitly identifies pin construction. Search-index evidence was available;
direct RS retrieval was blocked. Finish descriptions disagree, so confirm the
actual part rather than using the RS generic mounting/finish attribute list.

Install the **flat base against the TEC, pins downward**. For a straight-fin
alternative, channels should run **radially inner-to-outer**, not tangentially;
pin fins are less sensitive to in-plane direction but still have flow resistance.
Do not support delicate pin tips as if they were the CAD block's solid corners:
the floor-supported cartridge needs suitable metal bearing lands/an adapter and
a distinct TEC compression load path.

**At the same Z98 hot face, this stock sink occupies Z78–98**, with its 3.5 mm
base at Z94.5–98. Only **6 mm of its height is below deck Z84**, and only Z78–80
overlaps the proposed exhaust band. A large flow can therefore pass below its
pins. Raising support seats by 20 mm does not resolve this thermal geometry.
Retain the 40 mm allowance as a labelled packaging study until a real sink is
selected; test the 20 mm part in a representative deck pocket before accepting
it. Using it efficiently could require a changed cartridge/deck pocket or hot
face height, which is a separate mechanical decision. Do not silently transfer
the 40 mm-envelope airflow expectation to the 20 mm purchased part.

The catalogue **3.5 K/W is not an installed rating**: the retrieved text does not
establish matching orientation, airflow and temperature conditions. Even using
it only as a sensitivity gives 17.5 K sink-base rise at 5 W per sink and 35 K at
10 W, above the **local** air temperature, before interface resistance. The
advertised 21.4 W dissipation corresponds to roughly 75 K rise at 3.5 K/W;
it is not a cool-running TEC design point.

## Fan and opening-area sizing

[Noctua manufacturer specifications](https://www.noctua.at/en/products/nf-a12x25-pwm/specifications),
retrieved through search-index text on 2026-10-24 (direct page returned 429):
NF-A12x25 PWM, **2000 rpm**, **102.1 m³/h / 60.09 CFM free air**, **2.34 mm H₂O
≈22.95 Pa shutoff pressure**, 12 V, 1.68 W maximum. With the low-noise adapter:
1700 rpm, 84.5 m³/h, 1.65 mm H₂O ≈16.18 Pa. **Maximum flow and maximum pressure
are different operating points**; neither is the installed feeder flow.

| Opening | Rounded-slot area | Relative to 120 × 120 fan square |
|---|---:|---:|
| Original bottom | 38.89 cm² | 27.0% |
| Original side | 78.95 cm² | 54.8% |
| Proposed bottom | 59.36 cm² | 41.2% |
| Proposed side | 78.70 cm² | 54.7% |

A nominal Ø120 circle is 113.1 cm², but the real rotor annulus is smaller and
partly blocked by its hub. These area comparisons are screening quantities,
not required minimum percentages. Frame overlap, corner seats and the 2 mm
distribution gap reduce effective inlet access; geometric throat area is
optimistic. Slot width through 12 mm wall thickness also matters.

Use `Δp = ρ/2 × [Q/(Cd A)]²` for each opening bank, adding inlet and outlet
losses. Here ρ=1.2 kg/m³, Q is m³/s, and **Cd=0.6–0.8 is an assumed sensitivity**,
not measured for these printed slots. It includes only a rough opening loss:
fins, turns, fan-frame/bridge obstruction, narrow inlet distribution and dust
are omitted. No full P–Q curve was digitised, so no installed operating point
is claimed.

| Flow scenario | Original inlet + exhaust loss | Proposed inlet + exhaust loss |
|---|---:|---:|
| 20 m³/h | 2.4–4.2 Pa | 1.3–2.3 Pa |
| 30 m³/h | 5.3–9.5 Pa | 2.9–5.2 Pa |
| 40 m³/h | 9.5–16.9 Pa | 5.2–9.2 Pa |
| 60 m³/h | 21.4–38.0 Pa | 11.6–20.6 Pa |

Values are rounded; lower loss uses Cd=0.8. Compare these with **22.95 Pa only
as an absolute full-speed catalogue pressure ceiling**, not pressure available
at the stated flow. Original slots can consume much of this fan's small
pressure budget. Enlarging the intake is useful; a much larger fan alone does
not resolve narrow openings or fin bypass. Reduced PWM speed needs a new
measured operating point; pressure capability falls approximately with speed².

## Heat balance: scenarios, not a TEC power prediction

Hot-side rejection is **Σ(Qc + V I)**, plus relevant motor/electronics/fan heat
in the air stream. A 100 W electrical supply does not make Qh exactly 100 W;
transferred cold-side heat must also be rejected. The food-only holding load
in the thermal model is not the complete Qc.

For net fresh-air flow, `ΔT_air = Qh / (ρ cp Q)`, cp=1005 J/(kg K):

| Net fresh flow | 60 W rejection | 100 W rejection | 150 W rejection |
|---|---:|---:|---:|
| 20 m³/h | 9.0 K | 14.9 K | 22.4 K |
| 30 m³/h | 6.0 K | 10.0 K | 14.9 K |
| 40 m³/h | 4.5 K | 7.5 K | 11.2 K |

These are mixed bulk outlet rises, not sink/TEC/food temperatures. Recirculated
fan flow must not be counted as fresh air. Uneven heat loading and bypass can
leave one sink hot even with a modest average exhaust rise. For reference,
100 W at a 10 K bulk rise requires ~30 m³/h of **net** flow; reaching that is a
measurement target, not a prediction that this housing supplies it.

Reproduce areas and tables with `python3 analysis/airflow.py`; the explicit
snapshot and all assumptions are in [the script](../analysis/airflow.py), with
[machine-readable output](../analysis/outputs/airflow.json). It does not read
changing CAD and must be updated if slot geometry changes.

## Physical checks that decide the next change

1. Print a fan-seat/skirt coupon. Check frame contact, intake direction, pad
   fit, blade clearance and bridge clearance; retain tool-free lift-out.
   Verify expanded slots do not undermine the corner seats after easing.
2. With deck and representative cartridges fitted, compare **original**, then
   **skirt**, then **skirt + upper exhaust band**, then enlarged intake at the
   same tachometer RPM. Use light tufts at each of the twelve sink outlets and
   side sectors; look for reversals and dead sites. Avoid contamination of
   food-contact parts. A visible tuft is not a volume-flow measurement.
3. Measure net flow with a low-resistance collection hood/flow instrument;
   account for hood back-pressure. A single anemometer reading at a narrow
   slit is insufficient. Measure differential pressure if practical.
4. Begin with one instrumented stock sink/TEC and log V, I, sink-base
   temperature, adjacent inlet/exhaust air and cold side. Then repeat around
   the ring under representative simultaneous loading, including motor duty.
   Use measured worst-sink temperature and selected TEC curves to set power.
5. Repeat with the intended room placement, dust exposure and reduced PWM.
   Check hot-air leakage through deck joints/drive hole into the cold chamber,
   condensation path and post-warm-up fit/creep. Decide on local removable
   baffles only from the observed poorly cooled sites.

**Outstanding:** actual fin geometry and support lands, operating P–Q point,
per-sink flow/thermal resistance, cartridge/deck air and moisture isolation,
and a demonstrated cooling/power envelope. No physical results are recorded.
