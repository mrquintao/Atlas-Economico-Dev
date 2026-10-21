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
    <nav aria-label="Principal">
      <ul className="flex flex-wrap gap-x-5 gap-y-1">
        {LINKS.map(({ href, label }) => {
          // A section stays current on its sub-pages (/estados/MG is under "Estados").
          const current = pathname === href || (href !== "/" && pathname.startsWith(`${href}/`));
          return (
            <li key={href}>
              <Link
                href={href}
                aria-current={current ? (pathname === href ? "page" : "location") : undefined}
                className={cn(
                  "text-sm underline-offset-4 hover:underline focus-visible:outline-2 focus-visible:outline-ring",
                  current ? "font-semibold text-foreground" : "text-muted-foreground",
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
