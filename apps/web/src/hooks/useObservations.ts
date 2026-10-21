"use client";

import { useCallback, useEffect, useState } from "react";

import { ApiError, fetchObservations } from "@/lib/api";
import type { DateRange } from "@/lib/period";
import type { ObservationsResponse, RequestedFrequency } from "@/types/api";

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
 * Loads an indicator series; refetches when code, range or frequency change. While a new
 * request is in flight the previous data is kept, so the chart does not flash empty.
 */
export function useObservations(
  code: string,
  range: DateRange,
  frequency: RequestedFrequency,
): ResourceState<ObservationsResponse> & { retry: () => void } {
  const [attempt, setAttempt] = useState(0);
  const [settled, setSettled] = useState<Settled<ObservationsResponse> | null>(null);
  const { start, end } = range;
  const key = JSON.stringify([code, start, end, frequency, attempt]);

  useEffect(() => {
    const controller = new AbortController();
    fetchObservations(code, { start, end }, frequency, controller.signal)
      .then((data) => setSettled({ key, data, error: null }))
      .catch((error: unknown) => {
        if (controller.signal.aborted) return;
        const apiError =
          error instanceof ApiError
            ? error
            : new ApiError("Erro inesperado ao carregar os dados.", null, "unknown");
        setSettled((previous) => ({ key, data: previous?.data ?? null, error: apiError }));
      });
    return () => controller.abort();
  }, [code, start, end, frequency, key]);

  const retry = useCallback(() => setAttempt((n) => n + 1), []);
  const data = settled?.data ?? null;

  if (settled?.key !== key) return { status: "loading", data, retry };
  if (settled.error) return { status: "error", data, error: settled.error, retry };
  return data
    ? { status: "success", data, retry }
    : { status: "loading", data: null, retry };
}
