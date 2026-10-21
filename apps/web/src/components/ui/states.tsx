export function LoadingState({ label = "Carregando dados oficiais…" }: { label?: string }) {
  return (
    <div role="status" aria-live="polite" className="flex h-[360px] items-center justify-center gap-3 text-sm text-muted-foreground">
      <span className="size-4 animate-spin rounded-full border-2 border-muted-foreground border-t-transparent" aria-hidden />
      {label}
    </div>
  );
}

export function ErrorState({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div role="alert" className="flex h-[360px] flex-col items-center justify-center gap-3 px-6 text-center">
      <p className="font-medium text-foreground">Não foi possível carregar os dados.</p>
      <p className="max-w-md text-sm text-muted-foreground">{message}</p>
      {onRetry && (
        <button
          type="button"
          onClick={onRetry}
          className="rounded-md border border-border px-3 py-1.5 text-sm font-medium hover:bg-muted focus-visible:outline-2 focus-visible:outline-ring"
        >
          Tentar novamente
        </button>
      )}
    </div>
  );
}

export function EmptyState({ message }: { message: string }) {
  return (
    <div className="flex h-[360px] items-center justify-center px-6 text-center text-sm text-muted-foreground">
      {message}
    </div>
  );
}
