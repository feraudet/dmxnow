#include "dmxnow/usb_dmx.h"

namespace dmxnow {

bool UsbDmxParser::feed(uint8_t b) {
    switch (st_) {
        case St::Start:
            if (b == kStart) st_ = St::Label;
            return false;
        case St::Label:
            label_ = b;
            st_ = St::LenLo;
            return false;
        case St::LenLo:
            len_ = b;
            st_ = St::LenHi;
            return false;
        case St::LenHi:
            len_ = uint16_t(len_ | b << 8);
            pos_ = 0;
            if (label_ == kLabelSendDmx && len_ > kDmxSlots + 1) st_ = St::Start;   // oversize: resync
            else st_ = len_ ? St::Data : St::End;
            return false;
        case St::Data:
            if (label_ == kLabelSendDmx) buf_[pos_] = b;
            if (++pos_ == len_) st_ = St::End;
            return false;
        case St::End:
            st_ = St::Start;
            return b == kEnd && label_ == kLabelSendDmx && len_ >= 1 && buf_[0] == 0;
    }
    return false;
}

}  // namespace dmxnow
