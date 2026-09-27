// DMX-side logic: fragment reassembly (PROTOCOL §4.2), loss counting (§4.3) and the
// "event + minimum refresh" output cadence (§4.4), shared by the node and the dongle.
#pragma once
#include <cstddef>
#include <cstdint>

#include "dmxnow/protocol.h"

namespace dmxnow {

// Wrap-safe millisecond comparisons (uint32_t millis() wraps after 49.7 days).
inline bool time_reached(uint32_t now, uint32_t deadline) { return int32_t(now - deadline) >= 0; }

class Reassembler {
public:
    enum class Result : uint8_t {
        None,       // nothing new to output (duplicate, or fragment waiting for LAST)
        Complete,   // full frame: every channel of this seq received
        Partial,    // frame published with missing fragments merged from the previous one
    };

    // Feeds one validated DMX_DATA packet (header fields + channel data).
    Result feed(uint16_t seq, uint16_t offset, uint16_t length, uint8_t flags, const uint8_t* data);

    const uint8_t* frame() const { return frame_; }
    uint16_t frame_len() const { return frame_len_; }   // channels beyond are 0

private:
    void mark(uint16_t off, uint16_t len);
    bool all_marked(uint16_t len) const;
    void start(uint16_t seq);

    uint8_t frame_[kDmxSlots] = {};
    uint16_t frame_len_ = 0;
    uint8_t got_[kDmxSlots / 8] = {};   // channels received for the current seq
    bool active_ = false;               // a fragmented seq is being assembled
    bool published_ = false;            // current seq already output as Complete
    bool pending_ = false;              // fragments applied but not output yet
    uint16_t seq_ = 0;
    uint16_t total_ = 0;                // from LAST: offset + length (0 = unknown)
};

class LossCounter {
public:
    void on_frame(uint16_t seq);
    uint32_t rx_frames() const { return rx_; }
    uint32_t lost_frames() const { return lost_; }

private:
    bool has_last_ = false;
    uint16_t last_ = 0;
    uint32_t rx_ = 0;
    uint32_t lost_ = 0;
};

// Emission on new data (at most one per min_interval, data arriving meanwhile is
// merged and sent at the deadline) and repetition every refresh period otherwise.
class OutputCadence {
public:
    explicit OutputCadence(uint32_t min_interval_ms = 10, uint32_t refresh_us = 22727)
        : min_ms_(min_interval_ms), refresh_us_(refresh_us) {}
    void set_refresh_hz(uint32_t hz) { refresh_us_ = hz ? 1000000u / hz : 22727; }
    void on_new_data() { dirty_ = true; }
    // now in microseconds
    bool due(uint32_t now_us) const;
    void sent(uint32_t now_us) { last_us_ = now_us; dirty_ = false; started_ = true; }
    bool dirty() const { return dirty_; }

private:
    uint32_t min_ms_;
    uint32_t refresh_us_;
    uint32_t last_us_ = 0;
    bool dirty_ = false;
    bool started_ = false;
};

// DMX512 frame duration for n slots (break 176 us + MAB 12 us + (n + 1) x 44 us).
constexpr uint32_t dmx_frame_us(uint16_t slots) { return 176 + 12 + (uint32_t(slots) + 1) * 44; }

}  // namespace dmxnow
