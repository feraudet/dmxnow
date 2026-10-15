// Role of a node board (SPEC §4.15, ADR 0018): one firmware, node by default. It becomes
// a dongle when the Pi daemon talks to it over USB (automatic, without restart, until the
// next power-on) or at boot when the dongle role is saved (dmxnow role). Pure logic: the
// caller reads the saved role (NVS) and a flag kept in RTC memory across esp_restart()
// (random after a power-on, hence a magic value).
#pragma once
#include <cstdint>

namespace dmxnow {

enum class Role : uint8_t { Node = 0, Dongle = 1 };

// How the dongle role was chosen, reported in the dongle STATUS (PROTOCOL §8.4).
enum class RoleSource : uint8_t { Fixed = 0, Automatic = 1, Saved = 2 };

constexpr uint32_t kRtcNodeThisBoot = 0x4E4F4445;   // "NODE": back to node, no auto switch

struct BootRole {
    Role role = Role::Node;
    RoleSource source = RoleSource::Saved;
    bool auto_switch = true;   // node role: become dongle if the daemon speaks on USB
};

// saved_role: value in NVS (0 node, 1 dongle, anything else = node). rtc: RTC flag.
BootRole boot_role(uint8_t saved_role, uint32_t rtc);

}  // namespace dmxnow
