// Consistent Overhead Byte Stuffing (PROTOCOL §8.2, ADR 0012). The encoder does not
// append the 0x00 delimiter; the caller does.
#pragma once
#include <cstddef>
#include <cstdint>

namespace dmxnow {

constexpr size_t cobs_max_encoded(size_t n) { return n + n / 254 + 1; }

// Returns the encoded size, 0 if out_cap is too small.
size_t cobs_encode(const uint8_t* in, size_t len, uint8_t* out, size_t out_cap);
// Returns the decoded size, or -1 on malformed input (zero byte, truncated block,
// output overflow).
long cobs_decode(const uint8_t* in, size_t len, uint8_t* out, size_t out_cap);

}  // namespace dmxnow
