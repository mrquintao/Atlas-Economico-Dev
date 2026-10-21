import { describe, expect, it } from "vitest";

import { barGeometry } from "./ranking-bars";

describe("barGeometry", () => {
  it("starts bars at the left edge when every value is non-negative", () => {
    expect(barGeometry([50, 25, 0])).toEqual({
      zero: 0,
      bars: [
        { left: 0, width: 100 },
        { left: 0, width: 50 },
        { left: 0, width: 0 },
      ],
    });
  });

  it("draws negative values to the left of zero", () => {
    const { zero, bars } = barGeometry([150, -50]);
    expect(zero).toBe(25);
    expect(bars).toEqual([
      { left: 25, width: 75 },
      { left: 0, width: 25 },
    ]);
  });

  it("handles all-zero and empty inputs", () => {
    expect(barGeometry([0, 0]).bars).toEqual([
      { left: 0, width: 0 },
      { left: 0, width: 0 },
    ]);
    expect(barGeometry([]).bars).toEqual([]);
  });
});
