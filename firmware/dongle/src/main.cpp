// dmxnow dongle on the XIAO ESP32-C3 (SPEC 4.10): always a dongle. The application is
// shared with the node boards in dongle role (firmware/dongle_app).
#include <Arduino.h>

#include "dongle_app.h"

void setup() {
    dongle_app::Hooks h;
    h.probe_pin = D10;   // latency probe (ENF-01)
    h.board = 0;         // XIAO: role fixed, SET_ROLE refused
    dongle_app::setup(h);
}

void loop() { dongle_app::loop(); }
