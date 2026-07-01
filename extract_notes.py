#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import math
from dataclasses import asdict, dataclass
from pathlib import Path

NOTE_NAMES = [
    "C",
    "C#",
    "D",
    "D#",
    "E",
    "F",
    "F#",
    "G",
    "G#",
    "A",
    "A#",
    "B",
]


@dataclass
class Event:
    freq: int
    dur: int
    note: str
    rest: bool


def midi_to_name(midi: int) -> str:
    return f"{NOTE_NAMES[midi % 12]}{midi // 12 - 1}"


def quantize_frequency(freq: float) -> tuple[int, str]:
    midi = int(round(69 + 12 * math.log2(freq / 440.0)))
    quantized = midi_to_frequency(midi)
    return quantized, midi_to_name(midi)


def midi_to_frequency(midi: int) -> int:
    return int(round(440.0 * (2.0 ** ((midi - 69) / 12.0))))


def merge_adjacent(events: list[Event]) -> list[Event]:
    merged: list[Event] = []

    for event in events:
        if event.dur <= 0:
            continue

        if (
            merged
            and merged[-1].freq == event.freq
            and merged[-1].rest == event.rest
        ):
            merged[-1].dur += event.dur
        else:
            merged.append(event)

    return merged


def absorb_short_events(
    events: list[Event],
    minimum_ms: int,
) -> list[Event]:
    if len(events) < 2:
        return events

    result = events[:]
    index = 0

    while index < len(result):
        event = result[index]

        if event.dur >= minimum_ms:
            index += 1
            continue

        previous = result[index - 1] if index > 0 else None
        following = (
            result[index + 1]
            if index + 1 < len(result)
            else None
        )

        if (
            previous is not None
            and following is not None
            and previous.freq == following.freq
            and previous.rest == following.rest
        ):
            previous.dur += event.dur + following.dur
            del result[index : index + 2]
            continue

        if previous is not None:
            previous.dur += event.dur
            del result[index]
            continue

        if following is not None:
            following.dur += event.dur
            del result[index]
            continue

        index += 1

    return merge_adjacent(result)


def normalize_timeline(events: list[Event], minimum_event_ms: int) -> list[Event]:
    events = merge_adjacent(events)
    events = absorb_short_events(events, minimum_event_ms)
    return merge_adjacent(events)


def extract_events(
    input_path: Path,
    sample_rate: int,
    hop_length: int,
    frame_length: int,
    min_note: str,
    max_note: str,
    voiced_threshold: float,
    median_size: int,
    minimum_event_ms: int,
    duration: float | None,
) -> tuple[list[Event], float]:
    try:
        import librosa
        import numpy as np
        from scipy.ndimage import median_filter
    except ImportError as exc:
        raise SystemExit(
            "Audio input requires librosa, numpy, and scipy. "
            "Install requirements-audio.txt first."
        ) from exc

    audio, sr = librosa.load(
        input_path,
        sr=sample_rate,
        mono=True,
        duration=duration,
    )

    total_seconds = len(audio) / sr

    f0, voiced_flag, voiced_probs = librosa.pyin(
        audio,
        fmin=librosa.note_to_hz(min_note),
        fmax=librosa.note_to_hz(max_note),
        sr=sr,
        frame_length=frame_length,
        hop_length=hop_length,
    )

    frame_count = len(f0)

    midi_values = np.full(frame_count, np.nan)
    valid = (
        voiced_flag
        & np.isfinite(f0)
        & np.isfinite(voiced_probs)
        & (voiced_probs >= voiced_threshold)
    )

    midi_values[valid] = np.rint(librosa.hz_to_midi(f0[valid]))

    sentinel = -9999
    filtered_input = np.where(
        np.isfinite(midi_values),
        midi_values,
        sentinel,
    ).astype(np.int32)

    filtered = median_filter(
        filtered_input,
        size=max(1, median_size),
        mode="nearest",
    )

    frame_ms = 1000.0 * hop_length / sr

    labels: list[int | None] = [
        None if value == sentinel else int(value)
        for value in filtered
    ]

    events: list[Event] = []

    if not labels:
        return events, total_seconds

    current = labels[0]
    frame_total = 1

    def append_event(label: int | None, frames: int) -> None:
        duration_ms = int(round(frames * frame_ms))

        if label is None:
            events.append(
                Event(
                    freq=0,
                    dur=duration_ms,
                    note="REST",
                    rest=True,
                )
            )
        else:
            events.append(
                Event(
                    freq=midi_to_frequency(label),
                    dur=duration_ms,
                    note=midi_to_name(label),
                    rest=False,
                )
            )

    for label in labels[1:]:
        if label == current:
            frame_total += 1
        else:
            append_event(current, frame_total)
            current = label
            frame_total = 1

    append_event(current, frame_total)

    events = normalize_timeline(events, minimum_event_ms)

    expected_ms = int(round(total_seconds * 1000))
    actual_ms = sum(event.dur for event in events)
    drift_ms = expected_ms - actual_ms

    if events and drift_ms:
        events[-1].dur = max(1, events[-1].dur + drift_ms)

    return events, total_seconds


def pick_midi_note(active: dict[int, int], policy: str) -> int | None:
    notes = [
        note
        for note, count in active.items()
        if count > 0
    ]
    if not notes:
        return None
    if policy == "lowest":
        return min(notes)
    return max(notes)


def append_midi_segment(
    events: list[Event],
    note: int | None,
    duration_sec: float,
    transpose: int,
) -> None:
    duration_ms = int(round(duration_sec * 1000.0))
    if duration_ms <= 0:
        return
    if note is None:
        events.append(
            Event(
                freq=0,
                dur=duration_ms,
                note="REST",
                rest=True,
            )
        )
        return

    shifted = note + transpose
    events.append(
        Event(
            freq=midi_to_frequency(shifted),
            dur=duration_ms,
            note=midi_to_name(shifted),
            rest=False,
        )
    )


def extract_midi_events(
    input_path: Path,
    minimum_event_ms: int,
    note_policy: str,
    transpose: int,
    track_index: int | None,
    include_drums: bool,
) -> tuple[list[Event], float]:
    try:
        import mido
    except ImportError as exc:
        raise SystemExit(
            "MIDI input requires mido. Install requirements-audio.txt first."
        ) from exc

    midi_file = mido.MidiFile(str(input_path))
    if track_index is not None and not 0 <= track_index < len(midi_file.tracks):
        raise SystemExit(
            "--midi-track must be between 0 and %d" % (len(midi_file.tracks) - 1)
        )

    merged_messages = []
    for index, track in enumerate(midi_file.tracks):
        tick = 0
        for message in track:
            tick += message.time
            merged_messages.append((tick, index, message))

    merged_messages.sort(key=lambda item: item[0])
    ticks_per_beat = midi_file.ticks_per_beat
    tempo = 500000
    current_sec = 0.0
    current_tick = 0
    last_sec = 0.0
    active: dict[int, int] = {}
    events: list[Event] = []

    for tick, index, message in merged_messages:
        delta_ticks = tick - current_tick
        if delta_ticks:
            current_sec += mido.tick2second(delta_ticks, ticks_per_beat, tempo)
            current_tick = tick

        if current_sec > last_sec:
            append_midi_segment(
                events,
                pick_midi_note(active, note_policy),
                current_sec - last_sec,
                transpose,
            )
            last_sec = current_sec

        if message.type == "set_tempo":
            tempo = message.tempo
            continue

        if track_index is not None and index != track_index:
            continue

        channel = getattr(message, "channel", None)
        if not include_drums and channel == 9:
            continue

        if message.type == "note_on" and message.velocity > 0:
            active[message.note] = active.get(message.note, 0) + 1
        elif message.type == "note_off" or (
            message.type == "note_on" and message.velocity == 0
        ):
            count = active.get(message.note, 0)
            if count <= 1:
                active.pop(message.note, None)
            else:
                active[message.note] = count - 1

    total_seconds = current_sec
    events = normalize_timeline(events, minimum_event_ms)
    return events, total_seconds


def choose_melody_track(summaries: list[dict[str, object]]) -> int | None:
    candidates = [
        summary
        for summary in summaries
        if int(summary["melodic_notes"]) > 0
    ]
    if not candidates:
        return None

    substantial = [
        summary
        for summary in candidates
        if int(summary["melodic_notes"]) >= 8
    ]
    pool = substantial if substantial else candidates
    best = max(
        pool,
        key=lambda item: (
            float(item["mean_pitch"]),
            int(item["melodic_notes"]),
        ),
    )
    return int(best["index"])


def midi_track_summaries(input_path: Path) -> list[dict[str, object]]:
    try:
        import mido
    except ImportError as exc:
        raise SystemExit(
            "MIDI input requires mido. Install requirements-audio.txt first."
        ) from exc

    midi_file = mido.MidiFile(str(input_path))
    summaries = []
    for index, track in enumerate(midi_file.tracks):
        name = ""
        notes = 0
        melodic_notes = 0
        pitch_sum = 0
        channels = set()
        drums = 0
        for message in track:
            if message.type == "track_name":
                name = message.name
            if message.type == "note_on" and message.velocity > 0:
                notes += 1
                channel = getattr(message, "channel", None)
                if channel is not None:
                    channels.add(channel)
                    if channel == 9:
                        drums += 1
                    else:
                        melodic_notes += 1
                        pitch_sum += message.note
                else:
                    melodic_notes += 1
                    pitch_sum += message.note
        mean_pitch = pitch_sum / float(melodic_notes) if melodic_notes else 0.0
        summaries.append(
            {
                "index": index,
                "name": name or "(unnamed)",
                "notes": notes,
                "melodic_notes": melodic_notes,
                "channels": sorted(channels),
                "drum_notes": drums,
                "mean_pitch": mean_pitch,
            }
        )
    return summaries


def is_midi_file(path: Path) -> bool:
    return path.suffix.lower() in {".mid", ".midi"}


def write_outputs(events: list[Event], json_output: Path, text_output: Path) -> None:
    json_output.write_text(
        json.dumps(
            [asdict(event) for event in events],
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    with text_output.open("w", encoding="utf-8") as file:
        file.write("# freq_hz duration_ms\n")
        for event in events:
            file.write(f"{event.freq} {event.dur}\n")


def print_summary(events: list[Event], total_seconds: float, source_kind: str) -> None:
    note_events = [
        event
        for event in events
        if not event.rest
    ]
    rests = [
        event
        for event in events
        if event.rest
    ]

    frequencies = [
        event.freq
        for event in note_events
        if event.freq > 0
    ]

    total_event_ms = sum(event.dur for event in events)

    print(f"Source: {source_kind}")
    print(f"Input duration: {total_seconds:.3f}s")
    print(f"Event duration: {total_event_ms / 1000:.3f}s")
    print(f"Events: {len(events)}")
    print(f"Notes: {len(note_events)}")
    print(f"Rests: {len(rests)}")

    if frequencies:
        print(
            f"Frequency range: "
            f"{min(frequencies)}-{max(frequencies)} Hz"
        )


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Convert MIDI or approximate monophonic audio into tone3 song.txt."
        )
    )
    parser.add_argument("input", type=Path)
    parser.add_argument(
        "--json-output",
        type=Path,
        default=Path("song.json"),
    )
    parser.add_argument(
        "--text-output",
        type=Path,
        default=Path("song.txt"),
    )
    parser.add_argument("--sample-rate", type=int, default=22050)
    parser.add_argument("--hop-length", type=int, default=512)
    parser.add_argument("--frame-length", type=int, default=2048)
    parser.add_argument("--min-note", default="C3")
    parser.add_argument("--max-note", default="C6")
    parser.add_argument(
        "--voiced-threshold",
        type=float,
        default=0.75,
    )
    parser.add_argument("--median-size", type=int, default=5)
    parser.add_argument(
        "--minimum-event-ms",
        type=int,
        default=80,
    )
    parser.add_argument("--duration", type=float)
    parser.add_argument(
        "--midi-note-policy",
        choices=("highest", "lowest"),
        default="highest",
        help="When MIDI has chords, choose this note from active notes.",
    )
    parser.add_argument(
        "--transpose",
        type=int,
        default=0,
        help="Transpose MIDI output by this many semitones.",
    )
    parser.add_argument(
        "--midi-track",
        default="auto",
        help=(
            "Use a MIDI track index, 'auto' to choose a likely melody track, "
            "or 'all' to merge melodic tracks with skyline selection."
        ),
    )
    parser.add_argument(
        "--include-drums",
        action="store_true",
        help="Keep MIDI channel 10 percussion notes instead of ignoring them.",
    )
    parser.add_argument(
        "--list-midi-tracks",
        action="store_true",
        help="Print MIDI track indexes, names, channels, and note counts.",
    )
    args = parser.parse_args()

    if not args.input.is_file():
        raise SystemExit(f"Input file not found: {args.input}")

    if not 0.0 <= args.voiced_threshold <= 1.0:
        raise SystemExit("--voiced-threshold must be 0-1")

    if args.list_midi_tracks:
        if not is_midi_file(args.input):
            raise SystemExit("--list-midi-tracks requires a MIDI input file")
        for summary in midi_track_summaries(args.input):
            print(
                "%(index)d: %(name)s | notes=%(notes)d | "
                "melodic=%(melodic_notes)d | channels=%(channels)s | "
                "drum_notes=%(drum_notes)d | mean_pitch=%(mean_pitch).1f"
                % summary
            )
        return

    if is_midi_file(args.input):
        track_index = None
        midi_track = str(args.midi_track).strip().lower()
        if midi_track == "auto":
            summaries = midi_track_summaries(args.input)
            track_index = choose_melody_track(summaries)
            if track_index is None:
                print(
                    "No melodic MIDI track found; falling back to all tracks.",
                    flush=True,
                )
            else:
                summary = summaries[track_index]
                print(
                    "Auto MIDI track: %(index)d %(name)s "
                    "(melodic=%(melodic_notes)d, mean_pitch=%(mean_pitch).1f)"
                    % summary,
                    flush=True,
                )
        elif midi_track in ("all", "skyline"):
            track_index = None
        else:
            try:
                track_index = int(midi_track)
            except ValueError as exc:
                raise SystemExit(
                    "--midi-track must be an integer, 'auto', or 'all'"
                ) from exc

        events, total_seconds = extract_midi_events(
            input_path=args.input,
            minimum_event_ms=args.minimum_event_ms,
            note_policy=args.midi_note_policy,
            transpose=args.transpose,
            track_index=track_index,
            include_drums=args.include_drums,
        )
        source_kind = "MIDI"
    else:
        print(
            "Warning: polyphonic/full-mix audio may produce "
            "incorrect melody extraction. MIDI is more accurate.",
            flush=True,
        )
        events, total_seconds = extract_events(
            input_path=args.input,
            sample_rate=args.sample_rate,
            hop_length=args.hop_length,
            frame_length=args.frame_length,
            min_note=args.min_note,
            max_note=args.max_note,
            voiced_threshold=args.voiced_threshold,
            median_size=args.median_size,
            minimum_event_ms=args.minimum_event_ms,
            duration=args.duration,
        )
        source_kind = "audio"

    write_outputs(events, args.json_output, args.text_output)
    print_summary(events, total_seconds, source_kind)


if __name__ == "__main__":
    main()
