/**
 * Loading, error and empty states shared by every data component, so they look and behave the
 * same everywhere: a skeleton/spinner on first load, "Atualizando…" while reloading over stale
 * data, and every error offering "Tentar novamente".
 */

export function LoadingState({ label = "Carregando dados oficiais…" }: { label?: string }) {
  return (
    <div role="status" aria-live="polite" className="flex h-[360px] items-center justify-center gap-3 text-sm text-muted-foreground">
      <Spinner />
      {label}
    </div>
  );
}

function Spinner() {
  return (
    <span
      className="size-4 shrink-0 animate-spin rounded-full border-2 border-muted-foreground border-t-transparent"
      aria-hidden
    />
  );
}

/** Shown while new data loads and the previous data stays on screen. */
export function RefreshingIndicator({ label = "Atualizando…" }: { label?: string }) {
  return (
    <span role="status" aria-live="polite" className="inline-flex items-center gap-2 text-xs text-muted-foreground">
      <Spinner />
      {label}
    </span>
  );
}

export function RetryButton({ onRetry }: { onRetry: () => void }) {
  return (
    <button
      type="button"
      onClick={onRetry}
      className="rounded-md border border-border px-2.5 py-1 text-sm font-medium text-foreground hover:bg-muted focus-visible:outline-2 focus-visible:outline-ring"
    >
      Tentar novamente
    </button>
  );
}

/** Compact error with retry, for places where content (or stale data) stays visible. */
export function InlineError({ message, onRetry }: { message: string; onRetry: () => void }) {
  return (
    <div role="alert" className="flex flex-wrap items-center gap-3 text-sm text-danger">
      <span>{message}</span>
      <RetryButton onRetry={onRetry} />
    </div>
  );
}

/** Full-size error replacing a chart that has nothing to show yet. */
export function ErrorState({ message, onRetry }: { message: string; onRetry: () => void }) {
  return (
    <div role="alert" className="flex h-[360px] flex-col items-center justify-center gap-3 px-6 text-center">
      <p className="font-medium text-foreground">Não foi possível carregar os dados.</p>
      <p className="max-w-md text-sm text-muted-foreground">{message}</p>
      <RetryButton onRetry={onRetry} />
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
