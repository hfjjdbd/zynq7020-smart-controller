# GitHub Open-Source Notes

This project borrows ideas, not code, from existing open-source work.

## Audio To MIDI

- `spotify/basic-pitch`
  - Repository: https://github.com/spotify/basic-pitch
  - Useful idea: use a dedicated audio-to-MIDI model for MP3/WAV first, then
    convert MIDI to `song.txt`.
  - Why it matters here: direct MP3 pitch tracking is fragile for full songs.
    A MIDI intermediate lets us inspect tracks and clean the melody before the
    board ever sees `song.txt`.

Recommended path:

```text
MP3/WAV
  -> basic-pitch
  -> MIDI
  -> extract_notes.py
  -> song.txt
```

## MIDI To Buzzer

- `MyMotox/Midi2InoBuzz`
  - Repository: https://github.com/MyMotox/Midi2InoBuzz
  - Useful ideas: list MIDI tracks, ignore drum channel 10, choose a likely
    melody track automatically, and collapse chords to a monophonic buzzer line.

Implemented in this project:

- `--list-midi-tracks`
- `--midi-track auto`
- `--midi-track all`
- `--midi-track N`
- default drum-channel filtering
- highest/lowest active note policy for chords

## Zynq FPGA Loading Without JTAG

- Red Pitaya and other Zynq projects commonly load FPGA bitstreams from Linux
  or boot storage instead of relying only on JTAG.
  - Example repository found during research:
    https://github.com/lvillasen/RedPitaya-Hello-World-FPGA

For this board, the known-good path remains:

```text
copy new .bit to /media/boot under a new name
load temporarily with /dev/xdevcfg
test AXI PWM with a short tone
only then update boot configuration
```

## What Not To Import

Avoid copying large external projects into this repository. Keep the local code
small:

- Use `basic-pitch` as an optional PC-side tool.
- Keep `extract_notes.py` as the final MIDI/audio-to-`song.txt` adapter.
- Keep FPGA hardware focused on AXI PWM, not full hardware song playback.
