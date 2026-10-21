/** Types mirroring the internal API (services/api/app/schemas). */

export type Frequency = "daily" | "monthly" | "quarterly" | "annual";
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

export interface ApiErrorBody {
  error: { code: string; message: string; details?: unknown };
}
