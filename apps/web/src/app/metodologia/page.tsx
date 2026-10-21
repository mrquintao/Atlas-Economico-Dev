import type { Metadata } from "next";

import { MethodologyCatalog } from "@/features/catalog/MethodologyCatalog";
import { PageHeader } from "@/components/layout/PageHeader";

export const metadata: Metadata = {
  title: "Metodologia — Atlas Econômico Brasileiro",
  description:
    "Metadados de cada indicador do Atlas: fonte e série oficial, unidade, frequência, metodologia, período armazenado e última coleta.",
};

export default function MethodologyPage() {
  return (
    <div className="flex flex-col gap-8">
      <PageHeader eyebrow="Transparência" title="Metodologia">
        <p>
          Catálogo dos indicadores exibidos no Atlas. Os metadados abaixo são servidos pela API do
          Atlas, a mesma que alimenta os gráficos, e trazem a fonte e a série oficial, a unidade, a
          frequência, a metodologia, o período armazenado e a data da última coleta.
        </p>
      </PageHeader>
      <MethodologyCatalog />
    </div>
  );
}
