#include "dmxnow/relay.h"

#include "dmxnow/dmx.h"

namespace dmxnow {

void RelayLogic::begin(uint8_t power_on, bool last_state, bool relay_dmx, uint16_t min_ms, uint32_t now) {
    relay_dmx_ = relay_dmx;
    min_ms_ = min_ms;
    state_ = false;               // GPIO is low (relay off) until the first update()
    desired_ = power_on == 1 ? true : power_on == 0 ? false : last_state;
    force_ = Force::Auto;
    have_dmx_ = false;
    switched_once_ = false;
    (void)now;
}

void RelayLogic::command(Force f, uint32_t now) {
    force_ = f;
    if (f == Force::On) desired_ = true;
    else if (f == Force::Off) desired_ = false;
    else if (relay_dmx_ && have_dmx_) desired_ = dmx_on_;   // back to the DMX channel
    // Auto without a DMX stream: keep the current desired state
    (void)now;
}

void RelayLogic::dmx_level(uint8_t level, uint32_t now) {
    have_dmx_ = true;
    dmx_on_ = level >= 128;
    if (relay_dmx_ && force_ == Force::Auto) desired_ = dmx_on_;
    (void)now;
}

bool RelayLogic::update(uint32_t now) {
    if (desired_ == state_) return false;
    // the first switch after power-on is free (the contact starts open)
    if (switched_once_ && !time_reached(now, last_switch_ + min_ms_)) return false;
    state_ = desired_;
    last_switch_ = now;
    switched_once_ = true;
    // opening at power-on (state already false) is not a switch; any real change is
    ++count_;
    return true;
}

}  // namespace dmxnow
