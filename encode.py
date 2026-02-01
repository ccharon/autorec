import os
import subprocess
from pathlib import Path


def encode_mp3(wav_path: Path, mp3_path: Path) -> bool:
    """
    Encodes WAV to MP3 via lame.
    Returns True/False.
    """
    env = os.environ.copy()
    env["LC_ALL"] = "C"
    try:
        res = subprocess.run(
            ["lame", "--quiet", "--cbr", "-b", "192", "-q", "0", "-m", "j", "--resample", "44.1", str(wav_path), str(mp3_path)],
            check=False,
            env=env,
        )

    except FileNotFoundError:
        print("[!] lame not found, conversion skipped")
        return False

    if res.returncode == 0:
        print(f"[+] Converted: {wav_path} → {mp3_path}")
        return True

    print(f"[!] Conversion failed (exit {res.returncode}): {wav_path}")

    return False
