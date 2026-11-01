# Turnkey PCB assembly for the cat feeder

**Research date: 2026-10-24. Recommendation and budget allowances, not a vendor
quote or tested controller.** Later work produced an independently reviewed
[controller design](pcb-design.md) and a prepared JLCPCB project.
No quote request or order was submitted. Context: [KB index](README.md), [decisions](decisions.md),
[BOM](../BOM.md), [TEC power/control](tec-control.md). The current electronics
evidence includes the reviewed draft, but not fabrication acceptance or bench qualification.


**Latest owner clarification:** screw terminals are explicitly permitted for
this electronics investigation under D22. The earlier proposed removal of
DPS5005 screw terminals is superseded. Mechanical mounting and daily cleaning
remain screwless/tool-free; this does not settle enclosure changes.

The owner subsequently requested a component-availability-driven design
iteration (D23). The functional scope and costs below are research assumptions;
they must be reconciled with the resulting PCB's actual BOM and assembly mix.

## Recommendation

**Use [JLCPCB Economic PCBA](https://jlcpcb.com/pcb-assembly) for a small,
single-side-populated controller/carrier, with the screw terminals fitted by
the factory. Keep the purchased DPS5005 as the separate TEC power stage.**
JLC can fabricate the board, procure its stocked components and assemble both
SMT and supported through-hole parts in one manufacturing order. EasyEDA's
JLC/LCSC-linked library makes part selection convenient; KiCad is equally usable
with the correct manufacturing exports. LCSC stock alone does not prove JLC
assembly availability: select actual JLC assembly-library parts.

- If only one working board is wanted, budget for **two assembled boards** at
  JLC's published minimum. Five assembled boards spread setup/shipping costs,
  but two limit money tied up in a first revision.
- Budget roughly **£100–220 delivered for two**, or **£150–330 for five**, for
  the proposed populated controller below. These are deliberately broad planning
  estimates including an allowance for UK VAT, **excluding design/firmware and
  the external TEC regulator**. Details and confidence are below.
- Use [PCBWay turnkey assembly](https://www.pcbway.com/pcb-assembly.html) as the
  comparison/backup when unusual connectors, purchased daughterboards, harnesses
  or bespoke hand assembly make JLC's library workflow awkward.
- If “one-stop” includes **inventing the circuit and writing firmware**, PCBWay
  also offers a separately quoted [electronic design service](https://www.pcbway.com/pcbdesign.html).
  Assembly pricing does not cover that engineering.

## What the first board should contain

Proposed functional scope, not approved pin assignments or a schematic:

| Function | Practical first-board scope |
|---|---|
| Controller | Factory-soldered Espressif ESP32 module, decoupling, boot/reset and accessible programming pads/header. Keep its antenna at a board edge with the manufacturer's keep-out. A bare ESP32 chip adds unnecessary RF design work. |
| Motion | One current-regulating A4988-class driver circuit for the existing 1 A/phase NEMA17, with local bulk capacitance, current-setting provision, sleep/enable and motor screw terminals. A socket for the already-selected Pololu carrier is an engineering-saving alternative; then the purchased carrier is an extra item, not automatically part of turnkey assembly. |
| Fan | Keyed 4-pin PC fan header, 12 V supply, open-drain PWM interface and 3.3 V-safe tach input. Fan stays powered when the TEC is disabled. |
| Sensors | Several labelled temperature-probe headers with appropriate pull-ups/protection; two position-feedback inputs and an I²C expansion header for the proposed presence sensor. Sensor count and connector pinout remain to settle. |
| Auxiliary rails | Stock-component 12 V fan and 5 V/3.3 V logic supplies, designed for the selected source and actual startup loads. These small supplies are distinct from the high-power TEC converter. |
| Power distribution | Screw-terminal DC input from the external PD trigger; input fuse/protection, reverse-polarity/transient provisions, source-voltage monitoring and default-off TEC enable. Size copper, connectors and protection for the real current/temperature; a terminal's headline rating is not a PCB rating. |
| TEC interface | Connections to DPS input/output, UART and independent shutdown/interlock. Four protected branch outputs if the conditional 3S4P arrangement is retained; keep converter output return/sense routing separate as required by its actual shunt topology. UART voltage/grounding needs the checks in the TEC study. |

Start the layout exercise around **80 × 60 to 100 × 80 mm**, 2-layer FR-4,
1.6 mm, green mask, ordinary finish, components on one side; these are tentative
costing dimensions, **not a verified bay fit**. Four layers or heavier copper may
be justified by the actual power/ground layout. Allow terminal height, wire bend
radius, screwdriver access and dry-side strain relief. The existing DPS5005 is
42 × 45 × 80 mm and already fails the provisional converter-pocket dimensions;
it is initially external bench equipment, not a plug-in module that already fits.

### Why retain the purchased TEC buck?

The proposed source is **20 V/5 A input**, not a requirement for 20 V at 5 A
output. The conditional array needs roughly 4–4.8 A total at a lower voltage;
the TEC study proposes a 70 W output budget. A buck cannot deliver a regulated
20 V from a nominal 20 V input with normal losses, and 100 W output would leave
no allowance for conversion losses or the fan/controller/motor.

A fully custom replacement for DPS5005 needs an appropriately rated switching
controller, inductor, MOSFETs/diode, current sensing, CV/current-limit loops,
compensation, low-ripple output, default-off behaviour and thermal/EMI layout.
An ESP32 PWM pin plus MOSFET is not an equivalent smooth-DC TEC regulator.
Startup, short-circuit behaviour, ripple, efficiency and installed temperature
would need bench qualification and possibly another PCB revision.

Retaining a roughly **£45 inc-VAT DPS5005** (existing BOM observation, delivery
extra) avoids that first-spin development work. Connect it by terminals/UART;
only mount a regulator daughterboard directly on the carrier after selecting
an exact board, pinout, mechanical support and proven continuous rating.
Do not assume JLC stocks or will assemble the retail Joy-IT module. PCBWay can
quote procurement/integration, but its acceptance and price remain unverified.
The recommended low-cost order is one-stop **for the populated controller PCB**;
the regulator, source, motor, fan, probes and TECs remain purchased peripherals.

## Manufacturer evidence and assembly tradeoffs

**D = directly retrieved manufacturer page; I = manufacturer page observed via
search index only.** All observations below are from this research date. Library
stock and prices can change before design completion.

### JLCPCB — best starting point for low total cost

- **D:** [Capabilities](https://jlcpcb.com/capabilities/pcb-assembly-capabilities)
  explicitly permit single-sided **SMT/through-hole** in Economic, quantity
  **2–50**; Standard lists **2–80,000**, including double-sided placement.
  Some board-option combinations have tighter limits. PCB fabrication quantity
  and assembled quantity are separate; allow a small bare-board lot even when
  only two are populated.
- **D:** [Assembly FAQ](https://jlcpcb.com/help/article/pcb-assembly-faqs)
  says library parts marked **“Wave Soldering” are assembled manually**, with
  about one extra production day. Thus factory-fitted screw terminals are a
  normal supported service, not necessarily an expensive custom exception.
  An unlisted connector/module still needs individual acceptance and pricing.
- **I:** Concrete candidate: Ningbo Kangnex **WJ500V-5.08-2P,
  [C8465](https://jlcpcb.com/partdetail/WJ500V-5.08-2P/C8465)**, two-pole
  5.08 mm screw terminal. The listing marks **Wave Soldering / Economic and
  Standard**. The [terminal-library index](https://jlcpcb.com/parts/2nd/Connectors/Screw_Terminal_Blocks_2204)
  showed 336,802 stock and about **US$0.1345 each at quantity 1**. Direct product
  retrieval returned no body, so stock/price are indexed observations, not a
  checkout confirmation. Verify its datasheet, wire entry and height before use.
- **I:** Espressif **ESP32-WROOM-32E(M113EH6400PH3Q0),
  [C7274980](https://jlcpcb.com/partdetail/C7274980)** is listed for SMT assembly
  on Economic/Standard. This demonstrates a module route, not selection of that
  exact flash variant or confirmation of current stock.
- **D:** The [price table, updated 22 October 2026](https://jlcpcb.com/help/article/pcb-assembly-price)
  lists Economic setup **$8.18**, stencil **$1.53**, SMT **$0.0016/joint**,
  hand-solder labour **$3.58/order**, manual joints **$0.0164/joint**, and
  **$3.07 per unique Extended SMT part**. Basic and Preferred Extended parts
  avoid that Economic feeder-loading fee. The older FAQ shows slightly different
  figures; use the newer price table and ultimately the actual quote.
- Example: ten two-pin terminals on each of five boards give **100 joints**:
  approximately **$5.22 total hand-solder labour/joints**, plus terminal parts
  and any separately applicable processing. That is not the whole PCBA price.
  JLC's [October cost explanation](https://jlcpcb.com/blog/reduce-pcb-assembly-cost-prototype)
  says through-hole parts do not carry SMT feeder-loading fees.
- Standard's current setup is **$25.56/side**, stencil **$8.21/side**, feeder
  loading **$1.53 per unique Basic/Extended part**, with possible handling,
  fixtures and X-ray charges. Keep the first board eligible for Economic where
  practical; confirm the chosen module/driver's actual assembly classification.

**Procurement matters more than pennies per joint:** use in-stock Basic/Preferred
parts for common passives and minimise different Extended part numbers. Twelve
unique Extended SMT types alone add **$36.84/order** before buying their parts.
Minimum purchase quantities and assembly attrition mean a one-board BOM is not
the same as a one-board component bill.

JLC supports pre-order, global sourcing and consigned components. Its
[global-sourcing terms](https://jlcpcb.com/help/article/global-sourcing-parts-order-terms-conditions)
(**D**) describe possible 3–30% import charges for some part categories, $20/type
inspection fees for some connectors/switches/fuses, and loose-part/baking fees.
These are sourcing-to-China charges, distinct from shipping the finished board
to Britain. Its [consignment terms](https://jlcpcb.com/help/article/consignment-part-terms-conditions)
(**D**) list **$85 for 1–50 overseas part numbers**, plus applicable taxes;
other [consignment guidance](https://jlcpcb.com/help/article/important-note-before-you-consign-the-part-to-jlcpcb)
(**I**) gives $45/$85 value-dependent cases. Treat the exact current charge as
unresolved rather than choosing the lowest figure. Overseas consignment is a
poor default for a cheap two-board spin. Use stocked terminals instead.

### PCBWay — flexible turnkey and hand-assembly alternative

- [Assembly service](https://www.pcbway.com/pcb-assembly.html),
  [through-hole service](https://www.pcbway.com/pcb_prototype/Through_Hole_Assembly.html)
  and [component sourcing](https://www.pcbway.com/pcb_prototype/Electronic_Components.html)
  (**I**) offer SMT, through-hole and mixed assembly; turnkey, customer-supplied
  or mixed procurement; and distributor sourcing including DigiKey/Mouser.
  It can procure specified terminals and quote hand assembly. There is no
  verified universal terminal-fitting price; this is BOM/job-specific.
- **Minimum ambiguity:** its current [capabilities page](https://www.pcbway.com/assembly-capabilities.html)
  (**D**) says five pieces. Its older official
  [Q&A](https://www.pcbway.com/blog/PCB_Basic_Information/PCBWay_Q_A_003___Common_Questions_for_PCBA_Ordering_01.html)
  (**I**) explicitly permits one assembled piece, and
  [another Q&A](https://www.pcbway.com/blog/PCB_Basic_Information/PCBWay_Q_A_004___Common_Questions_for_PCB_Assembly_Service_on_PCBWay_02.html)
  distinguishes five bare PCBs from no assembly MOQ. **One assembled board is
  a quote request, not a confirmed current entitlement; five is the safe comparison.**
- Its [21 October 2026 $29 assembly promotion](https://www.pcbway.com/blog/PCB_Assembly/How_to_Get_29_PCB_Assembly_and_Meet_the_Requirements_e334dbde.html)
  (**I**) requires PCBWay-supplied parts, rigid boards, ≤20 boards, ≤200
  components/board, ≤600 components/order, ≤100 unique types and **≤100
  through-hole joints across the entire order**, plus customer eligibility.
  Ten two-pin terminals × five boards already use all 100 joints: fan/sensor
  headers or driver sockets would exceed it. Do not budget this feeder around
  the $29 headline. PCB fabrication, parts, shipping and taxes are additional.
- [Ordering](https://www.pcbway.com/helpcenter/Findproducts/How_do_I_place_an_order_.html)
  (**I**) says the assembly stencil is supplied without a separate purchase.
  [Overage rules](https://www.pcbway.com/assembly-faq.html) (**I**) require extra
  parts, sometimes a minimum of 50/100 passives; procurement and hand-assembly
  labour should be itemised in the eventual quote. Programming and functional
  testing require supplied methods and separate agreement.

### Optional UK comparison: PCB Train / Newbury Electronics

[PCB Train assembly](https://www.pcbtrain.co.uk/products-and-services/pcb-assembly/)
(**I**) offers UK manufacture/assembly, component procurement, SMT plus
technician/selective-soldered through-hole parts, included stencil/tooling and
some [free stocked components](https://www.pcbtrain.co.uk/pcb-train-free-components-list/).
Its [FAQ](https://www.pcbtrain.co.uk/frequently-asked-questions/) says bare-board
fabrication and assembly are separate transactions with the same supplier.
Exact one/five-board minimum acceptance and prices were not established. It is
a credible domestic comparison, not evidence of a cheaper option; obtain its
all-in quote rather than assigning an invented UK manufacturing price.

## One versus five: honest UK-delivered budget

Assumptions: the proposed small populated controller, roughly 15–30 unique BOM
types / 50–100 placements, ordinary stocked parts, modest through-hole terminals
and headers, no bespoke harness, no expedited delivery, no design or firmware
service. **These are engineering allowances, not prices returned by a quote tool.**

| Service | Need one functional prototype | Five populated boards | Confidence |
|---|---|---|---|
| JLC Economic | Order two: **£100–220 total**; exactly one is below published MOQ | **£150–330 total**, approximately £30–66 each | Medium on service/fee structure; low-to-medium on total until BOM/layout exist |
| PCBWay turnkey | **£100–250 total if one assembled board is accepted**; expect a minimum bare-board lot | **£180–400 total**, approximately £36–80 each | Low: procurement, terminal labour and promotion eligibility unresolved; may overlap/beat JLC on a particular BOM |
| PCB Train UK | Quote required | Quote required | Capability credible; no defensible project-specific price obtained |

JLC allowance derivation, in GBP before VAT: **£5–15 PCB lot + £25–55
setup/stencil/loading/assembly + £15–30 components per populated board + £5–15
attrition/part minimums + £15–30 shipping**. Two boards give approximately
£96–210 after 20% VAT; five give £150–318. Rounded budgets above allow modest
variation. GBP values are budgeting assumptions, not a live USD exchange quote;
specific power parts, Standard-only assembly or customs charges can exceed them.
PCBWay's broader allowance uses similar component/shipping costs with more
uncertainty in fixed procurement/assembly costs; no comparative quote was run.

Allow **another ~£45 per actually equipped feeder** for its DPS5005, plus delivery
if applicable; spare controller boards do not each need a regulator. Source/PD
trigger, fan, probes, motor, TECs, wiring and programming adapter are outside
the PCB totals. A socket-only carrier would have a lower PCB BOM but require
adding the purchased ESP32/driver/rail modules to compare equivalent systems.

For delivery to **Great Britain**, allow normal **20% VAT** on the relevant
taxable total, including shipping; [HMRC guidance](https://www.gov.uk/goods-sent-from-abroad/tax-and-duty)
explains checkout collection for purchases ≤£135 and import collection for
higher-value consignments. Above that threshold, customs duty depends on
classification; do not assume a particular assembled-controller tariff. Check
tax-paid versus receiver-paid shipping and carrier clearance fees, and avoid
counting VAT twice. Northern Ireland arrangements can differ. Final postcode,
weight, shipping method and tariff have not been quoted.

## What must exist before manufacture

### API automation and board outline — follow-up assessment

The [official API overview](https://jlcpcb.com/help/article/jlcpcb-online-api-available-now)
was directly rechecked on 2026-10-24. It documents Gerber upload, automated PCB
pricing, PCB order creation/tracking, and component specification/stock/price
queries. Access requires an application at [api.jlcpcb.com](https://api.jlcpcb.com/)
and supplier approval; an ordinary account does not guarantee access. Public
documentation does **not establish complete PCBA BOM/CPL matching, placement
review and assembled-order checkout API coverage**. Confirm the granted API
scope before promising an end-to-end assembled order. The unauthenticated API
list rendered only a shell during this review. No API access was used.

The owner authorizes preparation of the supplier order, will submit the quote
request personally, and requires independent PCB review before creating any
quotable components/project (D25).


Circular/annular outlines are feasible, but not required merely because the
enclosure is cylindrical. The current bore is Ø292 mm and the central fan is
120 mm square, so a large floor-level board would need a substantial centre
opening plus keep-outs for cartridge supports and wiring. It adds board area
and mechanical constraints. A small rectangular/rounded controller near the
perimeter is the preferred first-layout study; a crescent or separate passive
distribution ring is worth considering only if measured fit/wiring benefits
justify it. This is a recommendation, not an owner-selected outline or a passed
fit check. Subsequent owner direction D24 favours the crescent option if it
improves packaging; that preference has been passed to the PCB design agent.

### Manufacturing inputs

1. **Electrical design:** complete KiCad/EasyEDA schematic and PCB, verified
   footprints and source/rail/current ratings. Pin down the PD interface,
   motor current, sensor count, TEC branch protection, shutdown and connector
   orientations. The existing shopping BOM is not an assembly BOM.
2. **Manufacturing package:** Gerber layers and drill files; BOM with reference
   designators, exact manufacturer part numbers, quantities and JLC/LCSC codes
   where applicable; CPL/pick-and-place XY/rotation/side; assembly drawing with
   polarities, terminal wire-entry directions and any do-not-fit parts. See
   [JLC's file FAQ](https://jlcpcb.com/help/article/pcb-assembly-faqs) and
   [PCBWay's file requirements](https://www.pcbway.com/assembly-file-requirements.html).
3. **Programming/test:** provide firmware image, flashing interface/procedure
   and acceptance tests if factory programming/testing is wanted. Assembly
   inspection, AOI and bare-board continuity do not demonstrate local thermostat
   logic, fan-fault shutdown, loaded motor indexing or TEC performance. The
   ESP32 arrives without the feeder application unless separately arranged.

JLC's [layout service](https://design.jlcpcb.com/) requires a supplied schematic;
its [layout FAQ](https://jlcpcb.com/help/article/pcb-layout-faqs) (**I**) explicitly
excludes schematic design/modification and lists a **$100 starting layout fee**,
subject to review. That is not a full controller-design quote. PCBWay's
[design service](https://www.pcbway.com/pcbdesign.html) (**D**) advertises circuit
and ESP32 firmware development, but price/timing for this feeder are unverified;
its delivery options differ in whether editable source files are included.

**Next decision:** retain the purchased TEC power stage and define one small,
factory-populated controller with approved screw terminals. Then compare the
same manufacturing files at JLC (two/five assembled) and PCBWay (one/five,
subject to minimum confirmation). This research supports that sourcing route;
it does not establish refrigeration performance or release a board for ordering.
