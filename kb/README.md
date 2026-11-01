# Cat feeder knowledge base

**Status: early mechanical prototype / packaging study, reviewed 2026-10-24.** CAD geometry is not evidence of cooling, hygienic cleanability, reliable indexing or production readiness.

| Page | Contents |
|---|---|
| [Decisions](decisions.md) | Current user requirements, exploratory choices and superseded brief assumptions |
| [General review 2026-10-25](review-2026-10-25.md) | Five-reviewer findings: rev A/B blockers, JLCPCB rules, thermal/drag concept limits; do not quote yet |
| [Cold-air plenum thermal study](plenum-thermal.md) | D35 forced-air alternative compared with direct contact at sub-zero faces |
| [Cold-air plenum CAD study](plenum-cad.md) | D35 geometry: channel, cold stacks, rollers, drains, electronics bays; checks and known gaps |
| [D34 hand-soldered controller](d34-controller.md) | Three through-hole cards (ctrl/pwr/tec) for the plenum bays: protection, TEC cut-off, checks, open risks |
| [D34 sourcing](d34-sourcing.md) | RS-first sourced BOM with verified datasheets, UK PCB fab comparison, costs, remaining uncertainties |
| [D34 simulation](d34-simulation.md) | ngspice/behavioural suite over the real netlists: hot-plug, reverse polarity, shorts, interlock, sensors, thermal (simulation, not test) |
| [Cable harness and fit](harness.md) | Card models, device mounts, 3D-routed harness with bend/clearance/water checks, cut list, hand access |
| [Plenum sizing on CAD geometry](plenum-sizing.md) | Hot/cold sink and fan models, TEC operating points, controller requirements (2026-10-26) |
| [Mechanical review](mechanical-review.md) | Actual CAD, missing interfaces, cleaning/access/printing and next physical checks |
| [Thermal model](thermal-model.md) | Thermal agent's separate analysis; consult its assumptions and status |
| [Direct-contact thermal model](direct-contact-thermal.md) | Current ceramic/PETG comparison, contact-gap sensitivity and food-path loads |
| [Bottom fan airflow](airflow.md) | Inlet skirt, upper exhaust band, opening areas and sink-fit limitations |
| [TEC power and control](tec-control.md) | Purchasable bench regulator/TEC, conditional 3S4P wiring, budgets and ESP32 integration |
| [Turnkey PCB assembly](pcb-assembly.md) | JLCPCB/PCBWay capabilities, fitted screw terminals and indicative UK-delivered prototype budgets |
| [Controller PCB draft](pcb-design.md) | Editable crescent KiCad design, reviewed fabrication/assembly files and integrated mounting |
| [Integrated controller revision B](../electronics/revb/README.md) | In-development USB-C PD, onboard stepper, efficient logic/fan supplies and source-based version identifier |
| [JLCPCB rule files](../electronics/dfm/README.md) | KiCad minimum/recommended DRC tiers from official pages |
| [Independent PCB review](pcb-review.md) | Corrections verified; cleared for project preparation; remaining supplier/bench checks |
| [Electrical simulation results](pcb-simulation.md) | Executed ngspice studies, automated regressions, operating limits and physical-test gaps |
| [Power simulation details](pcb-power-simulation.md) | Regulator thermal/load-step assumptions and motor-supply RLC transients |
| [Independent simulation review](pcb-simulation-review.md) | Reproduction, numerical/model checks and verified runner-failure fixes |
| [Physical PCB test plan](../electronics/bench/README.md) | Connector-level bring-up, measurement criteria and explicitly unrun hardware/firmware cases |
| [Revision B motor circuit](pcb-motor-integration.md) | Direct A4988, current setting, exact package and transient/layout requirements |
| [Revision B buck supplies](pcb-buck-integration.md) | Stocked 3.3 V/12 V converters, rail budgets and manufacturer-reference circuits |
| [PCB packaging](pcb-packaging.md) | Integrated Z33 edge seat, two lift-out sink cradles, four ledge notches and checked loading paths |
| [Component references](component-references.md) | Verified catalogue envelopes, mounting guidance and sourcing gaps |
| [Product-linked BOM](../BOM.md) | UK purchase routes, prototype/full quantities, prices and fit dependencies |
| [Sourcing evidence](sourcing.md) | Supplier findings, TEC comparison, dimensional mismatches and unresolved purchases |
| [Geometry validation](validation.md) | Mesh dimensions, bowl capacity, motion checks and defects caught |
| [Drop-in layout](drop-in-layout.md) | Floor supports, electrical pockets, staged top-loading and motor bridge |
| [Printing](printing.md) | Editable Bambu projects, honeycomb settings and unsliced status |

## Read first

- **Latest user decisions take precedence** over [the initial brief](../initial-design-brief.md). The brief remains historical context, not the current bill of materials.
- Current direction: twelve rounded pizza-slice food compartments, a thin removable tray on a broad keyed lift-off stepper coupling, and a hinged clip lid reusing the rowing IMU mechanism. No screws/bolts or foam; prioritize simple cleaning, maintenance and readily sourced components.
- **Latest enclosure direction:** honeycomb is a Bambu print setting, not CAD geometry. One clip, a domed lid sloping to a thin feeding lip, 12 mm cylindrical walls, a slotted closed underside and floor-supported, top-loaded component bays.
- Latest cooling prototype: **twelve distributed Peltier positions at radius 105 mm**, with **direct ceramic-to-PETG contact**. Small metal caps are removed at the owner's direction. One bottom axial fan supplies the hot-side bay; airflow and power studies support prototype choices, not a validated refrigerator.
- [Parameters](../cad/parameters.scad) and [geometry](../cad/feeder.scad) currently describe a 316 mm body, 280 mm tray and four three-compartment tray sectors. Dimensions remain provisional.
- Printable prototype geometry: tray sector, hub, drive, reused clip and closure coupons. Deck quarters are packaging coupons. The full shell/lid and purchased-component blocks are not a complete printable, retained assembly. See the review before printing a complete feeder.

## Provenance and evidence

- Rowing source: the upstream rowing-computer project, revision `5eb1d5683712bf8eaba0b004c4f59e09f8ab5160`.
- Nested OpenSCAD: `9431e59a74a1aa01c7ff742ec9e643a3d80cd0a5`; existing build image: `rowing-openscad`.
- Reused IMU mechanics (`enclosure/sensor/sensor.scad`, with its upstream validation limits); edge treatments use `openscad/libraries/edges.scad` from the same project.
- This KB review is source inspection and dimensional reasoning. Export/mesh reports are separate evidence; upstream fit trials apply to the small IMU enclosure, not automatically to this feeder. No feeder bench performance is established here.
