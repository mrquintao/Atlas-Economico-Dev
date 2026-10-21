/**
 * Horizontal bars of a ranking, in percentages of the bar track. Bars start at zero, which sits
 * at the left edge when every value is non-negative and inside the track otherwise, so negative
 * values (deficits, DCL below zero) extend to the left and are never drawn as small positives.
 */
export interface BarGeometry {
  /** Position of zero in the track (0–100). */
  zero: number;
  bars: { left: number; width: number }[];
}

export function barGeometry(values: readonly number[]): BarGeometry {
  const min = Math.min(0, ...values);
  const max = Math.max(0, ...values);
  const span = max - min;
  if (span === 0) return { zero: 0, bars: values.map(() => ({ left: 0, width: 0 })) };
  const at = (v: number) => ((v - min) / span) * 100;
  const zero = at(0);
  return {
    zero,
    bars: values.map((v) => ({ left: Math.min(zero, at(v)), width: Math.abs(at(v) - zero) })),
  };
}
