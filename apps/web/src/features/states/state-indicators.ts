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
