import { describe, expect, it } from "vitest";

import { formatChange, formatDate, formatMonth, formatNumber, formatRate, parseIsoDate } from "./format";

describe("format", () => {
  it("uses Brazilian decimal comma", () => {
    expect(formatNumber(13.75)).toBe("13,75");
    expect(formatNumber(1234.5)).toBe("1.234,50");
  });

  it("formats rate levels with their unit", () => {
    expect(formatRate(13.75, "% a.a.")).toBe("13,75% a.a.");
    expect(formatRate(76.1, "% do PIB")).toBe("76,10% do PIB");
    expect(formatRate(2, "índice")).toBe("2,00 índice");
  });

  it("expresses rate changes in percentage points with sign", () => {
    // 10% → 12% is +2 p.p., not +2% or +20%
    expect(formatChange(12 - 10, "p.p.")).toBe("+2,00 p.p.");
    expect(formatChange(-0.25, "p.p.")).toBe("-0,25 p.p.");
    expect(formatChange(0, "p.p.")).toBe("0,00 p.p.");
    expect(formatChange(-0.0000001, "p.p.")).toBe("0,00 p.p.");
  });

  it("formats ISO dates without timezone shifts", () => {
    expect(formatDate("2008-01-01")).toBe("01/01/2008");
    expect(formatDate("2026-10-21")).toBe("21/10/2026");
    expect(formatMonth("2024-02-29")).toBe("fev/2024");
  });

  it("rejects malformed dates", () => {
    expect(() => parseIsoDate("21/10/2026")).toThrow();
  });
});
