// Gamma correction tables (SPEC §4.7): 8-bit input -> 256 entries, 16-bit input -> 257
// points with linear interpolation. Output: duty 0..(2^bits - 1). gamma_x10 = 10 gives a
// linear curve. Monotonic, 0 -> 0, max -> full scale.
#pragma once
#include <cstdint>

namespace dmxnow {

class GammaTable {
public:
    void build(uint8_t gamma_x10, uint8_t out_bits);
    uint32_t lookup8(uint8_t v) const { return t8_[v]; }
    uint32_t lookup16(uint16_t v) const;
    uint32_t max_duty() const { return max_; }

private:
    uint32_t t8_[256] = {};
    uint32_t t16_[257] = {};
    uint32_t max_ = 0;
};

// LEDC resolution for a PWM frequency: floor(log2(80 MHz / f)), capped at 14 bits.
uint8_t pwm_resolution_bits(uint32_t freq_hz);

}  // namespace dmxnow
