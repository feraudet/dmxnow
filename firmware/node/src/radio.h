// ESP-NOW v2 radio of the node (SPEC 4.1, PROTOCOL 2): STA not associated, no power
// save, fixed channel, 6 Mbit/s for our own transmissions (HEARTBEAT, ACK).
#pragma once
#include <cstddef>
#include <cstdint>

#include "dmxnow/protocol.h"

namespace radio {

struct Packet {
    uint16_t len;
    int8_t rssi;
    uint8_t src[6];
    uint8_t data[dmxnow::kMaxPacketV2];
};

bool begin(uint8_t channel, uint16_t net_id);
void set_net_id(uint16_t net_id);      // filter used by the receive callback
bool set_channel(uint8_t channel);
uint8_t channel();
void own_mac(uint8_t mac[6]);

// Next validated packet (steps 1-8 of PROTOCOL 2.5), false if none within wait_ms.
bool receive(Packet* p, uint32_t wait_ms);
uint32_t rejected();

// dst = nullptr: broadcast.
bool send(const uint8_t* dst, const uint8_t* data, size_t len);

}  // namespace radio
