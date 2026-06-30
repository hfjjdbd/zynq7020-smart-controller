import { NextRequest, NextResponse } from "next/server";
import { boardFetch } from "@/lib/board";

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const freq = Number(body.freq);
    const duration = Number(body.duration ?? 300);

    if (!Number.isInteger(freq) || freq < 0 || freq > 5000) {
      return NextResponse.json(
        { ok: false, error: "Frequency must be an integer from 0 to 5000" },
        { status: 400 },
      );
    }

    if (!Number.isInteger(duration) || duration < 10 || duration > 1000) {
      return NextResponse.json(
        { ok: false, error: "Duration must be 10-1000 ms" },
        { status: 400 },
      );
    }

    const params = new URLSearchParams({
      freq: String(freq),
      duration: String(duration),
    });

    const response = await boardFetch(`/buzzer?${params.toString()}`);
    const data = await response.json().catch(() => ({}));

    return NextResponse.json(data, {
      status: response.ok ? 200 : 502,
    });
  } catch (error) {
    return NextResponse.json(
      {
        ok: false,
        error:
          error instanceof Error ? error.message : "Buzzer request failed",
      },
      { status: 502 },
    );
  }
}
