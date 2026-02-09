OMNI-Link

OMNI-Link is a Linux desktop application for video streaming and MAVLink telemetry routing, built with PyQt5 and distributed as an AppImage.

==================================================

Run (Development)

Run the application from the repository root:

cd omnilink
python3 -m omnilink.main

Required dependencies:

Python 3.10+

PyQt5

ffmpeg

MediaMTX

mavlink-routerd

==================================================

Build AppImage

Build the AppImage locally from the repository root:

cd omnilink
bash scripts/build_appimage.sh

Output:
OMNI-Link-x86_64.AppImage

Build artifacts must not be committed to Git.

==================================================

CI and Releases

Pushes to main trigger an AppImage build in GitHub Actions

Version tags (vX.Y.Z) create a GitHub Release with an attached AppImage

==================================================
