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

export interface ApiErrorBody {
  error: { code: string; message: string; details?: unknown };
}
