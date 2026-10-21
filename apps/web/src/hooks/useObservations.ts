"use client";

import {
  fetchIndicators,
  fetchNationalDashboard,
  fetchObservations,
  fetchSources,
  fetchStateDashboard,
  fetchStateIndicators,
} from "@/lib/api";
import type { DateRange } from "@/lib/period";
import type {
  Indicator,
  NationalDashboard,
  ObservationsResponse,
  RequestedFrequency,
  Source,
  StateDashboard,
  StateIndicators,
} from "@/types/api";

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

/** Loads the official data sources registered in the catalog. */
export function useSources() {
  return useResource<Source[]>("sources", fetchSources);
}

/** Loads the national dashboard summary (latest value and 12-month change per indicator). */
export function useNationalDashboard() {
  return useResource<NationalDashboard>("dashboard/national", fetchNationalDashboard);
}

/** Loads a UF's state indicators (series in the range); refetches when UF or range change. */
export function useStateIndicators(uf: string, range: DateRange) {
  const { start, end } = range;
  return useResource<StateIndicators>(JSON.stringify(["states", uf, start, end]), (signal) =>
    fetchStateIndicators(uf, { start, end }, signal),
  );
}

/** Loads a UF's summary (latest value and comparison with the same period a year earlier). */
export function useStateDashboard(uf: string) {
  return useResource<StateDashboard>(`states/${uf}/dashboard`, (signal) =>
    fetchStateDashboard(uf, signal),
  );
}
