#include "radio.h"

#include <Arduino.h>
#include <WiFi.h>
#include <esp_now.h>
#include <esp_wifi.h>
#include <freertos/queue.h>

#include <atomic>
#include <cstring>

namespace radio {

namespace {
const uint8_t kBroadcast[6] = {0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF};
QueueHandle_t queue = nullptr;
std::atomic<uint16_t> net_id_{0};
std::atomic<uint32_t> rejected_{0};
uint8_t channel_ = 6;
Packet rx_slot;   // callback scratch (the Wi-Fi task is the only writer)

void set_rate(const uint8_t* peer) {
    esp_now_rate_config_t rc = {};
    rc.phymode = WIFI_PHY_MODE_11G;
    rc.rate = WIFI_PHY_RATE_6M;
    esp_now_set_peer_rate_config(peer, &rc);
}

bool ensure_peer(const uint8_t* mac) {
    if (esp_now_is_peer_exist(mac)) return true;
    esp_now_peer_info_t p = {};
    std::memcpy(p.peer_addr, mac, 6);
    p.channel = 0;          // current channel
    p.ifidx = WIFI_IF_STA;
    p.encrypt = false;
    if (esp_now_add_peer(&p) != ESP_OK) return false;
    set_rate(mac);
    return true;
}

// Wi-Fi task context: checks and a copy only (PROTOCOL 2.5)
void on_recv(const esp_now_recv_info_t* info, const uint8_t* data, int len) {
    if (len <= 0 || size_t(len) > dmxnow::kMaxPacketV2) {
        ++rejected_;
        return;
    }
    if (dmxnow::validate(data, size_t(len), net_id_.load()) != dmxnow::Reject::None) {
        ++rejected_;
        return;
    }
    rx_slot.len = uint16_t(len);
    rx_slot.rssi = info->rx_ctrl ? int8_t(info->rx_ctrl->rssi) : 0;
    std::memcpy(rx_slot.src, info->src_addr, 6);
    std::memcpy(rx_slot.data, data, size_t(len));
    xQueueSend(queue, &rx_slot, 0);   // queue full: dropped (the next frame follows)
}
}  // namespace

bool begin(uint8_t ch, uint16_t net_id) {
    net_id_ = net_id;
    if (!queue) queue = xQueueCreate(6, sizeof(Packet));
    WiFi.mode(WIFI_STA);
    WiFi.disconnect();
    esp_wifi_set_ps(WIFI_PS_NONE);
    esp_wifi_set_max_tx_power(60);   // 15 dBm (0.25 dBm steps)
    if (!set_channel(ch)) return false;
    if (esp_now_init() != ESP_OK) return false;
    uint32_t v = 0;
    esp_now_get_version(&v);
    log_i("ESP-NOW v%lu", (unsigned long)v);   // 2: 1470-byte payloads (ADR 0011)
    esp_now_register_recv_cb(on_recv);
    return ensure_peer(kBroadcast);
}

void set_net_id(uint16_t id) { net_id_ = id; }

bool set_channel(uint8_t ch) {
    if (esp_wifi_set_channel(ch, WIFI_SECOND_CHAN_NONE) != ESP_OK) return false;
    channel_ = ch;
    return true;
}

uint8_t channel() { return channel_; }

void own_mac(uint8_t mac[6]) { esp_wifi_get_mac(WIFI_IF_STA, mac); }

bool receive(Packet* p, uint32_t wait_ms) { return xQueueReceive(queue, p, pdMS_TO_TICKS(wait_ms)) == pdTRUE; }

uint32_t rejected() { return rejected_.load(); }

bool send(const uint8_t* dst, const uint8_t* data, size_t len) {
    const uint8_t* to = dst ? dst : kBroadcast;
    if (!ensure_peer(to)) return false;
    return esp_now_send(to, data, len) == ESP_OK;
}

}  // namespace radio
