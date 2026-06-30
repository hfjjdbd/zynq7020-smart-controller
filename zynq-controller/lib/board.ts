const DEFAULT_BOARD_BASE_URL = "http://192.168.1.100:8080";

export function getBoardBaseUrl(): string {
  const raw = process.env.BOARD_BASE_URL || DEFAULT_BOARD_BASE_URL;
  return raw.replace(/\/+$/, "");
}

export async function boardFetch(
  path: string,
  init?: RequestInit,
): Promise<Response> {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 3000);

  try {
    return await fetch(`${getBoardBaseUrl()}${path}`, {
      ...init,
      cache: "no-store",
      signal: controller.signal,
      headers: {
        Accept: "application/json",
        ...(init?.headers || {}),
      },
    });
  } finally {
    clearTimeout(timeout);
  }
}
