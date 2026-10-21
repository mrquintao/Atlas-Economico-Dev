/**
 * The 27 federative units (26 states and the Distrito Federal), as seeded by the API migration
 * 0006 from the official IBGE localidades API. Used to build the /estados routes at build time,
 * so an unknown UF is a 404 without asking the API. The economic data always comes from the API.
 */
export interface StateUnit {
  ibgeCode: string;
  acronym: string;
  name: string;
  region: string;
}

export const REGION_NAMES: Record<string, string> = {
  "1": "Norte",
  "2": "Nordeste",
  "3": "Sudeste",
  "4": "Sul",
  "5": "Centro-Oeste",
};

export const STATES: readonly StateUnit[] = [
  { ibgeCode: "11", acronym: "RO", name: "Rondônia", region: "1" },
  { ibgeCode: "12", acronym: "AC", name: "Acre", region: "1" },
  { ibgeCode: "13", acronym: "AM", name: "Amazonas", region: "1" },
  { ibgeCode: "14", acronym: "RR", name: "Roraima", region: "1" },
  { ibgeCode: "15", acronym: "PA", name: "Pará", region: "1" },
  { ibgeCode: "16", acronym: "AP", name: "Amapá", region: "1" },
  { ibgeCode: "17", acronym: "TO", name: "Tocantins", region: "1" },
  { ibgeCode: "21", acronym: "MA", name: "Maranhão", region: "2" },
  { ibgeCode: "22", acronym: "PI", name: "Piauí", region: "2" },
  { ibgeCode: "23", acronym: "CE", name: "Ceará", region: "2" },
  { ibgeCode: "24", acronym: "RN", name: "Rio Grande do Norte", region: "2" },
  { ibgeCode: "25", acronym: "PB", name: "Paraíba", region: "2" },
  { ibgeCode: "26", acronym: "PE", name: "Pernambuco", region: "2" },
  { ibgeCode: "27", acronym: "AL", name: "Alagoas", region: "2" },
  { ibgeCode: "28", acronym: "SE", name: "Sergipe", region: "2" },
  { ibgeCode: "29", acronym: "BA", name: "Bahia", region: "2" },
  { ibgeCode: "31", acronym: "MG", name: "Minas Gerais", region: "3" },
  { ibgeCode: "32", acronym: "ES", name: "Espírito Santo", region: "3" },
  { ibgeCode: "33", acronym: "RJ", name: "Rio de Janeiro", region: "3" },
  { ibgeCode: "35", acronym: "SP", name: "São Paulo", region: "3" },
  { ibgeCode: "41", acronym: "PR", name: "Paraná", region: "4" },
  { ibgeCode: "42", acronym: "SC", name: "Santa Catarina", region: "4" },
  { ibgeCode: "43", acronym: "RS", name: "Rio Grande do Sul", region: "4" },
  { ibgeCode: "50", acronym: "MS", name: "Mato Grosso do Sul", region: "5" },
  { ibgeCode: "51", acronym: "MT", name: "Mato Grosso", region: "5" },
  { ibgeCode: "52", acronym: "GO", name: "Goiás", region: "5" },
  { ibgeCode: "53", acronym: "DF", name: "Distrito Federal", region: "5" },
];

/** The UF for a URL segment ("MG" or "mg"); null for anything else (regions, codes, typos). */
export function findState(segment: string): StateUnit | null {
  let key: string;
  try {
    key = decodeURIComponent(segment).toUpperCase();
  } catch {
    return null;
  }
  return STATES.find((s) => s.acronym === key) ?? null;
}

/** Canonical page of a UF. */
export function statePath(state: Pick<StateUnit, "acronym">): string {
  return `/estados/${state.acronym}`;
}
