from __future__ import annotations

import os
import tempfile
from typing import List, Optional

from PyQt5 import QtCore, QtWidgets

from omnilink.utils import find_free_tcp_port, is_valid_ip, is_valid_port, set_status_label, which
from omnilink.telemetry.workers import TcpRxDetector, UdpPrimer


class RouterWidget(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.router_bin = which("mavlink-routerd") or "mavlink-routerd"
        self.proc = QtCore.QProcess(self)
        self.proc.setProcessChannelMode(QtCore.QProcess.MergedChannels)
        self.proc.stateChanged.connect(self._on_proc_state)

        self.primer: Optional[UdpPrimer] = None
        self.rxdet: Optional[TcpRxDetector] = None

        self._effective_tcp_port = 5760
        self._mavlink_seen = False

        self._build_ui()
        self._apply_input_mode()

        self._ui_timer = QtCore.QTimer(self)
        self._ui_timer.setInterval(800)
        self._ui_timer.timeout.connect(self._refresh_status)
        self._ui_timer.start()
        self._refresh_status()

    # -------------------------
    # UI
    # -------------------------
    def _build_ui(self):
        v = QtWidgets.QVBoxLayout(self)

        top = QtWidgets.QHBoxLayout()
        v.addLayout(top)

        self.btn_start = QtWidgets.QPushButton("Start Router")
        self.btn_stop = QtWidgets.QPushButton("Stop")
        self.btn_stop.setEnabled(False)

        self.btn_start.clicked.connect(self.start)
        self.btn_stop.clicked.connect(self.stop)

        self.state = QtWidgets.QLabel("STOPPED")
        self.state.setStyleSheet("font-weight:700; color: rgb(180, 60, 60);")

        top.addWidget(self.btn_start)
        top.addWidget(self.btn_stop)
        top.addStretch(1)
        top.addWidget(QtWidgets.QLabel("Status:"))
        top.addWidget(self.state)

        gb = QtWidgets.QGroupBox("Link Settings")
        v.addWidget(gb)
        g = QtWidgets.QGridLayout(gb)

        self.in_mode = QtWidgets.QComboBox()
        self.in_mode.addItems(["UDP (Server)", "TCP (Client)"])
        self.in_mode.setCurrentIndex(0)
        self.in_mode.currentIndexChanged.connect(lambda _i: self._apply_input_mode())

        self.listen_port = QtWidgets.QSpinBox()
        self.listen_port.setRange(1, 65535)
        self.listen_port.setValue(19856)

        self.tcp_up_ip = QtWidgets.QLineEdit("192.168.144.12")
        self.tcp_up_port = QtWidgets.QSpinBox()
        self.tcp_up_port.setRange(1, 65535)
        self.tcp_up_port.setValue(5760)

        self.upstream_ip = QtWidgets.QLineEdit("192.168.144.12")
        self.upstream_port = QtWidgets.QSpinBox()
        self.upstream_port.setRange(1, 65535)
        self.upstream_port.setValue(19856)

        self.tcp_port = QtWidgets.QSpinBox()
        self.tcp_port.setRange(0, 65535)
        self.tcp_port.setValue(5760)

        self.run_sudo = QtWidgets.QCheckBox("Administrator")
        self.run_sudo.setChecked(False)

        self.do_primer = QtWidgets.QCheckBox("Primer")
        self.do_primer.setChecked(True)

        self.targets = QtWidgets.QPlainTextEdit()
        self.targets.setPlaceholderText(
            "One target per line, format: IP:PORT\nExample:\n192.168.144.98:14550\n192.168.144.120:14550"
        )
        self.targets.setPlainText("192.168.144.98:14550\n192.168.144.120:14550")

        self.rx_lbl = QtWidgets.QLabel("RX: waiting")
        self.rx_lbl.setStyleSheet("font-weight:600; color: rgb(140, 140, 140);")

        g.addWidget(QtWidgets.QLabel("Input mode"), 0, 0)
        g.addWidget(self.in_mode, 0, 1, 1, 3)

        g.addWidget(QtWidgets.QLabel("Listen UDP port"), 1, 0)
        g.addWidget(self.listen_port, 1, 1)
        g.addWidget(QtWidgets.QLabel("TCP server port"), 1, 2)
        g.addWidget(self.tcp_port, 1, 3)

        g.addWidget(QtWidgets.QLabel("TCP upstream IP"), 2, 0)
        g.addWidget(self.tcp_up_ip, 2, 1)
        g.addWidget(QtWidgets.QLabel("TCP upstream port"), 2, 2)
        g.addWidget(self.tcp_up_port, 2, 3)

        g.addWidget(QtWidgets.QLabel("Upstream IP"), 3, 0)
        g.addWidget(self.upstream_ip, 3, 1)
        g.addWidget(QtWidgets.QLabel("Upstream port"), 3, 2)
        g.addWidget(self.upstream_port, 3, 3)

        g.addWidget(self.do_primer, 4, 0, 1, 2)
        g.addWidget(self.run_sudo, 4, 2, 1, 2)

        g.addWidget(QtWidgets.QLabel("Targets"), 5, 0, 1, 4)
        g.addWidget(self.targets, 6, 0, 1, 4)

        g.addWidget(self.rx_lbl, 7, 0, 1, 4)

        v.addStretch(1)

    def _apply_input_mode(self) -> None:
        tcp_mode = (self.in_mode.currentIndex() == 1)

        self.listen_port.setEnabled(not tcp_mode)

        self.tcp_up_ip.setEnabled(tcp_mode)
        self.tcp_up_port.setEnabled(tcp_mode)

        self.do_primer.setEnabled(not tcp_mode)
        self.upstream_ip.setEnabled(not tcp_mode)
        self.upstream_port.setEnabled(not tcp_mode)

    # -------------------------
    # Validation and config build
    # -------------------------
    def _parse_targets(self) -> List[tuple[str, int]]:
        items: List[tuple[str, int]] = []
        for raw in self.targets.toPlainText().splitlines():
            line = raw.strip()
            if not line:
                continue
            if ":" not in line:
                raise ValueError(f"Target invalid: {line} (gunakan IP:PORT)")
            ip, ps = line.rsplit(":", 1)
            ip = ip.strip()
            ps = ps.strip()
            if not is_valid_ip(ip):
                raise ValueError(f"Target IP invalid: {ip}")
            if not ps.isdigit():
                raise ValueError(f"Target port invalid: {line}")
            port = int(ps)
            if not is_valid_port(port):
                raise ValueError(f"Target port invalid: {line}")
            items.append((ip, port))
        if not items:
            raise ValueError("Target fanout kosong")
        return items

    def _build_input_lines(self) -> List[str]:
        tcp_mode = (self.in_mode.currentIndex() == 1)
        if not tcp_mode:
            addr = "0.0.0.0"
            in_port = int(self.listen_port.value())
            if not is_valid_port(in_port):
                raise ValueError("Listen port invalid")
            return ["[UdpEndpoint input]", "Mode=Server", f"Address={addr}", f"Port={in_port}", ""]
        tip = self.tcp_up_ip.text().strip()
        tport = int(self.tcp_up_port.value())
        if not is_valid_ip(tip):
            raise ValueError("TCP upstream IP invalid")
        if not is_valid_port(tport):
            raise ValueError("TCP upstream port invalid")
        return ["[TcpEndpoint input]", "Mode=Client", f"Address={tip}", f"Port={tport}", ""]

    def _build_output_lines(self, targets: List[tuple[str, int]]) -> List[str]:
        lines: List[str] = []
        seen = set()
        i = 1
        for ip, port in targets:
            key = (ip, port)
            if key in seen:
                continue
            seen.add(key)
            lines += [f"[UdpEndpoint gcs{i}]", "Mode=Normal", f"Address={ip}", f"Port={port}", ""]
            i += 1
        return lines

    def _build_config_text(self) -> str:
        tcp_ui = int(self.tcp_port.value())
        tcp_port = find_free_tcp_port(tcp_ui)
        self._effective_tcp_port = tcp_port

        targets = self._parse_targets()

        lines: List[str] = []
        lines.append("[General]")
        lines.append(f"TcpServerPort={tcp_port}")
        lines.append("ReportStats=false")
        lines.append("")

        lines += self._build_input_lines()
        lines += self._build_output_lines(targets)

        return "\n".join(lines)

    def _write_temp_config(self) -> str:
        text = self._build_config_text()
        fd, path = tempfile.mkstemp(prefix="omni-link-router-", suffix=".conf")
        os.close(fd)
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)
        return path

    # -------------------------
    # RX detection and primer
    # -------------------------
    def _start_rx_detector(self):
        self._mavlink_seen = False
        self.rx_lbl.setText("RX: waiting")
        self.rx_lbl.setStyleSheet("font-weight:600; color: rgb(140, 140, 140);")

        tcp_port = int(self._effective_tcp_port)
        if tcp_port <= 0:
            self.rx_lbl.setText("RX: (TCP off)")
            self.rx_lbl.setStyleSheet("font-weight:600; color: rgb(140, 140, 140);")
            return

        self.rxdet = TcpRxDetector(tcp_port)
        self.rxdet.detected.connect(self._on_mavlink_detected)
        self.rxdet.start()

    def _on_mavlink_detected(self):
        if self._mavlink_seen:
            return
        self._mavlink_seen = True
        self.rx_lbl.setText("RX: detected")
        self.rx_lbl.setStyleSheet("font-weight:700; color: rgb(0, 150, 0);")
        if self.rxdet:
            self.rxdet.stop()

    def _stop_rx(self):
        if self.rxdet:
            self.rxdet.stop()
            self.rxdet.wait(600)
            self.rxdet = None

    def _run_primer_blocking(self):
        if self.in_mode.currentIndex() == 1:
            return
        if not self.do_primer.isChecked():
            return

        up_ip = self.upstream_ip.text().strip()
        up_port = int(self.upstream_port.value())
        listen_port = int(self.listen_port.value())

        if not is_valid_ip(up_ip) or not is_valid_port(up_port):
            return

        self.primer = UdpPrimer(
            listen_port=listen_port,
            upstream_ip=up_ip,
            upstream_port=up_port,
            count=3,
            interval_ms=200,
            use_mavlink_heartbeat=True,
        )
        self.primer.start()
        self.primer.wait(1200)
        self.primer = None

    # -------------------------
    # Process lifecycle
    # -------------------------
    def _on_proc_state(self, st: QtCore.QProcess.ProcessState):
        running = st == QtCore.QProcess.Running
        self.btn_start.setEnabled(not running)
        self.btn_stop.setEnabled(running)

    def start(self):
        if self.proc.state() == QtCore.QProcess.Running:
            return

        if not which("mavlink-routerd") and self.router_bin == "mavlink-routerd":
            QtWidgets.QMessageBox.critical(self, "OMNI-Link", "mavlink-routerd tidak ditemukan.")
            return

        try:
            conf_path = self._write_temp_config()
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "OMNI-Link", str(e))
            return

        self._run_primer_blocking()

        cmd = self.router_bin
        args = ["-c", conf_path]
        if self.run_sudo.isChecked():
            cmd = "sudo"
            args = [self.router_bin] + args

        self.proc.start(cmd, args)
        if not self.proc.waitForStarted(1500):
            QtWidgets.QMessageBox.critical(self, "OMNI-Link", "Gagal menjalankan mavlink-routerd.")
            return

        self._start_rx_detector()
        set_status_label(self.state, "RUNNING", True)

    def stop(self):
        self._stop_rx()
        if self.proc.state() != QtCore.QProcess.Running:
            return
        self.proc.terminate()
        if not self.proc.waitForFinished(1500):
            self.proc.kill()
            self.proc.waitForFinished(1500)
        set_status_label(self.state, "STOPPED", False)

    def _refresh_status(self):
        running = self.proc.state() == QtCore.QProcess.Running
        if running:
            set_status_label(self.state, "RUNNING", True)
        else:
            set_status_label(self.state, "STOPPED", False)

    def is_running(self) -> bool:
        return self.proc.state() == QtCore.QProcess.Running
