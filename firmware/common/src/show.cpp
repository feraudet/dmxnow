#include "dmxnow/show.h"

#include <cstring>

#include "dmxnow/protocol.h"

namespace dmxnow {

namespace {
struct Table {
    uint32_t t[256];
    constexpr Table() : t() {
        for (uint32_t i = 0; i < 256; ++i) {
            uint32_t c = i;
            for (int b = 0; b < 8; ++b) c = (c & 1) ? (c >> 1) ^ 0xEDB88320u : c >> 1;
            t[i] = c;
        }
    }
};
constexpr Table kTable;
}  // namespace

uint32_t crc32(const uint8_t* data, size_t len, uint32_t crc) {
    crc = ~crc;
    for (size_t i = 0; i < len; ++i) crc = (crc >> 8) ^ kTable.t[(crc ^ data[i]) & 0xFF];
    return ~crc;
}

// Layout (PROTOCOL §10.1): magic 4, name 16, channels u16 (was channels u8 + flags u8 at 0,
// so the older files read the same), resume_s u16,
// steps u32, channel slots u16 x n, steps (duration_ms u16, values u8 x n) x steps, crc32.
bool show_parse(const uint8_t* d, size_t cap, ShowInfo* info) {
    if (cap < kShowHeaderSize || std::memcmp(d, kShowMagic, 4) != 0) return false;
    uint16_t n = get16(d + 20);
    uint16_t resume_s = get16(d + 22);
    uint32_t steps = get32(d + 24);
    if (n == 0 || n > kShowMaxChannels || resume_s == 0 || resume_s > 3600 || steps == 0) return false;
    uint64_t size = uint64_t(kShowHeaderSize) + 2u * n + uint64_t(steps) * (2u + n) + 4u;
    if (size > cap) return false;
    for (uint16_t c = 0; c < n; ++c) {
        uint16_t s = get16(d + kShowHeaderSize + 2 * c);
        bool ok = (s & kShowRelative) ? (s & ~kShowRelative) < kDmxSlots : (s >= 1 && s <= kDmxSlots);
        if (!ok) return false;
    }
    if (crc32(d, size_t(size) - 4) != get32(d + size - 4)) return false;
    uint32_t loop_ms = 0;
    const uint8_t* p = d + kShowHeaderSize + 2 * n;
    for (uint32_t i = 0; i < steps; ++i, p += 2 + n) loop_ms += get16(p);
    if (loop_ms == 0) return false;
    if (info) {
        std::memset(info->name, 0, sizeof info->name);
        std::memcpy(info->name, d + 4, 16);
        info->channels = n;
        info->resume_s = resume_s;
        info->steps = steps;
        info->size = uint32_t(size);
        info->crc = get32(d + size - 4);
        info->loop_ms = loop_ms;
    }
    return true;
}

bool ShowPlayer::load(const uint8_t* data, size_t cap) {
    data_ = show_parse(data, cap, &info_) ? data : nullptr;
    cur_ = 0;
    seg_start_ = 0;
    return data_ != nullptr;
}

const uint8_t* ShowPlayer::step(uint32_t i) const {
    return data_ + kShowHeaderSize + 2 * info_.channels + size_t(i) * (2 + info_.channels);
}

uint16_t ShowPlayer::duration(uint32_t i) const { return get16(step(i)); }

void ShowPlayer::restart(uint32_t now_ms) {
    cur_ = 0;
    seg_start_ = now_ms;
}

void ShowPlayer::render(uint32_t now, uint16_t start_address, uint8_t* frame) {
    if (!data_) return;
    // keyframe i is reached duration(i) ms after keyframe i - 1; after the last one the
    // show goes back to keyframe 0 (with duration(0)). Past a whole loop late (the loop
    // was stalled), start again from keyframe 0 rather than catching up.
    uint32_t next = (cur_ + 1) % info_.steps;
    uint32_t guard = 0;
    while (now - seg_start_ >= duration(next)) {
        if (++guard > info_.steps) { restart(now); next = 1 % info_.steps; break; }
        seg_start_ += duration(next);
        cur_ = next;
        next = (cur_ + 1) % info_.steps;
    }
    uint32_t d = duration(next), el = now - seg_start_;
    const uint8_t* a = step(cur_) + 2;
    const uint8_t* b = step(next) + 2;
    const uint8_t* slots = data_ + kShowHeaderSize;
    for (uint16_t c = 0; c < info_.channels; ++c) {
        uint16_t s = get16(slots + 2 * c);
        uint32_t idx = (s & kShowRelative) ? uint32_t(start_address) - 1 + (s & ~kShowRelative) : uint32_t(s) - 1;
        if (idx >= kDmxSlots) continue;
        uint32_t v = d ? (uint32_t(a[c]) * (d - el) + uint32_t(b[c]) * el + d / 2) / d : b[c];
        frame[idx] = uint8_t(v);
    }
}

}  // namespace dmxnow
