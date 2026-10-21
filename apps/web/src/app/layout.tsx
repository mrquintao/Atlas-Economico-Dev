import type { Metadata, Viewport } from "next";
import Link from "next/link";
import { SiteNav } from "@/components/layout/SiteNav";

import "@fontsource-variable/ibm-plex-sans/wght.css";
import "./globals.css";

export const metadata: Metadata = {
  title: "Atlas Econômico Brasileiro",
  description:
    "Evolução histórica de indicadores econômicos do Brasil a partir de dados oficiais, com fontes e metodologia.",
};

export const viewport: Viewport = {
  themeColor: "#ffffff",
  colorScheme: "light",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="pt-BR" className="h-full antialiased">
      <body className="flex min-h-full flex-col bg-background text-foreground">
        <a
          href="#conteudo"
          className="sr-only focus:not-sr-only focus:absolute focus:left-4 focus:top-4 focus:z-50 focus:rounded focus:bg-card focus:px-3 focus:py-2"
        >
          Pular para o conteúdo
        </a>
        <header className="border-b border-border bg-card">
          <div className="mx-auto flex max-w-6xl flex-col px-4 sm:flex-row sm:items-center sm:justify-between sm:gap-8 sm:px-6">
            <Link
              href="/"
              className="flex items-center gap-2.5 py-3.5 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring sm:py-0"
            >
              <span aria-hidden className="size-3 shrink-0 bg-accent" />
              <span className="text-[15px] font-semibold tracking-tight">
                Atlas Econômico <span className="font-normal text-muted-foreground">Brasileiro</span>
              </span>
            </Link>
            <SiteNav />
          </div>
        </header>
        <main id="conteudo" className="mx-auto w-full max-w-6xl flex-1 px-4 py-10 sm:px-6 sm:py-12">
          {children}
        </main>
        <footer className="border-t border-border bg-card">
          <div className="mx-auto grid max-w-6xl gap-8 px-4 py-10 text-sm sm:grid-cols-[minmax(0,2fr)_minmax(0,1fr)] sm:px-6">
            <div className="flex max-w-xl flex-col gap-2">
              <p className="font-semibold">Atlas Econômico Brasileiro</p>
              <p className="text-muted-foreground">
                Dados de fontes oficiais, armazenados e servidos pela API do Atlas. Projeto
                apartidário: os gráficos descrevem a evolução dos indicadores e não atribuem causas.
              </p>
            </div>
            <div className="flex flex-col gap-2">
              <p className="font-semibold">Fontes oficiais</p>
              <p className="text-muted-foreground">
                Banco Central do Brasil, IBGE e Tesouro Nacional (SICONFI).{" "}
                <Link href="/fontes" className="text-foreground underline underline-offset-2 hover:text-accent">
                  Ver todas as fontes
                </Link>
              </p>
            </div>
          </div>
        </footer>
      </body>
    </html>
  );
}
