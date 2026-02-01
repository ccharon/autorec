import json
import os
import subprocess
from pathlib import Path
from typing import Any, Dict, Optional, Tuple


LOUDNORM_TARGET = "I=-14:TP=-2:LRA=7"

def _extract_loudnorm_stats(output: str) -> Optional[Dict[str, Any]]:
    """
    Expects JSON output from ffmpeg loudnorm (print_format=json).
    Returns the JSON dict or None on failure.
    """
    try:
        start = output.rfind("{")
        end = output.rfind("}")
        if start == -1 or end == -1 or end <= start:
            return None

        raw = output[start : end + 1]
        data = json.loads(raw)
        return data

    except (json.JSONDecodeError, TypeError):
        return None

def _build_pass2_filter(measured: Dict[str, str]) -> str:
    return (
        f"loudnorm={LOUDNORM_TARGET}:"
        f"measured_I={measured['measured_I']}:"
        f"measured_TP={measured['measured_TP']}:"
        f"measured_LRA={measured['measured_LRA']}:"
        f"measured_thresh={measured['measured_thresh']}:"
        f"offset={measured['offset']}:"
        "print_format=summary"
    )


def _select_measured_fields(data: Optional[Dict[str, Any]]) -> Optional[Dict[str, str]]:
    """
    Maps ffmpeg JSON to the keys required for pass 2.
    """
    if not data:
        return None

    mapping = {
        "measured_I": "input_i",
        "measured_TP": "input_tp",
        "measured_LRA": "input_lra",
        "measured_thresh": "input_thresh",
        "offset": "target_offset",
    }

    # All values must be present
    missing = [v for v in mapping.values() if v not in data]
    if missing:
        raise KeyError(f"loudnorm pass1: missing keys in JSON: {', '.join(missing)}")

    # All values must be numeric
    measured: Dict[str, str] = {}
    for out_key, in_key in mapping.items():
        val = data[in_key]

        try:
            float(val)
        except (TypeError, ValueError):
            raise ValueError(f"loudnorm pass1: invalid value for {in_key}: {val!r}") from None

        measured[out_key] = str(val)

    return measured


def _assess_loudnorm(data: Optional[Dict[str, Any]]) -> Tuple[str, str]:
    """
    Returns (smiley, text) based on loudness values.
    """
    if not data:
        return ":-|", "Assessment not possible"

    input_i = float(data["input_i"])
    input_tp = float(data["input_tp"])
    output_i = float(data["output_i"])
    output_tp = float(data["output_tp"])

    # Critical: clipping/overload
    if (input_tp is not None and input_tp >= 0.0) or (output_tp is not None and output_tp >= 0.0):
        return ":-(", "Clipping (True Peak >= 0 dBTP)"

    # Notable: very quiet or target missed by a wide margin
    if input_i is not None and input_i <= -23.0:
        return ":-|", "Input signal very quiet"

    if output_i is not None and abs(output_i - (-14.0)) > 1.5:
        return ":-|", "Target loudness missed by a wide margin"

    if output_tp is not None and output_tp > -1.0:
        return ":-|", "True Peak near the limit"

    return ":-)", "Normalization within target range"


def normalize_wav(wav_path: Path, norm_wav: Path) -> Path:
    """
    Two-pass loudness normalization with ffmpeg (loudnorm).
    Returns the path of the WAV to use (normalized or original).
    """
    used_source = wav_path

    env = os.environ.copy()
    env["LC_ALL"] = "C"

    # --- PASS 1: measure ---
    try:
        p1 = subprocess.run(
            ["ffmpeg", "-y", "-hide_banner", "-nostats", "-loglevel", "info", "-i", str(wav_path), "-af", f"loudnorm={LOUDNORM_TARGET}:print_format=json", "-f", "null", "-"],
            capture_output=True,
            text=True,
            check=False,
            env=env,
        )
    except FileNotFoundError:
        print("[!] ffmpeg not found, normalization skipped")
        return used_source

    out_text = (p1.stderr or "") + (p1.stdout or "")
    stats = _extract_loudnorm_stats(out_text)
    measured = _select_measured_fields(stats)

    # If parsing the measurement failed, return the original WAV
    if not measured:
        print("[!] loudnorm measurement: results not parsed, using original WAV")
        print("[debug] ffmpeg loudnorm output (pass1):")
        print(out_text)

        return used_source

    # Print measurements and assessment
    if stats:
        smiley, note = _assess_loudnorm(stats)
        print(
            "[i] Loudness: "
            f"before I={stats.get('input_i')} LUFS, TP={stats.get('input_tp')} dBTP | "
            f"after I={stats.get('output_i')} LUFS, TP={stats.get('output_tp')} dBTP "
            f"{smiley} ({note})"
        )

    # --- PASS 2: apply ---
    filter_arg = _build_pass2_filter(measured)
    p2 = subprocess.run(
        ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-i", str(wav_path), "-af", filter_arg, "-ar", "44100", "-ac", "2", "-c:a", "pcm_s24le", str(norm_wav)],
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )

    if not p2 or p2.returncode != 0 or not norm_wav.exists():
        rc = p2.returncode if p2 is not None else "n/a"
        print(f"[!] Normalization (pass 2) failed (exit {rc}), using original")
        return used_source

    used_source = norm_wav
    print(f"[+] Normalized (2-pass): {wav_path} → {norm_wav}")
    return used_source
