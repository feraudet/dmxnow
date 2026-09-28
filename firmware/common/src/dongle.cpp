#include "dmxnow/dongle.h"

#include <cstring>

#include "dmxnow/config.h"

namespace dmxnow {

constexpr uint32_t CommandTracker::kWait[5];

bool apply_dongle_config(const uint8_t* tlv, size_t len, DongleSettings* s) {
    DongleSettings n = *s;
    bool ok = true;
    bool wf = tlv_for_each(tlv, len, [&](uint8_t k, const uint8_t* v, uint8_t l) {
        if (!ok) return;
        switch (k) {
            case 0x01: ok = l == 1 && v[0] >= 1 && v[0] <= 13; if (ok) n.channel = v[0]; break;
            case 0x02: ok = l == 2 && get16(v) >= 1; if (ok) n.net_id = get16(v); break;
            // wifi_phy_rate_t legacy rates: 0x00-0x03 (DSSS long preamble), 0x05-0x07
            // (short preamble), 0x08-0x0F (OFDM); 0x04 does not exist
            case 0x03: ok = l == 1 && v[0] <= 0x0F && v[0] != 0x04; if (ok) n.phy_rate = v[0]; break;
            case 0x04: ok = l == 1 && v[0] >= 2 && v[0] <= 20; if (ok) n.power_dbm = v[0]; break;
            case 0x05: ok = l == 4 && get32(v) >= 1000; if (ok) n.hold_timeout_ms = get32(v); break;
            case 0x06: ok = l == 1 && v[0] >= 1 && v[0] <= 60; if (ok) n.refresh_hz = v[0]; break;
            case 0x07: ok = l == 1 && v[0] <= 1; if (ok) n.mode = v[0]; break;
            default: ok = false;
        }
    });
    if (!wf || !ok) return false;
    *s = n;
    return true;
}

Reject validate_dongle(const uint8_t* pkt, size_t size, uint16_t my_net_id, Header* out) {
    Reject r = validate(pkt, size, my_net_id, out);
    if (r != Reject::NetId) return r;
    // enrolment: HEARTBEAT of an unconfigured node
    Header h = decode_header(pkt);
    if (h.net_id != 0 || h.type != uint8_t(MsgType::Heartbeat)) return r;
    // run the remaining checks with the node's (zero) net_id
    std::size_t need = kHeaderSize + h.length + ((h.flags & flags::kAuth) ? kAuthSize : 0);
    if (size != need) return Reject::Length;
    if (packet_crc(pkt, size) != h.crc16) return Reject::Crc;
    if (h.length < kHeartbeatPayload) return Reject::TypeCheck;
    if (out) *out = h;
    return Reject::None;
}

// --- UniverseTable ----------------------------------------------------------------------
void UniverseTable::set_refresh_hz(uint8_t hz) {
    refresh_us_ = hz ? 1000000u / hz : 22727;
    for (auto& u : u_) u.cadence.set_refresh_hz(hz);
}

bool UniverseTable::update(uint16_t id, const uint8_t* data, uint16_t len, uint32_t now_ms) {
    if (len > kDmxSlots) return false;
    Universe* slot = nullptr;
    for (auto& u : u_)
        if (u.used && u.id == id) { slot = &u; break; }
    if (!slot) {
        for (auto& u : u_)
            if (!u.used) { slot = &u; break; }
        if (!slot) return false;
        *slot = Universe();
        slot->used = true;
        slot->id = id;
        slot->cadence = OutputCadence(10, refresh_us_);
    } else if (slot->cadence.dirty()) {
        ++coalesced_;   // previous data not sent yet: merged (PROTOCOL 4.4)
    }
    std::memcpy(slot->data, data, len);
    slot->len = len;
    slot->last_data_ms = now_ms;
    slot->cadence.on_new_data();
    return true;
}

void UniverseTable::expire(uint32_t now_ms, uint32_t hold) {
    for (auto& u : u_)
        if (u.used && now_ms - u.last_data_ms >= hold) u.used = false;
}

UniverseTable::Universe* UniverseTable::due(uint32_t now_us) {
    Universe* best = nullptr;
    for (auto& u : u_) {
        if (!u.used || !u.cadence.due(now_us)) continue;
        // new data first, then the one waiting for the longest time
        if (!best || (u.cadence.dirty() && !best->cadence.dirty())) best = &u;
    }
    return best;
}

void UniverseTable::sent(Universe* u, uint32_t now_us) {
    u->cadence.sent(now_us);
    ++u->seq;
}

uint8_t UniverseTable::active() const {
    uint8_t n = 0;
    for (const auto& u : u_) n += u.used;
    return n;
}

// --- CommandTracker ------------------------------------------------------------------------
bool CommandTracker::add(uint16_t id, const uint8_t target[6], const uint8_t* pkt, size_t len, uint32_t now) {
    if (len > kMaxPacket) return false;
    for (auto& c : c_) {
        if (c.used) continue;
        c = Cmd();
        c.used = true;
        c.id = id;
        std::memcpy(c.target, target, 6);
        c.broadcast = mac_is_broadcast(target);
        std::memcpy(c.pkt, pkt, len);
        c.len = len;
        c.start_ms = now;
        c.next_ms = now;
        c.end_ms = now + (c.broadcast ? kBroadcastCollectMs : 0);
        return true;
    }
    return false;
}

const uint8_t* CommandTracker::due(uint32_t now, size_t* len) {
    for (auto& c : c_) {
        if (!c.used || c.acked || !time_reached(now, c.next_ms)) continue;
        uint8_t max = c.broadcast ? kBroadcastEmissions : kTargetedAttempts;
        if (c.attempts >= max) continue;
        ++c.attempts;
        if (c.broadcast) {
            c.next_ms = now + kBroadcastSpacingMs;
        } else {
            c.next_ms = now + kWait[c.attempts - 1];
            c.end_ms = c.next_ms;   // result time if no ACK (after the last wait)
        }
        *len = c.len;
        return c.pkt;
    }
    return nullptr;
}

void CommandTracker::on_ack(uint16_t id, const uint8_t src[6], uint32_t now) {
    for (auto& c : c_) {
        if (!c.used || c.id != id || c.broadcast) continue;   // broadcast: ACKs go to the Pi only
        if (std::memcmp(c.target, src, 6) != 0) continue;       // ACK of another node
        c.acked = true;
        c.end_ms = now;
    }
}

bool CommandTracker::pop_done(uint32_t now, Done* d) {
    for (auto& c : c_) {
        if (!c.used) continue;
        bool finished;
        Result r;
        if (c.broadcast) {
            finished = c.attempts >= kBroadcastEmissions && time_reached(now, c.end_ms);
            r = Result::BroadcastDone;
        } else if (c.acked) {
            finished = true;
            r = Result::Acked;
        } else {
            finished = c.attempts >= kTargetedAttempts && time_reached(now, c.end_ms);
            r = Result::Timeout;
        }
        if (!finished) continue;
        d->cmd_id = c.id;
        std::memcpy(d->target, c.target, 6);
        d->result = r;
        d->attempts = c.attempts;
        c.used = false;
        return true;
    }
    return false;
}

bool CommandTracker::pending() const {
    for (const auto& c : c_)
        if (c.used) return true;
    return false;
}

// --- Scheduler ------------------------------------------------------------------------------
Scheduler::Tx Scheduler::next(uint32_t now_ms, uint32_t now_us, uint32_t hold) {
    Tx t;
    universes.expire(now_ms, hold);
    if ((t.cmd = commands.due(now_ms, &t.cmd_len))) {
        t.kind = Kind::Command;
        return t;
    }
    if ((t.uni = universes.due(now_us))) {
        t.kind = Kind::Dmx;
        return t;
    }
    if (!beacon_started_ || time_reached(now_ms, next_beacon_ms_)) {
        beacon_started_ = true;
        next_beacon_ms_ = now_ms + kBeaconMs;
        t.kind = Kind::Beacon;
    }
    return t;
}

}  // namespace dmxnow
