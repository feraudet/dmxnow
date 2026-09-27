"""Serial link to the dongle (PROTOCOL §8, EF-02): pyserial read in a dedicated thread
bridged to asyncio, PING every second, port reopened after 3 s without PONG or on any
error (USB unplugged), dongle configuration pushed at each (re)connection."""
from __future__ import annotations

import asyncio
import logging
import struct
import threading
import time

import serial

from . import protocol as P

log = logging.getLogger("dmxnow.dongle")


class DongleLink:
    PING_PERIOD = 1.0
    PONG_TIMEOUT = 3.0
    RETRY_DELAY = 1.0

    def __init__(self, port: str, on_frame, on_connect=None, baudrate: int = 921600):
        self.port = port
        self.baudrate = baudrate
        self.on_frame = on_frame          # (type, seq, payload), called in the event loop
        self.on_connect = on_connect      # called in the event loop after each (re)connection
        self.ser = None
        self.loop = None
        self.decoder = P.SerialDecoder()
        self.seq = 0
        self.lock = threading.Lock()
        self.connected = asyncio.Event()
        self.reconnects = 0
        self.last_pong = 0.0
        self._broken = None
        self._stop = False

    # --- public ---------------------------------------------------------------------------
    def send(self, ftype: int, payload: bytes = b"") -> bool:
        """Non-blocking write of one frame; False when the dongle is not connected."""
        ser = self.ser
        if ser is None:
            return False
        frame = P.serial_encode(ftype, self.seq, payload)
        self.seq = (self.seq + 1) & 0xFF
        try:
            with self.lock:
                ser.write(frame)
            return True
        except (serial.SerialException, OSError) as e:
            self._fail(f"write: {e}")
            return False

    async def run(self):
        self.loop = asyncio.get_running_loop()
        while not self._stop:
            try:
                self.ser = serial.Serial(self.port, self.baudrate, timeout=0.05, write_timeout=0.5)
            except (serial.SerialException, OSError) as e:
                log.debug("open %s: %s", self.port, e)
                await asyncio.sleep(self.RETRY_DELAY)
                continue
            self._broken = self.loop.create_future()
            reader = threading.Thread(target=self._reader, args=(self.ser,), daemon=True)
            reader.start()
            self.last_pong = time.monotonic()
            self.connected.set()
            log.info("dongle connected on %s", self.port)
            if self.on_connect:
                self.on_connect()
            try:
                await self._supervise()
            finally:
                self.connected.clear()
                ser, self.ser = self.ser, None
                try:
                    ser.close()
                except Exception:
                    pass
                reader.join(timeout=1)
                self.reconnects += 1
            if not self._stop:
                await asyncio.sleep(self.RETRY_DELAY)

    def stop(self):
        self._stop = True
        if self._broken and not self._broken.done():
            self._broken.set_result("stop")

    # --- internals ------------------------------------------------------------------------------
    async def _supervise(self):
        while True:
            self.send(P.S_PING, struct.pack("<I", int(time.monotonic() * 1000) & 0xFFFFFFFF))
            try:
                reason = await asyncio.wait_for(asyncio.shield(self._broken), self.PING_PERIOD)
                log.warning("dongle link closed: %s", reason)
                return
            except asyncio.TimeoutError:
                pass
            if time.monotonic() - self.last_pong > self.PONG_TIMEOUT:
                log.warning("no PONG for %.0f s: reopening %s", self.PONG_TIMEOUT, self.port)
                return

    def _reader(self, ser):
        while ser.is_open:
            try:
                data = ser.read(max(1, ser.in_waiting))
            except (serial.SerialException, OSError, TypeError) as e:
                self.loop.call_soon_threadsafe(self._fail, f"read: {e}")
                return
            if data:
                self.loop.call_soon_threadsafe(self._feed, data)

    def _feed(self, data: bytes):
        for ftype, seq, payload in self.decoder.feed(data):
            if ftype == P.S_PONG:
                self.last_pong = time.monotonic()
            self.on_frame(ftype, seq, payload)

    def _fail(self, reason: str):
        if self._broken and not self._broken.done():
            self._broken.set_result(reason)
