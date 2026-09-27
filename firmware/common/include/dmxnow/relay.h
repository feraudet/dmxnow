// Relay decision logic (SPEC §4.5). Pure logic: the caller drives the GPIO and persists
// the state when switched() returns true.
//
// Priority: command force (RELAY 0/1) > DMX channel level (relay_dmx = 1, stream
// present) > power-on state. The DMX channel acts on level (>= 128 = on). A change
// requested less than min_interval after the last switch is deferred, not dropped:
// the latest desired state applies at the deadline. Stream loss never moves the relay.
#pragma once
#include <cstdint>

namespace dmxnow {

class RelayLogic {
public:
    enum class Force : uint8_t { Off = 0, On = 1, Auto = 2 };

    // Power-on: power_on 0 = off, 1 = on, 2 = last persisted state.
    void begin(uint8_t power_on, bool last_state, bool relay_dmx, uint16_t min_interval_ms, uint32_t now_ms);
    void set_relay_dmx(bool enabled) { relay_dmx_ = enabled; }
    void set_min_interval(uint16_t ms) { min_ms_ = ms; }

    void command(Force f, uint32_t now_ms);
    void dmx_level(uint8_t level, uint32_t now_ms);   // each valid frame carrying the slot

    // Returns true if the contact must change now (then state() is the new state).
    bool update(uint32_t now_ms);

    bool state() const { return state_; }
    bool forced() const { return force_ != Force::Auto; }
    bool pending() const { return desired_ != state_; }
    uint8_t heartbeat_bits() const { return uint8_t((state_ ? 1 : 0) | (forced() ? 2 : 0) | (pending() ? 4 : 0)); }
    uint32_t switch_count() const { return count_; }
    void set_switch_count(uint32_t c) { count_ = c; }

private:
    bool state_ = false;
    bool desired_ = false;
    bool relay_dmx_ = true;
    bool have_dmx_ = false;
    bool dmx_on_ = false;
    Force force_ = Force::Auto;
    uint16_t min_ms_ = 3000;
    bool switched_once_ = false;
    uint32_t last_switch_ = 0;
    uint32_t count_ = 0;
};

}  // namespace dmxnow
