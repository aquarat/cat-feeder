# Controller revision B — integrated power and motion

**In development.** The owner requested integrating USB-C PD, the stepper
driver and the logic/fan regulators onto the main PCB. This revision is a new
design, not the independently reviewed revision A saved in the supplier project.

## Intended electrical architecture

```text
USB-C, 20 V / 5 A capable source and e-marked cable
  └─ STUSB4500 negotiation, protection and controlled power path
       ├─ efficient 3.3 V supply → ESP32, sensors and interface logic
       ├─ efficient 12 V supply → four-wire fan
       ├─ onboard current-regulating A4988 → bipolar stepper
       └─ DC power output → external DPS5005 → TEC array
```

The PD breakout, plug-in motor carrier and separate logic/fan buck modules are
replaced by assembler-fitted components. The DPS5005 remains a separate TEC
regulator. A 100 W input contract is a total-source budget, not 100 W available
to the TECs after auxiliaries and conversion losses.

Functional circuit selection, component stock/footprint checks and JLCPCB
design-rule research are being developed in `pd/`, `motor/`, `power/` and `dfm/`.
The generator emits an editable KiCad schematic and explicitly **unrouted**
placement; those alone are not manufacturing deliverables. Routing, DRC,
electrical review, populated enclosure clearance and supplier-process checks
must refer to this revision's actual artifacts.

## Version identification

`version.py` computes a full SHA-256 digest of the explicitly listed circuit,
footprint and layout sources. The PCB silkscreen and schematic title carry:

- `Rev B / <12-character Git hash>` for committed, unchanged design sources;
- the same with `-dirty` when those sources differ or are untracked;
- `Rev B / src-<12-character source hash>` before the first Git commit.

`version.json` records the full commit, source digest and individual source
hashes. Generated PCB/Gerber/BOM files are hashed separately after export;
feeding them into their own printed identifier would create a circular hash.
The Git identifier is the latest commit touching the listed design sources;
committing only generated artifacts therefore does not force another identifier.
The current repository has no commits, so its initial identifier uses the
source hash. No commit or supplier upload is implicit in generating a version.

Revision A's frozen files and simulation results remain under `../pcb/` and
`../sim/`. Their numerical checks do not qualify the changed revision B circuit.
