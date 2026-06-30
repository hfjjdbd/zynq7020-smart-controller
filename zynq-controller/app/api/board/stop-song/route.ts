import { NextResponse } from "next/server";
import { boardFetch } from "@/lib/board";

export async function POST() {
  try {
    const response = await boardFetch("/stop_song", { method: "POST" });
    const data = await response.json().catch(() => ({}));

    return NextResponse.json(data, {
      status: response.ok ? 200 : 502,
    });
  } catch (error) {
    return NextResponse.json(
      {
        ok: false,
        error: error instanceof Error ? error.message : "Stop request failed",
      },
      { status: 502 },
    );
  }
}
