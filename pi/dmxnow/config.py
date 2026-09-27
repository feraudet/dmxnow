"""Daemon configuration (/etc/dmxnow/dmxnowd.toml, SPEC 4.11) and persistent state
(/var/lib/dmxnow: authentication counter, strictly increasing, PROTOCOL §7)."""
from __future__ import annotations

import json
import logging
import os
import tomllib
from dataclasses import dataclass, field

from . import protocol as P

log = logging.getLogger("dmxnow")

DEFAULT_PATH = "/etc/dmxnow/dmxnowd.toml"


@dataclass
class Config:
    artnet_bind: str = "0.0.0.0"
    artnet_port: int = 6454
    universes: list = field(default_factory=lambda: [0])
    announce_ip: str = "127.0.0.1"
    dongle_port: str = "/dev/dmx-dongle"
    channel: int = 6
    net_id: int = 0
    phy_rate: str = "6M"
    power_dbm: int = 15
    hold_timeout_ms: int = 10000
    refresh_hz: int = 44
    mode: str = "v2"
    net_key_file: str = "/etc/dmxnow/net_key"
    state_dir: str = "/var/lib/dmxnow"
    control_socket: str = "/run/dmxnow/control.sock"

    def dongle_values(self) -> dict:
        return {"channel": self.channel, "net_id": self.net_id, "phy_rate": P.PHY_RATES[self.phy_rate],
                "power_dbm": self.power_dbm, "hold_timeout_ms": self.hold_timeout_ms,
                "refresh_hz": self.refresh_hz, "mode": 1 if self.mode == "v1" else 0}

    def net_key(self):
        """32-byte network key (hex in a root-only file), None = no authentication."""
        try:
            with open(self.net_key_file) as f:
                k = bytes.fromhex(f.read().strip())
        except FileNotFoundError:
            return None
        if len(k) != 32:
            raise ValueError(f"{self.net_key_file}: the key must be 32 bytes (64 hex digits)")
        return k


def load(path: str = DEFAULT_PATH) -> Config:
    c = Config()
    if not os.path.exists(path):
        log.warning("%s not found: default configuration", path)
        return c
    with open(path, "rb") as f:
        d = tomllib.load(f)
    a, g, s, ctl = d.get("artnet", {}), d.get("dongle", {}), d.get("security", {}), d.get("control", {})
    c.artnet_bind = a.get("bind", c.artnet_bind)
    c.artnet_port = int(a.get("port", c.artnet_port))
    c.universes = [int(u) for u in a.get("universes", c.universes)]
    c.announce_ip = a.get("announce_ip", c.announce_ip)
    c.dongle_port = g.get("port", c.dongle_port)
    c.channel = int(g.get("channel", c.channel))
    c.net_id = int(g.get("net_id", c.net_id))
    c.phy_rate = str(g.get("phy_rate", c.phy_rate))
    c.power_dbm = int(g.get("power_dbm", c.power_dbm))
    c.hold_timeout_ms = int(g.get("hold_timeout_ms", c.hold_timeout_ms))
    c.refresh_hz = int(g.get("refresh_hz", c.refresh_hz))
    c.mode = g.get("mode", c.mode)
    c.net_key_file = s.get("net_key_file", c.net_key_file)
    c.state_dir = s.get("state_dir", c.state_dir)
    c.control_socket = ctl.get("socket", c.control_socket)
    check(c)
    return c


def check(c: Config):
    if not all(0 <= u <= P.MAX_UNIVERSE for u in c.universes):
        raise ValueError("universes: 0 to 32767")
    if not 1 <= c.channel <= 13:
        raise ValueError("dongle.channel: 1 to 13")
    if not 1 <= c.net_id <= 65535:
        raise ValueError("dongle.net_id: 1 to 65535 (0 = unconfigured is reserved to nodes)")
    if c.phy_rate not in P.PHY_RATES:
        raise ValueError(f"dongle.phy_rate: one of {', '.join(P.PHY_RATES)}")
    if not 2 <= c.power_dbm <= 20:
        raise ValueError("dongle.power_dbm: 2 to 20")
    if c.power_dbm > 15:
        # 5 dBi dipole on the dongle case: 15 dBm already gives ~20 dBm EIRP (EU limit)
        log.warning("dongle.power_dbm = %d: with the 5 dBi antenna the EIRP exceeds 20 dBm (EU limit)",
                    c.power_dbm)
    if c.mode not in ("v1", "v2"):
        raise ValueError("dongle.mode: v1 or v2")


class State:
    """Persistent counters: authentication counter (never reused) and next cmd_id."""

    def __init__(self, directory: str):
        self.path = os.path.join(directory, "state.json")
        os.makedirs(directory, exist_ok=True)
        try:
            with open(self.path) as f:
                d = json.load(f)
        except (FileNotFoundError, ValueError):
            d = {}
        self.auth_counter = int(d.get("auth_counter", 0))
        self.cmd_id = int(d.get("cmd_id", 0))

    def _save(self):
        tmp = self.path + ".tmp"
        with open(tmp, "w") as f:
            json.dump({"auth_counter": self.auth_counter, "cmd_id": self.cmd_id}, f)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, self.path)

    def next_auth_counter(self) -> int:
        self.auth_counter += 1
        self._save()   # persisted before use: a counter is never sent twice
        return self.auth_counter

    def next_cmd_id(self) -> int:
        self.cmd_id = (self.cmd_id + 1) & 0xFFFF
        self._save()
        return self.cmd_id
