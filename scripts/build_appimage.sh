#!/usr/bin/env bash
set -euo pipefail

APP_NAME="OMNI-Link"
ICON_NAME="omnilink"

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

# Semua output tinggal di repo ini
rm -rf build dist AppDir *.AppImage *.spec run_omnilink.py

python3 -m pip install --upgrade pip
python3 -m pip install pyinstaller

# Entry untuk PyInstaller
cat > run_omnilink.py <<'PY'
#!/usr/bin/env python3
from omnilink.main import main
if __name__ == "__main__":
    main()
PY
chmod +x run_omnilink.py

pyinstaller \
  --noconfirm \
  --onedir \
  --windowed \
  --name "${APP_NAME}" \
  --hidden-import PyQt5.sip \
  --hidden-import PyQt5.QtCore \
  --hidden-import PyQt5.QtGui \
  --hidden-import PyQt5.QtWidgets \
  run_omnilink.py

mkdir -p AppDir/usr/bin
cp -r "dist/${APP_NAME}/"* AppDir/usr/bin/

cat > AppDir/AppRun <<'APP'
#!/bin/bash
HERE="$(dirname "$(readlink -f "$0")")"
export PYTHONHOME="$HERE/usr/bin"
export PYTHONPATH="$HERE/usr/bin"
exec "$HERE/usr/bin/OMNI-Link"
APP
chmod +x AppDir/AppRun

mkdir -p AppDir/usr/share/applications
cat > AppDir/usr/share/applications/OMNI-Link.desktop <<EOF
[Desktop Entry]
Type=Application
Name=OMNI-Link
Exec=OMNI-Link
Icon=${ICON_NAME}
Categories=Utility;
Terminal=false
EOF

mkdir -p AppDir/usr/share/icons/hicolor/256x256/apps

if [ -f "assets/${ICON_NAME}.png" ]; then
  cp "assets/${ICON_NAME}.png" "AppDir/usr/share/icons/hicolor/256x256/apps/${ICON_NAME}.png"
else
  if command -v convert >/dev/null 2>&1; then
    convert -size 256x256 xc:'#222222' "AppDir/usr/share/icons/hicolor/256x256/apps/${ICON_NAME}.png"
  else
    echo "Missing assets/${ICON_NAME}.png and ImageMagick not installed."
    echo "Fix: put icon at assets/${ICON_NAME}.png"
    exit 1
  fi
fi

cp -f "AppDir/usr/share/icons/hicolor/256x256/apps/${ICON_NAME}.png" "AppDir/${ICON_NAME}.png"

LINUXDEPLOY="./linuxdeploy-x86_64.AppImage"
if [ ! -f "$LINUXDEPLOY" ]; then
  wget -O "$LINUXDEPLOY" "https://github.com/linuxdeploy/linuxdeploy/releases/download/continuous/linuxdeploy-x86_64.AppImage"
  chmod +x "$LINUXDEPLOY"
fi

"$LINUXDEPLOY" --appdir AppDir --output appimage

ls -lh *.AppImage
