/**
 * Indicators shown on the national dashboard, in display order. Metadata (names, units,
 * sources) comes from the API; this only holds presentation choices.
 */
export interface DashboardIndicator {
  code: string;
  /** Shown while metadata is loading or unavailable. */
  fallbackName: string;
  /** Step line for levels that only change by decision (Selic target). */
  step: boolean;
  /** Daily series can also be shown as monthly (last value of each month). */
  frequencyToggle: boolean;
  /** Prefix of the card's reference month; stocks use "Posição de", period rates "Referência:". */
  referencePrefix?: string;
}

export const DASHBOARD_INDICATORS: DashboardIndicator[] = [
  { code: "SELIC_TARGET", fallbackName: "Meta Selic", step: true, frequencyToggle: true },
  { code: "DBGG_GDP", fallbackName: "Dívida bruta / PIB", step: false, frequencyToggle: false },
  {
    code: "IPCA_12M",
    fallbackName: "IPCA — 12 meses",
    step: false,
    frequencyToggle: false,
    referencePrefix: "Referência:",
  },
];
