# Autorec

Autorec automatically records audio from a specific PipeWire application stream. It watches for audio activity from the target app and starts/stops recording accordingly. Finished recordings are optionally normalized (ffmpeg loudnorm, two-pass) and encoded to MP3.

## How it works

- Finds the target app’s audio stream via `pw-dump`
- Checks activity via `pactl list sink-inputs` (corked: no)
- Starts/stops `pw-record` to capture WAV files
- Normalizes loudness with ffmpeg (two-pass loudnorm)
- Encodes MP3 via `lame`

## Requirements

- Linux with PipeWire running
- `pw-dump`, `pw-record`, `pactl` in `PATH`
- `ffmpeg` (for loudness normalization)
- `lame` (for MP3 encoding)

## Configuration

Edit `config.py` to match your setup:

- `OUTDIR`: output directory (default: `./recordings`)
- `SAMPLERATE`, `CHANNELS`, `FORMAT`: pw-record parameters
- `TARGET_APP`: application name to record (from PipeWire)
- `TARGET_MEDIA_CLASS`: media class prefix (e.g. `Stream/Output/Audio`)
- `ACTIVITY_WINDOW_SEC`: polling interval for activity detection

## Run

```bash
python3 autorec.py
```

The script will keep running and record whenever the target app is active.

## Output

- Raw recordings: `NNN.wav` in `recordings/`
- Normalized WAV: temporary `NNN.norm.wav` (removed after successful MP3)
- MP3: `NNN.mp3`

If normalization or encoding fails, the original WAV is kept.
