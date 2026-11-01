# Initial design guidelines

The starting brief for the project, condensed. Later owner decisions in
[`kb/decisions.md`](kb/decisions.md) take precedence; items marked
*superseded* are kept only as context.

## Intent

- A locally controlled, refrigerated feeder for small portions of wet cat
  food, built from PETG prints and ordinary purchased parts.
- Keep the mechanism simple: stationary cooling, one rotating food carrier,
  one fixed feeding opening. Effort goes into even cooling, reliable indexing
  and easy disassembly for cleaning.
- One portion is available at once. Eleven more advance on a schedule, then
  the feeder keeps cooling until it is cleaned and refilled. Assume a daily
  refill and clean, within the food maker's storage instructions. The
  food-age timer runs from when the food was opened.

## Food, size and printing

- Twelve portions of up to 40 mL each, with headroom above the fill.
  *Superseded:* the brief's commercial cups → twelve rounded compartments
  in a lift-out tray (D02, D09).
- The brief's starting size was about Ø340 mm. Size follows the portions
  and cat access; current dimensions are in D10.
- Every printed part fits a Bambu A1 Mini (180 mm cube nominal; aim for
  ≤170 × 170 mm, including joints and brim). Split large rings into sectors.
- Food-contact surfaces must be easy to wash. Layered FDM surfaces and
  filament additives are open food-contact questions, not solved ones.

## Mechanical

- No screws or bolts for construction or daily servicing (D05). Keys and
  interlocking surfaces carry loads; clips only retain them.
- Daily servicing is tool-free: lid off, tray out, wash, refill, reseat.
- Thermoelectric modules need flat, evenly compressed interfaces, with
  structural loads carried around the modules. Printed hooks should not hold
  that compression long-term; a removable cooling cartridge with metal spring
  retention is acceptable.
- *Superseded:* lift-off lid → hinged lid with one clip (D04, D14); foam
  insulation → printed air-gap insulation, no foam (D06, D12).

## Cooling

- Target 2–4 °C food, checked at the warmest location; US FDA guidance is
  ≤4.4 °C for opened wet food. Qualify at 30 °C ambient.
- Size modules from their performance at the real hot- and cold-face
  temperatures, not the headline maximum cooling figure.
- Keep warm exhaust air fully separate from the food chamber. Use guarded
  intakes, separate exhaust, and a grille or filter that is easy to clean.
- Manage condensation away from the motor and electronics. Avoid ice
  locking the tray. Pre-cool before loading food.
- Treat the brief's thermal budget (about 12–18 W holding load, 20–25 W
  useful cooling) as estimates to test, not as measured figures.
- *Superseded:* 300 mm aluminium cold plate with two TECs → distributed
  direct-contact TECs (D08, D19), with a cold-air plenum under comparison
  (D35); see the KB thermal pages.

## Power and electronics

- TEC supply: regulated, low-ripple, current-limited, and off by default
  until power and sensor readings are valid.
- *Superseded:* 100 W USB-C PD input → 24 V mains brick, with all
  electronics inside the case (D32, D33).

## Motion and control

- Central stepper (NEMA17 class, STEP/DIR driver). Advance 30° in about
  5–10 s with gentle acceleration, one direction only. Disable the coils
  when parked.
- Confirm every position with physical index feedback plus a unique home
  reference. A single home sensor is not enough.
- Defer movement while the cat is at the opening. Stop on timeout or
  obstruction. Stop after the eleventh advance.
- ESP32 with ESPHome. Cooling and the schedule run locally; Home Assistant
  is for configuration, visibility and alerts.

| Event | Behaviour |
|---|---|
| Network or Home Assistant down | Keep cooling and the local schedule |
| Manual advance | Same checks; consumes the next portion |
| Batch complete | Stop rotating, keep cooling |
| Tray jam | Stop the motor, keep cooling if healthy, alert |
| Cooling fault | Inhibit servings, alert, shut down unsafe cooling |
| Power interruption | Restart cooling safely; pause movement until checked |
| Duplicate or overdue command | No duplicate or rapid catch-up servings |

- Report location-labelled temperatures, fan status, position, portions
  left, next feed time, food-age deadline and fault state. A pause button,
  status light and buzzer are enough for a first version.

## Deliverables and order of work

1. A parameterised OpenSCAD assembly: one parameter file, purchased-part
   interfaces, assembly/exploded/section views and A1 Mini-sized parts.
   Reuse existing mechanical helpers and tolerance conventions.
2. A UK-oriented BOM with exact variants and purchase links.
3. Wiring, ESPHome configuration, and assembly, calibration, loading and
   cleaning instructions.
4. First establish food-container fit and access, cooling of the food,
   loaded rotation resistance and cooling at 30 °C ambient. Then finish
   the enclosure around those results.

Background references: [Ferrotec thermoelectric installation](https://thermal.ferrotec.com/technology/thermoelectric-reference-guide/thermalref06/)
and [power supply](https://thermal.ferrotec.com/technology/thermoelectric-reference-guide/thermalref07/) guides,
[FDA pet food storage](https://www.fda.gov/animal-veterinary/animal-health-literacy/proper-storage-pet-food-treats),
[Prusa food-safe printing](https://help.prusa3d.com/article/food-safe-fdm-printing_112313),
[ESPHome stepper](https://esphome.io/components/stepper/).
