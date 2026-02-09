from __future__ import annotations

import re
import shlex
import subprocess
from pathlib import Path
from typing import List

from omnilink.utils import has_cmd


def list_video_devices() -> List[str]:
    devs: List[str] = []
    for p in sorted(Path("/dev").glob("video*"), key=lambda x: int(re.sub(r"\D", "", x.name) or "9999")):
        devs.append(f"/dev/{p.name}")
    return devs


def get_device_label(dev: str) -> str:
    if has_cmd("v4l2-ctl"):
        out = subprocess.run(
            ["bash", "-lc", f"v4l2-ctl -D -d {shlex.quote(dev)} 2>/dev/null | sed -n 's/^Card type[ ]*:[ ]*//p'"],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        ).stdout.strip()
        if out:
            return f"{dev} ({out})"
    return dev
