import { describe, expect, it } from "vitest";

import {
  buildScale,
  NEGATIVE_PALETTE,
  POSITIVE_PALETTE,
  quantileGroups,
  SEQUENTIAL_PALETTE,
  spread,
} from "./map-scale";

describe("quantileGroups", () => {
  it("splits 27 values into 5 groups of similar size", () => {
    const values = Array.from({ length: 27 }, (_, i) => i);
    const sizes = quantileGroups(values, 5).map((g) => g.length);
    expect(sizes).toEqual([5, 6, 5, 6, 5]);
    expect(sizes.reduce((a, b) => a + b)).toBe(27);
  });

  it("keeps equal values in the same group", () => {
    const groups = quantileGroups([1, 2, 2, 2, 2, 3], 3);
    expect(groups).toEqual([[1, 2, 2, 2, 2], [3]]);
  });

  it("never creates more groups than values", () => {
    expect(quantileGroups([5, 7], 5)).toEqual([[5], [7]]);
    expect(quantileGroups([], 5)).toEqual([]);
  });
});

describe("spread", () => {
  it("uses the ends of the palette and a middle colour for a single class", () => {
    expect(spread(SEQUENTIAL_PALETTE, 5)).toEqual([...SEQUENTIAL_PALETTE]);
    expect(spread(SEQUENTIAL_PALETTE, 2)).toEqual([SEQUENTIAL_PALETTE[0], SEQUENTIAL_PALETTE[4]]);
    expect(spread(SEQUENTIAL_PALETTE, 1)).toEqual([SEQUENTIAL_PALETTE[2]]);
    expect(spread(NEGATIVE_PALETTE, 0)).toEqual([]);
  });
});

describe("buildScale", () => {
  it("sequential: 5 quantile classes with their real ranges; equal intervals are not used", () => {
    // One very large value (SP-like) does not flatten the others into one class.
    const values = [1, 2, 3, 4, 5, 6, 7, 8, 9, 1000];
    const scale = buildScale("sequential", values);
    expect(scale.classes.map((c) => [c.min, c.max, c.count])).toEqual([
      [1, 2, 2],
      [3, 4, 2],
      [5, 6, 2],
      [7, 8, 2],
      [9, 1000, 2],
    ]);
    expect(scale.classes.map((c) => c.color)).toEqual([...SEQUENTIAL_PALETTE]);
    expect(scale.classify(1)).toBe(0);
    expect(scale.classify(500)).toBe(4);
  });

  it("a missing value has no class (never the class of zero or of the minimum)", () => {
    const scale = buildScale("sequential", [0, 10, null, 20]);
    expect(scale.classify(null)).toBeNull();
    expect(scale.classify(0)).toBe(0);
    expect(scale.classes.reduce((n, c) => n + c.count, 0)).toBe(3);
  });

  it("diverging: zero is a class limit and each side has up to 3 classes", () => {
    const values = [-30, -20, -10, 5, 10, 20, 30, 40, 50, null];
    const scale = buildScale("diverging", values);
    expect(scale.classes.map((c) => [c.min, c.max])).toEqual([
      [-30, -30],
      [-20, -20],
      [-10, -10],
      [5, 10],
      [20, 30],
      [40, 50],
    ]);
    expect(scale.classes.map((c) => c.color)).toEqual([...NEGATIVE_PALETTE, ...POSITIVE_PALETTE]);
    for (const c of scale.classes) expect(c.min < 0 && c.max > 0).toBe(false);
    expect(scale.classify(-10)).toBe(2);
    expect(scale.classify(5)).toBe(3);
  });

  it("diverging with few negative UFs: fewer classes on that side", () => {
    const scale = buildScale("diverging", [-3, 1, 2, 3, 4, 5, 6]);
    expect(scale.classes[0]).toMatchObject({ min: -3, max: -3, color: NEGATIVE_PALETTE[1] });
    expect(scale.classes).toHaveLength(4);
  });

  it("diverging with only positive values keeps the diverging palette (scale from the catalog)", () => {
    const scale = buildScale("diverging", [1, 2, 3]);
    expect(scale.classes.map((c) => c.color)).toEqual([...POSITIVE_PALETTE]);
  });

  it("no values: no classes", () => {
    const scale = buildScale("sequential", [null, null]);
    expect(scale.classes).toEqual([]);
    expect(scale.classify(null)).toBeNull();
  });
});
