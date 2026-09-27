// Pin map of the dmxnow node PCB (SPEC 4.2, hardware/gen/design.py).
#pragma once
#include <cstdint>

namespace board {
constexpr int kStatusLed = 0;     // IO0, D4 via R19 (option A7, DNP by default)
constexpr int kBoardSense = 1;    // IO1, low = strip part present (R21 to GND)
constexpr int kPwm4 = 3;          // IO3 -> U4 -> Q5 (CH4)
constexpr int kDmxTx = 4;         // IO4 -> SP3485 DI (UART1 TX)
constexpr int kRelay = 5;         // IO5 -> Q1 gate (R6 pull-down)
constexpr int kPwm1 = 6;          // IO6 -> U4 -> Q2 (CH1)
constexpr int kPwm2 = 7;          // IO7 -> U4 -> Q3 (CH2)
constexpr int kButton = 9;        // IO9, SW1 / J3-BOOT to GND, R2 pull-up (strapping pin)
constexpr int kPwm3 = 10;         // IO10 -> U4 -> Q4 (CH3)
constexpr int kPwmPins[4] = {kPwm1, kPwm2, kPwm3, kPwm4};
}  // namespace board
