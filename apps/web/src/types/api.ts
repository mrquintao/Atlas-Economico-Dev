/** Types mirroring the internal API (services/api/app/schemas). */

import type { MultiPolygon, Polygon } from "geojson";

export type Frequency = "daily" | "monthly" | "bimonthly" | "quarterly" | "four_monthly" | "annual";
export type RequestedFrequency = "original" | "daily" | "monthly";

export interface Source {
  acronym: string;
  name: string;
  organization: string;
  base_url: string;
  documentation_url: string | null;
}

export interface Indicator {
  code: string;
  name: string;
  short_name: string;
  description: string;
  unit: string;
  change_unit: string;
  frequency: Frequency;
  geographic_level: string;
  methodology: string;
  methodology_version: string | null;
  first_available_date: string | null;
  source: Source;
  source_series_code: string;
  source_url: string;
  first_stored_date: string | null;
  last_stored_date: string | null;
  last_collected_at: string | null;
  /** Latest collection attempt, whatever its outcome (null if never attempted). */
  last_run: IngestionRun | null;
}

export interface IngestionRun {
  status: "running" | "success" | "failed";
  started_at: string;
  finished_at: string | null;
  error_type: string | null;
}

export interface Geography {
  ibge_code: string;
  acronym: string;
  name: string;
  geographic_level: string;
}

export interface Observation {
  date: string;
  value: number;
  period_start: string;
  period_end: string;
  partial: boolean;
}

export interface Point {
  date: string;
  value: number;
}

export interface SeriesStats {
  first: Point;
  last: Point;
  change: number;
  change_unit: string;
  min: Point;
  max: Point;
}

export interface ObservationsResponse {
  indicator: Indicator;
  geography: Geography;
  unit: string;
  original_frequency: Frequency;
  frequency: Frequency;
  aggregation: { method: "none" | "last_value_of_period"; description: string };
  start_date: string | null;
  end_date: string | null;
  count: number;
  stats: SeriesStats | null;
  observations: Observation[];
}

export interface LatestValue {
  date: string;
  value: number;
  period_start: string;
  period_end: string;
  /** Period not closed yet (e.g. the current month of a daily series). */
  partial: boolean;
}

/** Absolute difference versus the same month one year earlier, in `change_unit`. */
export interface Change12m {
  value: number;
  change_unit: string;
  reference_date: string;
  reference_value: number;
}

export interface NationalDashboardItem {
  indicator: Indicator;
  status: "available" | "no_data";
  aggregation: { method: "none" | "last_value_of_period"; description: string };
  latest: LatestValue | null;
  change_12m: Change12m | null;
}

export interface NationalDashboard {
  geography: Geography;
  indicators: NationalDashboardItem[];
}

/** One state indicator of a UF (/states/{uf}/indicators): the series plus availability. */
export interface StateIndicatorSeries extends ObservationsResponse {
  /** "no_data": nothing stored for the UF. "available" with count 0: nothing in the range. */
  status: "available" | "no_data";
  /** Accumulation window of each published value (year to date, 12 months, balance). */
  accumulation_window: string;
}

export interface StateIndicators {
  geography: Geography;
  start_date: string | null;
  end_date: string | null;
  /** Comparability caveats of the UF (e.g. the Distrito Federal). */
  notes: string[];
  indicators: StateIndicatorSeries[];
}

/** Latest value of a state indicator; `change_12m` compares with the same period a year earlier. */
export interface StateDashboardItem extends NationalDashboardItem {
  accumulation_window: string;
  /** Basis and unit of the comparison (null without comparison). */
  change_note: string | null;
}

export interface StateDashboard {
  geography: Geography;
  notes: string[];
  indicators: StateDashboardItem[];
}

/** A reference period of the state map and how many UFs published a value for it. */
export interface StateMapPeriod {
  reference_date: string;
  period_start: string;
  period_end: string;
  coverage: number;
}

export interface StateMapValue {
  geography: Geography;
  /** "no_data": no value published for the period (never zero). */
  status: "available" | "no_data";
  value: number | null;
}

/** One state indicator in the 27 UFs at a single reference period (/states/map/{code}). */
export interface StateMap {
  indicator: Indicator;
  accumulation_window: string;
  /** "diverging" (centred on zero) for indicators that can be negative; set by the catalog. */
  scale: "sequential" | "diverging";
  period: StateMapPeriod | null;
  default_rule: string;
  /** Most recent first. */
  available_periods: StateMapPeriod[];
  notes: string[];
  /** The 27 UFs, by acronym. */
  states: StateMapValue[];
}

export interface BoundaryFeature {
  type: "Feature";
  id: string;
  properties: { ibge_code: string; acronym: string; name: string };
  geometry: MultiPolygon | Polygon;
}

/** Official IBGE boundaries of the 27 UFs (/geographies/states/boundaries). */
export interface StateBoundaries {
  type: "FeatureCollection";
  metadata: { source_url: string; mesh_year: number; collected_at: string };
  features: BoundaryFeature[];
}

export interface ApiErrorBody {
  error: { code: string; message: string; details?: unknown };
}
