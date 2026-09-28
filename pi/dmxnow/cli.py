"""dmxnow: command line client of dmxnowd (EF-13), through the control socket."""
from __future__ import annotations

import argparse
import json
import socket
import sys

from . import config
from . import protocol as P

INT_KEYS = {k for k, (_, kind) in P.CONFIG_KEYS.items() if kind.startswith("u")}


def request(sock_path: str, req: dict) -> dict:
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:
        s.settimeout(10)
        s.connect(sock_path)
        s.sendall((json.dumps(req) + "\n").encode())
        buf = b""
        while not buf.endswith(b"\n"):
            chunk = s.recv(65536)
            if not chunk:
                break
            buf += chunk
    return json.loads(buf)


def parse_values(items):
    out = {}
    for it in items:
        if "=" not in it:
            raise SystemExit(f"expected key=value, got {it!r}")
        k, v = it.split("=", 1)
        if k not in P.CONFIG_KEYS:
            raise SystemExit(f"unknown key {k!r}; keys: {', '.join(P.CONFIG_KEYS)}")
        out[k] = int(v, 0) if k in INT_KEYS else v
    return out


def show_nodes(nodes):
    cols = [("name", 16), ("mac", 17), ("variant", 8), ("universe", 8), ("start_address", 7), ("dmx_out_slots", 5),
            ("rssi", 5), ("lost_frames", 7), ("relay", 6), ("uptime_s", 8), ("fw_version", 7), ("age_s", 6)]
    heads = {"start_address": "addr", "dmx_out_slots": "slots", "lost_frames": "lost", "uptime_s": "uptime",
             "fw_version": "fw", "age_s": "seen"}
    print("  ".join(heads.get(c, c).ljust(w) for c, w in cols))
    for n in nodes:
        n = dict(n, relay=("ON" if n["relay_on"] else "off") + ("*" if n["relay_forced"] else ""))
        line = "  ".join(str(n.get(c, "")).ljust(w)[:max(w, len(str(n.get(c, ""))))] for c, w in cols)
        flags = []
        if not n.get("configured"):
            flags.append("NOT ENROLLED")
        if n.get("stale"):
            flags.append("SILENT")
        if n.get("maintenance"):
            flags.append("MAINTENANCE")
        print(line + ("  " + ", ".join(flags) if flags else ""))
    short = [n["name"] for n in nodes if n.get("dmx_out_slots") == 512]
    if short:   # arbitration A3: 512 is the most compatible but the slowest
        print(f"\nnote: {', '.join(short)} still send 512-slot DMX frames; set dmx_out_slots to the "
              "fixture's last channel for the lowest latency (SPEC 5.1)", file=sys.stderr)


def show_result(res):
    print(f"cmd {res['cmd_id']}: {res['result']} ({res['attempts']} attempt(s))")
    for a in res["acks"]:
        print(f"  {a['mac']}: {a['status']}")
        if "config" in a:
            for k, v in a["config"].items():
                print(f"    {k} = {v}")


def main(argv=None):
    ap = argparse.ArgumentParser(prog="dmxnow", description="dmxnow nodes and dongle control")
    ap.add_argument("--socket", default=config.Config().control_socket)
    ap.add_argument("--json", action="store_true", help="raw JSON output")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("nodes", help="list the nodes heard")
    sub.add_parser("status", help="daemon and dongle status")
    p = sub.add_parser("identify", help="blink a node (IDENTIFY)")
    p.add_argument("target", help="MAC, name or 'all'")
    p.add_argument("-d", "--duration", type=int, default=10)
    p = sub.add_parser("set", help="SET_CONFIG key=value ...")
    p.add_argument("target")
    p.add_argument("values", nargs="+")
    p = sub.add_parser("enroll", help="join a new node to this network (net_id, key, universe, address)")
    p.add_argument("target")
    p.add_argument("--universe", type=int, required=True)
    p.add_argument("--address", type=int, required=True)
    p.add_argument("--name")
    p.add_argument("--slots", type=int, help="dmx_out_slots: last channel used by the fixture")
    p = sub.add_parser("get", help="GET_CONFIG")
    p.add_argument("target")
    p = sub.add_parser("relay", help="force the relay or give it back to DMX")
    p.add_argument("target")
    p.add_argument("mode", choices=["on", "off", "auto"])
    p = sub.add_parser("maintenance", help="access point + web page on the node")
    p.add_argument("target")
    p.add_argument("-t", "--timeout", type=int, default=0)
    p = sub.add_parser("reboot")
    p.add_argument("target")
    p = sub.add_parser("factory-reset")
    p.add_argument("target")
    p.add_argument("--yes", action="store_true", required=True, help="confirm")
    p = sub.add_parser("dongle-config", help="channel=, power_dbm=, phy_rate=, hold_timeout_ms=, refresh_hz=, mode=")
    p.add_argument("values", nargs="+")
    a = ap.parse_args(argv)

    if a.cmd in ("nodes", "status"):
        req = {"cmd": a.cmd}
    elif a.cmd == "identify":
        req = {"cmd": "identify", "target": a.target, "duration": a.duration}
    elif a.cmd == "set":
        req = {"cmd": "set", "target": a.target, "values": parse_values(a.values)}
    elif a.cmd == "enroll":
        st = request(a.socket, {"cmd": "status"})
        values = {"net_id": st["net_id"], "universe": a.universe, "start_address": a.address}
        if a.name:
            values["name"] = a.name
        if a.slots:
            values["dmx_out_slots"] = a.slots
        if st.get("authentication"):
            values["net_key"] = "daemon"
        req = {"cmd": "set", "target": a.target, "values": values}
    elif a.cmd == "get":
        req = {"cmd": "get_config", "target": a.target}
    elif a.cmd == "relay":
        req = {"cmd": "relay", "target": a.target, "mode": a.mode}
    elif a.cmd == "maintenance":
        req = {"cmd": "maintenance", "target": a.target, "timeout": a.timeout}
    elif a.cmd == "reboot":
        req = {"cmd": "reboot", "target": a.target}
    elif a.cmd == "factory-reset":
        req = {"cmd": "factory_reset", "target": a.target}
    else:
        values = {}
        for it in a.values:
            k, v = it.split("=", 1)
            values[k] = v if k in ("phy_rate", "mode") else int(v, 0)
        req = {"cmd": "dongle_config", "values": values}

    try:
        res = request(a.socket, req)
    except OSError as e:
        raise SystemExit(f"cannot reach dmxnowd on {a.socket}: {e}")
    if not res.pop("ok", False):
        raise SystemExit(f"error: {res.get('error')}")
    if a.json:
        print(json.dumps(res, indent=1))
    elif a.cmd == "nodes":
        show_nodes(res["nodes"])
    elif "acks" in res:
        show_result(res)
    else:
        print(json.dumps(res, indent=1))
    # non-zero exit for scripts: no answer, or a node that refused (invalid_arg,
    # auth_failed...), or a dongle running with other settings than the daemon's
    if "acks" in res and res["result"] != "acked" and res["result"] != "broadcast_done":
        return 1
    if "acks" in res and any(ack["status"] != "ok" for ack in res["acks"]):
        return 1
    if a.cmd == "status" and res.get("dongle_config_ok") is False:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
