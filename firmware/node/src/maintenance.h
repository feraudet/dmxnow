// Maintenance mode (SPEC 4.9, EF-12): WPA2 access point "dmxnow-<name>" on the ESP-NOW
// channel (reception continues, AP+STA), minimal web page (status, configuration,
// firmware upload), exit on button / page / timeout without client.
#pragma once
#include <cstddef>
#include <cstdint>
#include <functional>

#include "dmxnow/config.h"

namespace maint {

struct Hooks {
    // Applies a TLV list like SET_CONFIG; returns the ACK status.
    std::function<dmxnow::AckStatus(const uint8_t*, size_t)> apply_config;
    std::function<const dmxnow::NodeConfig&()> config;
    std::function<void(char*, size_t)> status_text;   // one line per item
    std::function<void(uint8_t)> relay;               // 0 off, 1 on, 2 auto
};

void start(const dmxnow::NodeConfig& cfg, uint16_t timeout_s, const Hooks& hooks);
bool active();
void loop();      // web server, timeout
void stop();      // back to STA only, same channel

}  // namespace maint
