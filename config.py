from pathlib import Path

"""
Configuration for Autorec.
"""

OUTDIR = Path("./recordings")
OUTDIR.mkdir(exist_ok=True)

SAMPLERATE = "44100"
CHANNELS = "2"
FORMAT = "s24"
TARGET_APP = "Firefox"
TARGET_MEDIA_CLASS = "Stream/Output/Audio"
ACTIVITY_WINDOW_SEC = 0.05
