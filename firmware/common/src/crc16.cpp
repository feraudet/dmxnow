#include "dmxnow/crc16.h"

namespace dmxnow {

namespace {
struct Table {
    uint16_t t[256];
    constexpr Table() : t() {
        for (int i = 0; i < 256; ++i) {
            uint16_t c = static_cast<uint16_t>(i << 8);
            for (int b = 0; b < 8; ++b) c = (c & 0x8000) ? static_cast<uint16_t>((c << 1) ^ 0x1021) : static_cast<uint16_t>(c << 1);
            t[i] = c;
        }
    }
};
constexpr Table kTable;
}  // namespace

uint16_t crc16(const uint8_t* data, size_t len, uint16_t crc) {
    for (size_t i = 0; i < len; ++i)
        crc = static_cast<uint16_t>((crc << 8) ^ kTable.t[((crc >> 8) ^ data[i]) & 0xFF]);
    return crc;
}

}  // namespace dmxnow
