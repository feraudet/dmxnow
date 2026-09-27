// dmxnow radio protocol v1: common header, message types, validation (PROTOCOL §2-§6).
// All multi-byte integers are little-endian; structures are serialised byte by byte
// (never memcpy'd), so the code is independent of the host endianness and alignment.
#pragma once
#include <cstddef>
#include <cstdint>

namespace dmxnow {

constexpr uint16_t kMagic = 0x4E44;           // 'D','N' on the wire
constexpr uint8_t kVersion = 1;
constexpr size_t kHeaderSize = 18;
constexpr size_t kAuthSize = 12;              // counter u32 + mac8
constexpr size_t kMaxPacketV2 = 1470;         // ESP_NOW_MAX_DATA_LEN_V2 (IDF >= 5.4.2)
constexpr size_t kMaxPacketV1 = 250;
constexpr size_t kMaxFragPayload = kMaxPacketV1 - kHeaderSize;   // 232
constexpr uint16_t kDmxSlots = 512;
constexpr uint16_t kNoUniverse = 0xFFFF;
constexpr uint16_t kMaxUniverse = 32767;

enum class MsgType : uint8_t {
    DmxData = 0x01,
    Command = 0x10,
    Ack = 0x11,
    Heartbeat = 0x20,
    Beacon = 0x30,
};

namespace flags {
constexpr uint8_t kLast = 0x01;
constexpr uint8_t kFrag = 0x02;
constexpr uint8_t kAuth = 0x04;
}  // namespace flags

struct Header {
    uint16_t magic = kMagic;
    uint8_t version = kVersion;
    uint8_t type = 0;
    uint16_t net_id = 0;
    uint16_t universe = kNoUniverse;
    uint16_t seq = 0;
    uint16_t offset = 0;
    uint16_t length = 0;
    uint8_t flags = 0;
    uint8_t reserved = 0;
    uint16_t crc16 = 0;
};

// Little-endian helpers.
inline void put16(uint8_t* p, uint16_t v) { p[0] = uint8_t(v); p[1] = uint8_t(v >> 8); }
inline void put32(uint8_t* p, uint32_t v) { for (int i = 0; i < 4; ++i) p[i] = uint8_t(v >> (8 * i)); }
inline uint16_t get16(const uint8_t* p) { return uint16_t(p[0] | (p[1] << 8)); }
inline uint32_t get32(const uint8_t* p) {
    return uint32_t(p[0]) | (uint32_t(p[1]) << 8) | (uint32_t(p[2]) << 16) | (uint32_t(p[3]) << 24);
}

void encode_header(const Header& h, uint8_t* out);   // writes 18 bytes (crc field as given)
Header decode_header(const uint8_t* in);             // reads 18 bytes

// CRC of a complete packet: header bytes 0..15, then everything after the header.
uint16_t packet_crc(const uint8_t* pkt, size_t size);

// Builds header + payload (+ optional 12-byte auth trailer, already computed) into out
// and fills length, flags.AUTH and crc16. Returns the packet size, 0 if it does not fit.
size_t build_packet(Header h, const uint8_t* payload, size_t payload_len, const uint8_t* auth_trailer,
                    uint8_t* out, size_t out_cap);

enum class Reject : uint8_t {
    None = 0,
    TooShort,     // 1. size < 18
    Magic,        // 2.
    Version,      // 3.
    NetId,        // 4.
    Length,       // 5. size != 18 + length (+12)
    Crc,          // 6.
    Type,         // 7. unknown type
    TypeCheck,    // 8. type-specific checks
};

const char* reject_name(Reject r);

// Validation in the order of PROTOCOL §2.5, steps 1 to 8 (authentication, step 9, is
// done by the command handler). my_net_id = 0: unconfigured node, accepts COMMAND and
// BEACON of any network (enrolment), never DMX_DATA.
Reject validate(const uint8_t* pkt, size_t size, uint16_t my_net_id, Header* out = nullptr);

// --- Payloads -------------------------------------------------------------------
constexpr size_t kHeartbeatPayload = 56;
constexpr size_t kBeaconPayload = 8;
constexpr size_t kCommandMinPayload = 7;
constexpr size_t kAckMinPayload = 2;

struct Heartbeat {
    uint8_t mac[6] = {};
    char name[16] = {};               // UTF-8, zero padded (not necessarily terminated)
    uint16_t start_address = 1;
    uint8_t fw_version[3] = {};
    uint8_t variant = 1;              // 1 fixture only, 2 fixture + strips
    uint8_t relay = 0;                // bit0 contact, bit1 forced, bit2 pending
    uint32_t relay_switch_count = 0;
    int8_t rssi = 0;
    uint32_t rx_frames = 0;
    uint32_t lost_frames = 0;
    uint32_t rejected_frames = 0;
    uint32_t uptime_s = 0;
    uint8_t status = 0;               // bit0 DMX, bit1 blackout, bit2 maint, bit3 identify, bit4 dongle known
    uint8_t radio_channel = 6;
    uint16_t dmx_out_slots = 512;
    uint8_t reset_reason = 0;
};
void encode_heartbeat(const Heartbeat& hb, uint8_t* out);            // 56 bytes
bool decode_heartbeat(const uint8_t* in, size_t len, Heartbeat* hb);

namespace hb_status {
constexpr uint8_t kDmx = 0x01, kBlackout = 0x02, kMaintenance = 0x04, kIdentify = 0x08, kDongleKnown = 0x10;
}

struct Beacon {
    uint8_t fw_version[3] = {};
    uint8_t active_universes = 0;
    uint32_t uptime_s = 0;
};
void encode_beacon(const Beacon& b, uint8_t* out);                    // 8 bytes
bool decode_beacon(const uint8_t* in, size_t len, Beacon* b);

enum class Opcode : uint8_t {
    Identify = 0x01,
    SetConfig = 0x02,
    GetConfig = 0x03,
    Relay = 0x04,
    Maintenance = 0x05,
    Reboot = 0x06,
    FactoryReset = 0x07,
};
constexpr uint32_t kFactoryResetConfirm = 0x52455345;   // "RESE"

enum class AckStatus : uint8_t {
    Ok = 0,
    UnknownOpcode = 1,
    InvalidArg = 2,
    AuthFailed = 3,
    Unsupported = 4,
    InternalError = 5,
};

struct CommandView {           // points into the received packet
    const uint8_t* target = nullptr;   // 6 bytes
    uint8_t opcode = 0;
    const uint8_t* args = nullptr;
    size_t args_len = 0;
};
bool parse_command(const uint8_t* payload, size_t len, CommandView* cmd);
bool mac_is_broadcast(const uint8_t* mac);

}  // namespace dmxnow
