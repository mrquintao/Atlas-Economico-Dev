/**
 * Presentation choices for the state fiscal indicators (S4). The list, order and metadata come
 * from the API (/states/{uf}/…); this only says how to draw each series.
 *
 * Values accumulated from January to the bimester (RREO): the chart does not join two years,
 * since December's total followed by January's value is a restart, not a fall.
 */
const YEAR_TO_DATE_CODES = new Set(["STATE_INVESTMENTS", "STATE_PRIMARY_RESULT", "STATE_NOMINAL_RESULT"]);

export function resetsEachYear(code: string): boolean {
  return YEAR_TO_DATE_CODES.has(code);
}

/** Sign convention of the fiscal results, as in the RREO (a convention, not a judgement). */
const RESULT_CODES = new Set(["STATE_PRIMARY_RESULT", "STATE_NOMINAL_RESULT"]);

export function signNote(code: string): string | null {
  return RESULT_CODES.has(code) ? "Positivo indica superávit; negativo, déficit." : null;
}

/** Display order of the state indicators (same as the API's STATE_DASHBOARD_CODES). */
export const STATE_INDICATOR_ORDER = [
  "STATE_RCL",
  "STATE_PERSONNEL_EXEC",
  "STATE_PERSONNEL_EXEC_RCL",
  "STATE_INVESTMENTS",
  "STATE_PRIMARY_RESULT",
  "STATE_NOMINAL_RESULT",
  "STATE_DC",
  "STATE_DCL",
  "STATE_DCL_RCL",
] as const;
