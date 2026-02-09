MEDIAMTX_BIN_DEFAULT = "/usr/local/bin/mediamtx"

RES_CHOICES = ["640x480", "1280x720", "1920x1080"]
FPS_CHOICES = ["10", "15", "20", "25", "30", "60"]

X264_PARAMS = (
    "nal-hrd=none:"
    "force-cfr=1:"
    "sliced-threads=1:"
    "sync-lookahead=0:"
    "rc-lookahead=0:"
    "bframes=0:"
    "ref=1"
)
