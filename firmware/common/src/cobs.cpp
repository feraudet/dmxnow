#include "dmxnow/cobs.h"

namespace dmxnow {

size_t cobs_encode(const uint8_t* in, size_t len, uint8_t* out, size_t cap) {
    if (cap < cobs_max_encoded(len)) return 0;
    size_t code_pos = 0, o = 1;
    uint8_t code = 1;
    for (size_t i = 0; i < len; ++i) {
        if (in[i] == 0) {
            out[code_pos] = code;
            code_pos = o++;
            code = 1;
        } else {
            out[o++] = in[i];
            if (++code == 0xFF) {   // full block: a new one only if data remains
                out[code_pos] = code;
                if (i + 1 == len) return o;
                code_pos = o++;
                code = 1;
            }
        }
    }
    out[code_pos] = code;
    return o;
}

long cobs_decode(const uint8_t* in, size_t len, uint8_t* out, size_t cap) {
    size_t i = 0, o = 0;
    while (i < len) {
        uint8_t code = in[i++];
        if (code == 0) return -1;
        for (uint8_t k = 1; k < code; ++k) {
            if (i >= len || in[i] == 0 || o >= cap) return -1;
            out[o++] = in[i++];
        }
        if (code != 0xFF && i < len) {
            if (o >= cap) return -1;
            out[o++] = 0;
        }
    }
    return long(o);
}

}  // namespace dmxnow
