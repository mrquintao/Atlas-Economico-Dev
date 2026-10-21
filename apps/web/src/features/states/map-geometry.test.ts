import { readFileSync } from "node:fs";
import { resolve } from "node:path";

import { geoArea, geoBounds } from "d3-geo";
import type { Feature, FeatureCollection, MultiPolygon, Polygon } from "geojson";
import { describe, expect, it } from "vitest";

import { rewindForD3, ringSignedArea } from "./map-geometry";

// Real sample of the official IBGE mesh (2022, quality "minima"): AP (16), SE (28) and DF (53),
// stored for the API connector tests.
const sample = JSON.parse(
  readFileSync(
    // Tests run from apps/web.
    resolve(process.cwd(), "../../services/api/tests/fixtures/ibge_malhas_uf_2022_minima_sample.json"),
    "utf8",
  ),
) as FeatureCollection<Polygon | MultiPolygon>;

const HEMISPHERE = 2 * Math.PI;

function rewound(feature: Feature<Polygon | MultiPolygon>): Feature<Polygon | MultiPolygon> {
  return { ...feature, geometry: rewindForD3(feature.geometry) };
}

describe("rewindForD3", () => {
  it("the official IBGE rings are read by d3 as the whole globe without rewinding", () => {
    // Documents the bug the rewind prevents (RFC 7946 orientation).
    expect(sample.features.some((f) => geoArea(f) > HEMISPHERE)).toBe(true);
  });

  it("makes every UF of the official sample a small area inside Brazil", () => {
    for (const feature of sample.features.map(rewound)) {
      expect(geoArea(feature)).toBeLessThan(0.01);
      const [[west, south], [east, north]] = geoBounds(feature);
      expect(west).toBeGreaterThan(-75);
      expect(east).toBeLessThan(-30);
      expect(south).toBeGreaterThan(-35);
      expect(north).toBeLessThan(6);
    }
  });

  it("is idempotent and keeps the coordinates", () => {
    const once = sample.features.map(rewound);
    const twice = once.map(rewound);
    expect(twice).toEqual(once);
    const ring = (sample.features[1].geometry as Polygon).coordinates[0];
    const out = (once[1].geometry as Polygon).coordinates[0];
    expect(out.toSorted()).toEqual(ring.toSorted());
  });

  it("exterior rings clockwise, holes counter-clockwise", () => {
    const square = (size: number) => [
      [0, 0],
      [size, 0],
      [size, size],
      [0, size],
      [0, 0],
    ];
    const ccwOuter = square(4);
    const cwHole = square(1).toReversed();
    expect(ringSignedArea(ccwOuter)).toBeGreaterThan(0);
    const result = rewindForD3({ type: "Polygon", coordinates: [ccwOuter, cwHole] });
    expect(ringSignedArea(result.coordinates[0])).toBeLessThan(0);
    expect(ringSignedArea(result.coordinates[1])).toBeGreaterThan(0);
    expect(geoArea({ type: "Polygon", coordinates: result.coordinates })).toBeLessThan(0.01);
  });
});
