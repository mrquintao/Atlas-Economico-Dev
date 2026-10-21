import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";

import { StateDashboard } from "@/features/states/StateDashboard";
import { findState, STATES } from "@/lib/states";

/**
 * The 27 UFs are prerendered. Unknown UFs (404) and lowercase acronyms (redirect) are handled in
 * src/proxy.ts, before streaming; notFound() here is only a safety net.
 */
export function generateStaticParams() {
  return STATES.map((state) => ({ uf: state.acronym }));
}

export async function generateMetadata({ params }: PageProps<"/estados/[uf]">): Promise<Metadata> {
  const state = findState((await params).uf);
  return state
    ? {
        title: `${state.name} (${state.acronym}) — Atlas Econômico Brasileiro`,
        description: `Indicadores fiscais de ${state.name} a partir dos relatórios entregues ao SICONFI, com fonte e metodologia.`,
      }
    : { title: "UF não encontrada — Atlas Econômico Brasileiro" };
}

export default async function StatePage({ params }: PageProps<"/estados/[uf]">) {
  const { uf } = await params;
  const state = findState(uf);
  if (!state) notFound();

  return (
    <div className="flex flex-col gap-8">
      <div className="flex max-w-3xl flex-col gap-3">
        <p className="text-sm">
          <Link href="/estados" className="text-muted-foreground underline underline-offset-2 hover:text-foreground">
            Estados
          </Link>
        </p>
        <h1 className="text-3xl font-semibold tracking-tight sm:text-4xl">
          {state.name} ({state.acronym})
        </h1>
        <p className="text-muted-foreground">
          Indicadores fiscais do estado calculados a partir dos relatórios da Lei de
          Responsabilidade Fiscal (RREO e RGF) que o governo estadual entrega ao Tesouro Nacional
          pelo SICONFI. Cada valor aparece como publicado, com período de referência, fonte e
          metodologia. Indicadores sem dados são indicados como tal e nunca estimados.
        </p>
      </div>
      <StateDashboard uf={state.acronym} name={state.name} />
    </div>
  );
}
