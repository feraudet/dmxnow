#include "node.h"

#include <Arduino.h>
#include <esp_mac.h>
#include <esp_ota_ops.h>
#include <esp_random.h>
#include <esp_system.h>
#include <esp_timer.h>

#include <cstring>

#include "board.h"
#include "dmx_out.h"
#include "dmxnow/auth.h"
#include "dmxnow/config.h"
#include "dmxnow/dmx.h"
#include "dmxnow/gamma.h"
#include "dmxnow/protocol.h"
#include "dmxnow/relay.h"
#include "maintenance.h"
#include "pwm_out.h"
#include "radio.h"
#include "store.h"

using namespace dmxnow;

// Arduino-ESP32: the image is validated by the application (first valid radio packet),
// not automatically at boot (SPEC 4.9, V-FW-06).
extern "C" bool verifyRollbackLater() { return true; }

namespace node {

namespace {
constexpr uint8_t kFw[3] = {DMXNOW_FW_MAJOR, DMXNOW_FW_MINOR, DMXNOW_FW_PATCH};
constexpr uint32_t kHeartbeatMs = 2000, kHeartbeatJitterMs = 250;
constexpr uint32_t kDongleForgetMs = 30000;
constexpr uint32_t kStreamPresentMs = 1000;
constexpr uint32_t kScanAfterMs = 60000, kScanDwellMs = 300;
constexpr uint32_t kOtaValidateMs = 60000;
constexpr uint32_t kPowerCycleWindowMs = 5000;
constexpr uint32_t kButtonDebounceMs = 20, kButtonMaintMs = 3000, kButtonResetMs = 10000;

NodeConfig cfg;
Variant variant = Variant::FixtureOnly;
Footprint fp;
uint8_t mac[6];

RelayLogic relay;
Reassembler reasm;
LossCounter loss;
GammaTable gamma;
CommandHistory history;
uint32_t auth_last = 0;

// radio / network
bool dongle_known = false;
uint8_t dongle[6];
uint32_t dongle_seen_ms = 0;
uint32_t net_seen_ms = 0;         // last valid packet of our network
uint32_t stream_ms = 0;           // last DMX_DATA of our universe
bool have_stream = false;
int16_t rssi_x8 = 0;              // EMA alpha 1/8, scaled x8
bool rssi_init = false;
uint16_t hb_seq = 0;
uint32_t next_hb_ms = 0;

// scan (A5)
bool scanning = false;
uint8_t scan_ch = 1;
uint32_t scan_step_ms = 0;

// outputs
uint8_t frame[kDmxSlots];
uint16_t frame_len = 0;
bool blackout = false;
uint32_t fade_start_ms = 0;
bool fading = false;
uint32_t identify_until = 0;
bool identifying = false;

// deferred actions
uint32_t channel_at = 0;
uint8_t channel_new = 0;
uint32_t reboot_at = 0;
bool factory_at_reboot = false;
bool ota_pending_verify = false;

// button
bool btn_down = false;
uint32_t btn_since = 0;
bool btn_reset_done = false;
uint32_t btn_raw_since = 0;
bool btn_raw = false;

bool boot_counter_cleared = false;

uint32_t now_ms() { return millis(); }
uint32_t uptime_s() { return uint32_t(esp_timer_get_time() / 1000000); }

void schedule_heartbeat() { next_hb_ms = now_ms(); }

// --- outputs ------------------------------------------------------------------------
void update_pwm() {
    if (variant != Variant::WithStrips) return;
    uint32_t now = now_ms();
    bool blink_on = identifying && ((now / 500) % 2 == 0);
    uint32_t fade_q16 = 65536;   // fade factor, 16.16
    if (fading) {
        uint32_t el = now - fade_start_ms;
        if (cfg.fade_on_ms == 0 || el >= cfg.fade_on_ms) fading = false;
        else fade_q16 = uint32_t((uint64_t(el) << 16) / cfg.fade_on_ms);
    }
    for (uint8_t ch = 0; ch < 4; ++ch) {
        uint32_t duty;
        if (identifying) {
            duty = blink_on ? gamma.max_duty() : 0;
        } else if (blackout) {
            duty = 0;
        } else {
            uint16_t v = pwm_value(fp, frame, frame_len, ch);
            if (fading) v = uint16_t((uint32_t(v) * fade_q16) >> 16);   // perceptual ramp, before gamma
            duty = (!fp.pwm16 && !fading) ? gamma.lookup8(uint8_t(v >> 8)) : gamma.lookup16(v);
        }
        pwm_out::set(ch, duty);
    }
}

void start_fade() {
    fading = true;
    fade_start_ms = now_ms();
}

void apply_relay_gpio() {
    digitalWrite(board::kRelay, relay.state() ? HIGH : LOW);
    store::save_relay(relay.state(), relay.switch_count());   // only on an effective switch
    if (relay.state()) start_fade();                         // LED supply restarts (SPEC 4.7)
    schedule_heartbeat();
}

void apply_identify_dmx() {
    // pushed to the DMX task only on a change (each push triggers an output frame)
    static uint16_t last_slot = 0;
    static uint8_t last_value = 0;
    uint16_t slot = identifying ? cfg.identify_slot : 0;
    uint8_t value = (slot && (now_ms() / 500) % 2 == 0) ? 255 : 0;
    if (slot == last_slot && value == last_value) return;
    last_slot = slot;
    last_value = value;
    dmx_out::set_override(slot, value);
}

void configure_outputs() {
    fp = footprint(cfg, variant);
    dmx_out::set_slots(cfg.dmx_out_slots);
    relay.set_relay_dmx(cfg.relay_dmx);
    relay.set_min_interval(cfg.relay_min_interval_ms);
    if (variant == Variant::WithStrips) {
        static uint16_t freq = 0;   // the LEDC is reconfigured only when the frequency changes
        if (freq != cfg.pwm_freq_hz && pwm_out::begin(cfg.pwm_freq_hz)) freq = cfg.pwm_freq_hz;
        gamma.build(cfg.gamma_x10, pwm_out::bits());
        update_pwm();
    }
}

// --- radio output -------------------------------------------------------------------
void send_packet(MsgType type, uint16_t net_id, uint16_t universe, uint16_t seq, const uint8_t* payload,
                 size_t len) {
    uint8_t buf[kHeaderSize + 256];
    Header h;
    h.type = uint8_t(type);
    h.net_id = net_id;
    h.universe = universe;
    h.seq = seq;
    size_t n = build_packet(h, payload, len, nullptr, buf, sizeof buf);
    if (n) radio::send(dongle_known ? dongle : nullptr, buf, n);
}

void send_heartbeat() {
    Heartbeat hb;
    std::memcpy(hb.mac, mac, 6);
    std::strncpy(hb.name, cfg.name, 16);
    hb.start_address = cfg.start_address;
    std::memcpy(hb.fw_version, kFw, 3);
    hb.variant = uint8_t(variant);
    hb.relay = relay.heartbeat_bits();
    hb.relay_switch_count = relay.switch_count();
    hb.rssi = int8_t(rssi_x8 / 8);
    hb.rx_frames = loss.rx_frames();
    hb.lost_frames = loss.lost_frames();
    hb.rejected_frames = radio::rejected();
    hb.uptime_s = uptime_s();
    hb.status = uint8_t((have_stream ? hb_status::kDmx : 0) | (blackout ? hb_status::kBlackout : 0) |
                        (maint::active() ? hb_status::kMaintenance : 0) | (identifying ? hb_status::kIdentify : 0) |
                        (dongle_known ? hb_status::kDongleKnown : 0));
    hb.radio_channel = radio::channel();
    hb.dmx_out_slots = cfg.dmx_out_slots;
    hb.reset_reason = uint8_t(esp_reset_reason());
    uint8_t p[kHeartbeatPayload];
    encode_heartbeat(hb, p);
    send_packet(MsgType::Heartbeat, cfg.net_id, cfg.universe, hb_seq++, p, sizeof p);
}

// --- commands -----------------------------------------------------------------------
void enter_maintenance(uint16_t timeout_s);

AckStatus apply_config(const uint8_t* tlv, size_t len) {
    NodeConfig n = cfg;
    uint32_t changed = 0;
    AckStatus st = apply_config_tlv(tlv, len, variant, &n, &changed);
    if (st != AckStatus::Ok) return st;
    uint16_t old_universe = cfg.universe;
    cfg = n;
    store::save_config(cfg);
    if (changed & (1u << key::kNetId)) radio::set_net_id(cfg.net_id);
    if (cfg.universe != old_universe) {
        reasm = Reassembler();
        loss = LossCounter();
        have_stream = false;
    }
    if ((changed & (1u << key::kRadioChannel)) && cfg.radio_channel != radio::channel()) {
        channel_new = cfg.radio_channel;          // applied 500 ms after the ACK
        channel_at = now_ms() + 500;
    }
    if (changed & (1u << key::kStatusLed)) {
        if (cfg.status_led) pinMode(board::kStatusLed, OUTPUT);
        else digitalWrite(board::kStatusLed, LOW);
    }
    configure_outputs();
    schedule_heartbeat();
    return AckStatus::Ok;
}

void set_relay_mode(uint8_t mode) {
    relay.command(RelayLogic::Force(mode), now_ms());
    schedule_heartbeat();
}

void handle_command(const radio::Packet& p, const Header& h) {
    CommandView cmd;
    if (!parse_command(p.data + kHeaderSize, h.length, &cmd)) return;
    if (!mac_is_broadcast(cmd.target) && std::memcmp(cmd.target, mac, 6) != 0) return;   // not for us

    uint8_t ack[CommandHistory::kMaxAck];
    size_t ack_len = 0;
    const uint8_t* old = history.find(h.seq, &ack_len);
    if (old) {   // repeated command: not executed again, same answer (PROTOCOL 6.2)
        send_packet(MsgType::Ack, h.net_id, kNoUniverse, h.seq, old, ack_len);
        return;
    }
    Opcode op = Opcode(cmd.opcode);
    AckStatus st = AckStatus::Ok;
    ack_len = 2;

    if (cfg.has_net_key && op != Opcode::Identify) {
        uint32_t counter = 0;
        if (auth_check(cfg.net_key, p.data, p.len, auth_last, &counter) != AuthResult::Ok) {
            st = AckStatus::AuthFailed;
        } else {
            auth_last = counter;
            store::set_auth_counter(counter);
        }
    }
    if (st == AckStatus::Ok) {
        switch (op) {
            case Opcode::Identify: {
                uint16_t d = cmd.args_len >= 2 ? get16(cmd.args) : 10;
                identifying = d > 0;
                identify_until = now_ms() + uint32_t(d) * 1000u;
                schedule_heartbeat();
                break;
            }
            case Opcode::SetConfig:
                st = apply_config(cmd.args, cmd.args_len);
                break;
            case Opcode::GetConfig: {
                size_t n = serialize_config_tlv(cfg, ack + 2, sizeof ack - 2);
                if (n) ack_len += n;
                else st = AckStatus::InternalError;
                break;
            }
            case Opcode::Relay:
                if (cmd.args_len < 1 || cmd.args[0] > 2) {
                    st = AckStatus::InvalidArg;
                } else {
                    set_relay_mode(cmd.args[0]);
                    ack[ack_len++] = relay.heartbeat_bits();
                }
                break;
            case Opcode::Maintenance:
                enter_maintenance(cmd.args_len >= 2 ? get16(cmd.args) : 0);
                break;
            case Opcode::Reboot:
                reboot_at = now_ms() + 200;
                break;
            case Opcode::FactoryReset:
                if (cmd.args_len < 4 || get32(cmd.args) != kFactoryResetConfirm) st = AckStatus::InvalidArg;
                else { factory_at_reboot = true; reboot_at = now_ms() + 200; }
                break;
            default:
                st = AckStatus::UnknownOpcode;
        }
    }
    ack[0] = cmd.opcode;
    ack[1] = uint8_t(st);
    if (st != AckStatus::Ok) ack_len = 2;
    history.remember(h.seq, ack, ack_len);
    send_packet(MsgType::Ack, h.net_id, kNoUniverse, h.seq, ack, ack_len);
}

// --- packets --------------------------------------------------------------------------
void on_dmx(const radio::Packet& p, const Header& h) {
    if (h.universe != cfg.universe) return;
    int8_t r = p.rssi;
    if (!rssi_init) { rssi_x8 = int16_t(r) * 8; rssi_init = true; }
    else rssi_x8 = int16_t(rssi_x8 + r - rssi_x8 / 8);
    Reassembler::Result res = reasm.feed(h.seq, h.offset, h.length, h.flags, p.data + kHeaderSize);
    if (res == Reassembler::Result::None) return;
    loss.on_frame(h.seq);
    std::memcpy(frame, reasm.frame(), kDmxSlots);
    frame_len = reasm.frame_len();
    stream_ms = now_ms();
    if (!have_stream) schedule_heartbeat();
    have_stream = true;
    if (blackout) { blackout = false; dmx_out::set_blackout(false); }
    dmx_out::set_frame(frame, frame_len);
    if (fp.relay_slot >= 0) relay.dmx_level(fp.relay_slot < frame_len ? frame[fp.relay_slot] : 0, now_ms());
    update_pwm();
}

void on_packet(const radio::Packet& p) {
    Header h = decode_header(p.data);
    uint32_t now = now_ms();
    if (ota_pending_verify) {   // the new image works: keep it
        esp_ota_mark_app_valid_cancel_rollback();
        ota_pending_verify = false;
    }
    if (cfg.net_id == 0 || h.net_id == cfg.net_id) {
        net_seen_ms = now;
        if (scanning) {   // found our network again (A5): adopt the channel
            scanning = false;
            if (cfg.radio_channel != radio::channel()) {
                cfg.radio_channel = radio::channel();
                store::save_config(cfg);
            }
            schedule_heartbeat();
        }
        if (h.type != uint8_t(MsgType::Heartbeat) && h.type != uint8_t(MsgType::Ack)) {
            if (!dongle_known || std::memcmp(dongle, p.src, 6) != 0) schedule_heartbeat();
            std::memcpy(dongle, p.src, 6);
            dongle_known = true;
            dongle_seen_ms = now;
        }
    }
    switch (MsgType(h.type)) {
        case MsgType::DmxData: on_dmx(p, h); break;
        case MsgType::Command: handle_command(p, h); break;
        default: break;   // BEACON: dongle learnt above; HEARTBEAT/ACK of other nodes ignored
    }
}

// --- maintenance, button, LED ------------------------------------------------------------
void status_text(char* out, size_t cap) {
    snprintf(out, cap,
             "MAC %02X:%02X:%02X:%02X:%02X:%02X  firmware %u.%u.%u\n"
             "variante %s, univers %u, adresse %u, trame DMX %u canaux\n"
             "canal radio %u, reseau %u, dongle %s, flux DMX %s\n"
             "trames recues %lu, perdues %lu, rejetees %lu, RSSI %d dBm\n"
             "relais %s%s, %lu commutations, en marche depuis %lu s",
             mac[0], mac[1], mac[2], mac[3], mac[4], mac[5], kFw[0], kFw[1], kFw[2],
             variant == Variant::WithStrips ? "rubans" : "projecteur seul", cfg.universe, cfg.start_address,
             cfg.dmx_out_slots, radio::channel(), cfg.net_id, dongle_known ? "connu" : "absent",
             have_stream ? "present" : "absent", (unsigned long)loss.rx_frames(), (unsigned long)loss.lost_frames(),
             (unsigned long)radio::rejected(), rssi_x8 / 8, relay.state() ? "allume" : "eteint",
             relay.forced() ? " (force)" : "", (unsigned long)relay.switch_count(), (unsigned long)uptime_s());
}

void enter_maintenance(uint16_t timeout_s) {
    maint::Hooks hk;
    hk.apply_config = apply_config;
    hk.config = []() -> const NodeConfig& { return cfg; };
    hk.status_text = status_text;
    hk.relay = set_relay_mode;
    maint::start(cfg, timeout_s, hk);
    schedule_heartbeat();
    // the USB console (J3, off mains) is the physical way to read the password (SPEC 4.9)
    Serial.printf("dmxnow: maintenance, AP dmxnow-%s, password %s, http://192.168.4.1/\n", cfg.name,
                  cfg.maint_password);
}

void poll_button(uint32_t now) {
    bool raw = digitalRead(board::kButton) == LOW;
    if (raw != btn_raw) { btn_raw = raw; btn_raw_since = now; }
    if (now - btn_raw_since < kButtonDebounceMs) return;   // 20 ms software debounce
    if (raw && !btn_down) {
        btn_down = true;
        btn_since = now;
        btn_reset_done = false;
    } else if (raw && btn_down && !btn_reset_done && now - btn_since >= kButtonResetMs) {
        btn_reset_done = true;   // >= 10 s: factory reset (net_key and password included)
        factory_at_reboot = true;
        reboot_at = now;
    } else if (!raw && btn_down) {
        btn_down = false;
        uint32_t held = now - btn_since;
        if (!btn_reset_done && held >= kButtonMaintMs) {   // >= 3 s: maintenance toggle
            if (maint::active()) maint::stop();
            else enter_maintenance(0);
            schedule_heartbeat();
        }
    }
}

void update_status_led(uint32_t now) {
    if (!cfg.status_led) return;
    bool on;
    if (identifying) on = (now / 500) % 2 == 0;
    else if (maint::active()) on = (now / 100) % 2 == 0;            // 5 Hz
    else if (have_stream) on = true;                                  // fixed: DMX stream
    else if (dongle_known) on = (now / 500) % 2 == 0;                // 1 Hz: network, no stream
    else { uint32_t t = now % 1000; on = t < 100 || (t >= 200 && t < 300); }   // double flash
    digitalWrite(board::kStatusLed, on ? HIGH : LOW);
}

void random_password(NodeConfig* c) {
    static const char kChars[] = "abcdefghijkmnpqrstuvwxyzABCDEFGHJKLMNPQRSTUVWXYZ23456789";
    for (int i = 0; i < 12; ++i) c->maint_password[i] = kChars[esp_random() % (sizeof kChars - 1)];
    c->maint_password[12] = 0;
    c->maint_password_len = 12;
}
}  // namespace

// ------------------------------------------------------------------------------------------
void setup() {
    // 1. PWM outputs low before anything else (SPEC 4.7), relay open
    pwm_out::early_off();
    pinMode(board::kRelay, OUTPUT);
    digitalWrite(board::kRelay, LOW);
    // 2. variant (EF-07): BOARD_SENSE low = strip part present
    pinMode(board::kBoardSense, INPUT_PULLUP);
    delayMicroseconds(50);
    variant = digitalRead(board::kBoardSense) == LOW ? Variant::WithStrips : Variant::FixtureOnly;
    pinMode(board::kButton, INPUT_PULLUP);

    Serial.begin(115200);
    esp_read_mac(mac, ESP_MAC_WIFI_STA);
    store::begin();
    cfg = default_config(mac);
    store::load_config(&cfg);
    if (cfg.maint_password_len == 0) {   // random, never derived from the MAC (SPEC 4.9)
        random_password(&cfg);
        store::save_config(cfg);
    }
    auth_last = store::auth_counter();
    if (cfg.status_led) pinMode(board::kStatusLed, OUTPUT);

    // relay: power-on state (A2 / SPEC 4.5)
    bool last_state;
    uint32_t count;
    store::load_relay(&last_state, &count);
    relay.begin(cfg.relay_power_on, last_state, cfg.relay_dmx, cfg.relay_min_interval_ms, now_ms());
    relay.set_switch_count(count);

    dmx_out::begin(cfg.dmx_out_slots);
    configure_outputs();
    if (variant == Variant::WithStrips) start_fade();

    const esp_partition_t* running = esp_ota_get_running_partition();
    esp_ota_img_states_t st;
    ota_pending_verify = esp_ota_get_state_partition(running, &st) == ESP_OK && st == ESP_OTA_IMG_PENDING_VERIFY;

    if (!radio::begin(cfg.radio_channel, cfg.net_id)) Serial.println("dmxnow: radio init failed");

    // three power-ups less than 5 s apart -> maintenance (A6, option)
    if (cfg.powercycle_maint) {
        uint8_t n = uint8_t(store::boot_count() + 1);
        if (n >= 3) {
            store::set_boot_count(0);
            enter_maintenance(0);
        } else {
            store::set_boot_count(n);
        }
    }
    net_seen_ms = now_ms();
    schedule_heartbeat();
    Serial.printf("dmxnow node %u.%u.%u, %s, universe %u, channel %u\n", kFw[0], kFw[1], kFw[2],
                  variant == Variant::WithStrips ? "strips" : "fixture only", cfg.universe, cfg.radio_channel);
    Serial.printf("dmxnow: name %s, maintenance password %s\n", cfg.name, cfg.maint_password);
}

void loop() {
    static radio::Packet pkt;   // 1.5 kB: not on the loop task stack
    if (radio::receive(&pkt, 2)) on_packet(pkt);
    uint32_t now = now_ms();

    if (relay.update(now)) apply_relay_gpio();

    // stream presence and optional blackout (EF-06: the relay is never affected)
    if (have_stream && now - stream_ms > kStreamPresentMs) {
        have_stream = false;
        schedule_heartbeat();
    }
    if (cfg.loss_blackout_ms && frame_len && !blackout && now - stream_ms > cfg.loss_blackout_ms) {
        blackout = true;
        dmx_out::set_blackout(true);
        update_pwm();
    }

    if (identifying && time_reached(now, identify_until)) {
        identifying = false;
        schedule_heartbeat();
    }
    apply_identify_dmx();
    if (identifying || fading) update_pwm();

    if (dongle_known && now - dongle_seen_ms > kDongleForgetMs) dongle_known = false;

    // channel scan after 60 s without our network (A5); DMX output goes on meanwhile
    if (cfg.net_id && !maint::active() && !scanning && now - net_seen_ms > kScanAfterMs) {
        scanning = true;
        scan_ch = 0;
        scan_step_ms = now;
    }
    if (scanning && time_reached(now, scan_step_ms)) {
        scan_ch = uint8_t(scan_ch % 13 + 1);
        radio::set_channel(scan_ch);
        scan_step_ms = now + kScanDwellMs;
    }

    if (channel_at && time_reached(now, channel_at)) {
        channel_at = 0;
        radio::set_channel(channel_new);
    }

    if (time_reached(now, next_hb_ms) && !scanning) {
        send_heartbeat();
        next_hb_ms = now + kHeartbeatMs - kHeartbeatJitterMs + esp_random() % (2 * kHeartbeatJitterMs + 1);
    }

    if (!boot_counter_cleared && now > kPowerCycleWindowMs) {
        boot_counter_cleared = true;
        if (cfg.powercycle_maint) store::set_boot_count(0);
    }
    if (ota_pending_verify && now > kOtaValidateMs) {
        esp_ota_mark_app_invalid_rollback_and_reboot();   // no valid packet in 60 s
    }

    poll_button(now);
    maint::loop();
    update_status_led(now);

    if (reboot_at && time_reached(now, reboot_at)) {
        if (factory_at_reboot) store::factory_reset();
        ESP.restart();
    }
}

}  // namespace node
