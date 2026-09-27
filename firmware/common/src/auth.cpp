#include "dmxnow/auth.h"

#include <cstring>

namespace dmxnow {

namespace {
constexpr uint32_t K[64] = {
    0x428a2f98, 0x71374491, 0xb5c0fbcf, 0xe9b5dba5, 0x3956c25b, 0x59f111f1, 0x923f82a4, 0xab1c5ed5,
    0xd807aa98, 0x12835b01, 0x243185be, 0x550c7dc3, 0x72be5d74, 0x80deb1fe, 0x9bdc06a7, 0xc19bf174,
    0xe49b69c1, 0xefbe4786, 0x0fc19dc6, 0x240ca1cc, 0x2de92c6f, 0x4a7484aa, 0x5cb0a9dc, 0x76f988da,
    0x983e5152, 0xa831c66d, 0xb00327c8, 0xbf597fc7, 0xc6e00bf3, 0xd5a79147, 0x06ca6351, 0x14292967,
    0x27b70a85, 0x2e1b2138, 0x4d2c6dfc, 0x53380d13, 0x650a7354, 0x766a0abb, 0x81c2c92e, 0x92722c85,
    0xa2bfe8a1, 0xa81a664b, 0xc24b8b70, 0xc76c51a3, 0xd192e819, 0xd6990624, 0xf40e3585, 0x106aa070,
    0x19a4c116, 0x1e376c08, 0x2748774c, 0x34b0bcb5, 0x391c0cb3, 0x4ed8aa4a, 0x5b9cca4f, 0x682e6ff3,
    0x748f82ee, 0x78a5636f, 0x84c87814, 0x8cc70208, 0x90befffa, 0xa4506ceb, 0xbef9a3f7, 0xc67178f2};
inline uint32_t rotr(uint32_t x, int n) { return (x >> n) | (x << (32 - n)); }
}  // namespace

void Sha256::reset() {
    static const uint32_t init[8] = {0x6a09e667, 0xbb67ae85, 0x3c6ef372, 0xa54ff53a,
                                     0x510e527f, 0x9b05688c, 0x1f83d9ab, 0x5be0cd19};
    std::memcpy(h_, init, sizeof h_);
    len_ = 0;
    fill_ = 0;
}

void Sha256::block(const uint8_t* p) {
    uint32_t w[64];
    for (int i = 0; i < 16; ++i)
        w[i] = (uint32_t(p[4 * i]) << 24) | (uint32_t(p[4 * i + 1]) << 16) | (uint32_t(p[4 * i + 2]) << 8) | p[4 * i + 3];
    for (int i = 16; i < 64; ++i) {
        uint32_t s0 = rotr(w[i - 15], 7) ^ rotr(w[i - 15], 18) ^ (w[i - 15] >> 3);
        uint32_t s1 = rotr(w[i - 2], 17) ^ rotr(w[i - 2], 19) ^ (w[i - 2] >> 10);
        w[i] = w[i - 16] + s0 + w[i - 7] + s1;
    }
    uint32_t a = h_[0], b = h_[1], c = h_[2], d = h_[3], e = h_[4], f = h_[5], g = h_[6], h = h_[7];
    for (int i = 0; i < 64; ++i) {
        uint32_t t1 = h + (rotr(e, 6) ^ rotr(e, 11) ^ rotr(e, 25)) + ((e & f) ^ (~e & g)) + K[i] + w[i];
        uint32_t t2 = (rotr(a, 2) ^ rotr(a, 13) ^ rotr(a, 22)) + ((a & b) ^ (a & c) ^ (b & c));
        h = g; g = f; f = e; e = d + t1; d = c; c = b; b = a; a = t1 + t2;
    }
    h_[0] += a; h_[1] += b; h_[2] += c; h_[3] += d; h_[4] += e; h_[5] += f; h_[6] += g; h_[7] += h;
}

void Sha256::update(const uint8_t* d, size_t n) {
    len_ += n;
    while (n) {
        size_t k = 64 - fill_ < n ? 64 - fill_ : n;
        std::memcpy(buf_ + fill_, d, k);
        fill_ += k; d += k; n -= k;
        if (fill_ == 64) { block(buf_); fill_ = 0; }
    }
}

void Sha256::finish(uint8_t out[32]) {
    uint64_t bits = len_ * 8;
    uint8_t pad = 0x80;
    update(&pad, 1);
    uint8_t z = 0;
    while (fill_ != 56) update(&z, 1);
    uint8_t l[8];
    for (int i = 0; i < 8; ++i) l[i] = uint8_t(bits >> (56 - 8 * i));
    update(l, 8);
    for (int i = 0; i < 8; ++i)
        for (int j = 0; j < 4; ++j) out[4 * i + j] = uint8_t(h_[i] >> (24 - 8 * j));
}

void hmac_sha256(const uint8_t* key, size_t key_len, const uint8_t* const* parts, const size_t* lens,
                 size_t nparts, uint8_t out[32]) {
    uint8_t k[64] = {};
    if (key_len > 64) {
        Sha256 s;
        s.update(key, key_len);
        s.finish(k);
    } else {
        std::memcpy(k, key, key_len);
    }
    uint8_t pad[64];
    Sha256 in;
    for (int i = 0; i < 64; ++i) pad[i] = k[i] ^ 0x36;
    in.update(pad, 64);
    for (size_t i = 0; i < nparts; ++i) in.update(parts[i], lens[i]);
    uint8_t inner[32];
    in.finish(inner);
    Sha256 o;
    for (int i = 0; i < 64; ++i) pad[i] = k[i] ^ 0x5c;
    o.update(pad, 64);
    o.update(inner, 32);
    o.finish(out);
}

void auth_trailer(const uint8_t key[32], const uint8_t* header16, const uint8_t* payload, size_t payload_len,
                  uint32_t counter, uint8_t out[kAuthSize]) {
    uint8_t c[4];
    put32(c, counter);
    const uint8_t* parts[3] = {header16, payload, c};
    size_t lens[3] = {16, payload_len, 4};
    uint8_t mac[32];
    hmac_sha256(key, 32, parts, lens, 3, mac);
    std::memcpy(out, c, 4);
    std::memcpy(out + 4, mac, 8);
}

AuthResult auth_check(const uint8_t key[32], const uint8_t* pkt, size_t size, uint32_t last, uint32_t* counter_out) {
    Header h = decode_header(pkt);
    if (!(h.flags & flags::kAuth) || size != kHeaderSize + h.length + kAuthSize) return AuthResult::Missing;
    const uint8_t* tr = pkt + kHeaderSize + h.length;
    uint32_t counter = get32(tr);
    uint8_t want[kAuthSize];
    auth_trailer(key, pkt, pkt + kHeaderSize, h.length, counter, want);
    uint8_t diff = 0;   // constant time
    for (size_t i = 4; i < kAuthSize; ++i) diff |= uint8_t(want[i] ^ tr[i]);
    if (diff) return AuthResult::BadMac;
    if (counter <= last) return AuthResult::Replay;
    if (counter_out) *counter_out = counter;
    return AuthResult::Ok;
}

const uint8_t* CommandHistory::find(uint16_t id, size_t* len) const {
    for (const auto& e : e_)
        if (e.used && e.id == id) {
            *len = e.len;
            return e.ack;
        }
    return nullptr;
}

void CommandHistory::remember(uint16_t id, const uint8_t* ack, size_t len) {
    if (len > kMaxAck) len = kMaxAck;
    Entry& e = e_[next_];
    next_ = (next_ + 1) % kEntries;
    e.used = true;
    e.id = id;
    e.len = uint8_t(len);
    std::memcpy(e.ack, ack, len);
}

}  // namespace dmxnow
