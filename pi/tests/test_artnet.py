from dmxnow import artnet


def test_artdmx_roundtrip():
    data = bytes(range(10))
    pkt = artnet.build_dmx(0x1234 & 0x7FFF, data, sequence=5)
    assert artnet.opcode(pkt) == artnet.OP_DMX
    u, seq, got = artnet.parse_dmx(pkt)
    assert (u, seq, bytes(got)) == (0x1234, 5, data)
    odd = artnet.parse_dmx(artnet.build_dmx(3, b"\x01\x02\x03"))   # padded to an even length
    assert bytes(odd[2]) == b"\x01\x02\x03\x00"


def test_artdmx_rejects_malformed():
    good = artnet.build_dmx(1, bytes(512))
    assert artnet.parse_dmx(b"Art-Net\x00" + good[8:17]) is None          # truncated header
    assert artnet.parse_dmx(good[:-1]) is None                            # truncated data
    assert artnet.parse_dmx(b"NotArtN\x00" + good[8:]) is None            # wrong id
    too_long = bytearray(good)
    too_long[16:18] = (514).to_bytes(2, "big")
    assert artnet.parse_dmx(bytes(too_long) + b"\0\0") is None
    assert artnet.opcode(artnet.build_poll()) == artnet.OP_POLL


def test_poll_replies_group_by_subnet_and_bind_index():
    unis = [0, 1, 2, 3, 4, 17, 0x123]
    replies = artnet.poll_replies(unis, "127.0.0.1")
    assert all(len(r) == artnet.REPLY_SIZE for r in replies)
    parsed = [artnet.parse_poll_reply(r) for r in replies]
    assert [p["bind_index"] for p in parsed] == [1, 2, 3, 4]
    assert sorted(u for p in parsed for u in p["ports"]) == sorted(unis)
    assert all(len(p["ports"]) <= 4 for p in parsed)
    assert artnet.opcode(replies[0]) == artnet.OP_POLL_REPLY
    assert replies[0][10:14] == bytes([127, 0, 0, 1])
