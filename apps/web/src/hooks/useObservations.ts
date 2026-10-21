"use client";

import {
  fetchIndicators,
  fetchNationalDashboard,
  fetchObservations,
  fetchSources,
  fetchStateBoundaries,
  fetchStateDashboard,
  fetchStateIndicators,
  fetchStateMap,
} from "@/lib/api";
import type { DateRange } from "@/lib/period";
import type {
  Indicator,
  NationalDashboard,
  ObservationsResponse,
  RequestedFrequency,
  Source,
  StateBoundaries,
  StateDashboard,
  StateIndicators,
  StateMap,
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

/** Loads one state indicator in the 27 UFs at a period (null: the API's default period). */
export function useStateMap(code: string, referenceDate: string | null) {
  return useResource<StateMap>(JSON.stringify(["states/map", code, referenceDate]), (signal) =>
    fetchStateMap(code, referenceDate, signal),
  );
}

/** Loads the official boundaries of the 27 UFs. */
export function useStateBoundaries() {
  return useResource<StateBoundaries>("geographies/states/boundaries", fetchStateBoundaries);
}
