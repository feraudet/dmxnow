"""Stored shows ("conduites", PROTOCOL §10): build, read, preview.

A show is a list of keyframes played in a loop by the node, with a linear fade from one
keyframe to the next. The node plays it from power-up while no DMX stream arrives, and
QLC+ takes over as soon as it sends this node's universe (SPEC 4.13, ADR 0016).

    from dmxnow.show import Show, rel, abs_slot
    s = Show("feu", [rel(1), rel(2), rel(3), rel(4)])   # the 4 strip channels
    s.step(120, [255, 80, 0, 10])                        # fade in 120 ms to these values
    open("feu.dxs", "wb").write(s.encode())
"""
from __future__ import annotations

import struct
import zlib
from dataclasses import dataclass, field

MAGIC = b"DXS\x01"
HEADER = struct.Struct("<4s16sHHI")  # channels u16 (was u8 + flags 0: older files read the same)
HEADER_SIZE = HEADER.size          # 28
MAX_CHANNELS = 512                 # a whole universe (100-pixel strip: 300)
MAX_SIZE = 0x20000                 # node partition (firmware/node/partitions.csv)
RELATIVE = 0x8000
WRITE_CHUNK = 192                  # SHOW_WRITE data bytes per command


def rel(offset: int) -> int:
    """Channel at start_address + offset (offset 0 = start_address, the relay channel
    when relay_dmx = 1; the strips are 1 to 4 then)."""
    if not 0 <= offset < 512:
        raise ValueError(f"offset out of range: {offset}")
    return RELATIVE | offset


def abs_slot(slot: int) -> int:
    """Absolute channel of the universe (1..512), e.g. a moving head on the XLR."""
    if not 1 <= slot <= 512:
        raise ValueError(f"slot out of range: {slot}")
    return slot


@dataclass
class Show:
    name: str
    channels: list[int]
    resume_s: int = 5
    steps: list[tuple[int, list[int]]] = field(default_factory=list)

    def step(self, duration_ms: int, values) -> "Show":
        """Keyframe reached duration_ms after the previous one (0 = jump). After the last
        keyframe the show fades back to the first one in the first keyframe's duration."""
        values = [int(round(v)) for v in values]
        if len(values) != len(self.channels):
            raise ValueError(f"{len(values)} values for {len(self.channels)} channels")
        if not 0 <= duration_ms <= 0xFFFF:
            raise ValueError(f"duration out of range: {duration_ms}")
        self.steps.append((int(duration_ms), [min(255, max(0, v)) for v in values]))
        return self

    @property
    def loop_ms(self) -> int:
        return sum(d for d, _ in self.steps)

    def encode(self) -> bytes:
        name = self.name.encode("utf-8")
        if not 1 <= len(name) <= 16:
            raise ValueError("name: 1 to 16 bytes")
        if not 1 <= len(self.channels) <= MAX_CHANNELS:
            raise ValueError(f"1 to {MAX_CHANNELS} channels")
        for c in self.channels:
            if not ((c & RELATIVE and (c & ~RELATIVE) < 512) or 1 <= c <= 512):
                raise ValueError(f"bad channel 0x{c:04x}: use rel() or abs_slot()")
        if not 1 <= self.resume_s <= 3600:
            raise ValueError("resume_s: 1 to 3600")
        if not self.steps or self.loop_ms == 0:
            raise ValueError("at least one keyframe and a loop longer than 0 ms")
        body = bytearray(HEADER.pack(MAGIC, name.ljust(16, b"\0"), len(self.channels), self.resume_s,
                                     len(self.steps)))
        for c in self.channels:
            body += struct.pack("<H", c)
        for d, values in self.steps:
            body += struct.pack("<H", d) + bytes(values)
        body += struct.pack("<I", zlib.crc32(body))
        if len(body) > MAX_SIZE:
            raise ValueError(f"show too large: {len(body)} bytes > {MAX_SIZE}")
        return bytes(body)

    @classmethod
    def decode(cls, data: bytes) -> "Show":
        if len(data) < HEADER_SIZE + 4:
            raise ValueError("file too short")
        magic, name, n, resume_s, count = HEADER.unpack_from(data)
        if magic != MAGIC:
            raise ValueError("not a dmxnow show (DXS1)")
        size = HEADER_SIZE + 2 * n + count * (2 + n) + 4
        if len(data) != size:
            raise ValueError(f"size {len(data)}, header says {size}")
        if zlib.crc32(data[:-4]) != struct.unpack_from("<I", data, size - 4)[0]:
            raise ValueError("bad CRC-32")
        channels = list(struct.unpack_from(f"<{n}H", data, HEADER_SIZE))
        s = cls(name.rstrip(b"\0").decode("utf-8", "replace"), channels, resume_s)
        o = HEADER_SIZE + 2 * n
        for _ in range(count):
            s.steps.append((struct.unpack_from("<H", data, o)[0], list(data[o + 2:o + 2 + n])))
            o += 2 + n
        s.encode()   # same range checks as the node (show_parse)
        return s

    def render(self, t_ms: int) -> list[int]:
        """Channel values at t_ms from the start, like the node (firmware/common/src/show.cpp)."""
        reached = [0]
        for d, _ in self.steps[1:]:
            reached.append(reached[-1] + d)
        tm = t_ms % self.loop_ms
        i = max(k for k in range(len(self.steps)) if reached[k] <= tm)
        nxt = (i + 1) % len(self.steps)
        d, el = self.steps[nxt][0], tm - reached[i]
        a, b = self.steps[i][1], self.steps[nxt][1]
        return [(x * (d - el) + y * el + d // 2) // d if d else y for x, y in zip(a, b)]

    def describe(self) -> str:
        chans = ", ".join(f"+{c & ~RELATIVE}" if c & RELATIVE else str(c) for c in self.channels)
        return (f"{self.name}: {len(self.channels)} channel(s) [{chans}], {len(self.steps)} keyframes, "
                f"loop {self.loop_ms / 1000:.1f} s, resume after {self.resume_s} s without DMX, "
                f"{len(self.encode())} bytes")


def chunks(data: bytes, size: int = WRITE_CHUNK):
    """(offset, bytes) for the SHOW_WRITE commands."""
    for off in range(0, len(data), size):
        yield off, data[off:off + size]


def decode_info(p: bytes) -> dict:
    """SHOW_INFO ACK data (PROTOCOL §10.2). channels is u16 (38 bytes); a node firmware
    from before the 512-channel shows sends it as u8 (37 bytes)."""
    fmt = "<BB16sIIIIHH" if len(p) >= 38 else "<BB16sIIIIHB"
    loaded, playing, name, size, crc, steps, loop_ms, resume_s, n = struct.unpack_from(fmt, p)
    if not loaded:
        return {"loaded": False, "playing": False}
    return {"loaded": True, "playing": bool(playing), "name": name.rstrip(b"\0").decode("utf-8", "replace"),
            "size": size, "crc32": f"{crc:08x}", "keyframes": steps, "loop_s": loop_ms / 1000,
            "resume_s": resume_s, "channels": n}
