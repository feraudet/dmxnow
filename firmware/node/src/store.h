// Persistent storage in NVS (Preferences). Writes are rare by design (SPEC 4.5, 4.9):
// configuration on SET_CONFIG, relay state on an effective switch, the anti-replay
// counter on an authenticated command, the power-cycle counter twice per boot.
#pragma once
#include <cstdint>

#include "dmxnow/config.h"

namespace store {

void begin();
bool load_config(dmxnow::NodeConfig* c);            // false: nothing stored (defaults kept)
void save_config(const dmxnow::NodeConfig& c);
// FACTORY_RESET: erases everything but the relay switch counter (PROTOCOL 6.3)
void factory_reset();

void load_relay(bool* state, uint32_t* count);
void save_relay(bool state, uint32_t count);

uint32_t auth_counter();
void set_auth_counter(uint32_t c);

uint8_t boot_count();
void set_boot_count(uint8_t n);

}  // namespace store
