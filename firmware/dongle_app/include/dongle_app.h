// dmxnow dongle application (SPEC 4.10, 4.15; PROTOCOL 4, 6, 8): USB CDC link to the Pi
// daemon (COBS frames) <-> ESP-NOW v2 broadcast to the nodes. Runs on the XIAO dongle
// (firmware/dongle) and on a node board in dongle role (firmware/node).
#pragma once
#include <cstdint>

namespace dongle_app {

struct Hooks {
    int probe_pin = -1;        // toggles at each emission (latency probe, ENF-01), -1 = none
    // node board switching at runtime: Serial already started, with the dongle buffers
    bool serial_started = false;
    uint8_t board = 0;         // reported in STATUS: 0 = XIAO dongle, 1 = node board
    uint8_t role_source = 0;   // reported in STATUS: dmxnow::RoleSource
    // node board: each universe received from the Pi (wired DMX output on the XLR)
    void (*on_universe)(uint16_t id, const uint8_t* data, uint16_t len) = nullptr;
    // SET_ROLE from the Pi; nullptr = role fixed (XIAO), the request is refused with a LOG
    void (*on_set_role)(uint8_t role) = nullptr;
};

void setup(const Hooks& hooks);
void loop();

}  // namespace dongle_app
