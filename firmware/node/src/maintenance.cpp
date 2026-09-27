#include "maintenance.h"

#include <Arduino.h>
#include <Update.h>
#include <WebServer.h>
#include <WiFi.h>

#include <cstring>

#include "radio.h"

namespace maint {

namespace {
WebServer* server = nullptr;
Hooks hooks_;
bool active_ = false;
uint32_t timeout_ms = 600000;
uint32_t last_client_ms = 0;
bool ota_ok = false;
bool exit_requested = false;

String esc(const char* s) {
    String o;
    for (; *s; ++s) {
        switch (*s) {
            case '<': o += "&lt;"; break;
            case '>': o += "&gt;"; break;
            case '&': o += "&amp;"; break;
            case '"': o += "&quot;"; break;
            default: o += *s;
        }
    }
    return o;
}

String field(const char* label, const char* name, long value) {
    return String("<label>") + label + " <input name=\"" + name + "\" value=\"" + value + "\"></label><br>";
}

void page() {
    const dmxnow::NodeConfig& c = hooks_.config();
    char st[512];
    hooks_.status_text(st, sizeof st);
    String h;
    h.reserve(3000);
    h += F("<!doctype html><meta charset=utf-8><meta name=viewport content='width=device-width'>"
           "<title>dmxnow</title><style>body{font-family:sans-serif;max-width:32em;margin:1em auto;padding:0 1em}"
           "input{width:9em}label{display:inline-block;margin:.2em 0}</style>");
    h += "<h1>" + esc(c.name) + "</h1><pre>" + esc(st) + "</pre>";
    h += F("<h2>Configuration</h2><form method=post action=/config>");
    h += String("<label>Nom <input name=name maxlength=16 value=\"") + esc(c.name) + "\"></label><br>";
    h += field("Univers", "universe", c.universe);
    h += field("Adresse DMX", "start_address", c.start_address);
    h += field("Canaux DMX émis", "dmx_out_slots", c.dmx_out_slots);
    h += field("Relais suit le DMX (0/1)", "relay_dmx", c.relay_dmx);
    h += field("Relais au démarrage (0 éteint, 1 allumé, 2 dernier)", "relay_power_on", c.relay_power_on);
    h += field("Canal radio (1-13)", "radio_channel", c.radio_channel);
    h += field("Identifiant de réseau", "net_id", c.net_id);
    h += F("<button>Enregistrer</button></form>");
    h += F("<h2>Relais</h2><form method=post action=/relay>"
           "<button name=mode value=1>Forcer allumé</button> <button name=mode value=0>Forcer éteint</button> "
           "<button name=mode value=2>Automatique</button></form>");
    h += F("<h2>Firmware</h2><form method=post action=/update enctype=multipart/form-data>"
           "<input type=file name=fw accept=.bin> <button>Téléverser</button></form>"
           "<h2>Sortie</h2><form method=post action=/exit><button>Quitter la maintenance</button></form>");
    server->send(200, "text/html; charset=utf-8", h);
}

void post_config() {
    uint8_t tlv[96];
    size_t n = 0;
    auto u16 = [&](uint8_t k, const char* arg) {
        if (!server->hasArg(arg) || n + 4 > sizeof tlv) return;
        long v = server->arg(arg).toInt();
        tlv[n++] = k;
        tlv[n++] = 2;
        tlv[n++] = uint8_t(v);
        tlv[n++] = uint8_t(v >> 8);
    };
    auto u8 = [&](uint8_t k, const char* arg) {
        if (!server->hasArg(arg) || n + 3 > sizeof tlv) return;
        tlv[n++] = k;
        tlv[n++] = 1;
        tlv[n++] = uint8_t(server->arg(arg).toInt());
    };
    if (server->hasArg("name")) {
        String s = server->arg("name");
        size_t l = s.length() > 16 ? 16 : s.length();
        tlv[n++] = dmxnow::key::kName;
        tlv[n++] = uint8_t(l);
        std::memcpy(tlv + n, s.c_str(), l);
        n += l;
    }
    u16(dmxnow::key::kUniverse, "universe");
    u16(dmxnow::key::kStartAddress, "start_address");
    u16(dmxnow::key::kDmxOutSlots, "dmx_out_slots");
    u8(dmxnow::key::kRelayDmx, "relay_dmx");
    u8(dmxnow::key::kRelayPowerOn, "relay_power_on");
    u8(dmxnow::key::kRadioChannel, "radio_channel");
    u16(dmxnow::key::kNetId, "net_id");
    dmxnow::AckStatus st = hooks_.apply_config(tlv, n);
    if (st == dmxnow::AckStatus::Ok) {
        server->sendHeader("Location", "/");
        server->send(303);
    } else {
        server->send(400, "text/plain; charset=utf-8", "Valeur refusée (plage ou empreinte DMX)");
    }
}

void post_relay() {
    hooks_.relay(uint8_t(server->arg("mode").toInt()));
    server->sendHeader("Location", "/");
    server->send(303);
}

void upload() {
    HTTPUpload& u = server->upload();
    if (u.status == UPLOAD_FILE_START) {
        ota_ok = Update.begin(UPDATE_SIZE_UNKNOWN);
    } else if (u.status == UPLOAD_FILE_WRITE && ota_ok) {
        ota_ok = Update.write(u.buf, u.currentSize) == u.currentSize;
    } else if (u.status == UPLOAD_FILE_END && ota_ok) {
        ota_ok = Update.end(true);
    } else if (u.status == UPLOAD_FILE_ABORTED) {
        Update.abort();
        ota_ok = false;
    }
    last_client_ms = millis();
}

void upload_done() {
    if (ota_ok) {
        server->send(200, "text/plain; charset=utf-8",
                     "Firmware accepté, redémarrage. Il sera confirmé au premier paquet radio valide (60 s).");
        delay(300);
        ESP.restart();
    } else {
        server->send(500, "text/plain; charset=utf-8", String("Échec de la mise à jour : ") + Update.errorString());
    }
}
}  // namespace

void start(const dmxnow::NodeConfig& cfg, uint16_t timeout_s, const Hooks& h) {
    if (active_) return;
    hooks_ = h;
    timeout_ms = uint32_t(timeout_s ? timeout_s : 600) * 1000u;
    String ssid = String("dmxnow-") + cfg.name;
    WiFi.mode(WIFI_AP_STA);
    // same channel as the ESP-NOW network: reception goes on (V-FW-05)
    WiFi.softAP(ssid.c_str(), cfg.maint_password, radio::channel(), 0, 2);
    radio::set_channel(radio::channel());
    server = new WebServer(80);
    server->on("/", HTTP_GET, page);
    server->on("/config", HTTP_POST, post_config);
    server->on("/relay", HTTP_POST, post_relay);
    server->on("/update", HTTP_POST, upload_done, upload);
    server->on("/exit", HTTP_POST, [] {
        server->send(200, "text/plain; charset=utf-8", "Sortie de maintenance.");
        exit_requested = true;   // the server cannot be deleted from its own handler
    });
    server->begin();
    active_ = true;
    last_client_ms = millis();
}

bool active() { return active_; }

void loop() {
    if (!active_) return;
    server->handleClient();
    if (exit_requested) {
        exit_requested = false;
        stop();
        return;
    }
    if (WiFi.softAPgetStationNum() > 0) last_client_ms = millis();
    if (millis() - last_client_ms > timeout_ms) stop();
}

void stop() {
    if (!active_) return;
    active_ = false;
    if (server) {
        server->stop();
        delete server;
        server = nullptr;
    }
    WiFi.softAPdisconnect(true);
    WiFi.mode(WIFI_STA);
    radio::set_channel(radio::channel());
}

}  // namespace maint
