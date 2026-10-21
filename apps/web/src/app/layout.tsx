import type { Metadata, Viewport } from "next";
import Link from "next/link";

import "./globals.css";

export const metadata: Metadata = {
  title: "Atlas Econômico Brasileiro",
  description:
    "Evolução histórica de indicadores econômicos do Brasil a partir de dados oficiais, com fontes e metodologia.",
};

export const viewport: Viewport = {
  themeColor: [
    { media: "(prefers-color-scheme: light)", color: "#ffffff" },
    { media: "(prefers-color-scheme: dark)", color: "#0b1120" },
  ],
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="pt-BR" className="h-full antialiased">
      <body className="flex min-h-full flex-col bg-background text-foreground">
        <a
          href="#conteudo"
          className="sr-only focus:not-sr-only focus:absolute focus:left-4 focus:top-4 focus:rounded focus:bg-card focus:px-3 focus:py-2"
        >
          Pular para o conteúdo
        </a>
        <header className="border-b border-border">
          <div className="mx-auto flex max-w-6xl items-center justify-between px-4 py-4 sm:px-6">
            <p className="text-sm font-bold tracking-[0.18em]">ATLAS ECONÔMICO BRASILEIRO</p>
            <nav aria-label="Principal">
              <Link href="/" aria-current="page" className="text-sm font-medium">
                Brasil
              </Link>
            </nav>
          </div>
        </header>
        <main id="conteudo" className="mx-auto w-full max-w-6xl flex-1 px-4 py-8 sm:px-6">
          {children}
        </main>
        <footer className="border-t border-border">
          <div className="mx-auto max-w-6xl px-4 py-6 text-xs text-muted-foreground sm:px-6">
            Dados de fontes oficiais, armazenados e servidos pela API do Atlas. Projeto
            apartidário: os gráficos descrevem a evolução dos indicadores e não atribuem causas.
          </div>
        </footer>
      </body>
    </html>
  );
}
