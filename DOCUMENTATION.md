# OMNI-Link Code Documentation

This document describes the purpose and responsibility of each module and file in the OMNI-Link project.
It is intended as a maintenance reference.

---

## Root Package: omnilink/

### __init__.py
Marks the omnilink directory as a Python package.
Must remain lightweight and must not import heavy modules or trigger side effects.

### main.py
Application entry point.
Responsibilities:
- Create QApplication
- Initialize MainWindow
- Start the Qt event loop

No business logic should exist here.

---

## utils/

Shared helper functions with no dependency on UI, video, or telemetry modules.

### utils/net.py
Network-related helper functions.
Typical responsibilities:
- Guess local IP address
- Validate IPv4 addresses
- Validate port numbers

Must not import Qt or application logic.

### utils/proc.py
Process and system helpers.
Typical responsibilities:
- Detect external binaries (ffmpeg, mediamtx, mavlink-routerd)
- Unified QProcess start/stop helpers
- Status label helpers for UI

Used by both video and telemetry modules.

---

## ui/

UI-only components.
Must not contain heavy logic or protocol handling.

### ui/main_window.py
Main application window.
Responsibilities:
- Tab layout (Video, Telemetry)
- Toolbar actions (Start All, Stop All)
- Status bar updates

Delegates all real work to video and telemetry modules.

---

## video/

Video streaming subsystem.

### video/constants.py
Video-related constants.
Typical contents:
- Resolution presets
- FPS presets
- x264 encoder parameters
- Default MediaMTX paths

No runtime logic.

### video/devices.py
Webcam device discovery.
Responsibilities:
- Enumerate /dev/video* devices
- Query device labels using v4l2-ctl if available

No UI logic.

### video/pipeline.py
Video processing logic.
Responsibilities:
- Validate video input configuration
- Build ffmpeg command arguments
- Write MediaMTX configuration files

Must not contain UI widgets.

### video/widget.py
Video control UI.
Responsibilities:
- Render video configuration UI
- Start and stop ffmpeg and MediaMTX processes
- Display runtime status

Must delegate logic to pipeline.py.

---

## telemetry/

MAVLink telemetry routing subsystem.

### telemetry/mavlink_utils.py
Low-level MAVLink utilities.
Responsibilities:
- X25 CRC implementation
- MAVLink v1 heartbeat packet generation

Must remain protocol-only and stateless.

### telemetry/workers.py
Background worker threads.
Responsibilities:
- UDP primer thread to trigger upstream telemetry
- TCP RX detection thread for MAVLink presence

No UI code.

### telemetry/router_config.py
Router configuration logic.
Responsibilities:
- Parse telemetry targets
- Generate mavlink-routerd configuration text
- Validate routing parameters

Pure logic module.

### telemetry/router_widget.py
Telemetry control UI.
Responsibilities:
- Telemetry configuration UI
- Start and stop mavlink-routerd
- Launch primer and RX detection workers

Must not embed routing logic directly.

---

## scripts/

### scripts/build_appimage.sh
Local AppImage build script.
Responsibilities:
- Build PyInstaller bundle
- Construct AppDir layout
- Invoke linuxdeploy to generate AppImage

Must be run from repository root.

---

## assets/

### assets/omnilink.png
Application icon.
Used by desktop file and AppImage packaging.

---

## .github/workflows/

### build-appimage.yml
GitHub Actions CI workflow.
Responsibilities:
- Build AppImage on push to main
- Build and attach AppImage to GitHub Releases on version tags

---

## Maintenance Rules Summary

- UI modules must remain thin
- Heavy logic belongs in pipeline, config, or worker modules
- utils must never depend on higher-level modules
- External processes must always stop cleanly
- Avoid side effects in imports

This structure is critical for long-term stability and maintainability.
