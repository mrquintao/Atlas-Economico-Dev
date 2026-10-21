"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { cn } from "@/lib/utils";

const LINKS = [
  { href: "/", label: "Brasil" },
  { href: "/estados", label: "Estados" },
  { href: "/metodologia", label: "Metodologia" },
  { href: "/fontes", label: "Fontes de dados" },
] as const;

export function SiteNav() {
  const pathname = usePathname();
  return (
    <nav aria-label="Principal" className="-mx-4 overflow-x-auto px-4 sm:mx-0 sm:overflow-visible sm:px-0">
      <ul className="flex gap-6">
        {LINKS.map(({ href, label }) => {
          // A section stays current on its sub-pages (/estados/MG is under "Estados").
          const current = pathname === href || (href !== "/" && pathname.startsWith(`${href}/`));
          return (
            <li key={href}>
              <Link
                href={href}
                aria-current={current ? (pathname === href ? "page" : "location") : undefined}
                className={cn(
                  // An inset bar at the bottom underlines the current section; it never overflows
                  // the scrollable nav on small screens.
                  "flex h-12 items-center whitespace-nowrap text-sm transition-[color,box-shadow] sm:h-14",
                  "focus-visible:outline-2 focus-visible:-outline-offset-2 focus-visible:outline-ring",
                  current
                    ? "font-medium text-foreground shadow-[inset_0_-2px_0_var(--accent)]"
                    : "text-muted-foreground hover:text-foreground hover:shadow-[inset_0_-2px_0_var(--border-strong)]",
                )}
              >
                {label}
              </Link>
            </li>
          );
        })}
      </ul>
    </nav>
  );
}
