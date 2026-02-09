from __future__ import annotations

import re
from pathlib import Path
from typing import List, Optional

from PyQt5 import QtCore, QtWidgets

from omnilink.utils import guess_ip, has_cmd, looks_like_rtsp, set_status_label
from omnilink.video.constants import FPS_CHOICES, MEDIAMTX_BIN_DEFAULT, RES_CHOICES, X264_PARAMS
from omnilink.video.devices import get_device_label, list_video_devices


class VideoWidget(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.mt: Optional[QtCore.QProcess] = None
        self.ff: Optional[QtCore.QProcess] = None

        self.watchdog = QtCore.QTimer(self)
        self.watchdog.setInterval(500)
        self.watchdog.timeout.connect(self._watch_processes)

        self._build_ui()
        self._update_out_url()
        self._apply_input_mode()

        self._ui_timer = QtCore.QTimer(self)
        self._ui_timer.setInterval(600)
        self._ui_timer.timeout.connect(self._refresh_status)
        self._ui_timer.start()
        self._refresh_status()

    # -------------------------
    # UI
    # -------------------------
    def _build_ui(self):
        v = QtWidgets.QVBoxLayout(self)

        gb = QtWidgets.QGroupBox("RTSP Output")
        v.addWidget(gb)
        g = QtWidgets.QGridLayout(gb)

        self.out_ip = QtWidgets.QLineEdit(guess_ip())
        self.out_port = QtWidgets.QSpinBox()
        self.out_port.setRange(1, 65535)
        self.out_port.setValue(8554)
        self.out_path = QtWidgets.QLineEdit("qgc")

        self.out_url = QtWidgets.QLineEdit("")
        self.out_url.setReadOnly(True)

        btn_copy = QtWidgets.QPushButton("Copy URL")
        btn_copy.clicked.connect(lambda: QtWidgets.QApplication.clipboard().setText(self.out_url.text().strip()))

        g.addWidget(QtWidgets.QLabel("PC IP"), 0, 0)
        g.addWidget(self.out_ip, 0, 1)
        g.addWidget(QtWidgets.QLabel("Port"), 0, 2)
        g.addWidget(self.out_port, 0, 3)
        g.addWidget(QtWidgets.QLabel("Path"), 0, 4)
        g.addWidget(self.out_path, 0, 5)

        g.addWidget(QtWidgets.QLabel("RTSP URL"), 1, 0)
        g.addWidget(self.out_url, 1, 1, 1, 4)
        g.addWidget(btn_copy, 1, 5)

        self.out_ip.textChanged.connect(self._update_out_url)
        self.out_path.textChanged.connect(self._update_out_url)
        self.out_port.valueChanged.connect(lambda _v: self._update_out_url())

        gb_in = QtWidgets.QGroupBox("Video Input")
        v.addWidget(gb_in)
        ig = QtWidgets.QGridLayout(gb_in)

        self.mode = QtWidgets.QComboBox()
        self.mode.addItems(["RTSP (default)", "Webcam"])
        self.mode.setCurrentIndex(0)
        self.mode.currentIndexChanged.connect(lambda _i: self._apply_input_mode())

        self.in_rtsp = QtWidgets.QLineEdit("rtsp://192.168.144.25:8554/main.264")
        self.in_rtsp.setPlaceholderText("rtsp://ip:port/path")

        self.cam_combo = QtWidgets.QComboBox()
        self.btn_refresh_cam = QtWidgets.QPushButton("Refresh")
        self.btn_refresh_cam.clicked.connect(self._refresh_cameras)

        self.res = QtWidgets.QComboBox()
        self.res.addItems(RES_CHOICES)
        self.res.setCurrentText("1280x720")

        self.fps = QtWidgets.QComboBox()
        self.fps.addItems(FPS_CHOICES)
        self.fps.setCurrentText("30")

        self.bitrate = QtWidgets.QSpinBox()
        self.bitrate.setRange(200, 20000)
        self.bitrate.setValue(2500)
        self.bitrate.setSuffix(" kbps")

        ig.addWidget(QtWidgets.QLabel("Input mode"), 0, 0)
        ig.addWidget(self.mode, 0, 1, 1, 3)

        ig.addWidget(QtWidgets.QLabel("RTSP URL"), 1, 0)
        ig.addWidget(self.in_rtsp, 1, 1, 1, 3)

        ig.addWidget(QtWidgets.QLabel("Webcam"), 2, 0)
        ig.addWidget(self.cam_combo, 2, 1, 1, 2)
        ig.addWidget(self.btn_refresh_cam, 2, 3)

        ig.addWidget(QtWidgets.QLabel("Resolution"), 3, 0)
        ig.addWidget(self.res, 3, 1)
        ig.addWidget(QtWidgets.QLabel("FPS"), 3, 2)
        ig.addWidget(self.fps, 3, 3)

        ig.addWidget(QtWidgets.QLabel("Bitrate"), 4, 0)
        ig.addWidget(self.bitrate, 4, 1)

        gb_ctl = QtWidgets.QGroupBox("Control")
        v.addWidget(gb_ctl)
        h = QtWidgets.QHBoxLayout(gb_ctl)

        self.mediamtx_bin = QtWidgets.QLineEdit(MEDIAMTX_BIN_DEFAULT)

        self.btn_start = QtWidgets.QPushButton("Start Video")
        self.btn_stop = QtWidgets.QPushButton("Stop")
        self.btn_stop.setEnabled(False)

        self.status = QtWidgets.QLabel("STOPPED")
        self.status.setStyleSheet("font-weight:700; color: rgb(180, 60, 60);")

        self.btn_start.clicked.connect(self.start_stream)
        self.btn_stop.clicked.connect(self.stop_stream)

        h.addWidget(QtWidgets.QLabel("mediamtx"))
        h.addWidget(self.mediamtx_bin, 1)
        h.addWidget(self.btn_start)
        h.addWidget(self.btn_stop)
        h.addStretch(1)
        h.addWidget(QtWidgets.QLabel("Status:"))
        h.addWidget(self.status)

        self._refresh_cameras()
        v.addStretch(1)

    def _update_out_url(self) -> None:
        ip = (self.out_ip.text().strip() or "<IP_PC>")
        port = int(self.out_port.value())
        path = (self.out_path.text().strip().lstrip("/") or "qgc")
        self.out_url.setText(f"rtsp://{ip}:{port}/{path}")

    def _apply_input_mode(self) -> None:
        rtsp = (self.mode.currentIndex() == 0)
        self.in_rtsp.setEnabled(rtsp)

        self.cam_combo.setEnabled(not rtsp)
        self.btn_refresh_cam.setEnabled(not rtsp)
        self.res.setEnabled(not rtsp)
        self.fps.setEnabled(not rtsp)

    def _refresh_cameras(self) -> None:
        self.cam_combo.clear()
        devs = list_video_devices()
        for d in devs:
            self.cam_combo.addItem(get_device_label(d), userData=d)
        if devs:
            self.cam_combo.setCurrentIndex(0)

    # -------------------------
    # Validation
    # -------------------------
    def _write_mediamtx_cfg_user(self, path_name: str) -> Path:
        cfg_dir = Path.home() / ".config" / "mediamtx"
        cfg_dir.mkdir(parents=True, exist_ok=True)
        cfg_path = cfg_dir / "mediamtx.yml"
        cfg_path.write_text(f"paths:\n  {path_name}:\n    source: publisher\n")
        return cfg_path

    def _validate(self) -> Optional[str]:
        mtbin = self.mediamtx_bin.text().strip() or MEDIAMTX_BIN_DEFAULT
        if not Path(mtbin).exists():
            return f"mediamtx tidak ditemukan: {mtbin}"
        if not has_cmd("ffmpeg"):
            return "ffmpeg tidak ditemukan"

        path = self.out_path.text().strip().lstrip("/") or "qgc"
        if any(c.isspace() for c in path):
            return "Path output tidak boleh ada spasi"

        if self.mode.currentIndex() == 0:
            src = self.in_rtsp.text().strip()
            if not src:
                return "RTSP input kosong"
            if not looks_like_rtsp(src):
                return "RTSP input harus diawali rtsp://"
        else:
            if self.cam_combo.count() == 0:
                return "Webcam tidak terdeteksi (/dev/video*)"
            dev = str(self.cam_combo.currentData())
            if not dev or not Path(dev).exists():
                return "Webcam device tidak valid"

            res = self.res.currentText().strip()
            if not re.match(r"^\d+x\d+$", res):
                return "Resolusi tidak valid"

            fps = self.fps.currentText().strip()
            if not fps.isdigit():
                return "FPS tidak valid"

        return None

    # -------------------------
    # Process lifecycle
    # -------------------------
    def start_stream(self) -> None:
        if self.mt or self.ff:
            return

        err = self._validate()
        if err:
            QtWidgets.QMessageBox.critical(self, "OMNI-Link", err)
            return

        mtbin = self.mediamtx_bin.text().strip() or MEDIAMTX_BIN_DEFAULT
        out_port = int(self.out_port.value())
        out_path = (self.out_path.text().strip().lstrip("/") or "qgc")
        br = int(self.bitrate.value())

        cfg_path = self._write_mediamtx_cfg_user(out_path)
        publish_url = f"rtsp://127.0.0.1:{out_port}/{out_path}"

        self.mt = QtCore.QProcess(self)
        self.mt.setProcessChannelMode(QtCore.QProcess.MergedChannels)
        self.mt.finished.connect(lambda _c, _s: self.stop_stream())
        self.mt.start(mtbin, [str(cfg_path)])

        if not self.mt.waitForStarted(2000):
            self.mt = None
            QtWidgets.QMessageBox.critical(self, "OMNI-Link", "mediamtx gagal start")
            return

        def start_ffmpeg():
            if not self.mt:
                return

            self.ff = QtCore.QProcess(self)
            self.ff.setProcessChannelMode(QtCore.QProcess.MergedChannels)
            self.ff.finished.connect(lambda _c, _s: self.stop_stream())

            args: List[str] = [
                "-loglevel", "error",
                "-fflags", "nobuffer",
                "-flags", "low_delay",
            ]

            if self.mode.currentIndex() == 0:
                src = self.in_rtsp.text().strip()
                args += [
                    "-rtsp_transport", "tcp",
                    "-i", src,
                ]
                gop = 30
            else:
                dev = str(self.cam_combo.currentData())
                res = self.res.currentText().strip()
                fps = int(self.fps.currentText().strip())
                gop = fps

                args += [
                    "-f", "v4l2",
                    "-input_format", "mjpeg",
                    "-framerate", str(fps),
                    "-video_size", res,
                    "-i", dev,
                ]

            args += [
                "-an",
                "-c:v", "libx264",
                "-preset", "ultrafast",
                "-tune", "zerolatency",
                "-pix_fmt", "yuv420p",
                "-profile:v", "baseline",
                "-g", str(gop),
                "-keyint_min", str(gop),
                "-sc_threshold", "0",
                "-bf", "0",
                "-b:v", f"{br}k",
                "-maxrate", f"{br}k",
                "-bufsize", f"{br * 2}k",
                "-x264-params", X264_PARAMS,
                "-f", "rtsp",
                "-rtsp_transport", "tcp",
                publish_url,
            ]

            self.ff.start("ffmpeg", args)

        QtCore.QTimer.singleShot(700, start_ffmpeg)

        self.watchdog.start()
        self.btn_start.setEnabled(False)
        self.btn_stop.setEnabled(True)
        set_status_label(self.status, "RUNNING", True)

    def _watch_processes(self) -> None:
        if self.mt and self.mt.state() == QtCore.QProcess.NotRunning:
            self.stop_stream()
            return
        if self.ff and self.ff.state() == QtCore.QProcess.NotRunning:
            self.stop_stream()
            return

    def stop_stream(self) -> None:
        self.watchdog.stop()

        if self.ff:
            try:
                self.ff.terminate()
                if not self.ff.waitForFinished(1200):
                    self.ff.kill()
                    self.ff.waitForFinished(1200)
            except Exception:
                pass

        if self.mt:
            try:
                self.mt.terminate()
                if not self.mt.waitForFinished(1200):
                    self.mt.kill()
                    self.mt.waitForFinished(1200)
            except Exception:
                pass

        if self.ff:
            self.ff.deleteLater()
            self.ff = None
        if self.mt:
            self.mt.deleteLater()
            self.mt = None

        self.btn_start.setEnabled(True)
        self.btn_stop.setEnabled(False)
        set_status_label(self.status, "STOPPED", False)

    def _refresh_status(self) -> None:
        running = bool(self.mt or self.ff)
        if running:
            set_status_label(self.status, "RUNNING", True)
        else:
            set_status_label(self.status, "STOPPED", False)

    def is_running(self) -> bool:
        return bool(self.mt or self.ff)
