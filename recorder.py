import os
import subprocess
from pathlib import Path
from typing import Optional

from pipewire import get_target_node_id


class Recorder:
    """Starts/stops pw-record for the app stream and manages output files."""
    def __init__(
        self,
        outdir: Path,
        samplerate: str,
        channels: str,
        fmt: str,
        target_app: str,
        target_media_class: str,
    ):
        self._outdir = outdir
        self._samplerate = samplerate
        self._channels = channels
        self._fmt = fmt
        self._target_app = target_app
        self._target_media_class = target_media_class

        self._recording_proc: Optional[subprocess.Popen] = None
        self._last_outfile: Optional[Path] = None
        self._counter = 1

    def start(self) -> Optional[Path]:
        if self._recording_proc:
            return

        target_id = get_target_node_id(self._target_app, self._target_media_class)
        if target_id is None:
            return

        outfile = self._next_filename()
        self._last_outfile = outfile
        print(f"[+] START → {outfile}")

        self._recording_proc = subprocess.Popen(
            ["pw-record", "--target", str(target_id), "--rate", self._samplerate, "--channels", self._channels, "--format", self._fmt, str(outfile)],
            env={**os.environ, "LC_ALL": "C"},
        )
        return outfile

    def stop(self) -> Optional[Path]:
        if not self._recording_proc:
            return

        print("[-] STOP")
        self._recording_proc.terminate()
        self._recording_proc.wait()
        self._recording_proc = None
        finished = self._last_outfile
        self._last_outfile = None
        return finished

    def _next_filename(self) -> Path:
        while True:
            pattern = f"{self._counter:03}.*"  # e.g. `001.*`
            if not any(self._outdir.glob(pattern)):
                return self._outdir / f"{self._counter:03}.wav"
            self._counter += 1
