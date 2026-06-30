import { NextRequest, NextResponse } from "next/server";
import { boardFetch } from "@/lib/board";

const ALLOWED_LEDS = new Set([
  "usr_led1",
  "usr_led2",
  "led_r",
  "led_g",
  "led_b",
]);

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const name = String(body.name || "");
    const value = Number(body.value);

    if (!ALLOWED_LEDS.has(name)) {
      return NextResponse.json(
        { ok: false, error: "Invalid LED name" },
        { status: 400 },
      );
    }

    if (value !== 0 && value !== 1) {
      return NextResponse.json(
        { ok: false, error: "LED value must be 0 or 1" },
        { status: 400 },
      );
    }

    const params = new URLSearchParams({
      name,
      val: String(value),
    });

    const response = await boardFetch(`/led?${params.toString()}`);
    const data = await response.json().catch(() => ({}));

    return NextResponse.json(data, {
      status: response.ok ? 200 : 502,
    });
  } catch (error) {
    return NextResponse.json(
      {
        ok: false,
        error: error instanceof Error ? error.message : "LED request failed",
      },
      { status: 502 },
    );
  }
}
