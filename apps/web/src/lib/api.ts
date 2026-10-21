import type {
  ApiErrorBody,
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
import type { DateRange } from "@/lib/period";

/** The frontend only talks to the internal API, never to official sources directly. */
export const API_BASE_URL = (process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000").replace(
  /\/$/,
  "",
);

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number | null,
    readonly code: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

function isApiErrorBody(value: unknown): value is ApiErrorBody {
  return (
    typeof value === "object" &&
    value !== null &&
    "error" in value &&
    typeof (value as ApiErrorBody).error?.message === "string"
  );
}

export function observationsUrl(
  code: string,
  range: DateRange,
  frequency: RequestedFrequency,
): string {
  const params = new URLSearchParams({ frequency });
  if (range.start) params.set("start_date", range.start);
  if (range.end) params.set("end_date", range.end);
  return `${API_BASE_URL}/api/v1/indicators/${encodeURIComponent(code)}/observations?${params}`;
}

async function getJson<T>(url: string, signal?: AbortSignal): Promise<T> {
  let response: Response;
  try {
    response = await fetch(url, { signal, headers: { Accept: "application/json" } });
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError") throw error;
    throw new ApiError(
      "Não foi possível conectar à API do Atlas. Verifique se o backend está em execução.",
      null,
      "network_error",
    );
  }
  const body: unknown = await response.json().catch(() => null);
  if (!response.ok) {
    if (isApiErrorBody(body)) {
      throw new ApiError(body.error.message, response.status, body.error.code);
    }
    throw new ApiError(`Erro inesperado da API (HTTP ${response.status}).`, response.status, "http_error");
  }
  if (body === null) {
    throw new ApiError("Resposta inválida da API.", response.status, "invalid_response");
  }
  return body as T;
}

export function fetchObservations(
  code: string,
  range: DateRange,
  frequency: RequestedFrequency,
  signal?: AbortSignal,
): Promise<ObservationsResponse> {
  return getJson<ObservationsResponse>(observationsUrl(code, range, frequency), signal);
}

export function fetchIndicators(signal?: AbortSignal): Promise<Indicator[]> {
  return getJson<Indicator[]>(`${API_BASE_URL}/api/v1/indicators`, signal);
}

export function fetchSources(signal?: AbortSignal): Promise<Source[]> {
  return getJson<Source[]>(`${API_BASE_URL}/api/v1/sources`, signal);
}

/** Latest value and 12-month change of every national dashboard indicator, in one request. */
export function fetchNationalDashboard(signal?: AbortSignal): Promise<NationalDashboard> {
  return getJson<NationalDashboard>(`${API_BASE_URL}/api/v1/dashboard/national`, signal);
}

function statePath(uf: string): string {
  return `${API_BASE_URL}/api/v1/states/${encodeURIComponent(uf)}`;
}

export function stateIndicatorsUrl(uf: string, range: DateRange): string {
  const params = new URLSearchParams();
  if (range.start) params.set("start_date", range.start);
  if (range.end) params.set("end_date", range.end);
  const query = params.toString();
  return `${statePath(uf)}/indicators${query ? `?${query}` : ""}`;
}

/** Every state indicator of a UF (metadata, availability and series in the range), in one request. */
export function fetchStateIndicators(
  uf: string,
  range: DateRange,
  signal?: AbortSignal,
): Promise<StateIndicators> {
  return getJson<StateIndicators>(stateIndicatorsUrl(uf, range), signal);
}

/** Latest value and change versus the same period a year earlier of each state indicator. */
export function fetchStateDashboard(uf: string, signal?: AbortSignal): Promise<StateDashboard> {
  return getJson<StateDashboard>(`${statePath(uf)}/dashboard`, signal);
}

export function stateMapUrl(code: string, referenceDate: string | null): string {
  const query = referenceDate ? `?${new URLSearchParams({ reference_date: referenceDate })}` : "";
  return `${API_BASE_URL}/api/v1/states/map/${encodeURIComponent(code)}${query}`;
}

/** One state indicator in the 27 UFs at one period (the most recent well-covered by default). */
export function fetchStateMap(
  code: string,
  referenceDate: string | null,
  signal?: AbortSignal,
): Promise<StateMap> {
  return getJson<StateMap>(stateMapUrl(code, referenceDate), signal);
}

/** Official IBGE boundaries of the 27 UFs (GeoJSON). */
export function fetchStateBoundaries(signal?: AbortSignal): Promise<StateBoundaries> {
  return getJson<StateBoundaries>(`${API_BASE_URL}/api/v1/geographies/states/boundaries`, signal);
}
