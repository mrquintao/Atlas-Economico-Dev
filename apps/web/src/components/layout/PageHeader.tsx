import Link from "next/link";
import type { ReactNode } from "react";

interface Props {
  title: string;
  /** Short label above the title: the section of the site, or a link back to it. */
  eyebrow?: string | { href: string; label: string };
  children?: ReactNode;
}

/** Title block shared by every page: eyebrow, h1 and an introductory paragraph. */
export function PageHeader({ title, eyebrow, children }: Props) {
  return (
    <div className="flex max-w-3xl flex-col gap-3">
      {eyebrow &&
        (typeof eyebrow === "string" ? (
          <p className="text-xs font-semibold uppercase tracking-[0.12em] text-accent">{eyebrow}</p>
        ) : (
          <p className="text-xs font-semibold uppercase tracking-[0.12em]">
            <Link
              href={eyebrow.href}
              className="text-accent underline-offset-4 hover:underline focus-visible:outline-2 focus-visible:outline-ring"
            >
              {eyebrow.label}
            </Link>
          </p>
        ))}
      <h1 className="text-3xl font-semibold tracking-tight text-balance sm:text-[2.5rem] sm:leading-[1.15]">
        {title}
      </h1>
      {children && <div className="flex flex-col gap-3 text-pretty text-muted-foreground sm:text-lg/relaxed">{children}</div>}
    </div>
  );
}
