// Node application: glues the protocol logic (firmware/common) to the peripherals.
// The same firmware also runs a node board as dongle (SPEC 4.15): boot_as_dongle()
// decides at power-up, from the saved role and the RTC flag.
#pragma once
#include <cstdint>

namespace node {

bool boot_as_dongle();

void setup();
void loop();

// dongle role: dongle application (firmware/dongle_app), wired DMX output of the
// node's universe on the XLR, relay open, PWM off
void dongle_setup();
void dongle_loop();

}  // namespace node
