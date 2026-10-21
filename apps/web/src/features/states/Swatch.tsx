import { NO_DATA_FILL } from "./map-scale";

/** Colour sample of a map class; hatched (outside the palette) for a UF without a value. */
export function Swatch({ color, hatched }: { color?: string; hatched?: boolean }) {
  return (
    <span
      aria-hidden
      className="inline-block size-3.5 shrink-0 rounded-[3px] border border-black/10"
      style={
        hatched
          ? {
              backgroundColor: NO_DATA_FILL,
              backgroundImage: "repeating-linear-gradient(45deg, #6b7280 0 1.5px, transparent 1.5px 6px)",
            }
          : { backgroundColor: color }
      }
    />
  );
}
