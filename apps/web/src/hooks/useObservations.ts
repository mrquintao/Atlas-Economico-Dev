"use client";

import { fetchIndicators, fetchObservations } from "@/lib/api";
import type { DateRange } from "@/lib/period";
import type { Indicator, ObservationsResponse, RequestedFrequency } from "@/types/api";

import { useResource } from "./useResource";

export type { ResourceState } from "./useResource";

/** Loads an indicator series; refetches when code, range or frequency change. */
export function useObservations(code: string, range: DateRange, frequency: RequestedFrequency) {
  const { start, end } = range;
  return useResource<ObservationsResponse>(JSON.stringify([code, start, end, frequency]), (signal) =>
    fetchObservations(code, { start, end }, frequency, signal),
  );
}

/** Loads the indicator catalog (metadata and stored date range of each indicator). */
export function useIndicators() {
  return useResource<Indicator[]>("indicators", fetchIndicators);
}
