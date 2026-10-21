import type { Metadata } from "next";

import { SourcesCatalog } from "@/features/catalog/SourcesCatalog";

export const metadata: Metadata = {
  title: "Fontes de dados — Atlas Econômico Brasileiro",
  description: "Fontes oficiais consultadas pelo Atlas e os indicadores obtidos de cada uma.",
};

export default function SourcesPage() {
  return (
    <div className="flex flex-col gap-8">
      <div className="flex max-w-3xl flex-col gap-3">
        <h1 className="text-3xl font-semibold tracking-tight sm:text-4xl">Fontes de dados</h1>
        <p className="text-muted-foreground">
          O Atlas usa exclusivamente dados de fontes oficiais. Os dados são coletados pelo backend,
          armazenados com o histórico de revisões e servidos pela API do Atlas; o site não consulta
          as fontes diretamente.
        </p>
      </div>
      <SourcesCatalog />
    </div>
  );
}
