#include "store.h"

#include <Preferences.h>

namespace store {

namespace {
Preferences prefs;
constexpr uint16_t kConfigLayout = 1;   // bump when NodeConfig changes layout
struct Blob {
    uint16_t layout;
    dmxnow::NodeConfig cfg;
};
}  // namespace

void begin() { prefs.begin("dmxnow", false); }

bool load_config(dmxnow::NodeConfig* c) {
    Blob b;
    if (prefs.getBytesLength("cfg") != sizeof b) return false;
    prefs.getBytes("cfg", &b, sizeof b);
    if (b.layout != kConfigLayout) return false;
    b.cfg.name[16] = 0;
    b.cfg.maint_password[32] = 0;
    *c = b.cfg;
    return true;
}

void save_config(const dmxnow::NodeConfig& c) {
    Blob b{kConfigLayout, c};
    prefs.putBytes("cfg", &b, sizeof b);
}

void factory_reset() {
    uint32_t count = prefs.getUInt("rcount", 0);
    prefs.clear();
    prefs.putUInt("rcount", count);
}

void load_relay(bool* state, uint32_t* count) {
    *state = prefs.getBool("rstate", false);
    *count = prefs.getUInt("rcount", 0);
}

void save_relay(bool state, uint32_t count) {
    prefs.putBool("rstate", state);
    prefs.putUInt("rcount", count);
}

uint32_t auth_counter() { return prefs.getUInt("actr", 0); }
void set_auth_counter(uint32_t c) { prefs.putUInt("actr", c); }

uint8_t boot_count() { return prefs.getUChar("boots", 0); }
void set_boot_count(uint8_t n) { prefs.putUChar("boots", n); }

}  // namespace store
