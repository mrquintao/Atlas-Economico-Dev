import type { Metadata } from "next";
import Link from "next/link";

import { PageHeader } from "@/components/layout/PageHeader";
import { StateExplorer } from "@/features/states/StateExplorer";
import { StateMapPanel } from "@/features/states/StateMap";
import { REGION_NAMES, statePath, STATES } from "@/lib/states";

export const metadata: Metadata = {
  title: "Estados — Atlas Econômico Brasileiro",
  description: "Indicadores fiscais das 27 unidades da federação, a partir de dados oficiais do SICONFI.",
};

export default function StatesPage() {
  const regions = Object.entries(REGION_NAMES).map(([code, name]) => ({
    code,
    name,
    states: STATES.filter((s) => s.region === code).toSorted((a, b) => a.name.localeCompare(b.name, "pt-BR")),
  }));
  return (
    <div className="flex flex-col gap-10">
      <div className="flex flex-col gap-5 lg:flex-row lg:items-end lg:justify-between lg:gap-10">
        <PageHeader eyebrow="Atlas estadual" title="Estados">
          <p>
            Indicadores fiscais dos 26 estados e do Distrito Federal: receita corrente líquida,
            despesa com pessoal do Poder Executivo, investimentos, resultados primário e nominal e
            dívida consolidada, como publicados nos relatórios entregues ao Tesouro Nacional
            (SICONFI). Escolha uma UF no mapa ou na lista abaixo.
          </p>
        </PageHeader>
        <Link
          href="/estados/comparar"
          className="inline-flex shrink-0 items-center self-start rounded-md border border-border-strong bg-card px-3.5 py-2 text-sm font-medium hover:border-foreground focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring lg:self-end"
        >
          Comparar UFs: ranking e evolução histórica
        </Link>
      </div>
      <StateExplorer />
      <StateMapPanel />
      <section aria-labelledby="regions" className="flex flex-col gap-4">
        <h2 id="regions" className="text-lg font-semibold">
          Lista das UFs por região
        </h2>
        <div className="grid gap-x-8 gap-y-6 sm:grid-cols-2 lg:grid-cols-5">
          {regions.map((region) => (
            <section key={region.code} aria-labelledby={`region-${region.code}`}>
              <h3
                id={`region-${region.code}`}
                className="border-b border-border pb-2 text-xs font-semibold uppercase tracking-[0.12em] text-muted-foreground"
              >
                {region.name}
              </h3>
              <ul className="mt-2 flex flex-col gap-1 text-sm">
                {region.states.map((state) => (
                  <li key={state.acronym}>
                    <Link href={statePath(state)} className="underline-offset-4 hover:text-accent hover:underline">
                      {state.name} ({state.acronym})
                    </Link>
                  </li>
                ))}
              </ul>
            </section>
          ))}
        </div>
      </section>
    </div>
  );
}
