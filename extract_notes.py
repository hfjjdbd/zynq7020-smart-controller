#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import math
from dataclasses import asdict, dataclass
from pathlib import Path

import librosa
import numpy as np
from scipy.ndimage import median_filter

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
    midi = int(round(librosa.hz_to_midi(freq)))
    quantized = int(round(librosa.midi_to_hz(midi)))
    return quantized, midi_to_name(midi)


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
            frequency = int(round(librosa.midi_to_hz(label)))
            events.append(
                Event(
                    freq=frequency,
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

    events = merge_adjacent(events)
    events = absorb_short_events(events, minimum_event_ms)
    events = merge_adjacent(events)

    expected_ms = int(round(total_seconds * 1000))
    actual_ms = sum(event.dur for event in events)
    drift_ms = expected_ms - actual_ms

    if events and drift_ms:
        events[-1].dur = max(1, events[-1].dur + drift_ms)

    return events, total_seconds


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Extract an approximate monophonic melody. "
            "Best results require an isolated melody track or MIDI."
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
    args = parser.parse_args()

    if not args.input.is_file():
        raise SystemExit(f"Input file not found: {args.input}")

    if not 0.0 <= args.voiced_threshold <= 1.0:
        raise SystemExit("--voiced-threshold must be 0-1")

    print(
        "Warning: polyphonic/full-mix audio may produce "
        "incorrect melody extraction.",
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

    args.json_output.write_text(
        json.dumps(
            [asdict(event) for event in events],
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    with args.text_output.open("w", encoding="utf-8") as file:
        file.write("# freq_hz duration_ms\n")
        for event in events:
            file.write(f"{event.freq} {event.dur}\n")

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

    print(f"Audio duration: {total_seconds:.3f}s")
    print(f"Event duration: {total_event_ms / 1000:.3f}s")
    print(f"Events: {len(events)}")
    print(f"Notes: {len(note_events)}")
    print(f"Rests: {len(rests)}")

    if frequencies:
        print(
            f"Frequency range: "
            f"{min(frequencies)}-{max(frequencies)} Hz"
        )


if __name__ == "__main__":
    main()
