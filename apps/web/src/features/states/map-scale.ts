/**
 * Colour classes of the state map (S6), as validated by the economist:
 *
 * - indicators that are never negative: up to 5 quantile classes, sequential viridis palette
 *   (equal intervals would put 26 UFs in one class next to SP);
 * - indicators that can be negative (results, DCL): zero is always a class limit and each side
 *   gets up to 3 quantile classes, diverging PuOr palette (no red/green "bad/good" reading);
 * - the scale type comes from the catalog (`StateMap.scale`), never from the period's values;
 * - a UF without a value has no class: it is drawn hatched, outside the palette.
 *
 * Quantiles by rank: sorted values are split into groups of similar size; equal values always
 * share a class. Each legend entry shows the real range of its members.
 */

/** Viridis, 5 steps (colour-blind safe, monotonic lightness). */
export const SEQUENTIAL_PALETTE = ["#440154", "#3b528b", "#21918c", "#5ec962", "#fde725"] as const;
/** PuOr (ColorBrewer): orange for negative values, purple for positive ones, darker away from zero. */
export const NEGATIVE_PALETTE = ["#b35806", "#f1a340", "#fee0b6"] as const;
export const POSITIVE_PALETTE = ["#d8daeb", "#998ec3", "#542788"] as const;
export const NO_DATA_FILL = "#e5e7eb";

export const SEQUENTIAL_CLASSES = 5;
export const CLASSES_PER_SIDE = 3;

export type ScaleKind = "sequential" | "diverging";

export interface MapClass {
  min: number;
  max: number;
  color: string;
  /** Number of UFs in the class. */
  count: number;
}

export interface MapScale {
  classes: MapClass[];
  /** Class index of a value, or null for a missing value. */
  classify: (value: number | null) => number | null;
}

/** Splits sorted values into at most `k` rank groups; equal values stay in the same group. */
export function quantileGroups(sorted: readonly number[], k: number): number[][] {
  const n = sorted.length;
  if (n === 0) return [];
  const groups: number[][] = [];
  let index = 0;
  for (let g = 0; g < k && index < n; g++) {
    let end = Math.max(index + 1, Math.round(((g + 1) * n) / k));
    // Never split a run of equal values between two classes.
    while (end < n && sorted[end] === sorted[end - 1]) end++;
    groups.push(sorted.slice(index, end));
    index = end;
  }
  return groups;
}

/** Picks `m` colours from a palette, spread from its first to its last entry. */
export function spread(palette: readonly string[], m: number): string[] {
  if (m <= 0) return [];
  if (m === 1) return [palette[Math.floor((palette.length - 1) / 2)]];
  return Array.from({ length: m }, (_, i) => palette[Math.round((i * (palette.length - 1)) / (m - 1))]);
}

function toClasses(groups: number[][], colors: string[]): MapClass[] {
  return groups.map((group, i) => ({
    min: group[0],
    max: group[group.length - 1],
    color: colors[i],
    count: group.length,
  }));
}

export function buildScale(kind: ScaleKind, values: readonly (number | null)[]): MapScale {
  const present = values.filter((v): v is number => v !== null && Number.isFinite(v)).toSorted((a, b) => a - b);
  let classes: MapClass[];
  if (kind === "sequential") {
    const groups = quantileGroups(present, SEQUENTIAL_CLASSES);
    classes = toClasses(groups, spread(SEQUENTIAL_PALETTE, groups.length));
  } else {
    const negative = quantileGroups(present.filter((v) => v < 0), CLASSES_PER_SIDE);
    const positive = quantileGroups(present.filter((v) => v >= 0), CLASSES_PER_SIDE);
    // Negative side: darkest for the most negative; positive side: darkest for the largest.
    const negativeColors = spread(NEGATIVE_PALETTE, negative.length);
    const positiveColors = spread(POSITIVE_PALETTE, positive.length);
    classes = [...toClasses(negative, negativeColors), ...toClasses(positive, positiveColors)];
  }
  return {
    classes,
    classify(value) {
      if (value === null || !Number.isFinite(value)) return null;
      const index = classes.findIndex((c) => value >= c.min && value <= c.max);
      return index === -1 ? null : index;
    },
  };
}
