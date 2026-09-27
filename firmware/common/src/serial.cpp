#include "dmxnow/serial.h"

#include <cstring>

#include "dmxnow/cobs.h"
#include "dmxnow/crc16.h"
#include "dmxnow/protocol.h"

namespace dmxnow {

size_t serial_encode(uint8_t type, uint8_t seq, const uint8_t* payload, size_t len, uint8_t* out, size_t cap) {
    if (len > ser::kMaxPayload) return 0;
    uint8_t raw[ser::kMaxFrame];
    raw[0] = type;
    raw[1] = seq;
    if (len) std::memcpy(raw + 2, payload, len);
    put16(raw + 2 + len, crc16(raw, 2 + len));
    size_t n = cobs_encode(raw, 4 + len, out, cap);
    if (!n || n + 1 > cap) return 0;
    out[n] = 0;
    return n + 1;
}

bool SerialDecoder::push(uint8_t b, Frame* f) {
    if (b != 0) {
        if (n_ < sizeof enc_) enc_[n_++] = b;
        else overflow_ = true;
        return false;
    }
    size_t n = n_;
    bool overflow = overflow_;
    n_ = 0;
    overflow_ = false;
    if (n == 0) return false;   // empty frame: idle delimiters
    long m = overflow ? -1 : cobs_decode(enc_, n, dec_, sizeof dec_);
    if (m < 4 || crc16(dec_, size_t(m) - 2) != get16(dec_ + m - 2)) {
        ++errors_;
        return false;
    }
    f->type = dec_[0];
    f->seq = dec_[1];
    f->payload = dec_ + 2;
    f->len = size_t(m) - 4;
    return true;
}

}  // namespace dmxnow
