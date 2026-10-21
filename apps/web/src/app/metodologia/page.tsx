import type { Metadata } from "next";

import { MethodologyCatalog } from "@/features/catalog/MethodologyCatalog";

export const metadata: Metadata = {
  title: "Metodologia — Atlas Econômico Brasileiro",
  description:
    "Metadados de cada indicador do Atlas: fonte e série oficial, unidade, frequência, metodologia, período armazenado e última coleta.",
};

export default function MethodologyPage() {
  return (
    <div className="flex flex-col gap-8">
      <div className="flex max-w-3xl flex-col gap-3">
        <h1 className="text-3xl font-semibold tracking-tight sm:text-4xl">Metodologia</h1>
        <p className="text-muted-foreground">
          Catálogo dos indicadores exibidos no Atlas. Os metadados abaixo são servidos pela API do
          Atlas, a mesma que alimenta os gráficos, e trazem a fonte e a série oficial, a unidade, a
          frequência, a metodologia, o período armazenado e a data da última coleta.
        </p>
      </div>
      <MethodologyCatalog />
    </div>
  );
}
