import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { SiteNav } from "./SiteNav";

const pathname = vi.hoisted(() => ({ current: "/" }));
vi.mock("next/navigation", () => ({ usePathname: () => pathname.current }));

describe("SiteNav", () => {
  it("links to every page and marks only the current one", () => {
    pathname.current = "/metodologia";
    render(<SiteNav />);
    const nav = screen.getByRole("navigation", { name: "Principal" });
    expect(nav).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Brasil" })).toHaveAttribute("href", "/");
    expect(screen.getByRole("link", { name: "Brasil" })).not.toHaveAttribute("aria-current");
    expect(screen.getByRole("link", { name: "Metodologia" })).toHaveAttribute("aria-current", "page");
    expect(screen.getByRole("link", { name: "Fontes de dados" })).toHaveAttribute("href", "/fontes");
  });
});
