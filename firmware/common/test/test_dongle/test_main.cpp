// Native tests of the dongle logic (SPEC 8.4): serial framing, scheduling, repetition,
// hold_timeout, command tracking and retransmissions.
#include <ArduinoJson.h>
#include <unity.h>

#include <cstring>
#include <fstream>
#include <sstream>
#include <string>
#include <vector>

#include "dmxnow/dongle.h"
#include "dmxnow/serial.h"

using namespace dmxnow;

static JsonDocument V;

static std::vector<uint8_t> hex(const char* s) {
    std::vector<uint8_t> out;
    for (size_t i = 0; s[i] && s[i + 1]; i += 2) {
        auto nib = [](char c) { return uint8_t(c <= '9' ? c - '0' : (c | 0x20) - 'a' + 10); };
        out.push_back(uint8_t(nib(s[i]) << 4 | nib(s[i + 1])));
    }
    return out;
}

void setUp() {}
void tearDown() {}

// --- Serial framing ------------------------------------------------------------------
static std::vector<SerialDecoder::Frame> feed(SerialDecoder& d, const std::vector<uint8_t>& bytes,
                                              std::vector<std::vector<uint8_t>>* payloads) {
    std::vector<SerialDecoder::Frame> out;
    SerialDecoder::Frame f;
    for (uint8_t b : bytes)
        if (d.push(b, &f)) {
            out.push_back(f);
            payloads->emplace_back(f.payload, f.payload + f.len);
        }
    return out;
}

void test_serial_roundtrip_and_zero_bytes() {
    uint8_t payload[600];
    for (size_t i = 0; i < sizeof payload; ++i) payload[i] = uint8_t(i % 7 == 0 ? 0 : i);
    uint8_t wire[1100];
    size_t n = serial_encode(ser::kUniverse, 42, payload, sizeof payload, wire, sizeof wire);
    TEST_ASSERT_TRUE(n > sizeof payload);
    TEST_ASSERT_EQUAL_UINT8(0, wire[n - 1]);
    for (size_t i = 0; i + 1 < n; ++i) TEST_ASSERT_NOT_EQUAL(0, wire[i]);
    SerialDecoder d;
    std::vector<std::vector<uint8_t>> p;
    auto fr = feed(d, std::vector<uint8_t>(wire, wire + n), &p);
    TEST_ASSERT_EQUAL(1u, fr.size());
    TEST_ASSERT_EQUAL_UINT8(ser::kUniverse, fr[0].type);
    TEST_ASSERT_EQUAL_UINT8(42, fr[0].seq);
    TEST_ASSERT_EQUAL(sizeof payload, p[0].size());
    TEST_ASSERT_EQUAL_MEMORY(payload, p[0].data(), sizeof payload);
    // maximum payload and one byte too many
    std::vector<uint8_t> big(ser::kMaxPayload, 0x55), buf(1100);
    TEST_ASSERT_TRUE(serial_encode(1, 0, big.data(), big.size(), buf.data(), buf.size()) > 0);
    big.push_back(1);
    TEST_ASSERT_EQUAL(0u, serial_encode(1, 0, big.data(), big.size(), buf.data(), buf.size()));
}

void test_serial_errors_and_resync() {
    uint8_t wire[64];
    const uint8_t ping[4] = {1, 2, 3, 4};
    size_t n = serial_encode(ser::kPing, 7, ping, 4, wire, sizeof wire);
    std::vector<uint8_t> stream = {0x13, 0x37, 0x42};   // connection mid-frame: garbage
    stream.push_back(0);
    stream.insert(stream.end(), wire, wire + n);          // valid frame
    std::vector<uint8_t> bad(wire, wire + n);
    size_t k = 3;                                         // CRC error, without
    while (bad[k] == 0x40) ++k;                           // creating a 0x00 delimiter
    bad[k] ^= 0x40;
    stream.insert(stream.end(), bad.begin(), bad.end());
    stream.push_back(0);                                  // idle delimiters are ignored
    stream.push_back(0);
    stream.insert(stream.end(), wire, wire + n);
    SerialDecoder d;
    std::vector<std::vector<uint8_t>> p;
    auto fr = feed(d, stream, &p);
    TEST_ASSERT_EQUAL(2u, fr.size());
    TEST_ASSERT_EQUAL_UINT32(2, d.errors());   // garbage + bad CRC
    TEST_ASSERT_EQUAL_MEMORY(ping, p[1].data(), 4);
    // too short (< 4 bytes decoded)
    const uint8_t tiny[] = {0x02, 0x05, 0x00};
    SerialDecoder d2;
    feed(d2, std::vector<uint8_t>(tiny, tiny + 3), &p);
    TEST_ASSERT_EQUAL_UINT32(1, d2.errors());
    // an endless frame without delimiter does not overflow and is rejected at the end
    SerialDecoder d3;
    std::vector<uint8_t> flood(5000, 0x11);
    flood.push_back(0);
    feed(d3, flood, &p);
    TEST_ASSERT_EQUAL_UINT32(1, d3.errors());
}

// --- Dongle configuration and validation ---------------------------------------------
void test_dongle_config_tlv() {
    DongleSettings s;
    const uint8_t ok[] = {0x01, 1, 11, 0x02, 2, 0x34, 0x12, 0x05, 4, 0x10, 0x27, 0, 0, 0x07, 1, 1};
    TEST_ASSERT_TRUE(apply_dongle_config(ok, sizeof ok, &s));
    TEST_ASSERT_EQUAL_UINT8(11, s.channel);
    TEST_ASSERT_EQUAL_UINT16(0x1234, s.net_id);
    TEST_ASSERT_EQUAL_UINT32(10000, s.hold_timeout_ms);
    TEST_ASSERT_EQUAL_UINT8(1, s.mode);
    DongleSettings before = s;
    const uint8_t bad[] = {0x01, 1, 6, 0x04, 1, 30};   // 30 dBm: refused, nothing applied
    TEST_ASSERT_FALSE(apply_dongle_config(bad, sizeof bad, &s));
    TEST_ASSERT_EQUAL_MEMORY(&before, &s, sizeof s);
    const uint8_t unknown[] = {0x42, 0};
    TEST_ASSERT_FALSE(apply_dongle_config(unknown, sizeof unknown, &s));
}

void test_dongle_accepts_unconfigured_heartbeats() {
    const uint16_t net = V["net_id"];
    // heartbeat of our network (vector)
    for (JsonObject o : V["valid"].as<JsonArray>()) {
        if (std::strcmp(o["name"], "heartbeat") != 0) continue;
        auto p = hex(o["hex"]);
        TEST_ASSERT_EQUAL(int(Reject::None), int(validate_dongle(p.data(), p.size(), net)));
        // the same heartbeat from an unconfigured node (net_id 0)
        Header h = decode_header(p.data());
        h.net_id = 0;
        std::vector<uint8_t> q(p.size());
        build_packet(h, p.data() + kHeaderSize, h.length, nullptr, q.data(), q.size());
        Header out;
        TEST_ASSERT_EQUAL(int(Reject::None), int(validate_dongle(q.data(), q.size(), net, &out)));
        TEST_ASSERT_EQUAL_UINT16(0, out.net_id);
        q[20] ^= 1;
        TEST_ASSERT_EQUAL(int(Reject::Crc), int(validate_dongle(q.data(), q.size(), net)));
        // another network's heartbeat is still rejected
        h.net_id = 0x9999;
        build_packet(h, p.data() + kHeaderSize, h.length, nullptr, q.data(), q.size());
        TEST_ASSERT_EQUAL(int(Reject::NetId), int(validate_dongle(q.data(), q.size(), net)));
    }
    // a DMX_DATA with net_id 0 is not an enrolment packet
    uint8_t d[8] = {1, 2, 3, 4, 5, 6, 7, 8}, pk[64];
    Header h;
    h.type = uint8_t(MsgType::DmxData);
    h.net_id = 0;
    h.universe = 1;
    h.flags = flags::kLast;
    size_t n = build_packet(h, d, 8, nullptr, pk, sizeof pk);
    TEST_ASSERT_EQUAL(int(Reject::NetId), int(validate_dongle(pk, n, net)));
}

// --- Universes: cadence, coalescing, hold_timeout ---------------------------------------
void test_universe_event_refresh_and_coalescing() {
    UniverseTable t;
    t.set_refresh_hz(44);
    uint8_t d[512] = {7};
    TEST_ASSERT_NULL(t.due(0));
    TEST_ASSERT_TRUE(t.update(3, d, 512, 0));
    auto* u = t.due(0);
    TEST_ASSERT_NOT_NULL(u);                 // new data: immediately
    TEST_ASSERT_EQUAL_UINT16(3, u->id);
    t.sent(u, 0);
    TEST_ASSERT_EQUAL_UINT16(1, u->seq);
    t.update(3, d, 512, 2);
    t.update(3, d, 512, 4);                  // arrives before the 10 ms: merged
    TEST_ASSERT_EQUAL_UINT32(1, t.coalesced());
    TEST_ASSERT_NULL(t.due(5000));
    TEST_ASSERT_NOT_NULL(t.due(10000));
    t.sent(u, 10000);
    TEST_ASSERT_NULL(t.due(20000));          // no new data: refresh at 1/44 s
    TEST_ASSERT_NOT_NULL(t.due(10000 + 22727));
    t.set_refresh_hz(20);                    // DONGLE_CONFIG refresh rate
    t.sent(u, 40000);
    TEST_ASSERT_NULL(t.due(40000 + 40000));
    TEST_ASSERT_NOT_NULL(t.due(40000 + 50000));
}

void test_universe_hold_timeout_and_capacity() {
    UniverseTable t;
    uint8_t d[4] = {};
    for (uint16_t i = 0; i < UniverseTable::kMax; ++i) TEST_ASSERT_TRUE(t.update(i, d, 4, 0));
    TEST_ASSERT_FALSE(t.update(100, d, 4, 0));   // table full
    TEST_ASSERT_EQUAL_UINT8(8, t.active());
    t.update(0, d, 4, 9000);                     // universe 0 keeps receiving
    t.expire(9999, 10000);
    TEST_ASSERT_EQUAL_UINT8(8, t.active());
    t.expire(10000, 10000);                      // the others: 10 s without data from the Pi
    TEST_ASSERT_EQUAL_UINT8(1, t.active());
    t.expire(19000, 10000);
    TEST_ASSERT_EQUAL_UINT8(0, t.active());
    TEST_ASSERT_TRUE(t.update(100, d, 4, 19000)); // slot free again
}

// --- Commands --------------------------------------------------------------------------------
static const uint8_t kNode[6] = {0x24, 0x0A, 0xC4, 0x12, 0x34, 0x56};
static const uint8_t kOther[6] = {0x24, 0x0A, 0xC4, 0x00, 0x00, 0x01};
static const uint8_t kAll[6] = {0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF};

void test_targeted_command_retransmissions_and_timeout() {
    CommandTracker c;
    uint8_t pkt[25] = {1};
    TEST_ASSERT_TRUE(c.add(500, kNode, pkt, sizeof pkt, 1000));
    std::vector<uint32_t> sent;
    CommandTracker::Done done;
    bool finished = false;
    for (uint32_t t = 1000; t < 2000 && !finished; ++t) {
        size_t len;
        if (c.due(t, &len)) sent.push_back(t - 1000);
        finished = c.pop_done(t, &done);
        if (finished) sent.push_back(100000 + t - 1000);   // marker: result time
    }
    const uint32_t want[] = {0, 30, 90, 210, 450, 100000 + 500};
    TEST_ASSERT_EQUAL(6u, sent.size());
    TEST_ASSERT_EQUAL_UINT32_ARRAY(want, sent.data(), 6);
    TEST_ASSERT_EQUAL(int(CommandTracker::Result::Timeout), int(done.result));
    TEST_ASSERT_EQUAL_UINT8(5, done.attempts);
    TEST_ASSERT_FALSE(c.pending());
}

void test_targeted_command_acked() {
    CommandTracker c;
    uint8_t pkt[25] = {1};
    size_t len;
    c.add(501, kNode, pkt, sizeof pkt, 0);
    TEST_ASSERT_NOT_NULL(c.due(0, &len));
    TEST_ASSERT_NOT_NULL(c.due(30, &len));        // no ACK after 30 ms: second attempt
    CommandTracker::Done d;
    c.on_ack(501, kOther, 40);                     // another node: ignored
    c.on_ack(502, kNode, 40);                      // another command: ignored
    TEST_ASSERT_FALSE(c.pop_done(41, &d));
    c.on_ack(501, kNode, 45);
    TEST_ASSERT_NULL(c.due(90, &len));             // no more attempts
    TEST_ASSERT_TRUE(c.pop_done(46, &d));
    TEST_ASSERT_EQUAL(int(CommandTracker::Result::Acked), int(d.result));
    TEST_ASSERT_EQUAL_UINT8(2, d.attempts);
    TEST_ASSERT_EQUAL_UINT16(501, d.cmd_id);
    TEST_ASSERT_EQUAL_MEMORY(kNode, d.target, 6);
}

void test_broadcast_command() {
    CommandTracker c;
    uint8_t pkt[25] = {1};
    size_t len;
    c.add(600, kAll, pkt, sizeof pkt, 0);
    std::vector<uint32_t> sent;
    CommandTracker::Done d;
    uint32_t done_at = 0;
    for (uint32_t t = 0; t < 1500; ++t) {
        if (c.due(t, &len)) sent.push_back(t);
        c.on_ack(600, kNode, t);   // ACKs are for the Pi, they do not stop a broadcast
        if (!done_at && c.pop_done(t, &d)) done_at = t;
    }
    const uint32_t want[] = {0, 20, 40};
    TEST_ASSERT_EQUAL(3u, sent.size());
    TEST_ASSERT_EQUAL_UINT32_ARRAY(want, sent.data(), 3);
    TEST_ASSERT_EQUAL_UINT32(1000, done_at);
    TEST_ASSERT_EQUAL(int(CommandTracker::Result::BroadcastDone), int(d.result));
    TEST_ASSERT_EQUAL_UINT8(3, d.attempts);
}

void test_command_table_limits() {
    CommandTracker c;
    uint8_t pkt[251] = {};
    TEST_ASSERT_FALSE(c.add(1, kNode, pkt, 251, 0));   // longer than a v1 packet
    for (uint16_t i = 0; i < CommandTracker::kMax; ++i) TEST_ASSERT_TRUE(c.add(i, kNode, pkt, 20, 0));
    TEST_ASSERT_FALSE(c.add(99, kNode, pkt, 20, 0));
}

// --- Scheduler priority -----------------------------------------------------------------------
void test_scheduler_priority() {
    Scheduler s;
    uint8_t d[8] = {};
    uint8_t pkt[25] = {};
    // at start, only the beacon (1 Hz, even without universes)
    auto t = s.next(0, 0, 10000);
    TEST_ASSERT_EQUAL(int(Scheduler::Kind::Beacon), int(t.kind));
    TEST_ASSERT_EQUAL(int(Scheduler::Kind::None), int(s.next(1, 1000, 10000).kind));
    // DMX data and a command pending, beacon due as well: command first
    s.universes.update(1, d, 8, 1000);
    s.commands.add(7, kNode, pkt, sizeof pkt, 1000);
    t = s.next(1000, 1000000, 10000);
    TEST_ASSERT_EQUAL(int(Scheduler::Kind::Command), int(t.kind));
    t = s.next(1000, 1000000, 10000);
    TEST_ASSERT_EQUAL(int(Scheduler::Kind::Dmx), int(t.kind));
    s.dmx_sent(t.uni, 1000000);
    t = s.next(1000, 1000000, 10000);
    TEST_ASSERT_EQUAL(int(Scheduler::Kind::Beacon), int(t.kind));
    TEST_ASSERT_EQUAL(int(Scheduler::Kind::None), int(s.next(1001, 1001000, 10000).kind));
    // after hold_timeout without data the universe stops, the beacon goes on
    t = s.next(11000, 11000000, 10000);
    TEST_ASSERT_TRUE(t.kind == Scheduler::Kind::Beacon || t.kind == Scheduler::Kind::Command);
    TEST_ASSERT_EQUAL_UINT8(0, s.universes.active());
}

int main() {
    std::ifstream f(VECTORS_PATH);
    std::stringstream ss;
    ss << f.rdbuf();
    if (deserializeJson(V, ss.str())) return 2;
    UNITY_BEGIN();
    RUN_TEST(test_serial_roundtrip_and_zero_bytes);
    RUN_TEST(test_serial_errors_and_resync);
    RUN_TEST(test_dongle_config_tlv);
    RUN_TEST(test_dongle_accepts_unconfigured_heartbeats);
    RUN_TEST(test_universe_event_refresh_and_coalescing);
    RUN_TEST(test_universe_hold_timeout_and_capacity);
    RUN_TEST(test_targeted_command_retransmissions_and_timeout);
    RUN_TEST(test_targeted_command_acked);
    RUN_TEST(test_broadcast_command);
    RUN_TEST(test_command_table_limits);
    RUN_TEST(test_scheduler_priority);
    return UNITY_END();
}
