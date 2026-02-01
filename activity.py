import os
import re
import subprocess
import threading
import time
from typing import Optional


class ActivityMonitor:
    """Monitors app audio via pactl (corked) and returns an active state."""
    def __init__(
        self,
        target_app: str,
        window_sec: float,
    ):
        self._target_app = target_app
        self._window_sec = window_sec

        self._active_state = False
        self._monitor_thread: Optional[threading.Thread] = None
        self._monitor_stop = threading.Event()

    def is_active(self) -> bool:
        return self._active_state

    def start(self):
        if self._monitor_thread and self._monitor_thread.is_alive():
            return
        self._monitor_stop.clear()
        self._monitor_thread = threading.Thread(target=self._monitor_audio, daemon=True)
        self._monitor_thread.start()

    def stop(self):
        self._monitor_stop.set()

    def _monitor_audio(self):
        # Start in waiting state
        self._active_state = False

        while not self._monitor_stop.is_set():
            self._active_state = self._pactl_active()
            time.sleep(self._window_sec)

    def _pactl_active(self) -> bool:
        """
        Checks with `LC_ALL=C pactl list sink-inputs` whether the sink input with
        application.name == TARGET_APP is active (Corked: no).
        """
        env = os.environ.copy()
        env["LC_ALL"] = "C"

        try:
            p = subprocess.run(["pactl", "list", "sink-inputs"], capture_output=True, text=True, check=False, env=env)
        except FileNotFoundError:
            return False

        out = p.stdout or ""
        if p.returncode != 0 or not out.strip():
            return False

        blocks = [b.strip() for b in out.split("\n\n") if b.strip()]

        for b in blocks:
            match_appname = re.search(r'application\.name\s*=\s*"(.*?)"', b)
            if not match_appname:
                match_appname = re.search(r"application\.name\s*=\s*'(.*?)'", b)
            if not match_appname:
                continue

            if match_appname.group(1) == self._target_app:
                return "corked: no" in b.lower()

        return False
