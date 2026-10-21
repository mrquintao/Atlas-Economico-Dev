import type { Metadata } from "next";

import { StateComparisonPanel } from "@/features/states/StateComparison";
import { StateRankingPanel } from "@/features/states/StateRanking";
import { PageHeader } from "@/components/layout/PageHeader";

export const metadata: Metadata = {
  title: "Comparar UFs — Atlas Econômico Brasileiro",
  description:
    "Ranking e evolução histórica de indicadores fiscais das 27 unidades da federação, a partir de dados oficiais do SICONFI.",
};

export default function CompareStatesPage() {
  return (
    <div className="flex flex-col gap-8">
      <PageHeader eyebrow={{ href: "/estados", label: "Estados" }} title="Comparar UFs">
        <p>
          Ranking das UFs num mesmo período e evolução histórica de um indicador em várias UFs,
          com os valores publicados nos relatórios entregues ao Tesouro Nacional (SICONFI).
          Percentuais da receita corrente líquida permitem comparar UFs de tamanhos diferentes;
          valores em reais refletem também o porte de cada UF. A ordem dos valores não indica
          desempenho melhor ou pior.
        </p>
      </PageHeader>
      <StateRankingPanel />
      <StateComparisonPanel />
    </div>
  );
}
