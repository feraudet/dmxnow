"""dmxnow protocol v1 (spec/PROTOCOL.md), Python side.

Same encodings as firmware/common: radio header and validation (§2), payloads (§5, §6),
configuration TLV (§6.4), command authentication (§7), serial framing (§8). Checked
against firmware/common/test_vectors.json by the tests.
"""
from __future__ import annotations

import hashlib
import hmac
import struct
from dataclasses import dataclass

MAGIC = 0x4E44
VERSION = 1
HEADER_SIZE = 18
AUTH_SIZE = 12
NO_UNIVERSE = 0xFFFF
MAX_UNIVERSE = 32767
BROADCAST = b"\xff" * 6

T_DMX, T_COMMAND, T_ACK, T_HEARTBEAT, T_BEACON = 0x01, 0x10, 0x11, 0x20, 0x30
F_LAST, F_FRAG, F_AUTH = 0x01, 0x02, 0x04

OP_IDENTIFY, OP_SET_CONFIG, OP_GET_CONFIG, OP_RELAY = 0x01, 0x02, 0x03, 0x04
OP_MAINTENANCE, OP_REBOOT, OP_FACTORY_RESET = 0x05, 0x06, 0x07
FACTORY_RESET_CONFIRM = 0x52455345

ACK_STATUS = {0: "ok", 1: "unknown_opcode", 2: "invalid_arg", 3: "auth_failed", 4: "unsupported",
              5: "internal_error"}

# serial link (§8)
S_UNIVERSE, S_COMMAND, S_DONGLE_CONFIG, S_PING, S_GET_STATUS = 0x01, 0x02, 0x03, 0x04, 0x05
S_RADIO_RX, S_CMD_RESULT, S_STATUS, S_PONG, S_LOG = 0x81, 0x82, 0x83, 0x84, 0x85
S_MAX_PAYLOAD = 1020
CMD_RESULT = {0: "acked", 1: "timeout", 2: "broadcast_done"}

_HDR = struct.Struct("<HBBHHHHHBB")   # without crc16


# --- CRC-16/CCITT-FALSE --------------------------------------------------------------
def _table():
    t = []
    for i in range(256):
        c = i << 8
        for _ in range(8):
            c = ((c << 1) ^ 0x1021) if c & 0x8000 else (c << 1)
        t.append(c & 0xFFFF)
    return t


_CRC = _table()


def crc16(data: bytes, crc: int = 0xFFFF) -> int:
    for b in data:
        crc = ((crc << 8) & 0xFFFF) ^ _CRC[((crc >> 8) ^ b) & 0xFF]
    return crc


# --- COBS ------------------------------------------------------------------------------
def cobs_encode(data: bytes) -> bytes:
    """Canonical COBS (a 254-byte block ending the input is not followed by 0x01)."""
    out, block = bytearray(), bytearray()
    for i, b in enumerate(data):
        if b == 0:
            out += bytes([len(block) + 1]) + block
            block = bytearray()
        else:
            block.append(b)
            if len(block) == 254:
                out += b"\xff" + block
                block = bytearray()
                if i == len(data) - 1:
                    return bytes(out)
    out += bytes([len(block) + 1]) + block
    return bytes(out)


def cobs_decode(data: bytes) -> bytes:
    out, i = bytearray(), 0
    while i < len(data):
        code = data[i]
        i += 1
        if code == 0 or i + code - 1 > len(data):
            raise ValueError("bad COBS block")
        chunk = data[i:i + code - 1]
        if 0 in chunk:
            raise ValueError("zero inside COBS data")
        out += chunk
        i += code - 1
        if code != 0xFF and i < len(data):
            out.append(0)
    return bytes(out)


# --- serial frames (§8.2) ------------------------------------------------------------------
def serial_encode(ftype: int, seq: int, payload: bytes = b"") -> bytes:
    if len(payload) > S_MAX_PAYLOAD:
        raise ValueError("serial payload too long")
    raw = bytes([ftype, seq & 0xFF]) + payload
    raw += struct.pack("<H", crc16(raw))
    return cobs_encode(raw) + b"\x00"


class SerialDecoder:
    """Byte stream -> frames (type, seq, payload); resynchronises on every 0x00."""

    def __init__(self):
        self.buf = bytearray()
        self.errors = 0

    def feed(self, data: bytes):
        frames = []
        for b in data:
            if b:
                if len(self.buf) < 4096:
                    self.buf.append(b)
                continue
            raw, self.buf = bytes(self.buf), bytearray()
            if not raw:
                continue
            try:
                dec = cobs_decode(raw)
            except ValueError:
                self.errors += 1
                continue
            if len(dec) < 4 or crc16(dec[:-2]) != struct.unpack("<H", dec[-2:])[0]:
                self.errors += 1
                continue
            frames.append((dec[0], dec[1], dec[2:-2]))
        return frames


# --- radio header and packets (§2) -----------------------------------------------------------
@dataclass
class Header:
    type: int
    net_id: int = 0
    universe: int = NO_UNIVERSE
    seq: int = 0
    offset: int = 0
    length: int = 0
    flags: int = 0
    magic: int = MAGIC
    version: int = VERSION
    reserved: int = 0
    crc16: int = 0

    def pack16(self) -> bytes:
        return _HDR.pack(self.magic, self.version, self.type, self.net_id, self.universe, self.seq & 0xFFFF,
                         self.offset, self.length, self.flags, self.reserved)

    @classmethod
    def unpack(cls, pkt: bytes) -> "Header":
        m, v, t, n, u, s, o, ln, f, r = _HDR.unpack_from(pkt)
        return cls(type=t, net_id=n, universe=u, seq=s, offset=o, length=ln, flags=f, magic=m, version=v,
                   reserved=r, crc16=struct.unpack_from("<H", pkt, 16)[0])


def build_packet(h: Header, payload: bytes = b"", trailer: bytes | None = None) -> bytes:
    h.length = len(payload)
    h.flags = (h.flags & ~F_AUTH) | (F_AUTH if trailer else 0)
    head = h.pack16()
    rest = payload + (trailer or b"")
    return head + struct.pack("<H", crc16(head + rest)) + rest


def packet_crc(pkt: bytes) -> int:
    return crc16(pkt[:16] + pkt[HEADER_SIZE:])


_MIN_LEN = {T_COMMAND: 7, T_ACK: 2, T_HEARTBEAT: 56, T_BEACON: 8}


def validate(pkt: bytes, my_net_id: int, dongle: bool = False):
    """PROTOCOL §2.5 steps 1-8. Returns (reject_name, header): 'ok' when valid.
    dongle=True: also accepts HEARTBEATs of unconfigured nodes (net_id 0), as the dongle."""
    if len(pkt) < HEADER_SIZE:
        return "too_short", None
    h = Header.unpack(pkt)
    if h.magic != MAGIC:
        return "magic", h
    if h.version != VERSION:
        return "version", h
    if my_net_id == 0:
        if h.type not in (T_COMMAND, T_BEACON):
            return "net_id", h
    elif h.net_id != my_net_id and not (dongle and h.net_id == 0 and h.type == T_HEARTBEAT):
        return "net_id", h
    if len(pkt) != HEADER_SIZE + h.length + (AUTH_SIZE if h.flags & F_AUTH else 0):
        return "length", h
    if packet_crc(pkt) != h.crc16:
        return "crc", h
    if h.type not in (T_DMX, T_COMMAND, T_ACK, T_HEARTBEAT, T_BEACON):
        return "type", h
    if h.type == T_DMX:
        ok = (h.universe <= MAX_UNIVERSE and 1 <= h.length <= 512 and h.offset + h.length <= 512
              and (h.flags & F_FRAG or h.offset == 0))
    else:
        ok = h.length >= _MIN_LEN[h.type]
    return ("ok" if ok else "type_check"), h


def payload_of(pkt: bytes, h: Header) -> bytes:
    return pkt[HEADER_SIZE:HEADER_SIZE + h.length]


# --- payloads ----------------------------------------------------------------------------------
_HB = struct.Struct("<6s16sH3sBBIbIIIIBBHBB")


def decode_heartbeat(p: bytes) -> dict:
    (mac, name, start, fw, variant, relay, count, rssi, rx, lost, rej, up, status, ch, slots, reason,
     _) = _HB.unpack_from(p)
    return {"mac": mac.hex(":"), "name": name.rstrip(b"\0").decode("utf-8", "replace"), "start_address": start,
            "fw_version": ".".join(str(x) for x in fw), "variant": {1: "fixture", 2: "strips"}.get(variant, str(variant)),
            "relay_on": bool(relay & 1), "relay_forced": bool(relay & 2), "relay_pending": bool(relay & 4),
            "relay_switch_count": count, "rssi": rssi, "rx_frames": rx, "lost_frames": lost,
            "rejected_frames": rej, "uptime_s": up, "dmx_stream": bool(status & 1), "blackout": bool(status & 2),
            "maintenance": bool(status & 4), "identify": bool(status & 8), "dongle_known": bool(status & 16),
            "radio_channel": ch, "dmx_out_slots": slots, "reset_reason": reason}


def decode_status(p: bytes) -> dict:
    fw, ch, net, rate, mode, active, ok, fail, serr, coal, up = struct.unpack_from("<3sBHBBBIIIII", p)
    return {"fw_version": ".".join(str(x) for x in fw), "channel": ch, "net_id": net, "phy_rate": rate,
            "mode": "v1" if mode else "v2", "active_universes": active, "tx_ok": ok, "tx_fail": fail,
            "serial_errors": serr, "coalesced": coal, "uptime_s": up}


# --- configuration TLV (§6.4) -----------------------------------------------------------------------
# name: (key, kind) ; kinds: u8, u16, u32, str (UTF-8), bytes
CONFIG_KEYS = {
    "universe": (0x01, "u16"), "start_address": (0x02, "u16"), "name": (0x03, "str"),
    "radio_channel": (0x04, "u8"), "relay_dmx": (0x05, "u8"), "relay_power_on": (0x06, "u8"),
    "relay_min_interval_ms": (0x07, "u16"), "loss_blackout_ms": (0x08, "u32"), "pwm_mode": (0x09, "u8"),
    "gamma_x10": (0x0A, "u8"), "fade_on_ms": (0x0B, "u16"), "pwm_freq_hz": (0x0C, "u16"),
    "dmx_out_slots": (0x0D, "u16"), "identify_slot": (0x0E, "u16"), "net_id": (0x0F, "u16"),
    "maint_password": (0x10, "str"), "net_key": (0x11, "bytes"), "powercycle_maint": (0x12, "u8"),
    "status_led": (0x13, "u8"),
}
_BY_KEY = {k: (name, kind) for name, (k, kind) in CONFIG_KEYS.items()}
_FMT = {"u8": "<B", "u16": "<H", "u32": "<I"}


def encode_config(values: dict) -> bytes:
    out = bytearray()
    for name, v in values.items():
        if name not in CONFIG_KEYS:
            raise KeyError(f"unknown configuration key: {name}")
        key, kind = CONFIG_KEYS[name]
        raw = (struct.pack(_FMT[kind], int(v)) if kind in _FMT else
               v.encode("utf-8") if kind == "str" else bytes(v))
        if len(raw) > 255:
            raise ValueError(f"{name}: value too long")
        out += bytes([key, len(raw)]) + raw
    return bytes(out)


def decode_config(tlv: bytes) -> dict:
    out, i = {}, 0
    while i + 2 <= len(tlv):
        k, ln = tlv[i], tlv[i + 1]
        v = tlv[i + 2:i + 2 + ln]
        i += 2 + ln
        name, kind = _BY_KEY.get(k, (f"0x{k:02x}", "bytes"))
        out[name] = (struct.unpack(_FMT[kind], v)[0] if kind in _FMT else
                     v.decode("utf-8", "replace") if kind == "str" else v.hex())
    return out


DONGLE_KEYS = {"channel": (0x01, "u8"), "net_id": (0x02, "u16"), "phy_rate": (0x03, "u8"),
               "power_dbm": (0x04, "u8"), "hold_timeout_ms": (0x05, "u32"), "refresh_hz": (0x06, "u8"),
               "mode": (0x07, "u8")}
PHY_RATES = {"1M": 0x00, "2M": 0x01, "5.5M": 0x02, "11M": 0x03, "6M": 0x0B, "12M": 0x0A, "24M": 0x09}


def encode_dongle_config(values: dict) -> bytes:
    out = bytearray()
    for name, v in values.items():
        key, kind = DONGLE_KEYS[name]
        raw = struct.pack(_FMT[kind], int(v))
        out += bytes([key, len(raw)]) + raw
    return bytes(out)


# --- commands and authentication (§6, §7) --------------------------------------------------------
def auth_trailer(key: bytes, header16: bytes, payload: bytes, counter: int) -> bytes:
    """counter u32 LE + first 8 bytes of HMAC-SHA256(key, header[0..15] || payload || counter)."""
    c = struct.pack("<I", counter)
    return c + hmac.new(key, header16 + payload + c, hashlib.sha256).digest()[:8]


def command_body(target: bytes, opcode: int, args: bytes = b"") -> bytes:
    return bytes(target) + bytes([opcode]) + args


def serial_command(net_id: int, cmd_id: int, target: bytes, opcode: int, args: bytes = b"",
                   key: bytes | None = None, counter: int | None = None) -> bytes:
    """COMMAND payload for the dongle (§8.3): cmd_id, flags, target, opcode, args, trailer.
    The trailer covers the radio header the dongle will build (net_id, seq = cmd_id,
    length, flags = AUTH), which the Pi can therefore compute."""
    body = command_body(target, opcode, args)
    flags = 0
    trailer = b""
    if key is not None:
        flags = F_AUTH
        h = Header(type=T_COMMAND, net_id=net_id, universe=NO_UNIVERSE, seq=cmd_id, length=len(body), flags=F_AUTH)
        trailer = auth_trailer(key, h.pack16(), body, counter)
    return struct.pack("<HB", cmd_id & 0xFFFF, flags) + body + trailer


def decode_ack(pkt: bytes, h: Header) -> dict:
    p = payload_of(pkt, h)
    return {"cmd_id": h.seq, "opcode": p[0], "status": ACK_STATUS.get(p[1], str(p[1])), "data": p[2:]}


def parse_mac(s: str) -> bytes:
    s = s.replace(":", "").replace("-", "").strip()
    if len(s) != 12:
        raise ValueError(f"bad MAC address: {s}")
    return bytes.fromhex(s)
