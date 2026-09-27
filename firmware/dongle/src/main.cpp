// dmxnow dongle (SPEC 4.10, PROTOCOL 4, 6, 8): USB CDC link to the Pi daemon (COBS
// frames) <-> ESP-NOW v2 broadcast to the nodes. The logic (universes, cadence,
// hold_timeout, command retransmissions, priorities) is in firmware/common/dongle.cpp
// and tested natively; this file only wires it to USB, ESP-NOW and NVS.
#include <Arduino.h>
#include <Preferences.h>
#include <WiFi.h>
#include <esp_now.h>
#include <esp_timer.h>
#include <esp_wifi.h>
#include <freertos/queue.h>

#include <atomic>
#include <cstring>

#include "dmxnow/dongle.h"
#include "dmxnow/protocol.h"
#include "dmxnow/serial.h"

using namespace dmxnow;

namespace {

constexpr uint8_t kFw[3] = {DMXNOW_FW_MAJOR, DMXNOW_FW_MINOR, DMXNOW_FW_PATCH};
constexpr int kTxProbePin = D10;             // toggles at each emission (latency probe, ENF-01)
constexpr uint32_t kStatusPeriodMs = 5000;
constexpr uint32_t kSendCallbackTimeoutMs = 50;
const uint8_t kBroadcast[6] = {0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF};

DongleSettings settings;
Preferences prefs;
Scheduler sched;
SerialDecoder decoder;
uint8_t tx_seq = 0;           // serial frames to the Pi
uint16_t beacon_seq = 0;
uint32_t next_status_ms = 0;

// transmission in progress (one packet at a time, SPEC 4.10)
std::atomic<bool> tx_busy{false};
uint32_t tx_started_ms = 0;
std::atomic<uint32_t> tx_ok{0}, tx_fail{0};
bool probe = false;

// fragmented v1 mode: remaining fragments of the universe being sent
uint8_t frag_buf[3][kMaxPacketV1];
size_t frag_len[3];
uint8_t frag_count = 0, frag_next = 0;

struct RxItem {
    uint16_t len;
    int8_t rssi;
    uint8_t src[6];
    uint8_t data[kMaxPacketV1];   // HEARTBEAT / ACK only (< 250 bytes)
};
QueueHandle_t rx_queue;
RxItem rx_slot;

// --- serial to the Pi -----------------------------------------------------------------
void send_pi(uint8_t type, const uint8_t* payload, size_t len) {
    static uint8_t wire[ser::kMaxFrame + ser::kMaxFrame / 254 + 4];
    size_t n = serial_encode(type, tx_seq++, payload, len, wire, sizeof wire);
    if (n) Serial.write(wire, n);
}

void send_status() {
    uint8_t p[32];
    std::memcpy(p, kFw, 3);
    p[3] = settings.channel;
    put16(p + 4, settings.net_id);
    p[6] = settings.phy_rate;
    p[7] = settings.mode;
    p[8] = sched.universes.active();
    put32(p + 9, tx_ok.load());
    put32(p + 13, tx_fail.load());
    put32(p + 17, decoder.errors());
    put32(p + 21, sched.universes.coalesced());
    put32(p + 25, uint32_t(esp_timer_get_time() / 1000000));
    send_pi(ser::kStatus, p, 29);
}

// --- radio ----------------------------------------------------------------------------
void on_sent(const esp_now_send_info_t*, esp_now_send_status_t status) {
    if (status == ESP_NOW_SEND_SUCCESS) ++tx_ok;
    else ++tx_fail;
    tx_busy = false;
}

void on_recv(const esp_now_recv_info_t* info, const uint8_t* data, int len) {
    // Wi-Fi task: checks and a copy only. HEARTBEAT and ACK are forwarded to the Pi.
    if (len <= 0 || size_t(len) > sizeof rx_slot.data) return;
    Header h;
    if (validate_dongle(data, size_t(len), settings.net_id, &h) != Reject::None) return;
    if (h.type != uint8_t(MsgType::Heartbeat) && h.type != uint8_t(MsgType::Ack)) return;
    rx_slot.len = uint16_t(len);
    rx_slot.rssi = info->rx_ctrl ? int8_t(info->rx_ctrl->rssi) : 0;
    std::memcpy(rx_slot.src, info->src_addr, 6);
    std::memcpy(rx_slot.data, data, size_t(len));
    xQueueSend(rx_queue, &rx_slot, 0);
}

void apply_radio() {
    esp_wifi_set_channel(settings.channel, WIFI_SECOND_CHAN_NONE);
    esp_wifi_set_max_tx_power(int8_t(settings.power_dbm * 4));
    esp_now_rate_config_t rc = {};
    rc.phymode = settings.phy_rate <= 0x07 ? WIFI_PHY_MODE_11B : WIFI_PHY_MODE_11G;
    rc.rate = wifi_phy_rate_t(settings.phy_rate);
    esp_now_set_peer_rate_config(kBroadcast, &rc);
    sched.universes.set_refresh_hz(settings.refresh_hz);
}

bool radio_send(const uint8_t* pkt, size_t len) {
    tx_busy = true;
    tx_started_ms = millis();
    if (esp_now_send(kBroadcast, pkt, len) != ESP_OK) {
        tx_busy = false;
        ++tx_fail;
        return false;
    }
    probe = !probe;
    digitalWrite(kTxProbePin, probe ? HIGH : LOW);
    return true;
}

void emit_universe(UniverseTable::Universe* u) {
    Header h;
    h.type = uint8_t(MsgType::DmxData);
    h.net_id = settings.net_id;
    h.universe = u->id;
    h.seq = u->seq;
    if (settings.mode == 0) {   // v2: the whole universe in one packet (PROTOCOL 4.1)
        static uint8_t pkt[kHeaderSize + kDmxSlots];
        h.flags = flags::kLast;
        size_t n = build_packet(h, u->data, u->len, nullptr, pkt, sizeof pkt);
        if (n) radio_send(pkt, n);
        return;
    }
    // v1 fallback: fragments of 232 channels, same seq, sent back to back (PROTOCOL 4.2)
    frag_count = 0;
    for (uint16_t off = 0; off < u->len && frag_count < 3; off += uint16_t(kMaxFragPayload)) {
        uint16_t n = uint16_t(u->len - off < kMaxFragPayload ? u->len - off : kMaxFragPayload);
        h.offset = off;
        h.flags = uint8_t(flags::kFrag | (off + n >= u->len ? flags::kLast : 0));
        frag_len[frag_count] = build_packet(h, u->data + off, n, nullptr, frag_buf[frag_count], kMaxPacketV1);
        ++frag_count;
    }
    frag_next = 0;
    if (frag_count) {
        radio_send(frag_buf[0], frag_len[0]);
        frag_next = 1;
    }
}

void emit_beacon() {
    Header h;
    h.type = uint8_t(MsgType::Beacon);
    h.net_id = settings.net_id;
    h.universe = kNoUniverse;
    h.seq = beacon_seq++;
    Beacon b;
    std::memcpy(b.fw_version, kFw, 3);
    b.active_universes = sched.universes.active();
    b.uptime_s = uint32_t(esp_timer_get_time() / 1000000);
    uint8_t p[kBeaconPayload], pkt[kHeaderSize + kBeaconPayload];
    encode_beacon(b, p);
    size_t n = build_packet(h, p, sizeof p, nullptr, pkt, sizeof pkt);
    if (n) radio_send(pkt, n);
}

// --- frames from the Pi ------------------------------------------------------------------
void handle_command(const uint8_t* p, size_t len, uint32_t now) {
    // cmd_id u16, flags u8 (bit 2 AUTH), target 6, opcode u8, args..., auth trailer
    if (len < 10) return;
    uint16_t cmd_id = get16(p);
    bool auth = p[2] & flags::kAuth;
    const uint8_t* body = p + 3;             // target + opcode + args (+ trailer)
    size_t body_len = len - 3;
    if (auth && body_len < kCommandMinPayload + kAuthSize) return;
    size_t payload_len = auth ? body_len - kAuthSize : body_len;
    Header h;
    h.type = uint8_t(MsgType::Command);
    h.net_id = settings.net_id;
    h.universe = kNoUniverse;
    h.seq = cmd_id;
    uint8_t pkt[CommandTracker::kMaxPacket];
    size_t n = build_packet(h, body, payload_len, auth ? body + payload_len : nullptr, pkt, sizeof pkt);
    if (!n || !sched.commands.add(cmd_id, body, pkt, n, now)) {
        uint8_t r[10];
        put16(r, cmd_id);
        std::memcpy(r + 2, body, 6);
        r[8] = uint8_t(CommandTracker::Result::Timeout);   // not sent: table full / too long
        r[9] = 0;
        send_pi(ser::kCmdResult, r, sizeof r);
    }
}

void handle_frame(const SerialDecoder::Frame& f, uint32_t now) {
    switch (f.type) {
        case ser::kUniverse:
            if (f.len >= 4) {
                uint16_t id = get16(f.payload), n = get16(f.payload + 2);
                if (n >= 1 && n <= kDmxSlots && f.len == 4u + n && id <= kMaxUniverse)
                    sched.universes.update(id, f.payload + 4, n, now);
            }
            break;
        case ser::kCommand:
            handle_command(f.payload, f.len, now);
            break;
        case ser::kDongleConfig:
            if (apply_dongle_config(f.payload, f.len, &settings)) {
                prefs.putBytes("settings", &settings, sizeof settings);
                apply_radio();
            }
            send_status();
            break;
        case ser::kPing:
            send_pi(ser::kPong, f.payload, f.len >= 4 ? 4 : f.len);
            break;
        case ser::kGetStatus:
            send_status();
            break;
        default:
            break;
    }
}

}  // namespace

void setup() {
    pinMode(kTxProbePin, OUTPUT);
    Serial.setRxBufferSize(8192);
    Serial.begin(921600);
    Serial.setTxTimeoutMs(0);   // never block when the Pi does not read
    prefs.begin("dongle", false);
    if (prefs.getBytesLength("settings") == sizeof settings) prefs.getBytes("settings", &settings, sizeof settings);
    rx_queue = xQueueCreate(16, sizeof(RxItem));

    WiFi.mode(WIFI_STA);
    WiFi.disconnect();
    esp_wifi_set_ps(WIFI_PS_NONE);
    esp_wifi_set_channel(settings.channel, WIFI_SECOND_CHAN_NONE);
    esp_now_init();
    esp_now_register_send_cb(on_sent);
    esp_now_register_recv_cb(on_recv);
    esp_now_peer_info_t peer = {};
    std::memcpy(peer.peer_addr, kBroadcast, 6);
    peer.channel = 0;
    peer.ifidx = WIFI_IF_STA;
    esp_now_add_peer(&peer);
    apply_radio();
}

void loop() {
    uint32_t now = millis();

    // Pi -> dongle
    while (Serial.available()) {
        SerialDecoder::Frame f;
        if (decoder.push(uint8_t(Serial.read()), &f)) handle_frame(f, now);
    }

    // radio -> Pi (HEARTBEAT, ACK), ACKs also close the command they answer
    RxItem it;
    while (xQueueReceive(rx_queue, &it, 0) == pdTRUE) {
        Header h = decode_header(it.data);
        if (h.type == uint8_t(MsgType::Ack)) sched.commands.on_ack(h.seq, it.src, now);
        uint8_t p[1 + 6 + sizeof it.data];
        p[0] = uint8_t(it.rssi);
        std::memcpy(p + 1, it.src, 6);
        std::memcpy(p + 7, it.data, it.len);
        send_pi(ser::kRadioRx, p, 7u + it.len);
    }
    CommandTracker::Done d;
    while (sched.commands.pop_done(now, &d)) {
        uint8_t r[10];
        put16(r, d.cmd_id);
        std::memcpy(r + 2, d.target, 6);
        r[8] = uint8_t(d.result);
        r[9] = d.attempts;
        send_pi(ser::kCmdResult, r, sizeof r);
    }

    // one emission at a time: wait for the send callback (with a safety timeout)
    if (tx_busy && now - tx_started_ms > kSendCallbackTimeoutMs) tx_busy = false;
    if (!tx_busy) {
        if (frag_next < frag_count) {
            radio_send(frag_buf[frag_next], frag_len[frag_next]);
            ++frag_next;
        } else {
            // the Pi silent for 3 s: universes go on until hold_timeout (PROTOCOL 8.5)
            Scheduler::Tx t = sched.next(now, uint32_t(esp_timer_get_time()), settings.hold_timeout_ms);
            switch (t.kind) {
                case Scheduler::Kind::Command: radio_send(t.cmd, t.cmd_len); break;
                case Scheduler::Kind::Dmx:
                    emit_universe(t.uni);
                    sched.dmx_sent(t.uni, uint32_t(esp_timer_get_time()));
                    break;
                case Scheduler::Kind::Beacon: emit_beacon(); break;
                case Scheduler::Kind::None: break;
            }
        }
    }

    if (int32_t(now - next_status_ms) >= 0) {   // spontaneous STATUS every 5 s (PROTOCOL 8.5)
        next_status_ms = now + kStatusPeriodMs;
        send_status();
    }
}
