# Melody Conversion Workflow

The board does not decode MP3 or MIDI. It only plays `song.txt`.

```text
music source
  -> extract_notes.py on PC/WSL
  -> song.txt
  -> /root/project/song.txt on board
  -> web_server.py
  -> tone3
  -> buzzer
```

## Best Input: MIDI

MIDI is the most accurate source because it already contains notes and timing.

```sh
python3 extract_notes.py input.mid --text-output song.txt --json-output song.json
```

For chords, the converter outputs one monophonic line for the buzzer. By
default it chooses the highest active note:

```sh
python3 extract_notes.py input.mid --midi-note-policy highest --text-output song.txt
```

For bass-like melodies:

```sh
python3 extract_notes.py input.mid --midi-note-policy lowest --text-output song.txt
```

Many MIDI files have separate melody, accompaniment, and drum tracks. List the
tracks first:

```sh
python3 extract_notes.py input.mid --list-midi-tracks
```

Then convert the melody track only:

```sh
python3 extract_notes.py input.mid --midi-track 2 --text-output song.txt
```

MIDI channel 10 percussion is ignored by default because a passive buzzer cannot
play drums musically. Keep it only for experiments:

```sh
python3 extract_notes.py input.mid --include-drums --text-output song.txt
```

If the melody is too high or too low for the buzzer:

```sh
python3 extract_notes.py input.mid --transpose -12 --text-output song.txt
```

## Acceptable Input: Isolated Audio

WAV/MP3/AAC can work when the file has a clear single melody line.

```sh
python3 extract_notes.py input.mp3 --text-output song.txt --json-output song.json
```

Audio extraction is approximate. Full-mix songs with drums, chords, and vocals
can produce wrong notes because the script has to guess pitch from sound.

Useful tuning options:

```sh
python3 extract_notes.py input.mp3 \
  --min-note C3 \
  --max-note C6 \
  --voiced-threshold 0.75 \
  --minimum-event-ms 80 \
  --text-output song.txt
```

## Best MP3 Path

For ordinary MP3 songs, use a melody-to-MIDI tool first, then run this project
from the MIDI result:

```text
MP3
  -> Basic Pitch or another audio-to-MIDI tool
  -> MIDI
  -> extract_notes.py
  -> song.txt
```

This is usually better than directly converting MP3 to `song.txt`.

Good open-source options to investigate:

- Spotify `basic-pitch`: audio-to-MIDI transcription, useful for MP3/WAV first
  pass.
- A MIDI editor such as MuseScore: inspect/delete accompaniment tracks before
  exporting a clean melody MIDI.

See also `docs/github-open-source-notes.md`.

## Output Format

`song.txt` is intentionally simple:

```text
# freq_hz duration_ms
440 300
0 50
523 300
```

- `freq_hz`: buzzer frequency in Hz
- `duration_ms`: duration in milliseconds
- `freq_hz = 0`: rest, keep silence for that duration

Do not remove rest events. They preserve rhythm.

## Deploy To Board

```sh
cat song.txt | ssh root@192.168.1.100 'cat > /root/project/song.txt'
```

Then play from the web page or:

```sh
ssh root@192.168.1.100 'cd /root/project && ./tone3 song song.txt'
```
