import Link from "next/link";

import { IndicatorMetadata } from "@/features/catalog/IndicatorMetadata";
import type { ObservationsResponse } from "@/types/api";

export function MethodologyPanel({ response }: { response: ObservationsResponse }) {
  const { indicator, aggregation } = response;
  return (
    <details className="group rounded-lg border border-border bg-muted/40 p-4 text-sm">
      <summary className="cursor-pointer font-medium focus-visible:outline-2 focus-visible:outline-ring">
        Sobre o indicador e a metodologia
      </summary>
      <div className="mt-4 flex flex-col gap-4">
        <IndicatorMetadata indicator={indicator} display={aggregation.description} />
        <Link
          href={`/metodologia#${encodeURIComponent(indicator.code)}`}
          className="self-start underline underline-offset-2"
        >
          Ver todos os indicadores na página de metodologia
        </Link>
      </div>
    </details>
  );
}
