// DMX frames received on the node's USB port, without radio (bench test, node off mains,
// powered through J3-5V). Format of the Enttec DMX USB Pro "Output Only Send DMX Packet"
// request (label 6): 0x7E, label, length LSB, length MSB, start code + slots, 0xE7.
// Pure logic: the caller feeds the bytes read from Serial. Other labels are skipped.
#pragma once
#include <cstdint>

#include "dmxnow/protocol.h"

namespace dmxnow {

class UsbDmxParser {
public:
    static constexpr uint8_t kStart = 0x7E, kEnd = 0xE7, kLabelSendDmx = 6;

    // One byte from the USB port. True when a complete frame with start code 0 is ready.
    bool feed(uint8_t b);
    const uint8_t* slots() const { return buf_ + 1; }
    uint16_t slot_count() const { return uint16_t(len_ - 1); }

private:
    enum class St : uint8_t { Start, Label, LenLo, LenHi, Data, End };
    St st_ = St::Start;
    uint8_t label_ = 0;
    uint16_t len_ = 0, pos_ = 0;
    uint8_t buf_[kDmxSlots + 1] = {};
};

}  // namespace dmxnow
