import type { MultiPolygon, Polygon, Position } from "geojson";

/**
 * The IBGE meshes follow RFC 7946: exterior rings counter-clockwise, holes clockwise. d3-geo
 * reads spherical polygons the other way round (exterior clockwise), so an RFC 7946 ring would
 * be drawn as "the whole globe minus the UF". This rewinds every ring to the d3 convention,
 * whatever the orientation received, without changing any coordinate.
 */

/** Twice the signed planar area of a ring (shoelace): > 0 when counter-clockwise in lon/lat. */
export function ringSignedArea(ring: readonly Position[]): number {
  let sum = 0;
  for (let i = 0, j = ring.length - 1; i < ring.length; j = i++) {
    sum += (ring[j][0] - ring[i][0]) * (ring[j][1] + ring[i][1]);
  }
  return sum;
}

function orient(ring: Position[], clockwise: boolean): Position[] {
  const counterClockwise = ringSignedArea(ring) > 0;
  return counterClockwise === clockwise ? ring.toReversed() : ring;
}

function rewindRings(rings: Position[][]): Position[][] {
  return rings.map((ring, index) => orient(ring, index === 0));
}

export function rewindForD3<G extends Polygon | MultiPolygon>(geometry: G): G {
  if (geometry.type === "Polygon") {
    return { ...geometry, coordinates: rewindRings(geometry.coordinates) };
  }
  return { ...geometry, coordinates: geometry.coordinates.map(rewindRings) };
}
