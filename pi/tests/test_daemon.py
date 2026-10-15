"""Daemon against a simulated dongle on a pseudo-terminal (SPEC 8.5)."""
import asyncio
import contextlib
import io
import json
import socket
import struct

import pytest

from dmxnow import artnet, cli, config, show
from dmxnow import protocol as P
from dmxnow.daemon import Daemon
from dmxnow.dongle import DongleLink
from tests.fake_dongle import NODE_MAC, FakeDongle

NET = 0x1234
KEY = bytes(range(32))


def free_udp_port():
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture
def fast_link(monkeypatch):
    monkeypatch.setattr(DongleLink, "PING_PERIOD", 0.1)
    monkeypatch.setattr(DongleLink, "PONG_TIMEOUT", 0.6)
    monkeypatch.setattr(DongleLink, "RETRY_DELAY", 0.2)


def make(tmp_path, key=None):
    dongle = FakeDongle(NET, key)
    cfg = config.Config(artnet_bind="127.0.0.1", artnet_port=free_udp_port(), universes=[0, 3],
                        dongle_port=dongle.path, net_id=NET, state_dir=str(tmp_path / "state"),
                        net_key_file=str(tmp_path / "net_key"), control_socket=str(tmp_path / "ctl.sock"))
    if key:
        (tmp_path / "net_key").write_text(key.hex())
    return dongle, cfg


async def started(cfg):
    d = Daemon(cfg)
    task = asyncio.create_task(d.run())
    await asyncio.wait_for(d.link.connected.wait(), 5)
    return d, task


async def stop(d, task):
    d.link.stop()
    await asyncio.wait_for(task, 5)


async def cli_run(cfg, *args):
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        code = await asyncio.to_thread(cli.main, ["--socket", cfg.control_socket, *args])
    return code, out.getvalue()


def test_artnet_to_dongle_and_config_push(tmp_path, fast_link):
    dongle, cfg = make(tmp_path)

    async def scenario():
        d, task = await started(cfg)
        assert await asyncio.to_thread(dongle.wait, lambda: dongle.configs)
        assert P.encode_dongle_config(cfg.dongle_values()) == dongle.configs[0]
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.sendto(artnet.build_dmx(3, bytes([1, 2, 3, 4])), ("127.0.0.1", cfg.artnet_port))
            s.sendto(artnet.build_dmx(7, bytes([9, 9])), ("127.0.0.1", cfg.artnet_port))   # not forwarded
            s.sendto(artnet.build_poll(), ("127.0.0.1", cfg.artnet_port))
            s.settimeout(2)
            reply, _ = await asyncio.to_thread(s.recvfrom, 1024)   # the loop must keep running
        assert await asyncio.to_thread(dongle.wait, lambda: dongle.universes)
        assert dongle.universes == [(3, bytes([1, 2, 3, 4]))]
        assert sorted(artnet.parse_poll_reply(reply)["ports"]) == [0, 3]
        assert d.stats["artdmx_ignored"] == 1
        await stop(d, task)

    asyncio.run(scenario())
    dongle.close()


def test_reconnection_when_the_dongle_stops_answering(tmp_path, fast_link):
    dongle, cfg = make(tmp_path)

    async def scenario():
        d, task = await started(cfg)
        dongle.answer_pings = False                       # USB alive but dongle hung
        assert await asyncio.to_thread(dongle.wait, lambda: d.link.reconnects >= 1, 5)
        dongle.answer_pings = True
        await asyncio.wait_for(d.link.connected.wait(), 5)
        # configuration pushed again after the reconnection
        assert await asyncio.to_thread(dongle.wait, lambda: len(dongle.configs) >= 2)
        # universes go through again
        d.on_artdmx(0, 0, b"\x05\x06")
        assert await asyncio.to_thread(dongle.wait, lambda: (0, b"\x05\x06") in dongle.universes)
        await stop(d, task)

    asyncio.run(scenario())
    dongle.close()


def test_cli_nodes_identify_get_and_unknown_target(tmp_path, fast_link):
    dongle, cfg = make(tmp_path)

    async def scenario():
        d, task = await started(cfg)
        dongle.heartbeat(name="lyre-cour", slots=512)
        assert await asyncio.to_thread(dongle.wait, lambda: d.nodes)
        code, out = await cli_run(cfg, "nodes")
        assert code == 0 and "lyre-cour" in out and "24:0a:c4:12:34:56" in out
        code, out = await cli_run(cfg, "identify", "lyre-cour", "-d", "5")
        assert code == 0 and "acked" in out and "ok" in out
        ident = [p for t, p in dongle.frames if t == P.S_COMMAND][-1]
        assert ident[2] == 0 and ident[3 + 6] == P.OP_IDENTIFY          # never signed
        code, out = await cli_run(cfg, "get", "24:0a:c4:12:34:56")
        assert code == 0 and "start_address = 1" in out
        code, out = await cli_run(cfg, "relay", "aa:bb:cc:dd:ee:ff", "on")
        assert code == 1 and "timeout" in out                            # nobody answers
        with pytest.raises(SystemExit):
            await cli_run(cfg, "identify", "no-such-node")
        await stop(d, task)

    asyncio.run(scenario())
    dongle.close()


def test_show_deploy_info_and_clear(tmp_path, fast_link):
    dongle, cfg = make(tmp_path, key=KEY)
    s = show.Show("feu", [show.rel(1), show.rel(2), show.rel(3), show.rel(4)])
    for i in range(120):   # > 1 kB: several SHOW_WRITE chunks
        s.step(100, [200 + i % 50, 60, 0, i % 20])
    f = tmp_path / "feu.dxs"
    f.write_bytes(s.encode())

    async def scenario():
        d, task = await started(cfg)
        dongle.heartbeat(name="lyre-cour")
        assert await asyncio.to_thread(dongle.wait, lambda: d.nodes)
        code, out = await cli_run(cfg, "show", "deploy", str(f), "lyre-cour")
        assert code == 0 and "deployed" in out, out
        assert dongle.show is not None and dongle.show.encode() == f.read_bytes()
        writes = [p for t, p in dongle.frames if t == P.S_COMMAND and p[3 + 6] == P.OP_SHOW_WRITE]
        assert len(writes) == -(-len(f.read_bytes()) // show.WRITE_CHUNK)
        assert all(p[2] & P.F_AUTH for p in writes)                       # signed like any command
        code, out = await cli_run(cfg, "show", "info", "lyre-cour")
        assert code == 0 and "feu, playing" in out and "120 keyframes" in out, out
        code, out = await cli_run(cfg, "show", "clear", "*")              # node by node only
        assert code == 1 and "node by node" in out and dongle.show is not None
        code, out = await cli_run(cfg, "show", "clear", "lyre-cour")
        assert code == 0 and dongle.show is None
        code, out = await cli_run(cfg, "show", "info", "lyre-cour")
        assert code == 0 and "no show" in out
        bad = tmp_path / "bad.dxs"
        bad.write_bytes(f.read_bytes()[:-1])
        with pytest.raises(SystemExit):                                   # refused before any upload
            await cli_run(cfg, "show", "deploy", str(bad), "lyre-cour")
        await stop(d, task)

    asyncio.run(scenario())
    dongle.close()


def test_ota_over_the_radio(tmp_path, fast_link):
    dongle, cfg = make(tmp_path, key=KEY)
    image = bytes([P.OTA_IMAGE_MAGIC]) + bytes((i * 7) & 0xFF for i in range(2999))   # 16 chunks
    fw = tmp_path / "firmware.bin"
    fw.write_bytes(image)

    async def scenario():
        d, task = await started(cfg)
        dongle.heartbeat(name="lyre-cour")
        assert await asyncio.to_thread(dongle.wait, lambda: d.nodes)
        code, out = await cli_run(cfg, "ota", str(fw), "lyre-cour", "--no-wait")
        assert code == 0 and "updated" in out, out
        assert dongle.firmware == image
        writes = [p for t, p in dongle.frames if t == P.S_COMMAND and p[3 + 6] == P.OP_OTA_WRITE]
        assert len(writes) == -(-len(image) // show.WRITE_CHUNK)
        assert all(p[2] & P.F_AUTH for p in writes)                        # signed like any command
        code, out = await cli_run(cfg, "ota", str(fw), "*", "--no-wait")   # node by node only
        assert code == 1 and "node by node" in out
        factory = bytes([P.OTA_IMAGE_MAGIC]) + bytes(0x8000 - 1) + b"\xaa\x50" + image   # bootloader first
        for bad in (b"\x00" + image[1:], factory,
                    bytes([P.OTA_IMAGE_MAGIC]) * (P.OTA_SLOT_SIZE + 1)):
            f = tmp_path / "bad.bin"
            f.write_bytes(bad)
            with pytest.raises(SystemExit):                                # refused before any upload
                await cli_run(cfg, "ota", str(f), "lyre-cour", "--no-wait")
        await stop(d, task)

    asyncio.run(scenario())
    dongle.close()


def test_signed_commands_and_enrolment(tmp_path, fast_link):
    dongle, cfg = make(tmp_path, key=KEY)

    async def scenario():
        d, task = await started(cfg)
        # an unconfigured node (net_id 0) is heard and shown as not enrolled
        dongle.heartbeat(name="node-123456", net_id=0)
        assert await asyncio.to_thread(dongle.wait, lambda: d.nodes)
        assert not d.nodes[NODE_MAC.hex(":")]["configured"]
        code, out = await cli_run(cfg, "enroll", "node-123456", "--universe", "3", "--address", "17",
                                  "--name", "lyre-cour", "--slots", "40")
        assert code == 0 and "ok" in out, out
        assert dongle.node_config["universe"] == 3 and dongle.node_config["start_address"] == 17
        assert dongle.node_config["net_key"] == KEY.hex() and dongle.node_config["net_id"] == NET
        # every command is signed with a strictly increasing counter, persisted
        code, out = await cli_run(cfg, "relay", "24:0a:c4:12:34:56", "off")
        assert code == 0 and "ok" in out
        first = dongle.last_counter
        code, out = await cli_run(cfg, "reboot", "24:0a:c4:12:34:56")
        assert code == 0 and dongle.last_counter == first + 1
        assert config.State(cfg.state_dir).auth_counter == dongle.last_counter
        await stop(d, task)

    asyncio.run(scenario())
    dongle.close()


def test_state_counters_survive_a_restart(tmp_path):
    s = config.State(str(tmp_path))
    assert [s.next_auth_counter() for _ in range(3)] == [1, 2, 3]
    s.cmd_id = 0xFFFF
    assert s.next_cmd_id() == 0                    # cmd_id wraps, the counter never does
    again = config.State(str(tmp_path))
    assert again.auth_counter == 3 and again.next_auth_counter() == 4


def test_lost_state_starts_cmd_id_at_random(tmp_path, monkeypatch):
    # nodes keep the ACKs of their last 16 cmd_id in RAM: a Pi that lost state.json and
    # restarts at cmd_id 1 would get old answers back for commands never executed
    monkeypatch.setattr(config.secrets, "randbelow", lambda n: 40000)
    fresh = config.State(str(tmp_path))
    assert fresh.cmd_id == 40000 and fresh.next_cmd_id() == 40001
    (tmp_path / "state.json").write_text("not json")
    assert config.State(str(tmp_path)).cmd_id == 40000     # unreadable file: same as lost
    (tmp_path / "state.json").write_text('{"auth_counter": 7, "cmd_id": 12}')
    assert config.State(str(tmp_path)).cmd_id == 12        # kept when the file is there


def test_config_file(tmp_path):
    p = tmp_path / "dmxnowd.toml"
    p.write_text('[artnet]\nuniverses = [0, 1, 2]\n[dongle]\nnet_id = 4660\nchannel = 11\nphy_rate = "12M"\n')
    c = config.load(str(p))
    assert c.universes == [0, 1, 2] and c.channel == 11 and c.dongle_values()["phy_rate"] == 0x0A
    p.write_text("[dongle]\nnet_id = 0\n")
    with pytest.raises(ValueError):
        config.load(str(p))
    p.write_text('[dongle]\nnet_id = 1\nmode = "v3"\n')
    with pytest.raises(ValueError):
        config.load(str(p))


def test_status_json(tmp_path, fast_link):
    dongle, cfg = make(tmp_path)

    async def scenario():
        d, task = await started(cfg)
        code, out = await cli_run(cfg, "--json", "status")
        st = json.loads(out)
        assert code == 0 and st["dongle_connected"] and st["net_id"] == NET and not st["authentication"]
        code, out = await cli_run(cfg, "--json", "dongle-config", "channel=11", "phy_rate=1M")
        assert json.loads(out)["sent"]["channel"] == 11
        assert await asyncio.to_thread(dongle.wait, lambda: len(dongle.configs) >= 2)
        assert dongle.configs[-1][:3] == bytes([0x01, 1, 11])
        await stop(d, task)

    asyncio.run(scenario())
    dongle.close()


def test_config_limits_match_the_dongle():
    # the dongle applies DONGLE_CONFIG all or nothing (firmware/common/src/dongle.cpp):
    # a value it refuses must be refused here first
    for bad in ({"refresh_hz": 100}, {"refresh_hz": 0}, {"hold_timeout_ms": 500}, {"universes": list(range(9))}):
        with pytest.raises(ValueError):
            config.check(config.Config(net_id=1, **bad))
    config.check(config.Config(net_id=1, refresh_hz=60, hold_timeout_ms=1000, universes=list(range(8))))


def test_dongle_status_checked_and_config_sent_again(tmp_path, fast_link):
    dongle, cfg = make(tmp_path)

    async def scenario():
        d, task = await started(cfg)
        assert await asyncio.to_thread(dongle.wait, lambda: dongle.configs)
        code, out = await cli_run(cfg, "--json", "status")
        st = json.loads(out)
        assert code == 0 and st["dongle_config_ok"] and st["dongle"]["net_id"] == NET
        # the dongle lost its settings (e.g. configuration sent while its USB port was
        # coming up): the next STATUS shows it, the daemon sends the configuration again
        dongle.settings["channel"], dongle.net_id = 3, 0
        dongle.status()
        assert await asyncio.to_thread(dongle.wait, lambda: len(dongle.configs) >= 2)
        assert dongle.net_id == NET and dongle.settings["channel"] == cfg.channel
        # a refusal is logged by the dongle and shown by "status"
        dongle.log("DONGLE_CONFIG refused (test)")
        code, out = await cli_run(cfg, "--json", "status")
        assert any("refused (test)" in x["text"] for x in json.loads(out)["dongle_logs"])
        await stop(d, task)

    asyncio.run(scenario())
    dongle.close()


def test_broadcast_acks_counted_once_per_node(tmp_path):
    dongle, cfg = make(tmp_path)
    d = Daemon(cfg)
    d.pending[77] = {"future": None, "acks": []}
    ack = P.build_packet(P.Header(type=P.T_ACK, net_id=NET, universe=P.NO_UNIVERSE, seq=77), bytes([1, 0]))
    for _ in range(3):   # the node answers each of the 3 broadcast emissions
        d.on_radio(-50, NODE_MAC, ack)
    assert len(d.pending[77]["acks"]) == 1
    dongle.close()
