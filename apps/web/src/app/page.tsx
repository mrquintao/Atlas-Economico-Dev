import { Dashboard } from "@/features/dashboard/Dashboard";

export default function HomePage() {
  return (
    <div className="flex flex-col gap-8">
      <div className="flex max-w-3xl flex-col gap-3">
        <h1 className="text-3xl font-semibold tracking-tight sm:text-4xl">Brasil em Perspectiva</h1>
        <p className="text-muted-foreground">
          Acompanhe a evolução histórica de indicadores econômicos nacionais com dados oficiais. Cada
          série informa fonte, unidade, metodologia e data da última coleta. Valores ausentes
          aparecem como lacunas e nunca são estimados.
        </p>
      </div>
      <Dashboard />
    </div>
  );
}
