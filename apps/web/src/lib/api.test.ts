import { afterEach, describe, expect, it, vi } from "vitest";

import { ApiError, fetchObservations, observationsUrl } from "./api";

afterEach(() => vi.unstubAllGlobals());

describe("api client", () => {
  it("builds the internal observations URL with only the given filters", () => {
    expect(observationsUrl("SELIC_TARGET", { start: "2015-01-01", end: null }, "monthly")).toBe(
      "http://localhost:8000/api/v1/indicators/SELIC_TARGET/observations?frequency=monthly&start_date=2015-01-01",
    );
  });

  it("surfaces the API error message", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(JSON.stringify({ error: { code: "invalid_range", message: "Intervalo inválido." } }), {
          status: 422,
        }),
      ),
    );
    await expect(fetchObservations("SELIC_TARGET", { start: null, end: null }, "daily")).rejects.toMatchObject({
      code: "invalid_range",
      status: 422,
      message: "Intervalo inválido.",
    });
  });

  it("reports network failures as a clear error", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("Failed to fetch")));
    const promise = fetchObservations("SELIC_TARGET", { start: null, end: null }, "daily");
    await expect(promise).rejects.toBeInstanceOf(ApiError);
    await expect(promise).rejects.toMatchObject({ code: "network_error" });
  });
});
