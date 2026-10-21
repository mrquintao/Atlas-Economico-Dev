import type { Metadata } from "next";
import { notFound } from "next/navigation";

import { StateDashboard } from "@/features/states/StateDashboard";
import { findState, STATES } from "@/lib/states";
import { PageHeader } from "@/components/layout/PageHeader";

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
        description: `Indicadores fiscais — ${state.name} (${state.acronym}): valores dos relatórios entregues ao SICONFI, com fonte e metodologia.`,
      }
    : { title: "Página não encontrada — Atlas Econômico Brasileiro" };
}

export default async function StatePage({ params }: PageProps<"/estados/[uf]">) {
  const { uf } = await params;
  const state = findState(uf);
  if (!state) notFound();

  return (
    <div className="flex flex-col gap-8">
      <PageHeader eyebrow={{ href: "/estados", label: "Estados" }} title={`${state.name} (${state.acronym})`}>
        <p>
          Indicadores fiscais extraídos dos relatórios da Lei de Responsabilidade Fiscal (RREO e
          RGF) que a UF entrega ao Tesouro Nacional pelo SICONFI. Cada valor aparece como
          publicado, com período de referência, fonte e metodologia. Indicadores sem dados
          aparecem como tal e nunca são estimados.
        </p>
      </PageHeader>
      <StateDashboard uf={state.acronym} />
    </div>
  );
}
