"""Simulated dongle on a pseudo-terminal (SPEC 8.5: reconnection tests without hardware).

Answers PING, records UNIVERSE and DONGLE_CONFIG frames, and plays a node for COMMAND:
checks the authentication trailer like the node firmware, then answers with an ACK
(RADIO_RX) and a CMD_RESULT, as the real dongle does.
"""
from __future__ import annotations

import os
import struct
import threading
import time

from dmxnow import protocol as P

NODE_MAC = bytes.fromhex("240ac4123456")


class FakeDongle:
    def __init__(self, net_id: int, key: bytes | None = None):
        self.master, slave = os.openpty()
        self.path = os.ttyname(slave)
        os.close(slave)   # the daemon opens it by path
        self.net_id = net_id
        self.key = key
        self.last_counter = 0
        self.decoder = P.SerialDecoder()
        self.frames = []            # (type, payload) received
        self.universes = []         # (universe, data)
        self.configs = []
        self.answer_pings = True
        self.node_config = {"universe": 0, "start_address": 1, "name": "node-123456"}
        self.settings = {"channel": 6, "phy_rate": 0x0B, "power_dbm": 15, "hold_timeout_ms": 10000,
                         "refresh_hz": 44, "mode": 0}
        self.seq = 0
        self._stop = False
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()

    def close(self):
        self._stop = True
        self.thread.join(timeout=1)
        os.close(self.master)

    def send(self, ftype: int, payload: bytes):
        os.write(self.master, P.serial_encode(ftype, self.seq, payload))
        self.seq = (self.seq + 1) & 0xFF

    def heartbeat(self, name="lyre-cour", universe=3, net_id=None, slots=512):
        hb = (NODE_MAC + name.encode().ljust(16, b"\0") + struct.pack("<H", 17) + bytes([1, 0, 0])
              + struct.pack("<BBIbIIIIBBHBB", 2, 1, 12, -60, 1000, 3, 0, 55, 0x11, 6, slots, 1, 0))
        pkt = P.build_packet(P.Header(type=P.T_HEARTBEAT, net_id=self.net_id if net_id is None else net_id,
                                      universe=universe, seq=1), hb)
        self.send(P.S_RADIO_RX, bytes([256 - 58]) + NODE_MAC + pkt)

    def wait(self, pred, timeout=5.0):
        end = time.monotonic() + timeout
        while time.monotonic() < end:
            if pred():
                return True
            time.sleep(0.02)
        return False

    # --- internals ---------------------------------------------------------------------------
    def _run(self):
        import select
        while not self._stop:
            r, _, _ = select.select([self.master], [], [], 0.05)
            if not r:
                continue
            try:
                data = os.read(self.master, 4096)
            except OSError:
                time.sleep(0.02)   # no reader on the slave side (port being reopened)
                continue
            for ftype, _seq, payload in self.decoder.feed(data):
                self.frames.append((ftype, payload))
                if ftype == P.S_PING and self.answer_pings:
                    self.send(P.S_PONG, payload[:4])
                elif ftype == P.S_UNIVERSE:
                    # same checks as firmware/dongle: universe <= 32767, 1..512 channels,
                    # exact length, 8 universes at most; refusals are reported by LOG
                    u, n = struct.unpack_from("<HH", payload) if len(payload) >= 4 else (0, 0)
                    known = {x for x, _ in self.universes}
                    if not (1 <= n <= 512 and len(payload) == 4 + n and u <= P.MAX_UNIVERSE):
                        self.log("UNIVERSE refused: bad universe or length")
                    elif u not in known and len(known) >= 8:
                        self.log("UNIVERSE refused: table full (8 universes max)")
                    else:
                        self.universes.append((u, payload[4:4 + n]))
                elif ftype == P.S_DONGLE_CONFIG:
                    self.configs.append(payload)
                    if not self._apply_config(payload):
                        self.log("DONGLE_CONFIG refused (unknown key or value out of range): nothing applied")
                    self.status()
                elif ftype == P.S_GET_STATUS:
                    self.status()
                elif ftype == P.S_COMMAND and len(payload) >= 10:   # shorter: dropped silently
                    self._command(payload)


    # --- like firmware/dongle ---------------------------------------------------------------------
    def log(self, text: str, level: int = 0):
        self.send(P.S_LOG, bytes([level]) + text.encode())

    def status(self):
        s = self.settings
        self.send(P.S_STATUS, struct.pack("<3sBHBBBIIIII", bytes([1, 0, 0]), s["channel"], self.net_id,
                                          s["phy_rate"], s["mode"], len({u for u, _ in self.universes}),
                                          0, 0, 0, 0, 1))

    def _apply_config(self, tlv: bytes) -> bool:
        """firmware/common/src/dongle.cpp apply_dongle_config: all or nothing."""
        new, net, i = dict(self.settings), self.net_id, 0
        while i < len(tlv):
            if i + 2 > len(tlv) or i + 2 + tlv[i + 1] > len(tlv):
                return False
            k, v = tlv[i], tlv[i + 2:i + 2 + tlv[i + 1]]
            i += 2 + len(v)
            n = int.from_bytes(v, "little") if v else -1
            ok = {1: len(v) == 1 and 1 <= n <= 13, 2: len(v) == 2 and n >= 1,
                  3: len(v) == 1 and n <= 0x0F and n != 0x04, 4: len(v) == 1 and 2 <= n <= 20,
                  5: len(v) == 4 and n >= 1000, 6: len(v) == 1 and 1 <= n <= 60, 7: len(v) == 1 and n <= 1}.get(k)
            if not ok:
                return False
            if k == 2:
                net = n
            else:
                new[{1: "channel", 3: "phy_rate", 4: "power_dbm", 5: "hold_timeout_ms", 6: "refresh_hz",
                     7: "mode"}[k]] = n
        self.settings, self.net_id = new, net
        return True

    def _command(self, payload: bytes):
        cmd_id, flags = struct.unpack_from("<HB", payload)
        body = payload[3:]
        trailer = body[-P.AUTH_SIZE:] if flags & P.F_AUTH else None
        if trailer:
            body = body[:-P.AUTH_SIZE]
        # the radio packet exactly as the dongle builds it
        pkt = P.build_packet(P.Header(type=P.T_COMMAND, net_id=self.net_id, universe=P.NO_UNIVERSE, seq=cmd_id),
                             body, trailer)
        why, h = P.validate(pkt, self.net_id)
        assert why == "ok", why
        target, opcode, args = body[:6], body[6], body[7:]
        status, data = 0, b""
        if self.key is not None and opcode != P.OP_IDENTIFY:   # node side of PROTOCOL §7
            if not trailer:
                status = 3
            else:
                counter = struct.unpack_from("<I", trailer)[0]
                want = P.auth_trailer(self.key, pkt[:16], body, counter)
                if want != trailer or counter <= self.last_counter:
                    status = 3
                else:
                    self.last_counter = counter
        if status == 0 and opcode == P.OP_GET_CONFIG:
            data = P.encode_config(self.node_config)
        elif status == 0 and opcode == P.OP_SET_CONFIG:
            self.node_config.update(P.decode_config(args))
        ack = P.build_packet(P.Header(type=P.T_ACK, net_id=self.net_id, universe=P.NO_UNIVERSE, seq=cmd_id),
                             bytes([opcode, status]) + data)
        if target in (NODE_MAC, P.BROADCAST):
            self.send(P.S_RADIO_RX, bytes([256 - 55]) + NODE_MAC + ack)
            result = 2 if target == P.BROADCAST else 0
        else:
            result = 1   # nobody answers: timeout after 5 attempts
        attempts = {0: 1, 1: 5, 2: 3}[result]   # like the real CommandTracker
        self.send(P.S_CMD_RESULT, struct.pack("<H6sBB", cmd_id, target, result, attempts))
