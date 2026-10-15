// Firmware update over the radio (PROTOCOL §11, SPEC §4.14). Pure logic: the node gives
// a sink that writes into the next OTA slot (Arduino Update). Chunks must arrive in order;
// a repeated chunk (lost ACK, retry) is acknowledged without being written twice, a gap is
// refused. Every ACK carries the next expected offset, so the sender can resume.
#pragma once
#include <cstddef>
#include <cstdint>

#include "dmxnow/protocol.h"

namespace dmxnow {

constexpr size_t kOtaWriteMax = kShowWriteMax;   // data bytes per OTA_WRITE
constexpr uint8_t kOtaImageMagic = 0xE9;         // first byte of an ESP32 app image

class OtaSession {
public:
    using Sink = bool (*)(const uint8_t* data, size_t len, void* ctx);

    // New upload: max_size is the size of the OTA slot. Restarts any upload in progress.
    AckStatus begin(uint32_t size, uint32_t crc32, uint32_t max_size);
    AckStatus write(uint32_t offset, const uint8_t* data, size_t len, Sink sink, void* ctx);
    // All bytes received and the CRC matches: the caller then finalises the image.
    AckStatus end(uint32_t size, uint32_t crc32) const;
    void abort() { active_ = false; }

    bool active() const { return active_; }
    uint32_t next_offset() const { return offset_; }

private:
    bool active_ = false;
    uint32_t size_ = 0, crc_ = 0, offset_ = 0, running_crc_ = 0;
};

}  // namespace dmxnow
