#!/usr/bin/env python3
"""Generates the SVG figures of docs/fonctionnement.md (no dependency).

Values come from the project sources, not from hand drawing:
  - carte.svg          enclosure/board.json (hardware/gen/export_board.py)
  - trame-dmx.svg      SPEC 4.4 / 5.1 (break 176 us, MAB 12 us, 44 us per slot)
  - latence.svg        SPEC 5.1 budget table (typical column)
  - pwm-dephasage.svg  SPEC 4.6-4.7 (4882 Hz, quarter-period hpoint shift)
  - gamma.svg          SPEC 4.7 (gamma_x10, 8-bit table)
  - relais.svg         SPEC 4.5 point 3 (deferred debounce), simulated

    python3 docs/figures/make_figures.py      # rewrites docs/figures/*.svg
"""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", ".."))

INK = "#1f2328"
MUTED = "#59636e"
GRID = "#d1d9e0"
MAINS = "#f4a261"       # 230 V (orange, like the cover)
LV = "#8ecae6"          # low voltage (blue, like the lid)
STRIP = "#a7d49b"       # strip section
ACCENT = "#d62828"
BLUE = "#1d70b8"
FONT = "font-family='Helvetica, Arial, sans-serif'"


class Svg:
    def __init__(self, w, h, title):
        self.w, self.h = w, h
        self.items = [f"<title>{title}</title>",
                      f"<rect width='{w}' height='{h}' fill='#ffffff'/>"]

    def add(self, s):
        self.items.append(s)

    def rect(self, x, y, w, h, fill="none", stroke=INK, sw=1, extra=""):
        self.add(f"<rect x='{x:.1f}' y='{y:.1f}' width='{w:.1f}' height='{h:.1f}' fill='{fill}' "
                 f"stroke='{stroke}' stroke-width='{sw}' {extra}/>")

    def line(self, x1, y1, x2, y2, stroke=INK, sw=1, extra=""):
        self.add(f"<line x1='{x1:.1f}' y1='{y1:.1f}' x2='{x2:.1f}' y2='{y2:.1f}' stroke='{stroke}' "
                 f"stroke-width='{sw}' {extra}/>")

    def path(self, pts, stroke=INK, sw=1.5, fill="none", extra=""):
        d = "M" + " L".join(f"{x:.1f},{y:.1f}" for x, y in pts)
        self.add(f"<path d='{d}' stroke='{stroke}' stroke-width='{sw}' fill='{fill}' {extra}/>")

    def text(self, x, y, s, size=12, fill=INK, anchor="start", weight="normal", extra=""):
        s = s.replace("&", "&amp;").replace("<", "&lt;")
        self.add(f"<text x='{x:.1f}' y='{y:.1f}' font-size='{size}' fill='{fill}' text-anchor='{anchor}' "
                 f"font-weight='{weight}' {FONT} {extra}>{s}</text>")

    def save(self, name):
        body = "\n".join(self.items)
        out = (f"<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 {self.w} {self.h}' "
               f"width='{self.w}' height='{self.h}'>\n{body}\n</svg>\n")
        with open(os.path.join(HERE, name), "w", encoding="utf-8") as f:
            f.write(out)
        print("wrote", name)


# --------------------------------------------------------------------------------------
def board_map():
    b = json.load(open(os.path.join(ROOT, "enclosure", "board.json")))
    k = 6.0                       # px per mm
    ox, oy = 40, 150              # origin of PCB (0, 0)
    X = lambda x: ox + x * k      # noqa: E731
    Y = lambda y: oy + y * k      # noqa: E731
    s = Svg(1000, 610, "Carte du nœud dmxnow : zones et composants")
    s.text(500, 28, "Carte du nœud : trois zones", 20, anchor="middle", weight="bold")
    s.text(500, 50, "vue de dessus, cotes en mm, générée depuis enclosure/board.json", 12, MUTED, "middle")

    # zones, clipped to the board outline
    s.add("<defs><clipPath id='pcb'>" + "".join(
        f"<rect x='{X(x1):.1f}' y='{Y(y1):.1f}' width='{(x2 - x1) * k:.1f}' height='{(y2 - y1) * k:.1f}'/>"
        for x1, y1, x2, y2 in b["rects"]) + "</clipPath>"
        "<pattern id='hatch' width='8' height='8' patternUnits='userSpaceOnUse' patternTransform='rotate(45)'>"
        "<line x1='0' y1='0' x2='0' y2='8' stroke='#9a6fb0' stroke-width='2'/></pattern></defs>")
    iso = b["iso_slot_x"]
    split = b["split_x"]
    s.add("<g clip-path='url(#pcb)'>")
    s.rect(X(-1), Y(-12), (iso + 1) * k, 80 * k, MAINS, "none", extra="fill-opacity='0.55'")
    s.rect(X(iso), Y(-12), (split - iso) * k, 80 * k, LV, "none", extra="fill-opacity='0.55'")
    s.rect(X(split), Y(-12), 60 * k, 80 * k, STRIP, "none", extra="fill-opacity='0.55'")
    ax1, ay1, ax2, ay2 = b["antenna"]
    s.rect(X(ax1), Y(ay1), (ax2 - ax1) * k, (ay2 - ay1) * k, "url(#hatch)", "none")
    s.add("</g>")
    for x1, y1, x2, y2 in b["rects"]:
        s.rect(X(x1), Y(y1), (x2 - x1) * k, (y2 - y1) * k, "none", INK, 2)

    # isolation slots and separation line
    for y1, y2 in b["iso_slots"]:
        s.rect(X(iso - b["iso_slot_w"] / 2), Y(y1), b["iso_slot_w"] * k, (y2 - y1) * k, INK, "none")
    ys = [0.0]
    for t1, t2 in b["tabs"]:
        ys += [t1, t2]
    ys.append(54.0)
    for i in range(0, len(ys), 2):
        s.rect(X(split - b["slot_w"] / 2), Y(ys[i]), b["slot_w"] * k, (ys[i + 1] - ys[i]) * k, "#ffffff", INK, 1)
    for t1, t2 in b["tabs"]:
        for yy in range(int(t1 + 1), int(t2), 2):
            s.add(f"<circle cx='{X(split):.1f}' cy='{Y(yy):.1f}' r='2.4' fill='#ffffff' stroke='{INK}'/>")

    labels = {
        "J1": "J1 IN", "J4": "J4 OUT 1", "J7": "J7 OUT 2", "F1": "F1 T500 mA", "RV1": "RV1",
        "K1": "K1 relais 16 A", "PS1": "PS1 230 V→5 V isolé", "U1": "U1 ESP32-C3", "U2": "U2 DMX",
        "J2": "J2 DMX", "J3": "J3 prog.", "SW1": "SW1", "D4": "D4", "U3": "U3",
        "J5": "J5 + −", "J6": "J6 V+ 1", "J8": "J8 2 3 4", "F2": "F2 20 A", "C7": "C7",
        "U4": "U4", "Q2": "Q2", "Q3": "Q3", "Q4": "Q4", "Q5": "Q5", "D3": "D3",
    }
    parts = {p["ref"]: p for p in b["parts"]}
    for ref in ["J1", "J4", "J7", "F1", "RV1", "K1", "PS1", "U1", "U2", "J2", "J3", "SW1", "D4", "U3",
                "J5", "J6", "J8", "F2", "C7", "U4", "Q2", "Q3", "Q4", "Q5", "D3"]:
        x1, y1, x2, y2 = parts[ref]["box"]
        big = ref in ("J1", "J4", "J7", "J5", "J6", "J8", "K1", "PS1", "F1", "F2", "U1", "RV1", "C7")
        s.rect(X(x1), Y(y1), (x2 - x1) * k, (y2 - y1) * k, "#ffffff" if big else "#f6f8fa", INK,
               1.2, "fill-opacity='0.85' rx='2'")
        size = 11 if big else 9
        s.text(X((x1 + x2) / 2), Y((y1 + y2) / 2) + size / 3, labels[ref], size, anchor="middle",
               weight="bold" if big else "normal")
    for h in b["holes"]:
        s.add(f"<circle cx='{X(h['x']):.1f}' cy='{Y(h['y']):.1f}' r='{h['d'] / 2 * k:.1f}' "
              f"fill='#ffffff' stroke='{INK}' stroke-width='1.5'/>")

    # legend and callouts
    ly = Y(54) + 40
    for i, (c, t) in enumerate([(MAINS, "230 V — sous le couvercle orange, vissé"),
                                (LV, "Basse tension 3,3 / 5 V — isolée par PS1"),
                                (STRIP, "Rubans 12/24 V TBTS — partie sécable")]):
        s.rect(40 + i * 320, ly, 18, 14, c, INK, 1, "fill-opacity='0.8'")
        s.text(64 + i * 320, ly + 12, t, 12)
    s.rect(40, ly + 26, 18, 14, "url(#hatch)", INK)
    s.text(64, ly + 38, "Zone d'antenne : rien de métallique à moins de 15 mm", 12)
    s.rect(360, ly + 26, 6, 14, INK, "none")
    s.text(374, ly + 38, "Fentes d'isolement sous K1 et PS1 (≥ 6 mm 230 V ↔ TBT)", 12)
    s.text(X(split), Y(-2), "ligne de découpe", 11, MUTED, "middle")
    s.text(X(split), Y(-2) - 13, "(languettes)", 11, MUTED, "middle")
    s.text(X(iso), Y(54) + 18, "barrière d'isolement", 11, ACCENT, "middle", "bold")
    s.line(X(iso), Y(-11.5), X(iso), Y(54) + 5, ACCENT, 1.5, "stroke-dasharray='5 4'")
    s.save("carte.svg")


# --------------------------------------------------------------------------------------
def dmx_frame():
    s = Svg(1000, 400, "Trame DMX émise par le nœud")
    s.text(500, 28, "Trame DMX émise par le nœud", 20, anchor="middle", weight="bold")
    # zoomed start of frame (not to scale on the slots)
    x0, yh, yl = 60, 90, 150
    us = 1.6    # px per microsecond for the zoom
    pts = [(x0, yh), (x0 + 40, yh), (x0 + 40, yl)]
    x = x0 + 40 + 176 * us
    pts += [(x, yl), (x, yh)]
    xb = x
    x += 12 * us
    xm = x
    pts += [(x, yh)]
    slots = []
    for i, bits in enumerate([[0] * 8, [1, 0, 1, 1, 0, 0, 1, 0], [0, 1, 1, 1, 1, 1, 1, 1]]):
        start = x
        seq = [0] + bits + [1, 1]         # start bit, 8 data LSB first, 2 stop bits
        for bit in seq:
            y = yl if bit == 0 else yh
            pts += [(x, pts[-1][1]), (x, y), (x + 4 * us, y)]
            x += 4 * us
        slots.append((start, x))
    pts += [(x + 30, yh)]
    s.path(pts, BLUE, 2)
    s.text(x + 40, yh + 5, "… jusqu'au canal dmx_out_slots", 13, MUTED)

    def brace(x1, x2, y, label, sub=""):
        s.line(x1, y, x2, y, INK, 1)
        s.line(x1, y - 5, x1, y + 5, INK, 1)
        s.line(x2, y - 5, x2, y + 5, INK, 1)
        s.text((x1 + x2) / 2, y + 18, label, 12, anchor="middle", weight="bold")
        if sub:
            s.text((x1 + x2) / 2, y + 33, sub, 11, MUTED, "middle")

    brace(x0 + 40, xb, yl + 20, "BREAK 176 µs", "(≥ 88 µs)")
    s.line(xb, yh - 10, xb, yh - 22, INK)
    s.line(xm, yh - 10, xm, yh - 22, INK)
    s.text((xb + xm) / 2, yh - 28, "MAB 12 µs", 12, anchor="middle", weight="bold")
    names = ["code de départ (0)", "canal 1", "canal 2"]
    for (a, e), n in zip(slots, names):
        brace(a, e, yl + 20, "44 µs", n)
    s.text(x0, yh + 5, "repos", 11, MUTED, "end")
    s.text(60, 250, "250 kbit/s, 8 bits + 2 bits de stop : 44 µs par canal. Durée d'une trame de N canaux : "
           "176 + 12 + (N + 1) × 44 µs.", 13)

    # to-scale comparison
    y = 290
    ms = 32.0   # px per ms
    for i, (n, label) in enumerate([(512, "512 canaux (défaut)"),
                                    (40, "40 canaux (dmx_out_slots = dernier canal du projecteur)")]):
        d = (176 + 12 + (n + 1) * 44) / 1000.0
        yy = y + i * 44
        s.rect(60, yy, d * ms, 24, BLUE if n == 40 else "#9fb3c8", "none", extra="rx='3'")
        s.text(60 + d * ms + 8, yy + 17, f"{d:.2f} ms — {label}".replace(".", ","), 13)
    for t in range(0, 26, 5):
        s.line(60 + t * ms, y + 84, 60 + t * ms, y + 90, MUTED)
        s.text(60 + t * ms, y + 104, f"{t} ms", 11, MUTED, "middle")
    s.line(60, y + 84, 60 + 25 * ms, y + 84, MUTED)
    s.save("trame-dmx.svg")


# --------------------------------------------------------------------------------------
def latency():
    steps = [("QLC+ → démon", 0.2), ("démon (Python)", 0.3), ("USB", 0.5), ("dongle", 0.1),
             ("radio 6 Mbit/s", 0.9), ("nœud", 0.1), ("fin de la trame DMX en cours", None),
             ("émission jusqu'au canal", 0.2)]
    colors = ["#264653", "#2a9d8f", "#8ab17d", "#e9c46a", "#f4a261", "#e76f51", "#9fb3c8", "#6d597a"]
    s = Svg(1000, 330, "Budget de latence Art-Net vers ligne DMX (typique)")
    s.text(500, 28, "Latence typique QLC+ → ligne DMX du projecteur", 20, anchor="middle", weight="bold")
    s.text(500, 50, "SPEC §5.1, valeurs typiques ; le pire cas est environ 2,5 fois plus long", 12, MUTED, "middle")
    ms = 50.0
    x0 = 190
    for i, (label, wait) in enumerate([("trame de 512 canaux", 11.0), ("trame de 40 canaux", 1.0)]):
        y = 90 + i * 70
        s.text(x0 - 10, y + 22, label, 13, anchor="end", weight="bold")
        x = x0
        for (name, v), c in zip(steps, colors):
            v = wait if v is None else v
            s.rect(x, y, v * ms, 34, c, "#ffffff", 0.8)
            x += v * ms
        total = x - x0
        s.text(x + 8, y + 22, f"≈ {total / ms:.1f} ms".replace(".", ","), 13, weight="bold")
    s.line(x0 + 10 * ms, 75, x0 + 10 * ms, 225, ACCENT, 1.5, "stroke-dasharray='6 4'")
    s.text(x0 + 10 * ms, 70, "objectif 10 ms (ENF-01)", 12, ACCENT, "middle", "bold")
    for t in range(0, 15, 2):
        s.line(x0 + t * ms, 228, x0 + t * ms, 234, MUTED)
        s.text(x0 + t * ms, 248, f"{t} ms", 11, MUTED, "middle")
    s.line(x0, 228, x0 + 14 * ms, 228, MUTED)
    lx, ly = 40, 275
    for i, ((name, _), c) in enumerate(zip(steps, colors)):
        col, row = i % 4, i // 4
        s.rect(lx + col * 240, ly + row * 22, 14, 14, c, "none")
        s.text(lx + col * 240 + 20, ly + row * 22 + 12, name, 12)
    s.save("latence.svg")


# --------------------------------------------------------------------------------------
def pwm_phase():
    period = 1e6 / 4882          # us
    duty = 0.40
    s = Svg(1000, 470, "Déphasage des quatre sorties PWM")
    s.text(500, 28, "Rubans : 4 PWM décalées d'un quart de période", 20, anchor="middle", weight="bold")
    s.text(500, 50, f"4882 Hz (période {period:.0f} µs), 14 bits ; exemple : les 4 canaux à 40 %", 12, MUTED, "middle")
    x0, px = 120, 2.0          # px per us
    span = 2 * period
    h = 26

    def wave(y, shift, color):
        pts = [(x0, y + h)]
        t = 0.0
        on = False
        # edges: on at shift + n*period, off at shift + duty*period + n*period
        edges = []
        for n in range(-1, 4):
            edges += [(shift + n * period, True), (shift + (n + duty) * period, False)]
        edges = sorted(e for e in edges if 0 <= e[0] <= span)
        # initial state
        start_phase = ((0 - shift) % period) / period
        on = start_phase < duty
        yv = y if on else y + h
        pts = [(x0, yv)]
        for t, st in edges:
            pts += [(x0 + t * px, yv)]
            yv = y if st else y + h
            pts += [(x0 + t * px, yv)]
        pts += [(x0 + span * px, yv)]
        s.path(pts, color, 2)

    cols = ["#d62828", "#2a9d8f", "#1d70b8", "#6d597a"]
    for i in range(4):
        y = 80 + i * 42
        s.text(x0 - 12, y + 18, f"canal {i + 1}", 12, anchor="end")
        wave(y, i * period / 4, cols[i])
    for n in range(3):
        s.line(x0 + n * period * px, 72, x0 + n * period * px, 250, GRID, 1, "stroke-dasharray='3 3'")
    for i in range(1, 4):
        xx = x0 + i * period / 4 * px
        s.text(xx, 262, f"+{i * period / 4:.0f} µs", 10, MUTED, "middle")

    # summed current, shifted vs in phase
    def total(shifts, y, label, color):
        s.text(x0 - 12, y + 30, label, 12, anchor="end")
        n = 800
        pts = []
        for j in range(n + 1):
            t = span * j / n
            c = sum(1 for sh in shifts if ((t - sh) % period) / period < duty)
            pts.append((x0 + t * px, y + 60 - c * 14))
        # staircase
        stair = [pts[0]]
        for p in pts[1:]:
            stair += [(p[0], stair[-1][1]), p]
        s.path(stair, color, 2)
        s.line(x0, y + 60, x0 + span * px, y + 60, GRID)
        for c in range(0, 5):
            s.text(x0 + span * px + 6, y + 64 - c * 14, f"{c}×", 9, MUTED)

    s.text(500, 290, "Courant total demandé à l'alimentation LED (en nombre de canaux conduisant)",
           13, anchor="middle", weight="bold")
    total([0, 0, 0, 0], 300, "sans déphasage", "#9fb3c8")
    total([i * period / 4 for i in range(4)], 380, "avec déphasage", BLUE)
    s.text(500, 462, "Le déphasage étale les appels de courant : l'ondulation dans C7 et sur les câbles baisse.",
           12, MUTED, "middle")
    s.save("pwm-dephasage.svg")


# --------------------------------------------------------------------------------------
def gamma():
    s = Svg(560, 440, "Courbes gamma des rubans")
    s.text(280, 28, "Gamma des rubans (gamma_x10)", 18, anchor="middle", weight="bold")
    x0, y0, w, h = 70, 380, 440, 320
    for i in range(0, 6):
        s.line(x0, y0 - i * h / 5, x0 + w, y0 - i * h / 5, GRID)
        s.text(x0 - 8, y0 - i * h / 5 + 4, f"{i * 20} %", 11, MUTED, "end")
        s.line(x0 + i * w / 5, y0, x0 + i * w / 5, y0 - h, GRID)
        s.text(x0 + i * w / 5, y0 + 18, f"{int(i * 255 / 5)}", 11, MUTED, "middle")
    s.text(x0 + w / 2, y0 + 40, "valeur DMX (8 bits)", 12, anchor="middle")
    s.text(18, y0 - h / 2, "rapport cyclique", 12, anchor="middle", extra=f"transform='rotate(-90 18 {y0 - h / 2})'")
    for g, c, label in [(1.0, "#9fb3c8", "10 : linéaire"), (2.2, BLUE, "22 : défaut"), (2.8, ACCENT, "28")]:
        pts = [(x0 + v / 255 * w, y0 - (v / 255) ** g * h) for v in range(256)]
        s.path(pts, c, 2.5)
    for i, (c, label) in enumerate([("#9fb3c8", "gamma_x10 = 10 (linéaire)"), (BLUE, "gamma_x10 = 22 (défaut)"),
                                    (ACCENT, "gamma_x10 = 28")]):
        s.line(x0 + 16, 70 + i * 20, x0 + 40, 70 + i * 20, c, 3)
        s.text(x0 + 48, 74 + i * 20, label, 12)
    s.save("gamma.svg")


# --------------------------------------------------------------------------------------
def relay_debounce():
    interval = 3.0
    # DMX level of the relay channel (>= 128 = on) changing quickly
    dmx = [(0.0, 0), (0.5, 1), (1.3, 0), (1.8, 1), (2.4, 0), (5.2, 1), (5.6, 0), (6.1, 1), (11.0, 1)]
    t_end = 11.0
    # simulation of SPEC 4.5 point 3: deferred, last desired value wins
    state, last_switch = 0, -99.0
    relay = [(0.0, 0)]
    t = 0.0
    step = 0.01
    while t <= t_end:
        desired = [v for tt, v in dmx if tt <= t + 1e-9][-1]
        if desired != state and t - last_switch >= interval - 1e-9:
            state, last_switch = desired, t
            relay.append((t, state))
        t = round(t + step, 4)
    s = Svg(1000, 330, "Anti-rebond du relais")
    s.text(500, 28, "Relais : au plus une commutation toutes les 3 s, la dernière demande gagne", 18,
           anchor="middle", weight="bold")
    x0, px = 160, 70.0

    def trace(events, y, label, color):
        s.text(x0 - 12, y + 20, label, 13, anchor="end", weight="bold")
        pts = []
        cur = events[0][1]
        pts.append((x0, y + (0 if cur else 30)))
        for tt, v in events[1:]:
            pts += [(x0 + tt * px, y + (0 if cur else 30)), (x0 + tt * px, y + (0 if v else 30))]
            cur = v
        pts.append((x0 + t_end * px, y + (0 if cur else 30)))
        s.path(pts, color, 2.5)
        s.text(x0 + t_end * px + 8, y + 5, "allumé", 10, MUTED)
        s.text(x0 + t_end * px + 8, y + 34, "éteint", 10, MUTED)

    trace(dmx[:-1], 70, "canal DMX ≥ 128 ?", "#9fb3c8")
    trace(relay, 150, "contact du relais", ACCENT)
    for tt, _ in relay[1:]:
        s.rect(x0 + tt * px, 200, interval * px, 14, "#fde2e2", "none")
        s.text(x0 + tt * px + 4, 211, "3 s", 10, ACCENT)
    for t in range(0, 12):
        s.line(x0 + t * px, 232, x0 + t * px, 238, MUTED)
        s.text(x0 + t * px, 252, f"{t} s", 11, MUTED, "middle")
    s.line(x0, 232, x0 + t_end * px, 232, MUTED)
    s.text(500, 290, "Les changements pendant l'intervalle ne sont pas perdus : la commutation est différée "
           "jusqu'à l'échéance,", 12, MUTED, "middle")
    s.text(500, 308, "puis c'est la dernière valeur demandée qui s'applique (relay_min_interval_ms, "
           "défaut 3000).", 12, MUTED, "middle")
    s.save("relais.svg")


if __name__ == "__main__":
    board_map()
    dmx_frame()
    latency()
    pwm_phase()
    gamma()
    relay_debounce()
