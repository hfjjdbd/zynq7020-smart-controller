import { NextResponse } from "next/server";
import { boardFetch, getBoardBaseUrl } from "@/lib/board";

export async function GET() {
  try {
    const response = await boardFetch("/health");
    const body = await response.text();

    let data: unknown;
    try {
      data = JSON.parse(body);
    } catch {
      data = { raw: body };
    }

    return NextResponse.json(
      {
        ok: response.ok,
        board: getBoardBaseUrl(),
        status: response.status,
        data,
      },
      { status: response.ok ? 200 : 502 },
    );
  } catch (error) {
    return NextResponse.json(
      {
        ok: false,
        board: getBoardBaseUrl(),
        error:
          error instanceof Error
            ? error.message
            : "Unknown board connection error",
      },
      { status: 502 },
    );
  }
}
