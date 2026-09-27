#include "dmxnow/dmx.h"

#include <cstring>

namespace dmxnow {

void Reassembler::mark(uint16_t off, uint16_t len) {
    for (uint16_t i = off; i < off + len && i < kDmxSlots; ++i) got_[i >> 3] |= uint8_t(1u << (i & 7));
}

bool Reassembler::all_marked(uint16_t len) const {
    for (uint16_t i = 0; i < len; ++i)
        if (!(got_[i >> 3] & (1u << (i & 7)))) return false;
    return true;
}

void Reassembler::start(uint16_t seq) {
    std::memset(got_, 0, sizeof got_);
    active_ = true;
    published_ = false;
    pending_ = false;
    seq_ = seq;
    total_ = 0;
}

Reassembler::Result Reassembler::feed(uint16_t seq, uint16_t offset, uint16_t length, uint8_t fl,
                                      const uint8_t* data) {
    if (uint32_t(offset) + length > kDmxSlots || length == 0) return Result::None;
    if (!(fl & flags::kFrag)) {
        // v2: the whole universe in one packet, channels beyond `length` are 0
        std::memcpy(frame_, data, length);
        std::memset(frame_ + length, 0, kDmxSlots - length);
        frame_len_ = length;
        active_ = false;
        return Result::Complete;
    }
    Result out = Result::None;
    if (!active_ || seq != seq_) {
        // a new seq: the previous incomplete frame is merged (its fragments are already
        // in frame_) and output if it never was
        if (active_ && pending_) out = Result::Partial;
        start(seq);
    } else if (published_) {
        return Result::None;   // late duplicate of a completed seq
    }
    bool dup = true;
    for (uint16_t i = offset; i < offset + length; ++i)
        if (!(got_[i >> 3] & (1u << (i & 7)))) { dup = false; break; }
    if (dup && !(fl & flags::kLast)) return out;
    std::memcpy(frame_ + offset, data, length);
    mark(offset, length);
    pending_ = true;
    if (fl & flags::kLast) total_ = uint16_t(offset + length);
    if (total_) {
        if (total_ < kDmxSlots) std::memset(frame_ + total_, 0, kDmxSlots - total_);
        frame_len_ = total_;
        if (all_marked(total_)) {
            published_ = true;
            pending_ = false;
            return Result::Complete;
        }
        if (fl & flags::kLast) {   // LAST arrived with holes: partial merge now
            pending_ = false;
            return Result::Partial;
        }
    }
    return out;
}

void LossCounter::on_frame(uint16_t seq) {
    if (has_last_ && seq == last_) return;   // same frame output twice (fragment merge)
    ++rx_;
    if (has_last_) {
        uint16_t gap = uint16_t(seq - last_ - 1);
        if (gap < 1000) lost_ += gap;   // else: dongle restarted: resynchronise
    }
    has_last_ = true;
    last_ = seq;
}

bool OutputCadence::due(uint32_t now) const {
    if (!started_) return dirty_;
    uint32_t since = now - last_us_;
    if (dirty_) return since >= min_ms_ * 1000u;
    return since >= refresh_us_;
}

}  // namespace dmxnow
