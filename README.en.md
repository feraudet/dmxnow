# dmxnow

**English** · [Français](README.fr.md)

Wireless DMX and LED strip nodes over ESP-NOW, driven by QLC+ from a Raspberry Pi.

![dmxnow board v0.3, top side (JLCPCB render)](docs/figures/jlcpcb-top.png)

## Context

In scenography (exhibitions, museums, shows, events), fixtures are often far from the
control desk: hung from the ceiling, spread over several rooms, hidden in a set. Each
one needs two cables: mains power, and a DMX line that starts at the console, runs from
fixture to fixture and ends with a terminator. Pulling and hiding those DMX lines takes
time at every setup, and they break or get unplugged.

Target equipment: moving heads, COB and conventional fixtures up to 200 W, plus 12/24 V
LED strips in the sets, all driven by QLC+.

## The need

- **One cable per fixture**: mains. DMX arrives by radio.
- **Switch a fixture's power from QLC+**, without a smart plug or a separate relay pack:
  after the show, so that fans do not keep running and nothing draws standby power.
- **Drive LED strips** in the same show as the fixtures, without a separate LED
  controller.
- **Latency nobody can see**: under 10 ms typical when the DMX frame is set to the
  channels the fixture uses (about 13 ms with a full 512-channel frame), and a normal
  DMX refresh (44 Hz).
- **No on-site settings**: a node is configured from the Pi, finds the network on its
  own and can be identified remotely (its strips or its status LED blink).
- **A reasonable cost per fixture**: about 53 € of parts for a node with LED strips,
  39 € without, for a batch of 20.
- **Safe hardware**: the node is on 230 V, and its isolation drives the design.

Most off-the-shelf wireless DMX receivers only do DMX: they neither switch the fixture's
power nor drive LED strips.

## Use cases

| Situation | What dmxnow brings |
|-----------|--------------------|
| **Exhibition or museum**: fixtures on tracks, spread over several rooms | Each fixture plugs into the nearest socket; no DMX line running from room to room |
| **Touring show or event**: setup and teardown every day | Fewer cables to pull and hide; a new node is enrolled with one command |
| **Lit set pieces**: LED strips in furniture, a display case, a set element | The 4 strip channels follow QLC+ like a fixture (RGBW, gamma, 8 or 16 bits) |
| **End of the show**: power down the whole rig without a ladder | Each node's relay follows a DMX channel, or a `dmxnow relay` command |
| **Permanent installation**: automatic lighting in a public venue | The Pi and QLC+ run unattended; a node that was switched off finds the network and its radio channel again by itself |
| **Fixture hung high up**: maintenance without taking it down | Firmware update over Wi-Fi (OTA) and a settings page, with the enclosure closed |

## How it works

![Overview: QLC+, daemon, dongle, nodes](docs/diagrams/vue-ensemble.png)

- **QLC+** sends Art-Net locally to the **`dmxnowd`** daemon on the Raspberry Pi.
- The daemon hands the universes over USB to a **dongle** (XIAO ESP32-C3, 5 dBi antenna).
- The dongle broadcasts them over **ESP-NOW**: one packet per universe, as soon as a
  value changes, repeated at 44 Hz. 4 universes per dongle recommended, 8 at most.
- Each **node** (ESP32-C3) keeps its universe, outputs the DMX frame, follows its relay
  channel and its strip channels, and sends a heartbeat back to the Pi.
- Commands (`dmxnow relay`, `set`, `reboot`...) are signed (HMAC-SHA256) and
  acknowledged.

The illustrated details are in [docs/fonctionnement.md](docs/fonctionnement.md). The
documentation is written in French; the diagrams speak for themselves.

## Two variants, one board

| Variant | Use | Enclosure |
|---------|-----|-----------|
| Full board | fixture + 4 LED strip channels | 208 × 88 × 34 mm |
| Broken board | fixture only (strip part removed) | 150 × 88 × 34 mm |

The strip part hangs on three breakaway tabs that carry its traces. The node detects
its variant on its own.

## Project status

| Deliverable | Status |
|-------------|--------|
| Specification, protocol, decisions ([spec/](spec/)) | Approved (v1.0) |
| Board v0.3 ([hardware/](hardware/)) | Ordered from JLCPCB, 5 assembled boards, placement to be approved |
| Node and dongle firmware ([firmware/](firmware/)) | Written, built and tested in CI |
| Pi daemon and CLI ([pi/](pi/)) | Written, 50 tests (simulated dongle) |
| 3D printed enclosures ([enclosure/](enclosure/)) | Node (2 variants) and dongle, STL and STEP |
| Documentation ([docs/](docs/)) | Assembly, flashing, wiring, commissioning, safety |

Still to be measured on the bench once the boards arrive: radio range and losses,
latency, dongle load with 8 universes, DMX timings on a logic analyser, mains tests of
the prototype. The full list is in [spec/SPEC.md](spec/SPEC.md) (items marked
« À valider »).

## Where to start

| I want to... | Read |
|--------------|------|
| Understand the system | [docs/fonctionnement.md](docs/fonctionnement.md) |
| Build and install nodes | [docs/README.md](docs/README.md), in order: safety, assembly, flashing, wiring, commissioning |
| Install the Pi | [pi/README.md](pi/README.md) |
| Rebuild the board | [hardware/README.md](hardware/README.md), JLCPCB order: [hardware/ORDER.md](hardware/ORDER.md) |
| Print the enclosures | [enclosure/README.md](enclosure/README.md) |
| Change the firmware | [firmware/README.md](firmware/README.md) |

## Repository layout

| Folder | Contents |
|--------|----------|
| `spec/` | [SPEC.md](spec/SPEC.md), [PROTOCOL.md](spec/PROTOCOL.md), architecture decisions ([spec/adr/](spec/adr/)) |
| `hardware/` | KiCad board generated by script, gerbers, JLCPCB BOM and placement |
| `firmware/` | `common/` (protocol, tested on PC), `node/`, `dongle/` (USB dongle) |
| `pi/` | `dmxnowd` daemon, `dmxnow` CLI, systemd service, udev rule, `install.sh` |
| `enclosure/` | Parametric CadQuery enclosures, STL and STEP |
| `docs/` | User documentation, figures and diagrams |

## Safety

🔴 The node is connected to **230 V mains**. Read [docs/securite.md](docs/securite.md)
before handling it. The whole mains part (board, enclosure, wiring) must be reviewed by
a qualified person before manufacturing and before powering on. This project comes with
no warranty whatsoever.

## License

Hardware (board, enclosures, documentation) under **CERN-OHL-S-2.0**, software
(firmware, daemon, CLI) under **GPL-3.0-or-later**, third-party KiCad libraries under
CC-BY-SA-4.0. Details in [LICENSE](LICENSE).
