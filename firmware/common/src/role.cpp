#include "dmxnow/role.h"

namespace dmxnow {

BootRole boot_role(uint8_t saved_role, uint32_t rtc) {
    BootRole b;
    if (rtc == kRtcNodeThisBoot) {   // explicit return to node: wins over everything, once
        b.auto_switch = false;
        return b;
    }
    if (saved_role == uint8_t(Role::Dongle)) {
        b.role = Role::Dongle;
        b.source = RoleSource::Saved;
        b.auto_switch = false;
    }
    return b;
}

}  // namespace dmxnow
