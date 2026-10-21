"use client";

import { useCallback, useEffect, useEffectEvent, useState } from "react";

import { ApiError } from "@/lib/api";

export type ResourceState<T> =
  | { status: "loading"; data: T | null }
  | { status: "error"; data: T | null; error: ApiError }
  | { status: "success"; data: T };

interface Settled<T> {
  key: string;
  data: T | null;
  error: ApiError | null;
}

/**
 * Loads a resource identified by `key`; reloads whenever the key changes. While a new request
 * is in flight the previous data is kept, so charts do not flash empty.
 */
export function useResource<T>(
  key: string,
  load: (signal: AbortSignal) => Promise<T>,
): ResourceState<T> & { retry: () => void } {
  const [attempt, setAttempt] = useState(0);
  const [settled, setSettled] = useState<Settled<T> | null>(null);
  const requestKey = `${key}#${attempt}`;
  // `load` is recreated on every render; the key alone decides when to reload.
  const runLoad = useEffectEvent((signal: AbortSignal) => load(signal));

  useEffect(() => {
    const controller = new AbortController();
    runLoad(controller.signal)
      .then((data) => setSettled({ key: requestKey, data, error: null }))
      .catch((error: unknown) => {
        if (controller.signal.aborted) return;
        const apiError =
          error instanceof ApiError
            ? error
            : new ApiError("Erro inesperado ao carregar os dados.", null, "unknown");
        setSettled((previous) => ({ key: requestKey, data: previous?.data ?? null, error: apiError }));
      });
    return () => controller.abort();
  }, [requestKey]);

  const retry = useCallback(() => setAttempt((n) => n + 1), []);
  const data = settled?.data ?? null;

  if (settled?.key !== requestKey) return { status: "loading", data, retry };
  if (settled.error) return { status: "error", data, error: settled.error, retry };
  return data ? { status: "success", data, retry } : { status: "loading", data: null, retry };
}
