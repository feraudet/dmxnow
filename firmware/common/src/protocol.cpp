#include "dmxnow/protocol.h"

#include <cstring>

#include "dmxnow/crc16.h"

namespace dmxnow {

void encode_header(const Header& h, uint8_t* o) {
    put16(o + 0, h.magic);
    o[2] = h.version;
    o[3] = h.type;
    put16(o + 4, h.net_id);
    put16(o + 6, h.universe);
    put16(o + 8, h.seq);
    put16(o + 10, h.offset);
    put16(o + 12, h.length);
    o[14] = h.flags;
    o[15] = h.reserved;
    put16(o + 16, h.crc16);
}

Header decode_header(const uint8_t* i) {
    Header h;
    h.magic = get16(i + 0);
    h.version = i[2];
    h.type = i[3];
    h.net_id = get16(i + 4);
    h.universe = get16(i + 6);
    h.seq = get16(i + 8);
    h.offset = get16(i + 10);
    h.length = get16(i + 12);
    h.flags = i[14];
    h.reserved = i[15];
    h.crc16 = get16(i + 16);
    return h;
}

uint16_t packet_crc(const uint8_t* pkt, size_t size) {
    uint16_t c = crc16(pkt, 16);
    return crc16(pkt + kHeaderSize, size - kHeaderSize, c);
}

size_t build_packet(Header h, const uint8_t* payload, size_t payload_len, const uint8_t* auth,
                    uint8_t* out, size_t cap) {
    size_t size = kHeaderSize + payload_len + (auth ? kAuthSize : 0);
    if (size > cap || payload_len > 0xFFFF) return 0;
    h.magic = kMagic;
    h.version = kVersion;
    h.length = uint16_t(payload_len);
    h.flags = uint8_t((h.flags & ~flags::kAuth) | (auth ? flags::kAuth : 0));
    h.reserved = 0;
    h.crc16 = 0;
    encode_header(h, out);
    if (payload_len) std::memcpy(out + kHeaderSize, payload, payload_len);
    if (auth) std::memcpy(out + kHeaderSize + payload_len, auth, kAuthSize);
    put16(out + 16, packet_crc(out, size));
    return size;
}

const char* reject_name(Reject r) {
    switch (r) {
        case Reject::None: return "ok";
        case Reject::TooShort: return "too_short";
        case Reject::Magic: return "magic";
        case Reject::Version: return "version";
        case Reject::NetId: return "net_id";
        case Reject::Length: return "length";
        case Reject::Crc: return "crc";
        case Reject::Type: return "type";
        case Reject::TypeCheck: return "type_check";
    }
    return "?";
}

static bool known_type(uint8_t t) {
    switch (MsgType(t)) {
        case MsgType::DmxData:
        case MsgType::Command:
        case MsgType::Ack:
        case MsgType::Heartbeat:
        case MsgType::Beacon:
            return true;
    }
    return false;
}

static bool type_ok(const Header& h) {
    switch (MsgType(h.type)) {
        case MsgType::DmxData:
            if (h.universe > kMaxUniverse || h.length < 1 || h.length > kDmxSlots) return false;
            if (uint32_t(h.offset) + h.length > kDmxSlots) return false;
            // unfragmented (v2) packets carry the whole universe from channel 0
            if (!(h.flags & flags::kFrag) && h.offset != 0) return false;
            return true;
        case MsgType::Command: return h.length >= kCommandMinPayload;
        case MsgType::Ack: return h.length >= kAckMinPayload;
        case MsgType::Heartbeat: return h.length >= kHeartbeatPayload;
        case MsgType::Beacon: return h.length >= kBeaconPayload;
    }
    return false;
}

Reject validate(const uint8_t* pkt, size_t size, uint16_t my_net_id, Header* out) {
    if (size < kHeaderSize) return Reject::TooShort;
    Header h = decode_header(pkt);
    if (h.magic != kMagic) return Reject::Magic;
    if (h.version != kVersion) return Reject::Version;
    if (my_net_id == 0) {
        if (h.type != uint8_t(MsgType::Command) && h.type != uint8_t(MsgType::Beacon)) return Reject::NetId;
    } else if (h.net_id != my_net_id) {
        return Reject::NetId;
    }
    if (size != kHeaderSize + h.length + ((h.flags & flags::kAuth) ? kAuthSize : 0)) return Reject::Length;
    if (packet_crc(pkt, size) != h.crc16) return Reject::Crc;
    if (!known_type(h.type)) return Reject::Type;
    if (!type_ok(h)) return Reject::TypeCheck;
    if (out) *out = h;
    return Reject::None;
}

void encode_heartbeat(const Heartbeat& hb, uint8_t* o) {
    std::memset(o, 0, kHeartbeatPayload);
    std::memcpy(o, hb.mac, 6);
    std::memcpy(o + 6, hb.name, 16);
    put16(o + 22, hb.start_address);
    std::memcpy(o + 24, hb.fw_version, 3);
    o[27] = hb.variant;
    o[28] = hb.relay;
    put32(o + 29, hb.relay_switch_count);
    o[33] = uint8_t(hb.rssi);
    put32(o + 34, hb.rx_frames);
    put32(o + 38, hb.lost_frames);
    put32(o + 42, hb.rejected_frames);
    put32(o + 46, hb.uptime_s);
    o[50] = hb.status;
    o[51] = hb.radio_channel;
    put16(o + 52, hb.dmx_out_slots);
    o[54] = hb.reset_reason;
    o[55] = 0;
}

bool decode_heartbeat(const uint8_t* i, size_t len, Heartbeat* hb) {
    if (len < kHeartbeatPayload) return false;
    std::memcpy(hb->mac, i, 6);
    std::memcpy(hb->name, i + 6, 16);
    hb->start_address = get16(i + 22);
    std::memcpy(hb->fw_version, i + 24, 3);
    hb->variant = i[27];
    hb->relay = i[28];
    hb->relay_switch_count = get32(i + 29);
    hb->rssi = int8_t(i[33]);
    hb->rx_frames = get32(i + 34);
    hb->lost_frames = get32(i + 38);
    hb->rejected_frames = get32(i + 42);
    hb->uptime_s = get32(i + 46);
    hb->status = i[50];
    hb->radio_channel = i[51];
    hb->dmx_out_slots = get16(i + 52);
    hb->reset_reason = i[54];
    return true;
}

void encode_beacon(const Beacon& b, uint8_t* o) {
    std::memcpy(o, b.fw_version, 3);
    o[3] = b.active_universes;
    put32(o + 4, b.uptime_s);
}

bool decode_beacon(const uint8_t* i, size_t len, Beacon* b) {
    if (len < kBeaconPayload) return false;
    std::memcpy(b->fw_version, i, 3);
    b->active_universes = i[3];
    b->uptime_s = get32(i + 4);
    return true;
}

bool parse_command(const uint8_t* p, size_t len, CommandView* c) {
    if (len < kCommandMinPayload) return false;
    c->target = p;
    c->opcode = p[6];
    c->args = p + 7;
    c->args_len = len - 7;
    return true;
}

bool mac_is_broadcast(const uint8_t* m) {
    for (int i = 0; i < 6; ++i)
        if (m[i] != 0xFF) return false;
    return true;
}

}  // namespace dmxnow
