// CRC-16/CCITT-FALSE (poly 0x1021, init 0xFFFF, no reflection, no final XOR).
// Check value on "123456789": 0x29B1. PROTOCOL §2.4.
#pragma once
#include <cstddef>
#include <cstdint>

namespace dmxnow {

uint16_t crc16(const uint8_t* data, size_t len, uint16_t crc = 0xFFFF);

}  // namespace dmxnow
