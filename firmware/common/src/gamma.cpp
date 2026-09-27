#include "dmxnow/gamma.h"

#include <cmath>

namespace dmxnow {

void GammaTable::build(uint8_t gamma_x10, uint8_t bits) {
    max_ = (1u << bits) - 1;
    double g = gamma_x10 / 10.0;
    auto curve = [&](double x) -> uint32_t {
        double y = (g == 1.0) ? x : std::pow(x, g);
        uint32_t d = uint32_t(std::lround(y * max_));
        return d > max_ ? max_ : d;
    };
    for (int i = 0; i < 256; ++i) t8_[i] = curve(i / 255.0);
    for (int i = 0; i <= 256; ++i) t16_[i] = curve(i / 256.0);
    // pow() and rounding keep the curve monotonic; enforce it anyway
    for (int i = 1; i < 256; ++i) if (t8_[i] < t8_[i - 1]) t8_[i] = t8_[i - 1];
    for (int i = 1; i <= 256; ++i) if (t16_[i] < t16_[i - 1]) t16_[i] = t16_[i - 1];
}

uint32_t GammaTable::lookup16(uint16_t v) const {
    // 65535 maps onto point 256; 256 segments of 256 codes (the last one 255 codes)
    if (v == 0xFFFF) return t16_[256];
    uint32_t i = v >> 8, frac = v & 0xFF;
    return t16_[i] + ((t16_[i + 1] - t16_[i]) * frac + 128) / 256;
}

uint8_t pwm_resolution_bits(uint32_t f) {
    uint8_t b = 0;
    while (b < 14 && (80000000u >> (b + 1)) >= f) ++b;
    return b;
}

}  // namespace dmxnow
