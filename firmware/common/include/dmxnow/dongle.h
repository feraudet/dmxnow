// Dongle logic (SPEC 4.10, PROTOCOL 4.4, 6.2, 8): universe table with the "event +
// refresh" cadence and hold_timeout, command tracking with retransmissions, and the
// transmission scheduler (COMMAND > DMX_DATA > BEACON, one packet at a time).
// Pure logic, clocked by the caller: natively testable.
#pragma once
#include <cstddef>
#include <cstdint>

#include "dmxnow/dmx.h"
#include "dmxnow/protocol.h"

namespace dmxnow {

struct DongleSettings {
    uint8_t channel = 6;
    uint16_t net_id = 0;
    uint8_t phy_rate = 0x0B;          // wifi_phy_rate_t: WIFI_PHY_RATE_6M
    uint8_t power_dbm = 15;
    uint32_t hold_timeout_ms = 10000;
    uint8_t refresh_hz = 44;
    uint8_t mode = 0;                 // 0 = ESP-NOW v2 single packet, 1 = fragmented v1
};

// DONGLE_CONFIG TLV (PROTOCOL 8.3): applied atomically, false on an invalid item.
bool apply_dongle_config(const uint8_t* tlv, size_t len, DongleSettings* s);

// Validation on the dongle: packets of its network, plus HEARTBEATs of unconfigured
// nodes (net_id 0) so that the Pi can enrol them.
Reject validate_dongle(const uint8_t* pkt, size_t size, uint16_t my_net_id, Header* out = nullptr);

class UniverseTable {
public:
    static constexpr size_t kMax = 8;
    struct Universe {
        bool used = false;
        uint16_t id = 0;
        uint8_t data[kDmxSlots] = {};
        uint16_t len = 0;
        uint16_t seq = 0;
        uint32_t last_data_ms = 0;
        OutputCadence cadence;
    };

    void set_refresh_hz(uint8_t hz);
    // New data from the Pi. Returns false if the table is full.
    bool update(uint16_t id, const uint8_t* data, uint16_t len, uint32_t now_ms);
    // Drops universes without data for hold_timeout.
    void expire(uint32_t now_ms, uint32_t hold_timeout_ms);
    // The universe whose emission is due (most overdue first), or nullptr.
    Universe* due(uint32_t now_us);
    void sent(Universe* u, uint32_t now_us);
    uint8_t active() const;
    uint32_t coalesced() const { return coalesced_; }

private:
    Universe u_[kMax];
    uint32_t refresh_us_ = 22727;
    uint32_t coalesced_ = 0;
};

class CommandTracker {
public:
    static constexpr size_t kMax = 8;
    static constexpr size_t kMaxPacket = 250;
    // Targeted: 5 attempts, waiting 30, 60, 120, 240 ms for an ACK, then 50 ms after the
    // last one (< 0.5 s in total). Broadcast: 3 emissions 20 ms apart, ACKs collected 1 s.
    static constexpr uint32_t kWait[5] = {30, 60, 120, 240, 50};
    static constexpr uint8_t kTargetedAttempts = 5;
    static constexpr uint8_t kBroadcastEmissions = 3;
    static constexpr uint32_t kBroadcastSpacingMs = 20;
    static constexpr uint32_t kBroadcastCollectMs = 1000;

    enum class Result : uint8_t { Acked = 0, Timeout = 1, BroadcastDone = 2 };
    struct Done {
        uint16_t cmd_id;
        uint8_t target[6];
        Result result;
        uint8_t attempts;
    };

    // pkt: the complete COMMAND radio packet. false: table full or packet too long.
    bool add(uint16_t cmd_id, const uint8_t target[6], const uint8_t* pkt, size_t len, uint32_t now_ms);
    // A packet is due: returns it (and counts the attempt), else nullptr.
    const uint8_t* due(uint32_t now_ms, size_t* len);
    // An ACK was received from src for cmd_id.
    void on_ack(uint16_t cmd_id, const uint8_t src[6], uint32_t now_ms);
    // Finished commands (to report as CMD_RESULT), one at a time.
    bool pop_done(uint32_t now_ms, Done* d);
    bool pending() const;

private:
    struct Cmd {
        bool used = false;
        bool broadcast = false;
        bool acked = false;
        uint16_t id = 0;
        uint8_t target[6] = {};
        uint8_t pkt[kMaxPacket] = {};
        size_t len = 0;
        uint8_t attempts = 0;
        uint32_t start_ms = 0;
        uint32_t next_ms = 0;
        uint32_t end_ms = 0;          // result time
    };
    Cmd c_[kMax];
};

// Transmission scheduler: one packet at a time (the caller waits for the ESP-NOW send
// callback before asking for the next), COMMAND > DMX_DATA > BEACON (1 Hz, always,
// even without an active universe).
class Scheduler {
public:
    enum class Kind : uint8_t { None, Command, Dmx, Beacon };
    struct Tx {
        Kind kind = Kind::None;
        const uint8_t* cmd = nullptr;           // Command: complete packet
        size_t cmd_len = 0;
        UniverseTable::Universe* uni = nullptr;  // Dmx: universe to emit (call sent())
    };
    static constexpr uint32_t kBeaconMs = 1000;

    UniverseTable universes;
    CommandTracker commands;

    Tx next(uint32_t now_ms, uint32_t now_us, uint32_t hold_timeout_ms);
    void dmx_sent(UniverseTable::Universe* u, uint32_t now_us) { universes.sent(u, now_us); }

private:
    bool beacon_started_ = false;
    uint32_t next_beacon_ms_ = 0;
};

}  // namespace dmxnow
