// LED strip PWM on the LEDC (SPEC 4.6, 4.7, EF-09): 4 channels, one timer, resolution
// deduced from the frequency (14 bits at 4882 Hz), channels shifted by a quarter of a
// period (hpoint) to spread the current pulses drawn from C7.
#pragma once
#include <cstdint>

namespace pwm_out {

// First instructions of the firmware: the 4 PWM pins driven low as plain GPIOs.
void early_off();
bool begin(uint32_t freq_hz);          // false if the LEDC refuses the frequency
uint8_t bits();
void set(uint8_t channel, uint32_t duty);
void all_off();

}  // namespace pwm_out
