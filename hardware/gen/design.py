"""dmxnow node: single source of truth for parts and nets (SPEC.md §8.2).

Both the schematic generator (sch.py) and the PCB generator (pcb.py) read this
file, and check.py verifies that the schematic netlist exported by KiCad matches it.

Net classes:
  MAINS      230 V copper. 🔴 Human review mandatory.
  MAINS_PWR  230 V load path (16 A copper, arbitrage A2). 🔴 Human review mandatory.
  LED_PWR    12/24 V strip path, 17 A.
  LV         everything else (default).
"""
from dataclasses import dataclass, field

# ---------------------------------------------------------------------------
# Parts
# ---------------------------------------------------------------------------


@dataclass
class Part:
    ref: str
    symbol: str          # KiCad lib_id of the schematic symbol
    footprint: str       # KiCad lib_id of the footprint
    value: str
    pins: dict           # pin number -> net name (None = no connect)
    mpn: str = ""
    lcsc: str = ""       # LCSC part number, "" = to source (V-HW-13)
    dnp: bool = False    # Do not populate by default
    variant: str = ""    # "" = always, "led" = only in the LED BOM variant (A7)
    section: str = "main"  # "main" or "strip" (breakaway part)
    note: str = ""
    extra: dict = field(default_factory=dict)


FP_R = "Resistor_SMD:R_0603_1608Metric"
FP_C = "Capacitor_SMD:C_0603_1608Metric"


def R(ref, value, a, b, lcsc="", section="main", **kw):
    return Part(ref, "Device:R", FP_R, value, {"1": a, "2": b}, lcsc=lcsc, section=section, **kw)


def C(ref, value, a, b, lcsc="", fp=FP_C, section="main", **kw):
    return Part(ref, "Device:C", fp, value, {"1": a, "2": b}, lcsc=lcsc, section=section, **kw)


ESP_GND_PINS = ["1", "2", "11", "14"] + [str(n) for n in range(36, 54)]
ESP_NC_PINS = ["4", "7", "9", "10", "15", "17", "24", "25", "28", "29", "32", "33", "34", "35"]

esp_pins = {p: "GND" for p in ESP_GND_PINS}
esp_pins.update({p: None for p in ESP_NC_PINS})
esp_pins.update({
    "3": "+3V3",
    "8": "EN",
    "12": "STATUS_LED",   # GPIO0, option A7
    "13": "BOARD_SENSE",  # GPIO1
    "5": "IO2_PU",        # GPIO2 strapping
    "6": "PWM4",          # GPIO3
    "18": "DMX_TX",       # GPIO4
    "19": "RELAY_CTRL",   # GPIO5
    "20": "PWM1",         # GPIO6
    "21": "PWM2",         # GPIO7
    "22": "IO8_PU",       # GPIO8 strapping
    "23": "BOOT",         # GPIO9 strapping / SW1
    "16": "PWM3",         # GPIO10
    "26": "USB_DM",       # GPIO18
    "27": "USB_DP",       # GPIO19
    "30": None,           # GPIO20 U0RXD, unused
    "31": None,           # GPIO21 U0TXD, unused
})

PARTS = [
    # --- 230 V section 🔴 --------------------------------------------------
    Part("J1", "Connector:Screw_Terminal_01x02", "dmxnow:TerminalBlock_WAGO_2604-1102_1x02_P5.00mm_Horizontal",
         "WAGO 2604-1102 (L N in)", {"1": "L_IN", "2": "N"}, mpn="2604-1102",
         note="PE is joined off-board by a WAGO 221-413 (arbitrage A9)"),
    Part("J4", "Connector:Screw_Terminal_01x02", "dmxnow:TerminalBlock_WAGO_2604-1102_1x02_P5.00mm_Horizontal",
         "WAGO 2604-1102 (L_SW N out 1)", {"1": "L_SW", "2": "N"}, mpn="2604-1102",
         note="PE is joined off-board by a WAGO 221-413 (arbitrage A9)"),
    Part("J7", "Connector:Screw_Terminal_01x02", "dmxnow:TerminalBlock_WAGO_2604-1102_1x02_P5.00mm_Horizontal",
         "WAGO 2604-1102 (L_SW N out 2, J4b)", {"1": "L_SW", "2": "N"}, mpn="2604-1102",
         note="PE is joined off-board by a WAGO 221-413 (arbitrage A9)"),
    Part("F1", "Device:Fuse", "Fuse:Fuse_Littelfuse_372_D8.50mm", "TR5 T500mA 250V",
         {"1": "L_IN", "2": "L_PSU"}, mpn="Littelfuse 37405000410"),
    Part("RV1", "Device:Varistor", "Varistor:RV_Disc_D12mm_W4.2mm_P7.5mm", "10D561K",
         {"1": "L_PSU", "2": "N"}),
    Part("PS1", "Converter_ACDC:IRM-03-5", "Converter_ACDC:Converter_ACDC_MeanWell_IRM-03-xx_THT",
         "IRM-03-5", {"1": "L_PSU", "3": "N", "5": None, "14": "GND", "16": "+5V"}, mpn="MEAN WELL IRM-03-5"),
    Part("K1", "Relay:Relay_SPST-NO", "dmxnow:Relay_SPST_Omron_G5RL-U1A-E",
         "G5RL-U1A-E DC5", {"13": "L_IN", "14": "L_SW", "A1": "+5V", "A2": "RELAY_DRV"},
         mpn="Omron G5RL-U1A-E DC5"),
    # --- Power, MCU --------------------------------------------------------
    Part("U3", "Regulator_Linear:AP2112K-3.3", "Package_TO_SOT_SMD:SOT-23-5", "AP2112K-3.3",
         {"1": "+5V", "2": "GND", "3": "+5V", "4": None, "5": "+3V3"}, lcsc="C51118", mpn="AP2112K-3.3TRG1"),
    C("C5", "1uF 16V", "+5V", "GND", lcsc="C15849"),
    C("C6", "1uF 16V", "+3V3", "GND", lcsc="C15849"),
    C("C1", "47uF 10V", "+3V3", "GND", fp="Capacitor_SMD:C_1206_3216Metric"),
    C("C2", "100nF", "+3V3", "GND", lcsc="C14663"),
    Part("U1", "Espressif:ESP32-C3-MINI-1", "Espressif:ESP32-C3-MINI-1", "ESP32-C3-MINI-1-N4",
         esp_pins, mpn="ESP32-C3-MINI-1-N4"),
    R("R1", "10k", "+3V3", "EN", lcsc="C25804"),
    C("C4", "1uF 16V", "EN", "GND", lcsc="C15849"),
    R("R2", "10k", "+3V3", "BOOT", lcsc="C25804"),
    R("R3", "10k", "+3V3", "IO8_PU", lcsc="C25804"),
    R("R4", "10k", "+3V3", "IO2_PU", lcsc="C25804"),
    Part("SW1", "Switch:SW_Push", "Button_Switch_SMD:SW_SPST_PTS810", "PTS810 (BOOT/maintenance)",
         {"1": "BOOT", "2": "GND"}, mpn="C&K PTS810 SJM 250 SMTR LFS"),
    Part("J3", "Connector_Generic:Conn_01x06", "Connector_PinHeader_2.54mm:PinHeader_1x06_P2.54mm_Vertical",
         "PROG (3V3 GND D- D+ EN BOOT)",
         {"1": "+3V3", "2": "GND", "3": "USB_DM", "4": "USB_DP", "5": "EN", "6": "BOOT"},
         dnp=True, note="Pads only, header not fitted"),
    # --- Status LED option (A7) -------------------------------------------
    R("R19", "1k", "STATUS_LED", "LED_A", lcsc="C21190", dnp=True, variant="led"),
    Part("D4", "Device:LED", "LED_SMD:LED_0603_1608Metric", "LED green 0603",
         {"1": "GND", "2": "LED_A"}, dnp=True, variant="led"),
    # --- Relay driver ------------------------------------------------------
    R("R5", "100R", "RELAY_CTRL", "RELAY_GATE", lcsc="C22775"),
    R("R6", "100k", "RELAY_GATE", "GND", lcsc="C25803"),
    Part("Q1", "Transistor_FET:AO3400A", "Package_TO_SOT_SMD:SOT-23", "AO3400A",
         {"1": "RELAY_GATE", "2": "GND", "3": "RELAY_DRV"}, lcsc="C20917"),
    Part("D2", "Device:D", "Diode_SMD:D_SOD-123", "1N4148W",
         {"1": "+5V", "2": "RELAY_DRV"}, lcsc="C81598"),
    # --- DMX ---------------------------------------------------------------
    Part("U2", "Interface_UART:SP3485EN", "Package_SO:SOIC-8_3.9x4.9mm_P1.27mm", "SP3485EN",
         {"1": None, "2": "+3V3", "3": "+3V3", "4": "DMX_TX", "5": "GND", "6": "DMX_A",
          "7": "DMX_B", "8": "+3V3"}, lcsc="C8963", mpn="SP3485EEN-L/TR"),
    C("C3", "100nF", "+3V3", "GND", lcsc="C14663"),
    Part("D1", "Diode:SM712_SOT23", "Package_TO_SOT_SMD:SOT-23", "SM712",
         {"1": "DMX_A", "2": "DMX_B", "3": "GND"}, mpn="SM712.TCT"),
    Part("J2", "Connector_Generic:Conn_01x03", "Connector_Wire:SolderWire-0.25sqmm_1x03_P4.2mm_D0.65mm_OD1.7mm",
         "DMX tail (1 GND 2 B 3 A)", {"1": "GND", "2": "DMX_B", "3": "DMX_A"}, dnp=True,
         note="Wire pads"),
    # --- Breakaway strip section ------------------------------------------
    Part("J5", "Connector:Screw_Terminal_01x02", "dmxnow:TerminalBlock_WAGO_2604-1102_1x02_P5.00mm_Horizontal",
         "WAGO 2604-1102 (VLED_IN GND_LED)", {"1": "VLED_IN", "2": "GND_LED"}, mpn="2604-1102", section="strip"),
    Part("F2", "Device:Fuse", "Fuse:FuseHolder_Blade_ATO_Littelfuse_FLR_178.6165", "ATO holder + 20A fuse",
         {"1": "VLED_IN", "2": "VLED"}, mpn="Littelfuse 178.6165.0002", section="strip"),
    Part("D3", "Device:D_Zener", "Diode_SMD:D_SMB", "SMBJ28A",
         {"1": "VLED", "2": "GND_LED"}, mpn="SMBJ28A", section="strip"),
    Part("C7", "Device:C_Polarized", "Capacitor_THT:CP_Radial_D10.0mm_P5.00mm", "470uF 35V low ESR",
         {"1": "VLED", "2": "GND_LED"}, section="strip"),
    C("C8", "1uF 50V", "VLED", "GND_LED", fp="Capacitor_SMD:C_1206_3216Metric", section="strip"),
    Part("U4", "74xx:74LVC125", "Package_SO:SOIC-14_3.9x8.7mm_P1.27mm", "74AHCT125",
         {"1": "GND", "2": "PWM1", "3": "DRV1", "4": "GND", "5": "PWM2", "6": "DRV2", "7": "GND",
          "8": "DRV3", "9": "PWM3", "10": "GND", "11": "DRV4", "12": "PWM4", "13": "GND", "14": "+5V"},
         mpn="SN74AHCT125DR", section="strip"),
    C("C9", "100nF", "+5V", "GND", lcsc="C14663", section="strip"),
    Part("J6", "Connector:Screw_Terminal_01x05", "dmxnow:TerminalBlock_WAGO_2604-1105_1x05_P5.00mm_Horizontal",
         "WAGO 2604-1105 (VLED CH1-CH4)",
         {"1": "VLED", "2": "CH1", "3": "CH2", "4": "CH3", "5": "CH4"}, mpn="2604-1105", section="strip"),
    # 0 ohm links: single deliberate connection points on the strip part (SPEC 4.8.4, 4.2)
    Part("R20", "Device:R", "Resistor_SMD:R_0805_2012Metric", "0R", {"1": "GND", "2": "GND_LED"},
         lcsc="C17477", section="strip", note="Logic ground to LED ground star point"),
    Part("R21", "Device:R", FP_R, "0R", {"1": "BOARD_SENSE", "2": "GND"},
         lcsc="C21189", section="strip", note="Variant detection (GPIO1 low = strip part present)"),
]

for i in range(4):
    n = i + 1
    PARTS += [
        R("R%d" % (15 + i), "100k", "PWM%d" % n, "GND", lcsc="C25803", section="main",
          note="PWM pull-down, main side of the V-cut (layout), SPEC 4.6"),
        R("R%d" % (7 + i), "100R", "DRV%d" % n, "GATE%d" % n, lcsc="C22775", section="strip"),
        R("R%d" % (11 + i), "100k", "GATE%d" % n, "GND_LED", lcsc="C25803", section="strip"),
        Part("Q%d" % (2 + i), "Device:Q_NMOS_GDS", "Package_TO_SOT_SMD:TO-252-2", "AOD4184A",
             {"1": "GATE%d" % n, "2": "CH%d" % n, "3": "GND_LED"}, mpn="AOD4184A", section="strip"),
    ]

# Mounting holes (NPTH, nylon screws or printed pegs; see SPEC 4.12).
# None in the 230 V zone: a metal screw there would defeat the 6 mm isolation.
for i, sec in ((1, "main"), (2, "main"), (3, "strip")):
    PARTS.append(Part("H%d" % i, "Mechanical:MountingHole", "MountingHole:MountingHole_3.2mm_M3",
                      "M3 NPTH", {}, section=sec))

# ---------------------------------------------------------------------------
# Net classes (widths in mm; clearances enforced by custom DRC rules)
# ---------------------------------------------------------------------------

NETCLASSES = {
    "MAINS_PWR": {"nets": ["L_IN", "L_SW", "N"], "track": 5.0, "clearance": 3.0},
    "MAINS": {"nets": ["L_PSU"], "track": 1.0, "clearance": 3.0},
    "LED_PWR": {"nets": ["VLED_IN", "VLED", "GND_LED", "CH1", "CH2", "CH3", "CH4"],
                "track": 5.0, "clearance": 0.2},
    "PWR": {"nets": ["+5V", "+3V3", "GND", "RELAY_DRV"], "track": 0.6, "clearance": 0.2},
}
MAINS_NETS = NETCLASSES["MAINS_PWR"]["nets"] + NETCLASSES["MAINS"]["nets"]

# Nets allowed to cross the V-cut (SPEC 4.8.4)
CROSSING_NETS = {"PWM1", "PWM2", "PWM3", "PWM4", "BOARD_SENSE", "+5V", "GND"}


def nets():
    """net name -> sorted list of (ref, pin)."""
    res = {}
    for p in PARTS:
        for pin, net in p.pins.items():
            if net is not None:
                res.setdefault(net, []).append((p.ref, pin))
    return {k: sorted(v) for k, v in sorted(res.items())}


def part(ref):
    return next(p for p in PARTS if p.ref == ref)


if __name__ == "__main__":
    for n, conns in nets().items():
        print("%-12s %s" % (n, " ".join("%s.%s" % c for c in conns)))
