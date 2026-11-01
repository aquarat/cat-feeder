#!/usr/bin/env python3
"""Reusable PD front-end connectivity; no layout and no supplier operations.

Run to regenerate circuit.json. Numbers in pins are FOOTPRINT pad numbers;
None means deliberately unconnected. See ../../../kb/pcb-pd-integration.md.
"""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent


def circuit():
    parts = []

    def part(ref, value, mpn, lcsc, footprint, pins, **extra):
        parts.append(dict(ref=ref, value=value, mpn=mpn, lcsc=lcsc,
                          footprint=footprint,
                          pins={str(k): v for k, v in pins.items()}, **extra))

    def r(ref, value, mpn, lcsc, a, b, watts=0.1, size="0603_1608"):
        part(ref, value, mpn, lcsc, f"Resistor_SMD:R_{size}Metric",
             {1: a, 2: b}, power_W=watts, voltage_V=200 if watts == 1 else 75)

    def c(ref, value, a, b="GND", ten_u=False):
        part(ref, value, "CL21A106KAYNNNE" if ten_u else
             ("CL10A105KB8NNNC" if value.startswith("1u") else "CC0603KRX7R9BB104"),
             "C15850" if ten_u else ("C15849" if value.startswith("1u") else "C14663"),
             "Capacitor_SMD:C_0805_2012Metric" if ten_u else
             "Capacitor_SMD:C_0603_1608Metric", {1: a, 2: b},
             voltage_V=25 if ten_u else 50)

    part("J201", "USB-C PD input 5A", "USB4105-GF-A-060", "C3025063",
         "Connector_USB:USB_C_Receptacle_GCT_USB4105-xx-A_16P_TopMnt_Horizontal",
         {"A1": "GND", "A12": "GND", "B1": "GND", "B12": "GND",
          "A4": "PD_VBUS_RAW", "A9": "PD_VBUS_RAW", "B4": "PD_VBUS_RAW", "B9": "PD_VBUS_RAW",
          "A5": "PD_CC1", "B5": "PD_CC2", "A6": None, "A7": None,
          "B6": None, "B7": None, "A8": None, "B8": None, "S1": "GND"},
         current_A=5, note="All four shell pads share S1. Paired power pads overlap intentionally in KiCad library.")
    part("U201", "STUSB4500QTR", "STUSB4500QTR", "C2678061",
         "Package_DFN_QFN:QFN-24-1EP_4x4mm_P0.5mm_EP2.7x2.7mm",
         {1: "PD_CC1", 2: "PD_CC1", 3: None, 4: "PD_CC2", 5: "PD_CC2",
          6: "PD_RESET", 7: "PD_SCL", 8: "PD_SDA", 9: "PD_DISCH_OUT", 10: "GND",
          11: None, 12: "GND", 13: "GND", 14: None, 15: None,
          16: "PD_EN_SNK_N", 17: None, 18: "PD_VBUS_SENSE", 19: None,
          20: "PD_PDO2_N", 21: "PD_VREG_1V2", 22: "GND", 23: "PD_VREG_2V7",
          24: "PD_VBUS_RAW", 25: "GND"},
         symbol="Interface_USB:STUSB4500QTR", i2c_address="0x28",
         pin_names={str(k): v for k, v in enumerate([
             "CC1DB", "CC1", "NC", "CC2", "CC2DB", "RESET", "SCL", "SDA", "DISCH", "GND",
             "ATTACH", "ADDR0", "ADDR1", "POWER_OK3", "GPIO", "VBUS_EN_SNK", "A_B_SIDE",
             "VBUS_VS_DISCH", "ALERT", "POWER_OK2", "VREG_1V2", "VSYS", "VREG_2V7", "VDD", "EP"], 1)})

    # ST DS12499 Fig.10 common-source back-to-back path, using SparkFun's lower-R FET.
    for ref, drain in [("Q201", "PD_VBUS_RAW"), ("Q202", "PD_20V")]:
        part(ref, "STL9P3LLH6", "STL9P3LLH6", "C2969828",
             "PD:ST_PowerFLAT_3.3x3.3_SparkFun",
             {1: "PD_FET_SOURCE", 2: "PD_FET_SOURCE", 3: "PD_FET_SOURCE", 4: "PD_GATE", 5: drain},
             physical_pin_aliases={"6": "5", "7": "5", "8": "5"},
             pin_names={"1": "S", "2": "S", "3": "S", "4": "G", "5": "D (aggregate 5-8)"},
             note="Custom footprint retains SparkFun/ST continuous drain land, numbered 5 on all three rectangles.")
    r("R201", "100k", "0603WAF1003T5E", "C25803", "PD_FET_SOURCE", "PD_GATE")
    r("R202", "22k", "0603WAF2202T5E", "C31850", "PD_GATE", "PD_EN_SNK_N")
    r("R203", "100", "0603WAF1000T5E", "C22775", "PD_GATE", "PD_GATE_RC")
    c("C204", "100n 50V", "PD_GATE_RC", "PD_20V")
    for ref, a, b in [("R204", "PD_VBUS_RAW", "PD_VBUS_SENSE"),
                      ("R205", "PD_20V", "PD_DISCH_OUT")]:
        r(ref, "1k 1W", "25121WF1001T4E", "C54315", a, b, watts=1, size="2512_6332")
    r("R206", "100k", "0603WAF1003T5E", "C25803", "PD_RESET", "GND")
    c("C201", "1u 50V", "PD_VBUS_RAW")
    c("C202", "1u 50V", "PD_VREG_1V2")
    c("C203", "1u 50V", "PD_VREG_2V7")
    c("C209", "100n 50V", "PD_20V")
    part("D201", "ESDA25W CC protection", "ESDA25W", "C2935152",
         "Package_TO_SOT_SMD:SOT-323_SC-70", {1: "PD_CC1", 2: "PD_CC2", 3: "GND"},
         pin_names={"1": "K1", "2": "K2", "3": "A_COMMON"})
    for ref, net in [("D202", "PD_VBUS_RAW"), ("D203", "PD_20V")]:
        part(ref, "ESDA25P35-1U1M", "ESDA25P35-1U1M", "C1974707",
             "Diode_SMD:ST_QFN-2L_1.6x1.0mm", {1: net, 2: "GND"},
             pin_names={"1": "K", "2": "A"}, standoff_V=22,
             note="ST reference ESD TVS, NOT a clamp guaranteed below 28V for arbitrary surge current.")

    # Dedicated PD-side bias supply avoids using either ST internal VREG to power anything.
    part("U202", "TPS70933DBVR", "TPS70933DBVR", "C89347",
         "Package_TO_SOT_SMD:SOT-23-5", {1: "PD_VBUS_RAW", 2: "GND", 3: None, 4: None, 5: "PD_3V3"},
         pin_names={"1": "IN", "2": "GND", "3": "EN", "4": "NC", "5": "OUT"},
         note="EN deliberately FLOATING per TI internal pull-up. NEVER tie EN to 20V input; EN max 6.5V operating.")
    c("C205", "1u 50V", "PD_VBUS_RAW")
    c("C206", "10u 25V", "PD_3V3", ten_u=True)
    part("U203", "TCA9517ADGKR", "TCA9517ADGKR", "C201698",
         "Package_SO:VSSOP-8_3x3mm_P0.65mm",
         {1: "PD_3V3", 2: "PD_SCL", 3: "PD_SDA", 4: "GND", 5: "+3V3",
          6: "HOST_SDA", 7: "HOST_SCL", 8: "+3V3"},
         symbol="Logic_LevelTranslator:TCA9517ADGK",
         pin_names={"1": "VCCA", "2": "SCLA", "3": "SDAA", "4": "GND", "5": "EN", "6": "SDAB", "7": "SCLB", "8": "VCCB"},
         note="ST MUST be on A side: A VOL max 0.2V meets ST VIL max 0.35V; B VOL max 0.6V does not.")
    for ref, rail, signal in [("R207", "PD_3V3", "PD_SCL"), ("R208", "PD_3V3", "PD_SDA"),
                              ("R209", "+3V3", "HOST_SCL"), ("R210", "+3V3", "HOST_SDA")]:
        r(ref, "4k7", "0603WAF4701T5E", "C23162", rail, signal)
    c("C207", "100n 50V", "PD_3V3")
    c("C208", "100n 50V", "+3V3")
    for ref, net in [("TP201", "PD_VBUS_RAW"), ("TP202", "PD_20V"), ("TP203", "PD_GATE"),
                     ("TP204", "PD_FET_SOURCE"), ("TP205", "PD_RESET"), ("TP206", "PD_PDO2_N"),
                     ("TP207", "PD_SCL"), ("TP208", "PD_SDA"), ("TP209", "GND"),
                     ("TP210", "+3V3")]:
        part(ref, net, None, None, "TestPoint:TestPoint_Pad_D1.5mm", {1: net},
             assembly="bare PCB pad, no purchased component")

    return dict(schema_version=1, status="connectivity proposal, NOT fabrication release",
                components=parts,
                ports={
                    "PD_20V": "20V nominal output, <=5A TOTAL including all loads; off on fallback after correct NVM programming",
                    "PD_VBUS_RAW": "USB input 5V fallback/20V negotiated; INTERNAL low-power loads only; test-power input with cable absent",
                    "+3V3": "host 3.3V supply, 3.0..3.6V; powers TCA B side, not the STUSB4500",
                    "HOST_SCL": "host open-drain SCL; 100kHz initial; host must tolerate TCA B VOL max 0.6V",
                    "HOST_SDA": "host open-drain SDA; 0x28; B-side offset buffer cascade restrictions apply",
                    "GND": "common ground; bus power-off isolation is NOT galvanic isolation"},
                nvm={"SNK_PDO_NUMB": 2, "PDO1_V": 5, "PDO1_A": 0.5,
                     "PDO2_V": 20, "PDO2_A": 5, "PDO3_V": 20, "PDO3_A": 5,
                     "PDO3_enabled": False, "POWER_ONLY_ABOVE_5V": 1,
                     "PWR_OK_CFG": 2, "GPIO_CFG": 1, "REQ_SRC_CURRENT": 0,
                     "USB_COMM_CAPABLE": 0, "SNK_UNCONS_POWER": 0,
                     "PDO2_undervoltage_percent": 10, "PDO2_overvoltage_percent": 5,
                     "VBUS_DISCH_DISABLE": 0, "VBUS_DISCH_TIME_TO_0V": 9,
                     "VBUS_DISCH_TIME_TO_PDO": 12},
                integration_limits={
                    "downstream_capacitance_effective_max_uF": 150,
                    "raw_input_nominal_capacitance_uF": 2,
                    "host_and_pd_pullups_ohm": 4700,
                    "bus_capacitance_each_side_at_100kHz_max_pF": 200,
                    "factory_nvm_programming_required": True,
                    "current_limiting_in_this_block": False,
                    "reverse_current_blocking": "back-to-back FETs block when OFF, not an ideal-diode controller while ON"})


if __name__ == "__main__":
    data = circuit()
    stock = {x["componentCode"]: x for x in json.loads((HERE / "stock-evidence.json").read_text())}
    for p in data["components"]:
        if p["lcsc"]:
            evidence = stock[p["lcsc"]]
            assert evidence["componentModelEn"] == p["mpn"], (p["ref"], evidence["componentModelEn"], p["mpn"])
    (HERE / "circuit.json").write_text(json.dumps(data, indent=2) + "\n")
    print(f"Wrote {len(data['components'])} components; all fitted MPN/code identities match public evidence")
