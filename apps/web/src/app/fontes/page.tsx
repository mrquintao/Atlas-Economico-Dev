import type { Metadata } from "next";

import { SourcesCatalog } from "@/features/catalog/SourcesCatalog";
import { PageHeader } from "@/components/layout/PageHeader";

export const metadata: Metadata = {
  title: "Fontes de dados — Atlas Econômico Brasileiro",
  description: "Fontes oficiais consultadas pelo Atlas e os indicadores obtidos de cada uma.",
};

export default function SourcesPage() {
  return (
    <div className="flex flex-col gap-8">
      <PageHeader eyebrow="Transparência" title="Fontes de dados">
        <p>
          O Atlas usa exclusivamente dados de fontes oficiais. Os dados são coletados pelo backend,
          armazenados no banco do Atlas (as revisões detectadas na recoleta são registradas) e
          servidos pela API do Atlas; o site não consulta as fontes diretamente.
        </p>
      </PageHeader>
      <SourcesCatalog />
    </div>
  );
}
