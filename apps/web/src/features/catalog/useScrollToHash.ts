"use client";

import { useEffect } from "react";

/** `#IPCA_12M` → `IPCA_12M`; a malformed escape (`#%E0`) is kept raw instead of throwing. */
function decodeHash(hash: string): string {
  const raw = hash.slice(1);
  try {
    return decodeURIComponent(raw);
  } catch {
    return raw;
  }
}

/**
 * The catalog pages render their sections only after the API answers, so the browser cannot
 * scroll to `#CODE` on its own. Once `ready`, scroll to the element named in the URL hash.
 */
export function useScrollToHash(ready: boolean): void {
  useEffect(() => {
    if (!ready) return;
    const id = decodeHash(window.location.hash);
    if (!id) return;
    document.getElementById(id)?.scrollIntoView?.();
  }, [ready]);
}
