#include "dmxnow/ota.h"

#include "dmxnow/show.h"   // crc32

namespace dmxnow {

AckStatus OtaSession::begin(uint32_t size, uint32_t crc32_value, uint32_t max_size) {
    active_ = false;
    if (size == 0 || size > max_size) return AckStatus::InvalidArg;
    active_ = true;
    size_ = size;
    crc_ = crc32_value;
    offset_ = 0;
    running_crc_ = 0;
    return AckStatus::Ok;
}

AckStatus OtaSession::write(uint32_t offset, const uint8_t* data, size_t len, Sink sink, void* ctx) {
    if (!active_ || len == 0 || len > kOtaWriteMax || uint64_t(offset) + len > size_) return AckStatus::InvalidArg;
    if (offset + len <= offset_) return AckStatus::Ok;   // repeated chunk: already written
    if (offset != offset_) return AckStatus::InvalidArg;   // gap or overlap: resume at next_offset()
    if (offset == 0 && data[0] != kOtaImageMagic) {
        active_ = false;
        return AckStatus::InvalidArg;
    }
    if (!sink(data, len, ctx)) {
        active_ = false;
        return AckStatus::InternalError;
    }
    running_crc_ = crc32(data, len, running_crc_);
    offset_ += uint32_t(len);
    return AckStatus::Ok;
}

AckStatus OtaSession::end(uint32_t size, uint32_t crc32_value) const {
    if (!active_ || size != size_ || crc32_value != crc_ || offset_ != size_ || running_crc_ != crc_)
        return AckStatus::InvalidArg;
    return AckStatus::Ok;
}

}  // namespace dmxnow
