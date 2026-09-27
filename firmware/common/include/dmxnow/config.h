// Node configuration, TLV codec and DMX footprint (PROTOCOL §6.4).
#pragma once
#include <cstddef>
#include <cstdint>

#include "dmxnow/protocol.h"

namespace dmxnow {

namespace key {
constexpr uint8_t kUniverse = 0x01, kStartAddress = 0x02, kName = 0x03, kRadioChannel = 0x04,
                  kRelayDmx = 0x05, kRelayPowerOn = 0x06, kRelayMinIntervalMs = 0x07,
                  kLossBlackoutMs = 0x08, kPwmMode = 0x09, kGammaX10 = 0x0A, kFadeOnMs = 0x0B,
                  kPwmFreqHz = 0x0C, kDmxOutSlots = 0x0D, kIdentifySlot = 0x0E, kNetId = 0x0F,
                  kMaintPassword = 0x10, kNetKey = 0x11, kPowercycleMaint = 0x12, kStatusLed = 0x13;
constexpr uint8_t kMax = 0x13;
}  // namespace key

enum class Variant : uint8_t { FixtureOnly = 1, WithStrips = 2 };

struct NodeConfig {
    uint16_t universe = 0;
    uint16_t start_address = 1;
    char name[17] = {};                 // NUL terminated, 1..16 bytes
    uint8_t radio_channel = 6;
    uint8_t relay_dmx = 1;
    uint8_t relay_power_on = 2;         // 0 off, 1 on, 2 last state
    uint16_t relay_min_interval_ms = 3000;
    uint32_t loss_blackout_ms = 0;
    uint8_t pwm_mode = 0;               // 0 = 8 bit, 1 = 16 bit
    uint8_t gamma_x10 = 22;
    uint16_t fade_on_ms = 500;
    uint16_t pwm_freq_hz = 4882;
    uint16_t dmx_out_slots = 512;
    uint16_t identify_slot = 0;
    uint16_t net_id = 0;
    uint8_t maint_password_len = 0;
    char maint_password[33] = {};
    bool has_net_key = false;
    uint8_t net_key[32] = {};
    uint8_t powercycle_maint = 1;
    uint8_t status_led = 0;
};

// Defaults, with name = "node-XXXXXX" (last 3 MAC bytes, upper-case hex).
NodeConfig default_config(const uint8_t mac[6]);

// DMX footprint from start_address: relay slot (if relay_dmx), then PWM1..4 (8 bit) or
// PWM1 MSB, PWM1 LSB ... PWM4 LSB (16 bit) on the strip variant.
struct Footprint {
    int relay_slot = -1;        // 0-based channel index, -1 = none
    int pwm_first = -1;         // 0-based index of PWM1 (MSB), -1 = none
    uint8_t pwm_count = 0;      // 4 or 0
    bool pwm16 = false;
    uint16_t size = 0;          // 0, 1, 4, 5, 8 or 9 channels
};
Footprint footprint(const NodeConfig& c, Variant v);

// PWM channel value (0..65535) from a DMX frame; 8-bit values are scaled v * 257.
uint16_t pwm_value(const Footprint& f, const uint8_t* frame, uint16_t frame_len, uint8_t channel);

// Iterates TLV items; returns false on a malformed list (truncated item).
template <typename F>
bool tlv_for_each(const uint8_t* p, size_t len, F&& fn) {
    size_t i = 0;
    while (i < len) {
        if (i + 2 > len) return false;
        uint8_t k = p[i], l = p[i + 1];
        if (i + 2 + l > len) return false;
        fn(k, p + i + 2, l);
        i += 2 + size_t(l);
    }
    return true;
}

// Applies a SET_CONFIG TLV list atomically: every item is checked (known key, length,
// range, final start_address against the footprint) before anything is changed.
// On success *changed gets one bit per key (bit k), and cfg is updated.
AckStatus apply_config_tlv(const uint8_t* tlv, size_t len, Variant v, NodeConfig* cfg, uint32_t* changed);

// GET_CONFIG: every key except the write-only secrets (0x10, 0x11). Returns the size
// written, 0 if out_cap is too small.
size_t serialize_config_tlv(const NodeConfig& c, uint8_t* out, size_t out_cap);

bool utf8_valid(const uint8_t* s, size_t n);

}  // namespace dmxnow
