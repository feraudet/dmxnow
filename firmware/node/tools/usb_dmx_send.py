"""Envoie du DMX à un nœud par son USB, sans radio (banc, nœud hors secteur, J3-5V).

    python usb_dmx_send.py /dev/cu.usbmodemXXXX 19=255 12=128 [--hz 30] [--seconds 10]

Chaque argument canal=valeur règle un canal DMX (1 à 512) ; les autres restent à 0. La
trame est répétée à --hz jusqu'à Ctrl-C ou --seconds. Format : requête « Output Only Send
DMX Packet » de l'Enttec DMX USB Pro (label 6), lue par firmware/common/src/usb_dmx.cpp.
Dépendance : pyserial.
"""
import argparse
import time

import serial


def frame(slots: bytes) -> bytes:
    payload = b"\0" + slots   # start code 0
    return bytes([0x7E, 6, len(payload) & 0xFF, len(payload) >> 8]) + payload + b"\xE7"


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("port")
    ap.add_argument("values", nargs="*", help="canal=valeur, par exemple 19=255")
    ap.add_argument("--hz", type=float, default=30)
    ap.add_argument("--seconds", type=float, default=0, help="0 = jusqu'à Ctrl-C")
    a = ap.parse_args()
    slots = bytearray(512)
    for v in a.values:
        ch, val = (int(x) for x in v.split("="))
        if not (1 <= ch <= 512 and 0 <= val <= 255):
            raise SystemExit(f"{v}: canal 1 à 512, valeur 0 à 255")
        slots[ch - 1] = val
    s = serial.Serial(a.port, 115200, write_timeout=1)
    s.dtr = True   # sans DTR, le pilote USB de l'ESP32-C3 peut ignorer ce qui arrive
    pkt, period = frame(bytes(slots)), 1 / a.hz
    end = time.monotonic() + a.seconds if a.seconds else None
    nxt = time.monotonic()
    try:
        while end is None or time.monotonic() < end:
            s.write(pkt)
            nxt += period
            time.sleep(max(0.0, nxt - time.monotonic()))
    except KeyboardInterrupt:
        pass
    s.write(frame(bytes(512)))   # noir avant de partir
    s.close()


if __name__ == "__main__":
    main()
