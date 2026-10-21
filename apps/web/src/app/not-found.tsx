import Link from "next/link";

export default function NotFound() {
  return (
    <div className="flex max-w-2xl flex-col gap-4">
      <h1 className="text-3xl font-semibold tracking-tight">Página não encontrada</h1>
      <p className="text-muted-foreground">
        O endereço não corresponde a nenhuma página do Atlas. As páginas dos estados usam a sigla
        de uma das 27 unidades da federação, como{" "}
        <Link href="/estados/MG" className="underline underline-offset-2">
          /estados/MG
        </Link>
        .
      </p>
      <ul className="flex flex-wrap gap-x-6 gap-y-2">
        <li>
          <Link href="/estados" className="font-medium underline underline-offset-2">
            Ver a lista de estados
          </Link>
        </li>
        <li>
          <Link href="/" className="font-medium underline underline-offset-2">
            Ir para o painel nacional
          </Link>
        </li>
      </ul>
    </div>
  );
}
