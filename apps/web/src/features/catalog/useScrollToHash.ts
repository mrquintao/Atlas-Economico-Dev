"use client";

import { useEffect } from "react";

/**
 * The catalog pages render their sections only after the API answers, so the browser cannot
 * scroll to `#CODE` on its own. Once `ready`, scroll to the element named in the URL hash.
 */
export function useScrollToHash(ready: boolean): void {
  useEffect(() => {
    if (!ready) return;
    const id = decodeURIComponent(window.location.hash.slice(1));
    if (!id) return;
    document.getElementById(id)?.scrollIntoView?.();
  }, [ready]);
}
