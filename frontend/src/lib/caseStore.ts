/**
 * The active verification ID, backed by localStorage.
 *
 * Modelled as an external store so components can read it with
 * `useSyncExternalStore` instead of copying it into state inside an effect.
 * That keeps the server snapshot (always "nothing selected") and the client
 * snapshot consistent, so there is no hydration mismatch.
 */

const KEY = "bidflux.activeVerificationId";

let listeners: (() => void)[] = [];

function emit(): void {
  for (const listener of listeners) listener();
}

export function getActiveId(): string | null {
  try {
    return window.localStorage.getItem(KEY);
  } catch {
    return null;
  }
}

/** The server has no access to localStorage, so nothing is selected there. */
export function getServerActiveId(): string | null {
  return null;
}

export function subscribeActiveId(onChange: () => void): () => void {
  listeners.push(onChange);
  const onStorage = (event: StorageEvent) => {
    if (event.key === KEY) onChange();
  };
  window.addEventListener("storage", onStorage);
  return () => {
    listeners = listeners.filter((listener) => listener !== onChange);
    window.removeEventListener("storage", onStorage);
  };
}

export function setActiveId(id: string | null): void {
  try {
    if (id) window.localStorage.setItem(KEY, id);
    else window.localStorage.removeItem(KEY);
  } catch {
    /* storage unavailable — the in-page state still updates via emit() */
  }
  emit();
}

export function clearActiveId(): void {
  setActiveId(null);
}
