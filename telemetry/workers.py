from __future__ import annotations

import socket
import time
from typing import Optional

from PyQt5 import QtCore

from omnilink.telemetry.mavlink_utils import mavlink_v1_heartbeat_packet


class UdpPrimer(QtCore.QThread):
    done = QtCore.pyqtSignal(bool)

    def __init__(
        self,
        listen_port: int,
        upstream_ip: str,
        upstream_port: int,
        count: int = 3,
        interval_ms: int = 200,
        use_mavlink_heartbeat: bool = True,
        parent=None,
    ):
        super().__init__(parent)
        self.listen_port = int(listen_port)
        self.upstream_ip = upstream_ip
        self.upstream_port = int(upstream_port)
        self.count = max(1, int(count))
        self.interval_ms = max(10, int(interval_ms))
        self.use_mavlink_heartbeat = bool(use_mavlink_heartbeat)

    def run(self):
        s: Optional[socket.socket] = None
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind(("0.0.0.0", self.listen_port))
            seq = 0
            for _i in range(self.count):
                payload = mavlink_v1_heartbeat_packet(seq) if self.use_mavlink_heartbeat else b"hi"
                seq = (seq + 1) & 0xFF
                s.sendto(payload, (self.upstream_ip, self.upstream_port))
                time.sleep(self.interval_ms / 1000.0)
            self.done.emit(True)
        except Exception:
            self.done.emit(False)
        finally:
            try:
                if s:
                    s.close()
            except Exception:
                pass


class TcpRxDetector(QtCore.QThread):
    detected = QtCore.pyqtSignal()

    def __init__(self, tcp_port: int, parent=None):
        super().__init__(parent)
        self.tcp_port = int(tcp_port)
        self._stop = False

    def stop(self):
        self._stop = True

    def run(self):
        while not self._stop:
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.settimeout(1.2)
                s.connect(("127.0.0.1", self.tcp_port))
                s.settimeout(1.0)
                while not self._stop:
                    try:
                        data = s.recv(4096)
                        if data:
                            try:
                                s.close()
                            except Exception:
                                pass
                            self.detected.emit()
                            return
                    except socket.timeout:
                        continue
            except Exception:
                time.sleep(0.6)
