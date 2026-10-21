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
    <nav aria-label="Principal" className="-mx-4 overflow-x-auto px-4 sm:mx-0 sm:px-0">
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
                  // The bottom border sits on the header's border: the current section is underlined.
                  "-mb-px flex h-12 items-center whitespace-nowrap border-b-2 text-sm transition-colors sm:h-14",
                  "focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring",
                  current
                    ? "border-accent font-medium text-foreground"
                    : "border-transparent text-muted-foreground hover:border-border-strong hover:text-foreground",
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
