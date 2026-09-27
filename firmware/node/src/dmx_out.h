// DMX512 output on UART1 / GPIO4 (SPEC 4.4, EF-05): 250 kbit/s 8N2, break 176 us by
// line inversion, MAB 12 us, start code 0 + dmx_out_slots slots. Sent by a dedicated
// task with the "event + 44 Hz minimum" cadence (PROTOCOL 4.4).
#pragma once
#include <cstdint>

namespace dmx_out {

void begin(uint16_t slots);
void set_slots(uint16_t slots);
// New universe data (channels beyond len are 0): output as soon as the cadence allows.
void set_frame(const uint8_t* data, uint16_t len);
// Forces one slot (1-based) to a value (IDENTIFY), 0 = none.
void set_override(uint16_t slot, uint8_t value);
void set_blackout(bool on);
uint32_t frames_sent();

}  // namespace dmx_out
