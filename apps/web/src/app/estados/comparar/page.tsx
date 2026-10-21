import type { Metadata } from "next";
import Link from "next/link";

import { StateComparisonPanel } from "@/features/states/StateComparison";
import { StateRankingPanel } from "@/features/states/StateRanking";

export const metadata: Metadata = {
  title: "Comparar UFs — Atlas Econômico Brasileiro",
  description:
    "Ranking e evolução histórica de indicadores fiscais das 27 unidades da federação, a partir de dados oficiais do SICONFI.",
};

export default function CompareStatesPage() {
  return (
    <div className="flex flex-col gap-8">
      <div className="flex max-w-3xl flex-col gap-3">
        <p className="text-sm">
          <Link href="/estados" className="underline-offset-4 hover:underline">
            ← Estados
          </Link>
        </p>
        <h1 className="text-3xl font-semibold tracking-tight sm:text-4xl">Comparar UFs</h1>
        <p className="text-muted-foreground">
          Ranking das UFs num mesmo período e evolução histórica de um indicador em várias UFs,
          com os valores publicados nos relatórios entregues ao Tesouro Nacional (SICONFI).
          Percentuais da receita corrente líquida permitem comparar UFs de tamanhos diferentes;
          valores em reais refletem também o porte de cada UF. A ordem dos valores não indica
          desempenho melhor ou pior.
        </p>
      </div>
      <StateRankingPanel />
      <StateComparisonPanel />
    </div>
  );
}
