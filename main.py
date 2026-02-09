from __future__ import annotations

import signal
import sys

from PyQt5 import QtCore, QtGui, QtWidgets

from omnilink.telemetry.router_widget import RouterWidget
from omnilink.video.widget import VideoWidget


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("OMNI-Link")
        self.resize(980, 620)

        self.tabs = QtWidgets.QTabWidget()
        self.setCentralWidget(self.tabs)

        self.video = VideoWidget()
        self.router = RouterWidget()

        self.tabs.addTab(self.video, "Video")
        self.tabs.addTab(self.router, "Telemetry")

        tb = self.addToolBar("Main")
        tb.setMovable(False)

        act_start_all = QtWidgets.QAction("Start All", self)
        act_stop_all = QtWidgets.QAction("Stop All", self)
        act_start_all.triggered.connect(self.start_all)
        act_stop_all.triggered.connect(self.stop_all)
        tb.addAction(act_start_all)
        tb.addAction(act_stop_all)

        self.statusBar().showMessage("Ready")

        self._ui_timer = QtCore.QTimer(self)
        self._ui_timer.setInterval(900)
        self._ui_timer.timeout.connect(self._refresh_statusbar)
        self._ui_timer.start()
        self._refresh_statusbar()

    def _refresh_statusbar(self):
        v = "ON" if self.video.is_running() else "OFF"
        r = "ON" if self.router.is_running() else "OFF"
        self.statusBar().showMessage(f"Video: {v} | Router: {r}")

    def start_all(self):
        self.router.start()
        self.video.start_stream()

    def stop_all(self):
        self.video.stop_stream()
        self.router.stop()

    def closeEvent(self, e: QtGui.QCloseEvent):
        try:
            self.stop_all()
        finally:
            e.accept()


def main():
    if sys.platform.startswith("linux"):
        signal.signal(signal.SIGINT, signal.SIG_DFL)

    app = QtWidgets.QApplication([])
    w = MainWindow()
    w.show()
    app.exec_()


if __name__ == "__main__":
    main()
