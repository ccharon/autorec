#!/usr/bin/env python3
import threading
import time
from pathlib import Path

from activity import ActivityMonitor
from config import ACTIVITY_WINDOW_SEC, CHANNELS, FORMAT, OUTDIR, SAMPLERATE, TARGET_APP, TARGET_MEDIA_CLASS
from recorder import Recorder
from normalize import normalize_wav
from encode import encode_mp3

"""
Autorec — automatic recording of PipeWire audio (app node)

Overview:
Finds the target app audio stream via `pw-dump`, checks activity via
`pactl list sink-inputs` (corked: no), and starts/stops `pw-record`.
Filenames are assigned sequentially (`001.wav`, `002.wav`, ...).

Requirements:
- PipeWire installed and running
- `pw-dump`, `pw-record`, `pactl` available in PATH

Configuration:
- OUTDIR: output directory (default: `./recordings`)
- SAMPLERATE, CHANNELS, FORMAT: pw-record parameters
- TARGET_APP: application.name of the app to record
- TARGET_MEDIA_CLASS: media.class of the stream node

Note:
This script starts external processes and expects PipeWire-specific
JSON structures. You may need to adjust `TARGET_APP` or parameters.
"""


def main():
    print("[*] Autorec started (audio activity monitoring)")

    monitor = ActivityMonitor(
        target_app=TARGET_APP,
        window_sec=ACTIVITY_WINDOW_SEC,
    )
    recorder = Recorder(
        outdir=OUTDIR,
        samplerate=SAMPLERATE,
        channels=CHANNELS,
        fmt=FORMAT,
        target_app=TARGET_APP,
        target_media_class=TARGET_MEDIA_CLASS,
    )

    def post_process(wav_path: Path):
        norm_wav = wav_path.with_suffix(".norm.wav")
        mp3_path = wav_path.with_suffix(".mp3")

        used_source = normalize_wav(wav_path, norm_wav)
        ok = encode_mp3(used_source, mp3_path)

        # Cleanup: keep original WAV, remove normalized WAV
        if ok:
            if norm_wav.exists() and norm_wav != wav_path:
                try:
                    norm_wav.unlink()
                except OSError:
                    pass
        else:
            if norm_wav.exists() and norm_wav != wav_path:
                try:
                    norm_wav.unlink()
                except OSError:
                    pass

    try:
        monitor.start()
        while True:
            if monitor.is_active():
                recorder.start()

            else:
                finished = recorder.stop()

                if finished and finished.exists():
                    t = threading.Thread(target=post_process, args=(finished,), daemon=True)
                    t.start()

            time.sleep(0.05)

    except KeyboardInterrupt:
        monitor.stop()
        recorder.stop()


if __name__ == "__main__":
    main()
