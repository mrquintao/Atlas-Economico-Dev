import type { Metadata } from "next";
import Link from "next/link";

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
    <div className="flex flex-col gap-8">
      <div className="flex max-w-3xl flex-col gap-3">
        <h1 className="text-3xl font-semibold tracking-tight sm:text-4xl">Estados</h1>
        <p className="text-muted-foreground">
          Indicadores fiscais dos 26 estados e do Distrito Federal: receita corrente líquida,
          despesa com pessoal do Poder Executivo, investimentos, resultados primário e nominal e
          dívida consolidada, como publicados nos relatórios entregues ao Tesouro Nacional
          (SICONFI). Escolha uma UF no mapa ou na lista abaixo.
        </p>
        <p>
          <Link href="/estados/comparar" className="font-medium underline underline-offset-4">
            Comparar UFs: ranking e evolução histórica
          </Link>
        </p>
      </div>
      <StateMapPanel />
      <h2 className="sr-only">Lista das UFs por região</h2>
      <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
        {regions.map((region) => (
          <section key={region.code} aria-labelledby={`region-${region.code}`}>
            <h2 id={`region-${region.code}`} className="text-lg font-semibold">
              {region.name}
            </h2>
            <ul className="mt-2 flex flex-col gap-1">
              {region.states.map((state) => (
                <li key={state.acronym}>
                  <Link href={statePath(state)} className="underline-offset-4 hover:underline">
                    {state.name} ({state.acronym})
                  </Link>
                </li>
              ))}
            </ul>
          </section>
        ))}
      </div>
    </div>
  );
}
