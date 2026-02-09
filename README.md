# OMNI-Link
Video Streaming and MAVLink Telemetry Router  
Platform: **Linux (x86_64)**  
UI Framework: **PyQt5**  
Distribution: **AppImage**

---

## Overview

OMNI-Link is a Linux desktop application designed for Ground Control Station workflows.  
It combines low latency video streaming and MAVLink telemetry routing into a single application.

The application can be run directly from source during development or distributed as a portable AppImage for deployment.

The design prioritizes stability, clean process management, and long term maintainability.

---

## Key Features

### Video Streaming
- RTSP input support
- Local webcam input support
- ffmpeg based encoding pipeline
- MediaMTX as RTSP server
- Optimized for low latency GCS streaming

### Telemetry Routing
- MAVLink routing using mavlink-routerd
- UDP server input
- Multiple UDP output targets
- Optional UDP primer for upstream activation
- TCP RX detection for link verification

### Desktop Application
- PyQt5 based graphical interface
- Separate Video and Telemetry control tabs
- Clean start and stop handling for all external processes

---

## Dependencies

### Runtime Requirements
- Linux x86_64
- Python 3.10 or newer
- PyQt5
- ffmpeg
- MediaMTX
- mavlink-routerd

---

## Running (Development)

Run the application from the repository root:

```bash
cd omnilink
python3 -m omnilink.main
```

Running individual files directly is not supported and may break package imports.

---

## Building AppImage

Build the AppImage locally from the repository root:

```bash
cd omnilink
bash scripts/build_appimage.sh
```

### Output
- OMNI-Link-x86_64.AppImage

Build artifacts must not be committed to the repository.

---

## CI and Releases

- Pushes to the `main` branch trigger an AppImage build in GitHub Actions
- Version tags following `vX.Y.Z` create a GitHub Release with an attached AppImage

Example release:

```bash
git tag v0.1.0
git push origin v0.1.0
```

---

## Code Maintenance Guidelines

### UI Responsibilities
- UI code must remain thin
- Widgets should only handle user input and process control
- Heavy logic must live outside UI modules

### Dependency Direction
Allowed dependency flow:
- UI → Video or Telemetry → Utils

Reverse dependencies are not allowed.

### Process Management
- All external processes must start and stop cleanly
- terminate, wait, and force kill if required
- No zombie processes are acceptable

### Logging
- Do not rely on print statements
- Use file based logging
- Logs should be written to a persistent user location

---

## Maintenance Reminder

If adding features becomes difficult or changes cause unexpected breakage, stop feature development and fix module boundaries first.

Stability and clarity take priority over speed.
