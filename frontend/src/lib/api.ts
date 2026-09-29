/**
 * The single API client for BIDFLUX.
 *
 * The base URL comes from NEXT_PUBLIC_API_URL and nothing else. In production a
 * missing value is a configuration error — there is deliberately no localhost
 * fallback that would silently point a deployed build at the operator's machine.
 */

const RAW_BASE = process.env.NEXT_PUBLIC_API_URL;

/** Thrown when the app is built without an API base URL. */
export class ConfigurationError extends Error {
  constructor() {
    super(
      "NEXT_PUBLIC_API_URL is not set. Set it to your backend origin " +
        "(for example https://bidflux-api.example.com) and rebuild.",
    );
    this.name = "ConfigurationError";
  }
}

export function apiBaseUrl(): string {
  if (!RAW_BASE) {
    if (process.env.NODE_ENV === "production") {
      throw new ConfigurationError();
    }
    // Development convenience only.
    return "http://localhost:8000";
  }
  return RAW_BASE.replace(/\/+$/, "");
}

export function hasApiConfigured(): boolean {
  return Boolean(RAW_BASE);
}

export class ApiError extends Error {
  readonly status: number;
  readonly code: string;

  constructor(message: string, status: number, code = "error") {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
  }
}

type Query = Record<string, string | number | boolean | undefined | null>;

function buildUrl(path: string, query?: Query): string {
  const base = apiBaseUrl();
  const url = new URL(`${base}/api${path}`);
  if (query) {
    for (const [key, value] of Object.entries(query)) {
      if (value !== undefined && value !== null && value !== "") {
        url.searchParams.set(key, String(value));
      }
    }
  }
  return url.toString();
}

async function unwrap<T>(response: Response): Promise<T> {
  if (response.ok) {
    if (response.status === 204) {
      return undefined as T;
    }
    return (await response.json()) as T;
  }

  let message = `Request failed with status ${response.status}.`;
  let code = "http_error";
  try {
    const body = (await response.json()) as { error?: { message?: string; code?: string } };
    if (body?.error?.message) {
      message = body.error.message;
    }
    if (body?.error?.code) {
      code = body.error.code;
    }
  } catch {
    /* response had no JSON body */
  }
  throw new ApiError(message, response.status, code);
}

export async function apiGet<T>(path: string, query?: Query): Promise<T> {
  const response = await fetch(buildUrl(path, query), {
    method: "GET",
    headers: { Accept: "application/json" },
    cache: "no-store",
  });
  return unwrap<T>(response);
}

export async function apiPost<T>(
  path: string,
  body?: unknown,
  query?: Query,
): Promise<T> {
  const response = await fetch(buildUrl(path, query), {
    method: "POST",
    headers: { "Content-Type": "application/json", Accept: "application/json" },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  return unwrap<T>(response);
}

export async function apiUpload<T>(
  path: string,
  form: FormData,
): Promise<T> {
  const response = await fetch(buildUrl(path), {
    method: "POST",
    body: form,
    headers: { Accept: "application/json" },
  });
  return unwrap<T>(response);
}

export function errorMessage(error: unknown): string {
  if (error instanceof ApiError) return error.message;
  if (error instanceof ConfigurationError) return error.message;
  if (error instanceof Error) return error.message;
  return "An unexpected error occurred.";
}
