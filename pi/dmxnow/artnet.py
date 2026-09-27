"""Art-Net 4 subset (SPEC 4.11, EF-01): ArtDmx (0x5000) in, ArtPoll (0x2000) ->
ArtPollReply (0x2100). The Port-Address is the 15-bit dmxnow universe.
"""
from __future__ import annotations

import struct

ID = b"Art-Net\x00"
PORT = 6454
OP_POLL, OP_POLL_REPLY, OP_DMX = 0x2000, 0x2100, 0x5000
PROT_VER = 14
REPLY_SIZE = 239


def opcode(pkt: bytes):
    if len(pkt) < 10 or pkt[:8] != ID:
        return None
    return struct.unpack_from("<H", pkt, 8)[0]


def parse_dmx(pkt: bytes):
    """ArtDmx -> (port_address, sequence, data) or None if malformed."""
    if opcode(pkt) != OP_DMX or len(pkt) < 18:
        return None
    seq, _phys, sub_uni, net = pkt[12], pkt[13], pkt[14], pkt[15]
    length = struct.unpack_from(">H", pkt, 16)[0]
    if not 2 <= length <= 512 or len(pkt) < 18 + length:
        return None
    return ((net & 0x7F) << 8) | sub_uni, seq, pkt[18:18 + length]


def build_dmx(port_address: int, data: bytes, sequence: int = 0) -> bytes:
    """ArtDmx (used by the tests and the loopback tools)."""
    if len(data) % 2:
        data += b"\x00"
    return (ID + struct.pack("<H", OP_DMX) + struct.pack(">H", PROT_VER)
            + bytes([sequence & 0xFF, 0, port_address & 0xFF, (port_address >> 8) & 0x7F])
            + struct.pack(">H", len(data)) + data)


def build_poll() -> bytes:
    return ID + struct.pack("<H", OP_POLL) + struct.pack(">H", PROT_VER) + bytes([0x00, 0x00])


def poll_replies(universes, ip: str, mac: bytes = b"\0" * 6, short_name: str = "dmxnow",
                 long_name: str = "dmxnow ESP-NOW gateway", report: str = "#0001 [0000] dmxnow OK"):
    """ArtPollReply packets announcing the forwarded universes as outputs: one reply per
    group of 4 universes sharing Net and Sub-Net (BindIndex 1, 2, ...)."""
    groups = {}
    for u in sorted(set(universes)):
        groups.setdefault(u >> 4, []).append(u & 0x0F)
    chunks = []
    for netsub, lows in sorted(groups.items()):
        for i in range(0, len(lows), 4):
            chunks.append((netsub, lows[i:i + 4]))
    if not chunks:
        chunks = [(0, [])]
    out = []
    ip_b = bytes(int(x) for x in ip.split("."))
    for bind, (netsub, ports) in enumerate(chunks, start=1):
        n = len(ports)
        p = bytearray(REPLY_SIZE)
        p[0:8] = ID
        struct.pack_into("<H", p, 8, OP_POLL_REPLY)
        p[10:14] = ip_b
        struct.pack_into("<H", p, 14, PORT)
        struct.pack_into(">H", p, 16, 1)                   # firmware version
        p[18] = (netsub >> 4) & 0x7F                       # NetSwitch
        p[19] = netsub & 0x0F                              # SubSwitch
        struct.pack_into(">H", p, 20, 0x00FF)              # OEM: unknown
        p[23] = 0xD0                                       # Status1: indicators normal, network addressed
        p[26:26 + 18] = short_name.encode()[:17].ljust(18, b"\0")
        p[44:44 + 64] = long_name.encode()[:63].ljust(64, b"\0")
        p[108:108 + 64] = report.encode()[:63].ljust(64, b"\0")
        struct.pack_into(">H", p, 172, n)                  # NumPorts
        for i in range(n):
            p[174 + i] = 0x80                              # output from Art-Net, DMX512
            p[182 + i] = 0x80                              # GoodOutput: data being output
            p[190 + i] = ports[i]                          # SwOut
        p[201:207] = mac
        p[207:211] = ip_b                                  # BindIp
        p[211] = bind                                      # BindIndex
        p[212] = 0x08                                      # Status2: 15-bit Port-Address
        out.append(bytes(p))
    return out


def parse_poll_reply(p: bytes) -> dict:
    """Decoder used by the tests: the announced Port-Addresses."""
    net, sub, n = p[18], p[19], struct.unpack_from(">H", p, 172)[0]
    return {"bind_index": p[211], "ports": [(net << 8) | (sub << 4) | p[190 + i] for i in range(n)],
            "short_name": p[26:44].rstrip(b"\0").decode()}
