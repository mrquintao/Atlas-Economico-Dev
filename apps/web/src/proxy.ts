import { NextResponse, type NextRequest } from "next/server";

import { findState, statePath } from "@/lib/states";

/**
 * State pages are streamed, so a notFound() or redirect() in the page would only take effect
 * after a 200 status. Checking the UF here, before rendering, gives real status codes:
 * a lowercase acronym redirects (308) to the canonical page and anything that is not one of the
 * 27 UFs gets the 404 page with a 404 status.
 */
export function proxy(request: NextRequest) {
  const segment = request.nextUrl.pathname.split("/")[2] ?? "";
  const state = findState(segment);
  if (!state) {
    // No route matches this path: Next.js renders app/not-found.tsx with a 404 status.
    return NextResponse.rewrite(new URL("/estados/uf-nao-encontrada/404", request.url));
  }
  if (segment !== state.acronym) {
    const url = request.nextUrl.clone();
    url.pathname = statePath(state);
    return NextResponse.redirect(url, 308);
  }
  return NextResponse.next();
}

export const config = {
  matcher: "/estados/:uf",
};
