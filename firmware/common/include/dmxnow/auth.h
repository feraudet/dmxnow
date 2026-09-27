// Command authentication (PROTOCOL §7) and command idempotence (§6.2).
#pragma once
#include <cstddef>
#include <cstdint>

#include "dmxnow/protocol.h"

namespace dmxnow {

// Portable SHA-256 / HMAC-SHA256 (FIPS 180-4, RFC 2104): same code on the host tests
// and the ESP32, no dependency on mbedTLS.
class Sha256 {
public:
    Sha256() { reset(); }
    void reset();
    void update(const uint8_t* d, size_t n);
    void finish(uint8_t out[32]);

private:
    void block(const uint8_t* p);
    uint32_t h_[8];
    uint8_t buf_[64];
    uint64_t len_ = 0;
    size_t fill_ = 0;
};

void hmac_sha256(const uint8_t* key, size_t key_len, const uint8_t* const* parts, const size_t* lens,
                 size_t nparts, uint8_t out[32]);

// Trailer = counter u32 LE + first 8 bytes of HMAC(net_key, header[0..15] || payload || counter).
void auth_trailer(const uint8_t key[32], const uint8_t* header16, const uint8_t* payload, size_t payload_len,
                  uint32_t counter, uint8_t out[kAuthSize]);

// Checks the trailer of a validated COMMAND packet and the anti-replay counter.
enum class AuthResult : uint8_t { Ok, Missing, BadMac, Replay };
AuthResult auth_check(const uint8_t key[32], const uint8_t* pkt, size_t size, uint32_t last_counter,
                      uint32_t* counter_out);

// Last 16 command ids with the ACK payload sent, so that a repeated COMMAND is not
// executed twice but acknowledged again with the stored answer.
class CommandHistory {
public:
    static constexpr size_t kEntries = 16;
    static constexpr size_t kMaxAck = 200;

    // Returns the stored ACK payload for cmd_id, or nullptr.
    const uint8_t* find(uint16_t cmd_id, size_t* len) const;
    void remember(uint16_t cmd_id, const uint8_t* ack, size_t len);

private:
    struct Entry {
        bool used = false;
        uint16_t id = 0;
        uint8_t len = 0;
        uint8_t ack[kMaxAck] = {};
    };
    Entry e_[kEntries];
    size_t next_ = 0;
};

}  // namespace dmxnow
