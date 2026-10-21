import { geoMercator, geoPath } from "d3-geo";
import type { MultiPolygon, Polygon, Position } from "geojson";

import type { BoundaryFeature, StateBoundaries } from "@/types/api";

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

/** A UF projected to SVG: its path, its centroid and its names. */
export interface ProjectedShape {
  acronym: string;
  name: string;
  d: string;
  centroid: [number, number];
}

/**
 * Projects the official boundaries (Mercator, fitted to the box) into SVG paths, sorted by name
 * so the tab order is alphabetical.
 */
export function projectShapes(
  boundaries: StateBoundaries,
  width: number,
  height: number,
  padding = 8,
): ProjectedShape[] {
  const features = boundaries.features.map((f) => ({ ...f, geometry: rewindForD3(f.geometry) }));
  const collection = { type: "FeatureCollection" as const, features };
  const projection = geoMercator().fitExtent(
    [
      [padding, padding],
      [width - padding, height - padding],
    ],
    collection,
  );
  const path = geoPath(projection);
  return features
    .map((feature: BoundaryFeature) => ({
      acronym: feature.properties.acronym,
      name: feature.properties.name,
      d: path(feature) ?? "",
      centroid: path.centroid(feature),
    }))
    .toSorted((a, b) => a.name.localeCompare(b.name, "pt-BR"));
}
