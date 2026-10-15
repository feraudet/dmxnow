// dmxnow node board - entry point. Node by default, dongle when the Pi daemon talks to it
// over USB or when the role is saved (SPEC 4.15). See node.cpp.
#include <Arduino.h>

#include "node.h"

namespace {
bool dongle = false;
}

void setup() {
    dongle = node::boot_as_dongle();
    if (dongle) node::dongle_setup();
    else node::setup();
}

void loop() {
    if (dongle) node::dongle_loop();
    else node::loop();
}
