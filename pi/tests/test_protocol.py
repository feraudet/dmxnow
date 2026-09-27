"""Protocol port checked against the vectors shared with the firmware (PROTOCOL §9)."""
import json
import os
import struct

import pytest

from dmxnow import protocol as P

VECTORS = os.path.join(os.path.dirname(__file__), "..", "..", "firmware", "common", "test_vectors.json")
V = json.load(open(VECTORS))


def test_crc_check_value():
    assert P.crc16(b"123456789") == 0x29B1
    for c in V["crc"]:
        data = c["ascii"].encode() if "ascii" in c else bytes.fromhex(c["hex"])
        assert P.crc16(data) == c["crc"]


@pytest.mark.parametrize("vec", V["valid"], ids=lambda v: v["name"])
def test_valid_packets(vec):
    pkt = bytes.fromhex(vec["hex"])
    why, h = P.validate(pkt, vec["my_net_id"])
    assert why == "ok"
    assert (h.type, h.universe, h.seq, h.offset, h.length, h.flags) == (
        vec["type"], vec["universe"], vec["seq"], vec["offset"], vec["length"], vec["flags"])
    assert P.payload_of(pkt, h).hex() == vec["payload"]
    # rebuilt from its fields: identical bytes
    trailer = pkt[P.HEADER_SIZE + h.length:] if h.flags & P.F_AUTH else None
    again = P.build_packet(P.Header(type=h.type, net_id=h.net_id, universe=h.universe, seq=h.seq,
                                    offset=h.offset, flags=h.flags), P.payload_of(pkt, h), trailer)
    assert again == pkt


@pytest.mark.parametrize("vec", V["invalid"], ids=lambda v: v["name"])
def test_invalid_packets(vec):
    assert P.validate(bytes.fromhex(vec["hex"]), vec["my_net_id"])[0] == vec["reject"]


def test_dongle_accepts_unconfigured_heartbeat_only():
    hb = next(v for v in V["valid"] if v["name"] == "heartbeat")
    pkt = bytes.fromhex(hb["hex"])
    h = P.Header.unpack(pkt)
    zero = P.build_packet(P.Header(type=h.type, net_id=0, universe=h.universe, seq=h.seq), P.payload_of(pkt, h))
    assert P.validate(zero, V["net_id"], dongle=True)[0] == "ok"
    assert P.validate(zero, V["net_id"])[0] == "net_id"


def test_heartbeat_decode():
    hb = next(v for v in V["valid"] if v["name"] == "heartbeat")
    pkt = bytes.fromhex(hb["hex"])
    d = P.decode_heartbeat(P.payload_of(pkt, P.Header.unpack(pkt)))
    e = hb["heartbeat"]
    assert d["mac"] == bytes.fromhex(e["mac"]).hex(":")
    assert d["name"] == e["name"] and d["start_address"] == e["start_address"]
    assert d["rssi"] == e["rssi"] and d["lost_frames"] == e["lost_frames"]
    assert d["variant"] == "strips" and d["relay_on"] and not d["relay_forced"] and d["relay_pending"]
    assert d["dmx_stream"] and d["dongle_known"] and d["dmx_out_slots"] == e["dmx_out_slots"]


@pytest.mark.parametrize("vec", V["cobs"], ids=lambda v: str(len(v["raw"]) // 2))
def test_cobs(vec):
    raw = bytes.fromhex(vec["raw"])
    assert P.cobs_encode(raw).hex() == vec["enc"]
    assert P.cobs_decode(bytes.fromhex(vec["enc"])) == raw


def test_cobs_malformed():
    for bad in (b"\x02\x00\x01", b"\x05\x01\x02", b"\x00"):
        with pytest.raises(ValueError):
            P.cobs_decode(bad)


def test_serial_frames_and_resync():
    d = P.SerialDecoder()
    f1 = P.serial_encode(P.S_UNIVERSE, 7, struct.pack("<HH", 3, 4) + b"\x00\x01\x00\x02")
    bad = bytearray(P.serial_encode(P.S_PING, 8, b"\x01\x02\x03\x04"))
    bad[2] ^= 0x40 if bad[2] != 0x40 else 0x20
    frames = d.feed(b"\x13\x37\x00" + f1 + bytes(bad) + b"\x00\x00" + f1)
    assert [f[0] for f in frames] == [P.S_UNIVERSE, P.S_UNIVERSE]
    assert frames[0][2] == struct.pack("<HH", 3, 4) + b"\x00\x01\x00\x02"
    assert d.errors == 2
    with pytest.raises(ValueError):
        P.serial_encode(1, 0, bytes(P.S_MAX_PAYLOAD + 1))


def test_command_signed_by_the_pi_equals_the_vector():
    """The Pi computes the trailer over the header the dongle will build (PROTOCOL §7)."""
    vec = next(v for v in V["valid"] if v["name"] == "cmd_relay_auth")
    key = bytes.fromhex(V["net_key"])
    target = bytes.fromhex(vec["command"]["target"])
    payload = P.serial_command(V["net_id"], vec["seq"], target, P.OP_RELAY, b"\x01", key=key,
                               counter=vec["auth_counter"])
    cmd_id, flags = struct.unpack_from("<HB", payload)
    body, trailer = payload[3:-P.AUTH_SIZE], payload[-P.AUTH_SIZE:]
    radio = P.build_packet(P.Header(type=P.T_COMMAND, net_id=V["net_id"], universe=P.NO_UNIVERSE, seq=cmd_id),
                           body, trailer)
    assert radio.hex() == vec["hex"] and flags == P.F_AUTH


def test_hmac_vectors():
    import hashlib
    import hmac
    for v in V["hmac_sha256"]:
        assert hmac.new(bytes.fromhex(v["key"]), bytes.fromhex(v["data"]), hashlib.sha256).hexdigest() == v["mac"]


def test_config_tlv_matches_the_firmware():
    tlv = bytes.fromhex(V["config_default_tlv"]["tlv"])
    d = P.decode_config(tlv)
    assert d["name"] == "node-123456" and d["pwm_freq_hz"] == 4882 and d["dmx_out_slots"] == 512
    assert P.encode_config(d) == tlv
    setc = next(v for v in V["valid"] if v["name"] == "cmd_set_config_unconfigured")["command"]["args"]
    assert P.encode_config({"universe": 5, "start_address": 10, "name": "lyre-1"}).hex() == setc
    with pytest.raises(KeyError):
        P.encode_config({"nope": 1})


def test_dongle_config_tlv():
    assert P.encode_dongle_config({"channel": 11, "net_id": 0x1234}) == bytes([1, 1, 11, 2, 2, 0x34, 0x12])
