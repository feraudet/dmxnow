"""dmxnowd: Art-Net (QLC+) -> USB dongle -> ESP-NOW nodes (SPEC 4.11, EF-01, EF-02).

Also keeps the node table from the heartbeats and runs the CLI commands received on
the control socket (JSON, one object per line).
"""
from __future__ import annotations

import argparse
import asyncio
import collections
import json
import logging
import os
import struct
import time

from . import artnet, config
from . import protocol as P
from .dongle import DongleLink

log = logging.getLogger("dmxnow")

RELAY_MODES = {"off": 0, "on": 1, "auto": 2}


class ArtNetServer(asyncio.DatagramProtocol):
    def __init__(self, daemon):
        self.d = daemon
        self.transport = None

    def connection_made(self, transport):
        self.transport = transport

    def datagram_received(self, data, addr):
        op = artnet.opcode(data)
        if op == artnet.OP_DMX:
            parsed = artnet.parse_dmx(data)
            if parsed:
                self.d.on_artdmx(*parsed)
        elif op == artnet.OP_POLL:
            for reply in artnet.poll_replies(self.d.cfg.universes, self.d.cfg.announce_ip):
                self.transport.sendto(reply, addr)
            self.d.stats["artpoll"] += 1


class Daemon:
    COMMAND_TIMEOUT = 3.0     # the dongle answers within 0.5 s (targeted) or 1 s (broadcast)
    NODE_STALE_S = 10.0

    def __init__(self, cfg: config.Config):
        self.cfg = cfg
        self.state = config.State(cfg.state_dir)
        self.key = cfg.net_key()
        self.link = DongleLink(cfg.dongle_port, self.on_frame, self.on_connect)
        self.nodes = {}              # mac -> dict (last heartbeat + reception data)
        self.pending = {}            # cmd_id -> {"future", "acks"}
        self.dongle_status = {}
        self.status_event = asyncio.Event()   # set on every STATUS (fresh answer to "status")
        self.dongle_logs = collections.deque(maxlen=20)
        self.config_mismatch = False
        self.config_resent_at = 0.0
        self.stats = {"artdmx": 0, "artdmx_ignored": 0, "artpoll": 0, "radio_rx": 0, "radio_rejected": 0}

    # --- Art-Net -> dongle ---------------------------------------------------------------------
    def on_artdmx(self, universe: int, _seq: int, data: bytes):
        if universe not in self.cfg.universes:
            self.stats["artdmx_ignored"] += 1
            return
        self.stats["artdmx"] += 1
        self.link.send(P.S_UNIVERSE, struct.pack("<HH", universe, len(data)) + bytes(data))

    # --- dongle -> daemon ------------------------------------------------------------------------
    def on_connect(self):
        self.link.send(P.S_DONGLE_CONFIG, P.encode_dongle_config(self.cfg.dongle_values()))
        self.link.send(P.S_GET_STATUS)

    def on_frame(self, ftype: int, _seq: int, payload: bytes):
        if ftype == P.S_RADIO_RX and len(payload) >= 7 + P.HEADER_SIZE:
            self.on_radio(payload[0] - 256 if payload[0] > 127 else payload[0], payload[1:7], payload[7:])
        elif ftype == P.S_CMD_RESULT and len(payload) >= 10:
            cmd_id, target, result, attempts = struct.unpack_from("<H6sBB", payload)
            p = self.pending.get(cmd_id)
            if p and not p["future"].done():
                p["future"].set_result({"result": P.CMD_RESULT.get(result, str(result)), "attempts": attempts})
        elif ftype == P.S_STATUS and len(payload) >= 29:
            self.dongle_status = P.decode_status(payload)
            self.status_event.set()
            self.check_dongle_config()
        elif ftype == P.S_LOG and payload:
            text = payload[1:].decode("utf-8", "replace")
            level = {0: logging.ERROR, 1: logging.WARNING}.get(payload[0], logging.INFO)
            log.log(level, "dongle: %s", text)
            self.dongle_logs.append({"time": time.time(), "level": payload[0], "text": text})


    def check_dongle_config(self):
        """The dongle reports its radio settings in every STATUS (every 5 s): if they
        differ from ours (config refused, or lost while the USB port was coming up),
        say it and send the configuration again, at most every 10 s."""
        want = self.cfg.dongle_values()
        s = self.dongle_status
        self.config_mismatch = (s.get("channel"), s.get("net_id"), s.get("phy_rate"), s.get("mode")) != (
            want["channel"], want["net_id"], want["phy_rate"], "v1" if want["mode"] else "v2")
        if self.config_mismatch and time.time() - self.config_resent_at > 10:
            log.warning("dongle settings differ from the configuration (dongle: channel %s, net_id %s): "
                        "sending the configuration again", s.get("channel"), s.get("net_id"))
            self.config_resent_at = time.time()
            self.link.send(P.S_DONGLE_CONFIG, P.encode_dongle_config(want))

    def on_radio(self, rssi: int, src: bytes, pkt: bytes):
        why, h = P.validate(pkt, self.cfg.net_id, dongle=True)
        if why != "ok":
            self.stats["radio_rejected"] += 1
            return
        self.stats["radio_rx"] += 1
        if h.type == P.T_HEARTBEAT:
            hb = P.decode_heartbeat(P.payload_of(pkt, h))
            hb.update({"universe": h.universe, "net_id": h.net_id, "configured": h.net_id != 0,
                       "dongle_rssi": rssi, "last_seen": time.time()})
            self.nodes[src.hex(":")] = hb
        elif h.type == P.T_ACK:
            ack = P.decode_ack(pkt, h)
            ack["mac"] = src.hex(":")
            p = self.pending.get(h.seq)
            # a broadcast command is sent 3 times: a node answers each repeat with the
            # same stored ACK (PROTOCOL 6.2), keep one per node
            if p is not None and all(a["mac"] != ack["mac"] for a in p["acks"]):
                p["acks"].append(ack)

    # --- commands --------------------------------------------------------------------------------
    def resolve(self, target: str) -> bytes:
        if target in ("all", "*"):
            return P.BROADCAST
        try:
            return P.parse_mac(target)
        except ValueError:
            pass
        found = [m for m, n in self.nodes.items() if n.get("name") == target]
        if len(found) != 1:
            raise ValueError(f"unknown or ambiguous node: {target}")
        return P.parse_mac(found[0])

    async def command(self, target: bytes, opcode: int, args: bytes = b"") -> dict:
        if not self.link.connected.is_set():
            raise RuntimeError("dongle not connected")
        cmd_id = self.state.next_cmd_id()
        signed = self.key is not None and opcode != P.OP_IDENTIFY
        payload = P.serial_command(self.cfg.net_id, cmd_id, target, opcode, args,
                                   key=self.key if signed else None,
                                   counter=self.state.next_auth_counter() if signed else None)
        fut = asyncio.get_running_loop().create_future()
        self.pending[cmd_id] = {"future": fut, "acks": []}
        try:
            self.link.send(P.S_COMMAND, payload)
            res = await asyncio.wait_for(fut, self.COMMAND_TIMEOUT)
            await asyncio.sleep(0.05)   # an ACK may trail the result by a few ms on USB
        except asyncio.TimeoutError:
            res = {"result": "no_answer_from_dongle", "attempts": 0}
        finally:
            acks = self.pending.pop(cmd_id)["acks"]
        res["cmd_id"] = cmd_id
        res["acks"] = [{"mac": a["mac"], "status": a["status"], "data": a["data"].hex()} for a in acks]
        return res

    async def handle(self, req: dict) -> dict:
        cmd = req.get("cmd")
        if cmd == "nodes":
            now = time.time()
            return {"nodes": [dict(n, mac=m, age_s=round(now - n["last_seen"], 1),
                                   stale=now - n["last_seen"] > self.NODE_STALE_S)
                              for m, n in sorted(self.nodes.items(), key=lambda kv: kv[1].get("name", ""))]}
        if cmd == "status":
            if self.link.connected.is_set():   # wait for the fresh STATUS, not the last one
                self.status_event.clear()
                self.link.send(P.S_GET_STATUS)
                try:
                    await asyncio.wait_for(self.status_event.wait(), 0.5)
                except asyncio.TimeoutError:
                    pass
            return {"dongle_connected": self.link.connected.is_set(), "dongle": self.dongle_status,
                    "dongle_config_ok": not self.config_mismatch, "dongle_logs": list(self.dongle_logs),
                    "reconnects": self.link.reconnects, "serial_errors_pi": self.link.decoder.errors,
                    "universes": self.cfg.universes, "net_id": self.cfg.net_id, "channel": self.cfg.channel,
                    "authentication": self.key is not None, "stats": self.stats}
        if cmd == "dongle_config":
            # runtime change (not written to the TOML file): checked like the file
            allowed = {"channel": int, "power_dbm": int, "hold_timeout_ms": int, "refresh_hz": int,
                       "phy_rate": str, "mode": str}
            new = config.Config(**vars(self.cfg))
            for k, v in req.get("values", {}).items():
                if k not in allowed:
                    raise ValueError(f"unknown dongle key: {k}")
                setattr(new, k, allowed[k](v))
            config.check(new)
            self.cfg = new
            self.on_connect()
            return {"sent": self.cfg.dongle_values()}
        target = self.resolve(req.get("target", ""))
        if cmd == "identify":
            return await self.command(target, P.OP_IDENTIFY, struct.pack("<H", int(req.get("duration", 10))))
        if cmd == "set":
            values = dict(req.get("values", {}))
            if values.get("net_key") == "daemon":      # enrolment: the daemon's own key
                if self.key is None:
                    raise ValueError("no network key configured on the daemon")
                values["net_key"] = self.key
            elif "net_key" in values:
                values["net_key"] = bytes.fromhex(values["net_key"])
            return await self.command(target, P.OP_SET_CONFIG, P.encode_config(values))
        if cmd == "get_config":
            res = await self.command(target, P.OP_GET_CONFIG)
            for a in res["acks"]:
                if a["status"] == "ok":
                    a["config"] = P.decode_config(bytes.fromhex(a.pop("data")))
            return res
        if cmd == "relay":
            return await self.command(target, P.OP_RELAY, bytes([RELAY_MODES[req.get("mode", "auto")]]))
        if cmd == "maintenance":
            return await self.command(target, P.OP_MAINTENANCE, struct.pack("<H", int(req.get("timeout", 0))))
        if cmd == "reboot":
            return await self.command(target, P.OP_REBOOT)
        if cmd == "factory_reset":
            return await self.command(target, P.OP_FACTORY_RESET, struct.pack("<I", P.FACTORY_RESET_CONFIRM))
        raise ValueError(f"unknown command: {cmd}")

    # --- control socket ---------------------------------------------------------------------------
    async def on_client(self, reader, writer):
        try:
            while line := await reader.readline():
                try:
                    reply = {"ok": True, **await self.handle(json.loads(line))}
                except Exception as e:   # reported to the CLI, the daemon goes on
                    reply = {"ok": False, "error": str(e)}
                writer.write((json.dumps(reply) + "\n").encode())
                await writer.drain()
        finally:
            writer.close()

    async def run(self):
        loop = asyncio.get_running_loop()
        transport, _ = await loop.create_datagram_endpoint(lambda: ArtNetServer(self),
                                                           local_addr=(self.cfg.artnet_bind, self.cfg.artnet_port),
                                                           reuse_port=True)
        os.makedirs(os.path.dirname(self.cfg.control_socket), exist_ok=True)
        if os.path.exists(self.cfg.control_socket):
            os.unlink(self.cfg.control_socket)
        server = await asyncio.start_unix_server(self.on_client, path=self.cfg.control_socket)
        os.chmod(self.cfg.control_socket, 0o660)
        log.info("Art-Net on %s:%d, universes %s; dongle %s; control %s", self.cfg.artnet_bind,
                 self.cfg.artnet_port, self.cfg.universes, self.cfg.dongle_port, self.cfg.control_socket)
        try:
            await self.link.run()
        finally:
            server.close()
            transport.close()


def main():
    ap = argparse.ArgumentParser(description="dmxnow daemon: Art-Net -> ESP-NOW")
    ap.add_argument("-c", "--config", default=config.DEFAULT_PATH)
    ap.add_argument("-v", "--verbose", action="store_true")
    a = ap.parse_args()
    logging.basicConfig(level=logging.DEBUG if a.verbose else logging.INFO,
                        format="%(levelname)s %(name)s: %(message)s")
    asyncio.run(Daemon(config.load(a.config)).run())


if __name__ == "__main__":
    main()
