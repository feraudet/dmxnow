// Stored show ("conduite", PROTOCOL §10): a list of keyframes played in a loop, with a
// linear fade from one keyframe to the next. The node renders it into its DMX frame
// when no DMX stream arrives (SPEC 4.13, ADR 0016).
#pragma once
#include <cstddef>
#include <cstdint>

namespace dmxnow {

constexpr uint8_t kShowMagic[4] = {'D', 'X', 'S', 1};
constexpr size_t kShowHeaderSize = 28;
constexpr uint16_t kShowMaxChannels = 512;   // a whole universe (100-pixel strip: 300)
constexpr uint16_t kShowRelative = 0x8000;   // channel bit 15: offset from start_address

// CRC-32 (IEEE 802.3, zlib.crc32): poly 0xEDB88320 reflected, init and final XOR 0xFFFFFFFF.
// Check value on "123456789": 0xCBF43926. Chains like zlib: crc32(b, crc32(a)).
uint32_t crc32(const uint8_t* data, size_t len, uint32_t crc = 0);

struct ShowInfo {
    char name[17] = {};
    uint16_t channels = 0;
    uint16_t resume_s = 0;
    uint32_t steps = 0;
    uint32_t size = 0;       // whole file, CRC included
    uint32_t crc = 0;
    uint32_t loop_ms = 0;    // sum of the step durations
};

// Checks the magic, the sizes against cap (bytes readable at data), the channel slots,
// the CRC-32 and a loop length > 0. The file size comes from the header.
bool show_parse(const uint8_t* data, size_t cap, ShowInfo* info);

class ShowPlayer {
public:
    // show_parse, then keeps the pointer (the data must stay readable: flash mapping).
    bool load(const uint8_t* data, size_t cap);
    void unload() { data_ = nullptr; }
    bool loaded() const { return data_ != nullptr; }
    const ShowInfo& info() const { return info_; }

    void restart(uint32_t now_ms);   // back to keyframe 0
    // Writes the show channels into frame (512 slots); the other slots are left as they
    // are. A channel that falls outside the universe is skipped.
    void render(uint32_t now_ms, uint16_t start_address, uint8_t* frame);

private:
    const uint8_t* step(uint32_t i) const;
    uint16_t duration(uint32_t i) const;

    const uint8_t* data_ = nullptr;
    ShowInfo info_;
    uint32_t cur_ = 0;        // last keyframe reached
    uint32_t seg_start_ = 0;  // when it was reached
};

}  // namespace dmxnow
