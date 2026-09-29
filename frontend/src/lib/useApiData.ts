import { useCallback, useEffect, useRef, useState } from "react";
import { ApiError } from "./api";

export interface LoadError {
  message: string;
  status?: number;
  code?: string;
}

export interface ApiData<T> {
  data: T | null;
  error: LoadError | null;
  refresh: () => void;
}

function toLoadError(err: unknown): LoadError {
  if (err instanceof ApiError) {
    return { message: err.message, status: err.status, code: err.code };
  }
  if (err instanceof Error) return { message: err.message };
  return { message: "An unexpected error occurred." };
}

/** Keep a ref pointing at the latest value without touching refs during render. */
function useLatest<T>(value: T) {
  const ref = useRef(value);
  useEffect(() => {
    ref.current = value;
  }, [value]);
  return ref;
}

interface Entry<T> {
  key: string | null;
  attempt: number;
  data: T | null;
  error: LoadError | null;
}

/**
 * One fetch with the life-cycle every data page needs:
 *
 * - A `cancelled` flag so a slow request can never overwrite a newer one (fixes
 *   cross-case bleed when the active verification changes mid-flight).
 * - Data and errors are only exposed while they belong to the current `key` and
 *   the latest attempt, so a case switch or a retry can never render stale
 *   results — including an old error sitting under a fresh spinner or a
 *   successful retry leaving a dead banner behind.
 * - `refresh()` re-runs the loader while keeping the current data visible.
 *
 * Pass a constant key (e.g. "dashboard") for endpoints that are not
 * case-scoped. The loader is read from a ref, so inline closures are safe.
 */
export function useApiData<T>(key: string | null, load: () => Promise<T>): ApiData<T> {
  const [reloadKey, setReloadKey] = useState(0);
  const [entry, setEntry] = useState<Entry<T>>({
    key: null,
    attempt: -1,
    data: null,
    error: null,
  });

  const latestLoad = useLatest(load);

  useEffect(() => {
    if (!key) return;
    let cancelled = false;
    latestLoad.current().then(
      (value) => {
        if (!cancelled) setEntry({ key, attempt: reloadKey, data: value, error: null });
      },
      (err: unknown) => {
        if (!cancelled)
          setEntry({ key, attempt: reloadKey, data: null, error: toLoadError(err) });
      },
    );
    return () => {
      cancelled = true;
    };
  }, [key, reloadKey, latestLoad]);

  const refresh = useCallback(() => setReloadKey((n) => n + 1), []);

  const fresh = entry.key === key && entry.attempt === reloadKey;
  return { data: fresh ? entry.data : null, error: fresh ? entry.error : null, refresh };
}