import { Dashboard } from "@/features/dashboard/Dashboard";
import { PageHeader } from "@/components/layout/PageHeader";

export default function HomePage() {
  return (
    <div className="flex flex-col gap-8">
      <PageHeader eyebrow="Painel nacional" title="Brasil em Perspectiva">
        <p>
          Acompanhe a evolução histórica de indicadores econômicos nacionais com dados oficiais. Cada
          série informa fonte, unidade, metodologia e data da última coleta. Valores ausentes
          aparecem como lacunas e nunca são estimados.
        </p>
      </PageHeader>
      <Dashboard />
    </div>
  );
}
