#include "pwm_out.h"

#include <Arduino.h>
#include <driver/ledc.h>

#include "board.h"
#include "dmxnow/gamma.h"

namespace pwm_out {

namespace {
constexpr ledc_mode_t kMode = LEDC_LOW_SPEED_MODE;
constexpr ledc_timer_t kTimer = LEDC_TIMER_0;
uint8_t bits_ = 0;
bool ready = false;

uint32_t hpoint(uint8_t ch) { return (uint32_t(ch) << bits_) / 4; }
}  // namespace

void early_off() {
    for (int p : board::kPwmPins) {
        pinMode(p, OUTPUT);
        digitalWrite(p, LOW);
    }
}

bool begin(uint32_t freq) {
    bits_ = dmxnow::pwm_resolution_bits(freq);
    ledc_timer_config_t t = {};
    t.speed_mode = kMode;
    t.duty_resolution = ledc_timer_bit_t(bits_);
    t.timer_num = kTimer;
    t.freq_hz = freq;
    t.clk_cfg = LEDC_USE_APB_CLK;
    if (ledc_timer_config(&t) != ESP_OK) return false;
    for (uint8_t ch = 0; ch < 4; ++ch) {
        ledc_channel_config_t c = {};
        c.gpio_num = board::kPwmPins[ch];
        c.speed_mode = kMode;
        c.channel = ledc_channel_t(ch);
        c.timer_sel = kTimer;
        c.duty = 0;
        c.hpoint = int(hpoint(ch));
        if (ledc_channel_config(&c) != ESP_OK) return false;
    }
    ready = true;
    return true;
}

uint8_t bits() { return bits_; }

void set(uint8_t ch, uint32_t duty) {
    if (!ready || ch >= 4) return;
    // the pulse must end inside the period (hpoint + duty <= 2^bits): whether the LEDC
    // wraps a pulse past the counter overflow is not documented. The start moves back
    // just enough; the phase shift is kept whenever it fits, the duty never changes.
    uint32_t period = 1u << bits_;
    if (duty > period) duty = period;
    uint32_t hp = hpoint(ch);
    if (hp + duty > period) hp = period - duty;
    ledc_set_duty_with_hpoint(kMode, ledc_channel_t(ch), duty, hp);
    ledc_update_duty(kMode, ledc_channel_t(ch));
}

void all_off() {
    for (uint8_t ch = 0; ch < 4; ++ch) set(ch, 0);
}

}  // namespace pwm_out
