Agreed—the saucer arrangement’s simplicity should be a **design requirement**. The brief keeps a stationary cooling assembly, one rotating food carrier and a fixed removable lid. The engineering work should concentrate on making that arrangement cool evenly, index reliably and come apart easily for cleaning.

An editable handoff document (a separate `.docx`, not included in this repository) accompanied this brief, with dimensions, component candidates, thermal and power budgets, assembly requirements and prototype checks.

The proposed baseline is a **340 mm diameter saucer with twelve removable cups, a stationary aluminium cold plate, two Peltier modules, one cooling fan, one tray motor and an ESP32**, powered from a **100 W USB-C PD supply**. These are starting specifications for the implementing agent; the cup dimensions and cooling performance need to be established before the enclosure geometry is finalised.

## 1. Design intent

Build a locally controlled refrigerated feeder for small portions of liquid cat food, using your existing OpenSCAD framework and PETG printing workflow.

The core arrangement is:

- A circular lower enclosure on four legs.
- A stationary refrigeration assembly inside the lower enclosure.
- A removable carrier holding twelve separate food cups.
- One central motor that advances the carrier by 30°.
- A fixed, removable lid with one feeding opening.
- ESP32 and ESPHome control, with the feeding schedule stored locally.

**One portion is available immediately; eleven subsequent portions can be scheduled.** After the final advance, the machine continues cooling and waits for cleaning and refilling. A fixed opening also means the last portion remains accessible until you remove it.

Use a daily refill and cleaning cycle as the initial operating assumption, subject to the food manufacturer’s storage instructions. The food-age timer should account for when the food was originally opened.

## 2. Proposed size and portion layout

| Feature | Starting specification |
|---|---|
| Outside diameter | **340 mm** |
| Overall height, including legs | **165 mm nominal**, with 150–180 mm available during packaging |
| Food rim height | Approximately **135–145 mm above the floor** |
| Legs | Four identical clip-in legs, approximately **30 mm clearance**, with compliant feet |
| Portions | **12 × 40 mL maximum**, 480 mL total |
| Cup capacity | Preferably **50–60 mL nominal**, providing headroom above a 40 mL fill |
| Cup rim diameter | **60 mm maximum target** |
| Cup centre layout | **240 mm pitch circle**, at 30° intervals |
| Rotating carrier | Approximately **308 mm diameter**, printed in four sections |
| Cold plate | One aluminium disc, **300 mm diameter × 6–8 mm thick** |
| Insulation | **15–20 mm closed-cell foam** wherever the geometry permits |
| Preferred printed part footprint | Within **170 × 170 mm**, including joining features |

The A1 Mini’s nominal build volume is 180 × 180 × 180 mm. Splitting the large circular components into quadrants gives room for joints while keeping the parts printable; the agent must check the complete bounding box of every part, including tabs and any brim allowance. [Technical Specifications](https://bambulab.com/en/a1-mini/tech-specs)

### Why start at 340 mm?

The cups and access for your cat determine much of the diameter. Twelve cup centres on a 240 mm pitch circle are approximately **62.1 mm apart**, allowing about 2 mm between adjacent 60 mm rims. Their outer edges reach a radius of 150 mm, leaving roughly 20 mm for clearance, insulation and the enclosure wall.

**The exact cups are the first unresolved component choice.** The implementing agent should source and measure a suitable cup before committing to the carrier. Capacity alone is insufficient: rim diameter, bottom shape, height and useful headroom all matter.

I would use removable commercial stainless-steel cups, with PETG forming the carrier. That gives straightforward washing and avoids making a layered printed surface the normal liquid-food container. Prusa’s guidance identifies both cleaning difficulties between print layers and uncertainty about filament additives as considerations for food-contact prints. [Prusa Knowledge Base](https://help.prusa3d.com/article/food-safe-fdm-printing_112313)

## 3. Mechanical stack

The brief specifies the following assembly, from top to bottom:

| Assembly | Purpose |
|---|---|
| **Fixed lid** | Covers the waiting portions and exposes one cup through a rounded feeding opening. Lifts off for loading and cleaning. |
| **Rotating carrier and cups** | Four interlocked PETG carrier sections, three cups per section, joined to a central drive hub. Cups lift out independently. |
| **Stationary cold plate** | Distributes cooling under all twelve positions, including the serving position. |
| **Insulation carrier** | Printed PETG structure that locates foam, supports the chilled assembly and separates it from the warm base. |
| **Cooling and drive assembly** | Two Peltier modules, their heat sinks, one ducted fan and a central motor cartridge. |
| **Lower enclosure and legs** | Houses the electronics, provides guarded vents and raises the inlet above the floor. |

### The cup-to-plate interface is the main mechanical prototype

The proposed simple arrangement has the **cup bottoms resting on the cold plate**, while the rotating carrier pushes them sideways. The cup pockets should permit slight vertical movement so that the carrier does not suspend the cups above the plate.

This interface needs an early test using the actual cups:

- Does the bottom make sufficient thermal contact?
- Does the upper layer of food stay cold?
- How much force is needed to start moving a full tray after several hours of cold, humid operation?
- Does condensation cause sticking?

A cup with a deeply recessed bottom could cool poorly even when its rim fits perfectly. Resolve that through cup selection and plate finish before designing the complete housing.

### Screwless assembly

Use **keys and interlocking surfaces to carry loads**, with clips retaining those joints.

The intended approach is:

- Sliding tongues or shallow dovetails between enclosure quadrants.
- Captive joining keys with replaceable snap tabs.
- A keyed motor pocket with a clip-in retaining bridge.
- A positively keyed shaft connection to the carrier.
- PCB rails and removable retaining clips.
- Clip-in legs and a removable fan cartridge.
- A keyed bayonet or clip ring for the lid.

The thermal assembly needs a different kind of clip: **metal spring retention with a metal load path**. Peltier modules require flat interfaces and controlled, even compression; printed PETG hooks should not be responsible for maintaining that compression against a warm heat sink. Ferrotec’s installation guidance also calls for structural loads to be supported independently of the thermoelectric module. [Thermoelectric](https://thermal.ferrotec.com/technology/thermoelectric-reference-guide/thermalref06/)

This still satisfies the screwless requirement. The agent should design a removable cooling cartridge retained in the printed housing, with spring clips or an over-centre metal clamp securing its thermal stack.

## 4. Refrigeration design

### Cold plate and Peltier modules

Start with a **300 mm aluminium plate**, evaluating **8 mm thickness** initially. Place two identical 40 × 40 mm Peltier modules beneath opposite sides, approximately **75–80 mm from the centre**.

Two cooling points shorten the heat-conduction distance to the cup ring and leave the middle available for the drive.

Suitable candidates are:

| Component | Candidate | Selection notes |
|---|---|---|
| Preferred Peltier module, quantity two | **TARK CP14-127-06-L1-RT-W4.5**, part **56760-500** | Approximately 40 × 40 × 3.81 mm, 6 A class, with sealed edges. Its quoted 49.3 W maximum cooling is measured at zero temperature difference and a 27°C hot face. [Tark Thermal Solutions](https://tark-solutions.com/products/thermoelectric-cooler-modules/peltier-cp-series/CP14-127-06-L1-RT-W4.5) |
| Alternative Peltier module | **Same Sky CP60440** | 40 × 40 × 4 mm, 6 A class, sealed. Recalculate performance and clamp spacing if substituted. [Single-Stage Peltier Modules](https://www.sameskydevices.com/product/thermal-management/peltier-devices/single-stage-peltier-modules/cp60440\) |
| Hot-side fan | **Noctua NF-A12x25 PWM** | 120 × 120 × 25 mm, 12 V, four-pin fan with PWM control and an RPM signal. [Noctua](https://www.noctua.at/en/products/nf-a12x25-pwm/specifications) |

The agent must select the modules using their performance at the intended hot- and cold-face temperatures. The maximum cooling figure on a product listing is insufficient for sizing the appliance.

### Thermal budget

The brief uses these **preliminary engineering estimates**:

- Approximately **12–18 W holding load**, including insulation losses, seams, the opening and structural bridges.
- A qualification target of **20–25 W useful cooling capacity** at the actual operating temperatures.
- Approximately **50–60 W electrical input** reserved for the Peltier pair at the upper end.
- Approximately **70–80 W heat rejection** under that condition.
- A **90 W hot-side test target** to provide some margin.

These figures give the implementing agent a starting point for calculations and bench tests. They are not measured performance.

The operating target is **2–4°C food**, with the warmest food location checked directly. FDA pet-food guidance recommends promptly refrigerating unused wet food and setting the refrigerator to 40°F, approximately 4.4°C, or below. The specific diet’s instructions still govern its storage life. [FDA](https://www.fda.gov/animal-veterinary/animal-health-literacy/proper-storage-pet-food-treats)

### Heat sinks, fan and vents

Reserve space for two heat sinks, each approximately **90–100 mm square and 35–45 mm high**, with one fan feeding a split air duct.

Those dimensions are packaging allowances; the heat sinks still need a verified thermal rating. The target in the brief is approximately **0.30–0.35 K/W or better per branch**, including the interface, at around 40 W per branch.

The geometry must preserve the motor gap. For example:

> Two 100 mm wide heat sinks centred 80 mm either side of the middle leave a 60 mm gap for the motor cartridge.

The lower housing should provide:

- Guarded intakes underneath or low on the sides.
- Exhaust openings separated from the intake.
- A duct that directs air through both heat sinks.
- Sufficient leg clearance to keep the inlet usable.
- Easy access to clean the grille or filter.
- Complete separation between warm cooling air and the food chamber.

### Insulation and condensation

The printed intermediate layer should **hold actual insulation**. Use closed-cell foam inserts around the cold chamber, beneath the plate and inside the lid, with thin PETG ribs where support is needed.

Provide seals around the chilled volume and the Peltier penetrations, and a removable condensation catch area isolated from the motor and electronics. Keep the cold regions above freezing during ordinary operation so ice does not obstruct the tray.

**Pre-cool the empty feeder before loading it.** An approximately 300 × 8 mm aluminium plate weighs around 1.5 kg; loading chilled food onto that plate while it is at room temperature would add a substantial warming load.

## 5. USB-C power and electronics

Use an external **100 W USB-C PD supply supporting 20 V at 5 A**, with a suitable 5 A electronically marked cable.

Two practical PD starting points are:

- **Adafruit product 5991**, the switchable breakout revision documented as supporting 5 A.
- A suitably rated **STUSB4500-based board**, configured for a 20 V / 5 A profile.

Adafruit documents voltage/current querying through I²C; ST documents autonomous negotiation up to 100 W using configured power profiles. The implementing agent must verify the exact board revision and its complete power path. [Adafruit Learning System](https://learn.adafruit.com/adafruit-usb-type-c-power-delivery-switchable-breakout/overview)

### Proposed electrical arrangement

Use **one current-regulated buck converter feeding the two Peltier modules in series**, with separate regulated supplies for the fan, motor and logic.

Initial bench evaluation can start around **2.5–3 A through the series pair**, subject to the modules’ measured voltage and cooling performance. Reserve up to approximately 60 W for the pair, with a total planned device peak around **85 W**.

The TEC supply should deliver controlled, low-ripple DC and default to off until the power contract and sensor readings are valid. Ferrotec’s power-supply guidance explains the importance of limiting supply ripple for thermoelectric operation. [Thermoelectric](https://thermal.ferrotec.com/technology/thermoelectric-reference-guide/thermalref07/)

The brief deliberately leaves the **exact controllable buck converter** as an engineering selection task. The agent needs to document its current limit, efficiency, enable behaviour and ESPHome interface. A PD board and a regulator should not be assumed to have native ESPHome support.

## 6. Tray rotation and local control

Use a central **NEMA17-class stepper with an A4988-compatible driver** as the starting architecture. The document names a short motor candidate, but final selection depends on the measured force needed to move the loaded, chilled cups.

ESPHome supports A4988 STEP/DIR control and a sleep pin for disabling the motor when parked. [Smart Home Made Simple](https://esphome.io/components/stepper/)

The required behaviour is:

- Advance **30° in approximately 5–10 seconds**, with gentle acceleration.
- Rotate in one direction.
- Disable the coils when parked.
- Confirm each position with physical indexing feedback.
- Defer movement while the cat is at the feeding opening.
- Stop promptly on a movement timeout or obstruction.
- Stop advancing after eleven successful moves.

Use an index feature at each serving position and a unique starting reference. A passive slotted ring with optical sensing in the dry base is one suitable implementation. A single home sensor would not confirm that each intermediate serving actually moved.

### ESPHome behaviour

Cooling and scheduling should run locally. Home Assistant provides configuration, visibility and alerts.

The brief requires:

| Event | Behaviour |
|---|---|
| Wi-Fi or Home Assistant unavailable | Continue cooling and a valid local feeding schedule |
| Manual advance | Apply the same checks and consume the next portion |
| Batch complete | Stop rotation and continue cooling |
| Tray jam | Stop the motor, retain cooling if healthy and alert |
| Cooling fault | Inhibit further servings and alert; shut down unsafe cooling operation |
| Power interruption | Restart cooling safely, but pause movement until the tray and food have been checked |
| Duplicate or overdue command | Avoid duplicate servings or several rapid catch-up advances |

ESPHome’s API and Wi-Fi disconnect reboot settings need deliberate configuration; both offer `reboot_timeout`, with `0s` disabling the respective disconnect-triggered reboot. [esphome.io](https://esphome.io/components/api/)

Provide temperature readings labelled by location, fan status, current position, portions remaining, next feed time, food-age deadline and fault state. A physical pause button, status light and buzzer are sufficient for the first version.

## 7. Instructions for the implementing agent

The document directs the next agent to **inspect and reuse your existing OpenSCAD framework**, including its build system, joint helpers and tolerance conventions. It does not assume framework APIs that have not been supplied.

The implementation should deliver:

1. A parameterised assembly with dimensions and purchased-component interfaces in one place.
2. Separate printable parts that fit the A1 Mini.
3. Assembly, exploded and sectional views.
4. Dimensioned drawings for the aluminium plate and other metal parts.
5. A UK-oriented bill of materials with exact variants.
6. A wiring diagram and ESPHome configuration.
7. Assembly, calibration, loading and cleaning instructions.

The first prototype work should establish **cup fit and access, cup-to-plate cooling, loaded rotation resistance, and cooling performance at 30°C ambient**. The full enclosure should follow those results.

The central handoff instruction is:

> **Preserve the simple saucer mechanism. Establish the actual cup dimensions and thermal interfaces first, then design the screwless printed housing around them.**
