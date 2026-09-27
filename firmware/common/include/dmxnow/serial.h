// Pi <-> dongle serial link (PROTOCOL 8): logical frame = type u8, seq u8, payload,
// crc16 u16 (over type, seq, payload), COBS-encoded and terminated by 0x00.
#pragma once
#include <cstddef>
#include <cstdint>

namespace dmxnow {

namespace ser {
// Pi -> dongle
constexpr uint8_t kUniverse = 0x01, kCommand = 0x02, kDongleConfig = 0x03, kPing = 0x04, kGetStatus = 0x05;
// dongle -> Pi
constexpr uint8_t kRadioRx = 0x81, kCmdResult = 0x82, kStatus = 0x83, kPong = 0x84, kLog = 0x85;
constexpr size_t kMaxPayload = 1020;
constexpr size_t kMaxFrame = 1 + 1 + kMaxPayload + 2;
}  // namespace ser

// Builds the complete wire frame (COBS + trailing 0x00). Returns its size, 0 if it does
// not fit in out_cap.
size_t serial_encode(uint8_t type, uint8_t seq, const uint8_t* payload, size_t len, uint8_t* out, size_t out_cap);

// Byte-stream decoder: resynchronises on every 0x00. Frames with a COBS error, a length
// < 4 or a bad CRC are dropped and counted.
class SerialDecoder {
public:
    struct Frame {
        uint8_t type;
        uint8_t seq;
        const uint8_t* payload;
        size_t len;
    };
    // Returns true when a valid frame is complete (valid until the next push()).
    bool push(uint8_t byte, Frame* out);
    uint32_t errors() const { return errors_; }

private:
    uint8_t enc_[ser::kMaxFrame + ser::kMaxFrame / 254 + 2];
    uint8_t dec_[ser::kMaxFrame];
    size_t n_ = 0;
    bool overflow_ = false;
    uint32_t errors_ = 0;
};

}  // namespace dmxnow
