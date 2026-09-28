#include "dmx_out.h"

#include <Arduino.h>
#include <driver/uart.h>
#include <esp_rom_sys.h>

#include <cstring>

#include "board.h"
#include "dmxnow/dmx.h"

namespace dmx_out {

namespace {
constexpr uart_port_t kUart = UART_NUM_1;
constexpr uint32_t kBreakUs = 176;
constexpr uint32_t kMabUs = 12;

portMUX_TYPE mux = portMUX_INITIALIZER_UNLOCKED;
uint8_t shared[dmxnow::kDmxSlots] = {};   // written by the control task
uint16_t shared_len = 0;
uint16_t slots_ = 512;
uint16_t override_slot = 0;
uint8_t override_value = 0;
bool blackout = false;
volatile bool fresh = false;
TaskHandle_t task = nullptr;
uint32_t sent = 0;

void send_frame(const uint8_t* slots, uint16_t n) {
    static uint8_t tx[1 + dmxnow::kDmxSlots];
    tx[0] = 0;   // start code
    std::memcpy(tx + 1, slots, n);
    uart_set_line_inverse(kUart, UART_SIGNAL_TXD_INV);   // break
    esp_rom_delay_us(kBreakUs);
    uart_set_line_inverse(kUart, 0);                     // mark after break
    esp_rom_delay_us(kMabUs);
    uart_write_bytes(kUart, tx, 1 + n);
    ++sent;
}

void run(void*) {
    dmxnow::OutputCadence cadence(10, 22727);
    uint8_t frame[dmxnow::kDmxSlots];
    for (;;) {
        // wake on new data, or every tick (1 ms) to hold the 1/44 s refresh deadline
        ulTaskNotifyTake(pdTRUE, 1);
        if (fresh) {
            fresh = false;
            cadence.on_new_data();
        }
        if (!cadence.due(micros())) continue;
        // wait for the end of the frame on the line first, then take the latest data:
        // data arriving during a 22.7 ms frame go out in the very next one (SPEC 5.1)
        uart_wait_tx_done(kUart, pdMS_TO_TICKS(40));
        if (fresh) {
            fresh = false;
            cadence.on_new_data();
        }
        uint16_t n;
        portENTER_CRITICAL(&mux);
        std::memcpy(frame, shared, sizeof frame);
        n = slots_;
        if (blackout) std::memset(frame, 0, sizeof frame);
        if (override_slot >= 1 && override_slot <= dmxnow::kDmxSlots) frame[override_slot - 1] = override_value;
        portEXIT_CRITICAL(&mux);
        cadence.sent(micros());
        send_frame(frame, n);
    }
}
}  // namespace

void begin(uint16_t slots) {
    slots_ = slots;
    uart_config_t cfg = {};
    cfg.baud_rate = 250000;
    cfg.data_bits = UART_DATA_8_BITS;
    cfg.parity = UART_PARITY_DISABLE;
    cfg.stop_bits = UART_STOP_BITS_2;
    cfg.flow_ctrl = UART_HW_FLOWCTRL_DISABLE;
    cfg.source_clk = UART_SCLK_DEFAULT;
    uart_driver_install(kUart, 256, 1024, 0, nullptr, 0);   // TX ring holds a whole frame
    uart_param_config(kUart, &cfg);
    uart_set_pin(kUart, board::kDmxTx, UART_PIN_NO_CHANGE, UART_PIN_NO_CHANGE, UART_PIN_NO_CHANGE);
    xTaskCreate(run, "dmx_out", 3072, nullptr, configMAX_PRIORITIES - 2, &task);
}

void set_slots(uint16_t slots) {
    portENTER_CRITICAL(&mux);
    slots_ = slots;
    portEXIT_CRITICAL(&mux);
}

void set_frame(const uint8_t* data, uint16_t len) {
    portENTER_CRITICAL(&mux);
    std::memcpy(shared, data, len);
    std::memset(shared + len, 0, dmxnow::kDmxSlots - len);
    shared_len = len;
    portEXIT_CRITICAL(&mux);
    fresh = true;
    if (task) xTaskNotifyGive(task);
}

void set_override(uint16_t slot, uint8_t value) {
    portENTER_CRITICAL(&mux);
    override_slot = slot;
    override_value = value;
    portEXIT_CRITICAL(&mux);
    fresh = true;
    if (task) xTaskNotifyGive(task);
}

void set_blackout(bool on) {
    portENTER_CRITICAL(&mux);
    bool changed = blackout != on;
    blackout = on;
    portEXIT_CRITICAL(&mux);
    if (changed) {
        fresh = true;
        if (task) xTaskNotifyGive(task);
    }
}

uint32_t frames_sent() { return sent; }

}  // namespace dmx_out
