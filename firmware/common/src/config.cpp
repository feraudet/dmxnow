#include "dmxnow/config.h"

#include <cstdio>
#include <cstring>

namespace dmxnow {

NodeConfig default_config(const uint8_t mac[6]) {
    NodeConfig c;
    std::snprintf(c.name, sizeof c.name, "node-%02X%02X%02X", mac[3], mac[4], mac[5]);
    return c;
}

Footprint footprint(const NodeConfig& c, Variant v) {
    Footprint f;
    int next = c.start_address - 1;
    if (c.relay_dmx) f.relay_slot = next++;
    if (v == Variant::WithStrips) {
        f.pwm_first = next;
        f.pwm_count = 4;
        f.pwm16 = c.pwm_mode == 1;
        next += f.pwm16 ? 8 : 4;
    }
    f.size = uint16_t(next - (c.start_address - 1));
    return f;
}

uint16_t pwm_value(const Footprint& f, const uint8_t* frame, uint16_t len, uint8_t ch) {
    if (f.pwm_first < 0 || ch >= f.pwm_count) return 0;
    auto at = [&](int i) -> uint8_t { return (i >= 0 && i < len) ? frame[i] : 0; };
    if (f.pwm16) {
        int i = f.pwm_first + 2 * ch;
        return uint16_t((at(i) << 8) | at(i + 1));
    }
    return uint16_t(at(f.pwm_first + ch) * 257);
}

bool utf8_valid(const uint8_t* s, size_t n) {
    size_t i = 0;
    while (i < n) {
        uint8_t b = s[i];
        size_t extra;
        uint32_t cp;
        if (b < 0x80) { ++i; continue; }
        if ((b & 0xE0) == 0xC0) { extra = 1; cp = b & 0x1F; }
        else if ((b & 0xF0) == 0xE0) { extra = 2; cp = b & 0x0F; }
        else if ((b & 0xF8) == 0xF0) { extra = 3; cp = b & 0x07; }
        else return false;
        if (i + extra >= n) return false;   // truncated sequence
        for (size_t k = 1; k <= extra; ++k) {
            if ((s[i + k] & 0xC0) != 0x80) return false;
            cp = (cp << 6) | (s[i + k] & 0x3F);
        }
        static const uint32_t kMin[] = {0, 0x80, 0x800, 0x10000};
        if (cp < kMin[extra] || cp > 0x10FFFF || (cp >= 0xD800 && cp <= 0xDFFF)) return false;
        i += extra + 1;
    }
    return true;
}

namespace {
bool fixed(uint8_t l, uint8_t want) { return l == want; }
uint16_t u16(const uint8_t* v) { return get16(v); }
}  // namespace

AckStatus apply_config_tlv(const uint8_t* tlv, size_t len, Variant var, NodeConfig* cfg, uint32_t* changed) {
    NodeConfig n = *cfg;
    uint32_t mask = 0;
    bool ok = true;
    bool well_formed = tlv_for_each(tlv, len, [&](uint8_t k, const uint8_t* v, uint8_t l) {
        if (!ok) return;
        switch (k) {
            case key::kUniverse:
                ok = fixed(l, 2) && u16(v) <= kMaxUniverse;
                if (ok) n.universe = u16(v);
                break;
            case key::kStartAddress:
                ok = fixed(l, 2) && u16(v) >= 1 && u16(v) <= kDmxSlots;
                if (ok) n.start_address = u16(v);
                break;
            case key::kName:
                ok = l >= 1 && l <= 16 && utf8_valid(v, l) && std::memchr(v, 0, l) == nullptr;
                if (ok) { std::memset(n.name, 0, sizeof n.name); std::memcpy(n.name, v, l); }
                break;
            case key::kRadioChannel:
                ok = fixed(l, 1) && v[0] >= 1 && v[0] <= 13;
                if (ok) n.radio_channel = v[0];
                break;
            case key::kRelayDmx:
                ok = fixed(l, 1) && v[0] <= 1;
                if (ok) n.relay_dmx = v[0];
                break;
            case key::kRelayPowerOn:
                ok = fixed(l, 1) && v[0] <= 2;
                if (ok) n.relay_power_on = v[0];
                break;
            case key::kRelayMinIntervalMs:
                ok = fixed(l, 2) && u16(v) >= 1000 && u16(v) <= 60000;
                if (ok) n.relay_min_interval_ms = u16(v);
                break;
            case key::kLossBlackoutMs:
                ok = fixed(l, 4);
                if (ok) n.loss_blackout_ms = get32(v);
                break;
            case key::kPwmMode:
                ok = fixed(l, 1) && v[0] <= 1;
                if (ok) n.pwm_mode = v[0];
                break;
            case key::kGammaX10:
                ok = fixed(l, 1) && v[0] >= 10 && v[0] <= 30;
                if (ok) n.gamma_x10 = v[0];
                break;
            case key::kFadeOnMs:
                ok = fixed(l, 2) && u16(v) <= 10000;
                if (ok) n.fade_on_ms = u16(v);
                break;
            case key::kPwmFreqHz:
                ok = fixed(l, 2) && u16(v) >= 1000 && u16(v) <= 19531;
                if (ok) n.pwm_freq_hz = u16(v);
                break;
            case key::kDmxOutSlots:
                ok = fixed(l, 2) && u16(v) >= 24 && u16(v) <= kDmxSlots;
                if (ok) n.dmx_out_slots = u16(v);
                break;
            case key::kIdentifySlot:
                ok = fixed(l, 2) && u16(v) <= kDmxSlots;
                if (ok) n.identify_slot = u16(v);
                break;
            case key::kNetId:
                ok = fixed(l, 2) && u16(v) >= 1;
                if (ok) n.net_id = u16(v);
                break;
            case key::kMaintPassword:
                ok = l >= 8 && l <= 32 && std::memchr(v, 0, l) == nullptr;
                if (ok) {
                    std::memset(n.maint_password, 0, sizeof n.maint_password);
                    std::memcpy(n.maint_password, v, l);
                    n.maint_password_len = l;
                }
                break;
            case key::kNetKey:
                ok = fixed(l, 32);
                if (ok) { std::memcpy(n.net_key, v, 32); n.has_net_key = true; }
                break;
            case key::kPowercycleMaint:
                ok = fixed(l, 1) && v[0] <= 1;
                if (ok) n.powercycle_maint = v[0];
                break;
            case key::kStatusLed:
                ok = fixed(l, 1) && v[0] <= 1;
                if (ok) n.status_led = v[0];
                break;
            default:
                ok = false;
        }
        if (ok) mask |= 1u << k;
    });
    if (!well_formed || !ok) return AckStatus::InvalidArg;
    // the whole footprint must fit in the universe
    Footprint f = footprint(n, var);
    if (f.size && uint32_t(n.start_address) - 1 + f.size > kDmxSlots) return AckStatus::InvalidArg;
    *cfg = n;
    if (changed) *changed = mask;
    return AckStatus::Ok;
}

size_t serialize_config_tlv(const NodeConfig& c, uint8_t* out, size_t cap) {
    size_t o = 0;
    bool fits = true;
    auto item = [&](uint8_t k, const uint8_t* v, uint8_t l) {
        if (o + 2 + l > cap) { fits = false; return; }
        out[o] = k;
        out[o + 1] = l;
        std::memcpy(out + o + 2, v, l);
        o += 2 + l;
    };
    auto i8 = [&](uint8_t k, uint8_t v) { item(k, &v, 1); };
    auto i16 = [&](uint8_t k, uint16_t v) { uint8_t b[2]; put16(b, v); item(k, b, 2); };
    auto i32 = [&](uint8_t k, uint32_t v) { uint8_t b[4]; put32(b, v); item(k, b, 4); };
    i16(key::kUniverse, c.universe);
    i16(key::kStartAddress, c.start_address);
    item(key::kName, reinterpret_cast<const uint8_t*>(c.name), uint8_t(std::strlen(c.name)));
    i8(key::kRadioChannel, c.radio_channel);
    i8(key::kRelayDmx, c.relay_dmx);
    i8(key::kRelayPowerOn, c.relay_power_on);
    i16(key::kRelayMinIntervalMs, c.relay_min_interval_ms);
    i32(key::kLossBlackoutMs, c.loss_blackout_ms);
    i8(key::kPwmMode, c.pwm_mode);
    i8(key::kGammaX10, c.gamma_x10);
    i16(key::kFadeOnMs, c.fade_on_ms);
    i16(key::kPwmFreqHz, c.pwm_freq_hz);
    i16(key::kDmxOutSlots, c.dmx_out_slots);
    i16(key::kIdentifySlot, c.identify_slot);
    i16(key::kNetId, c.net_id);
    i8(key::kPowercycleMaint, c.powercycle_maint);
    i8(key::kStatusLed, c.status_led);
    return fits ? o : 0;
}

}  // namespace dmxnow
