import { readFileSync } from "node:fs";
import { resolve } from "node:path";

import { describe, expect, it } from "vitest";

import { findState, REGION_NAMES, statePath, STATES } from "./states";

describe("STATES", () => {
  it("lists the 27 UFs once each", () => {
    expect(STATES).toHaveLength(27);
    expect(new Set(STATES.map((s) => s.acronym)).size).toBe(27);
    expect(new Set(STATES.map((s) => s.ibgeCode)).size).toBe(27);
    // The first digit of a UF's IBGE code is its region's code.
    for (const s of STATES) {
      expect(s.ibgeCode[0]).toBe(s.region);
      expect(REGION_NAMES[s.region]).toBeDefined();
    }
  });

  it("matches the UFs seeded by the API from the IBGE localidades API", () => {
    const migration = readFileSync(
      resolve(__dirname, "../../../../services/api/migrations/versions/0006_seed_regions_and_states.py"),
      "utf8",
    );
    const seeded = [...migration.matchAll(/\("(\d{2})", "([A-Z]{2})", "([^"]+)", "(\d)"\)/g)].map(
      ([, ibgeCode, acronym, name, region]) => ({ ibgeCode, acronym, name, region }),
    );
    expect(seeded).toEqual(STATES);
  });
});

describe("findState", () => {
  it("finds a UF by acronym, in any case", () => {
    expect(findState("MG")?.name).toBe("Minas Gerais");
    expect(findState("sp")?.acronym).toBe("SP");
    expect(findState("Df")?.ibgeCode).toBe("53");
  });

  it("rejects anything that is not a UF acronym", () => {
    for (const segment of ["BR", "XX", "31", "3", "Sudeste", "", "M G", "%E0%A4%A"]) {
      expect(findState(segment)).toBeNull();
    }
  });

  it("builds the canonical page path", () => {
    expect(statePath({ acronym: "MG" })).toBe("/estados/MG");
  });
});
