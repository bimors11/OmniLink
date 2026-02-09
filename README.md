OMNI-Link

OMNI-Link is a Linux desktop application for video streaming and MAVLink telemetry routing.
It is built with PyQt5 and distributed as an AppImage.

Run (Development)

Run the application from the repository root:

cd omnilink
python3 -m omnilink.main


Required dependencies:

Python 3.10 or newer

PyQt5

ffmpeg

MediaMTX

mavlink-routerd

Build AppImage (Local)

Build the AppImage from the repository root:

cd omnilink
bash scripts/build_appimage.sh


Output:

OMNI-Link-x86_64.AppImage

Build artifacts must not be committed to Git.

CI and Releases

Pushes to the main branch trigger an AppImage build in GitHub Actions

Version tags (vX.Y.Z) create a GitHub Release with an attached AppImage

Example release:

git tag v0.1.0
git push origin v0.1.0

Code Maintenance Rules

UI code must not contain heavy logic

Core logic must not depend on UI modules

utils must not import from higher-level modules

All external processes must start and stop cleanly

Use file-based logging instead of print

Maintenance Reminder

If the code becomes difficult to modify or fragile, stop adding features and fix module boundaries first.

Stability is the priority.
