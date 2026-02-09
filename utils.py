from __future__ import annotations

import os
import socket
import subprocess
from typing import Optional

from PyQt5 import QtWidgets


def which(cmd: str) -> Optional[str]:
    for p in os.environ.get("PATH", "").split(os.pathsep):
        full = os.path.join(p, cmd)
        if os.path.isfile(full) and os.access(full, os.X_OK):
            return full
    return None


def has_cmd(cmd: str) -> bool:
    return subprocess.call(["bash", "-lc", f"command -v {cmd} >/dev/null 2>&1"]) == 0


def guess_ip() -> str:
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


def is_valid_ip(ip: str) -> bool:
    parts = ip.strip().split(".")
    if len(parts) != 4:
        return False
    try:
        nums = [int(x) for x in parts]
    except ValueError:
        return False
    return all(0 <= n <= 255 for n in nums)


def is_valid_port(p: int) -> bool:
    return 1 <= p <= 65535


def looks_like_rtsp(url: str) -> bool:
    u = url.strip()
    return u.startswith("rtsp://") or u.startswith("rtsps://")


def parse_ss() -> str:
    ss_bin = which("ss")
    if not ss_bin:
        return ""
    try:
        return subprocess.check_output([ss_bin, "-lunpt"], stderr=subprocess.STDOUT, text=True)
    except Exception:
        return ""


def port_listening(ss_text: str, proto: str, port: int) -> bool:
    if not ss_text:
        return False
    needle = f":{port}"
    low = ss_text.lower()
    if proto.lower() == "udp":
        return ("udp" in low) and (needle in ss_text)
    if proto.lower() == "tcp":
        return ("tcp" in low) and (needle in ss_text)
    return False


def find_free_tcp_port(preferred: int, tries: int = 40) -> int:
    if preferred == 0:
        return 0
    ss_text = parse_ss()
    port = preferred
    for _ in range(max(1, tries)):
        if not port_listening(ss_text, "tcp", port):
            return port
        port += 1
    return preferred


def set_status_label(lbl: QtWidgets.QLabel, text: str, ok: bool, bold: bool = True) -> None:
    lbl.setText(text)
    fw = "700" if bold else "500"
    if ok:
        lbl.setStyleSheet(f"font-weight:{fw}; color: rgb(0, 150, 0);")
    else:
        lbl.setStyleSheet(f"font-weight:{fw}; color: rgb(180, 60, 60);")
