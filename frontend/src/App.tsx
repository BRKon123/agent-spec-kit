import { QueryCache, QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ErrorBoundary } from "react-error-boundary";
import { Link, NavLink, Outlet, Route, Routes, BrowserRouter } from "react-router-dom";
import { Toaster, toast } from "sonner";
import { TooltipProvider } from "@/components/ui/tooltip";
import { ApiError } from "@/api/http";
import { Button } from "@/components/ui/button";
import { RunsListPage } from "@/pages/RunsListPage";
import { RunDetailPage } from "@/pages/RunDetailPage";
import { ComparePage } from "@/pages/ComparePage";
import { NotFoundPage } from "@/pages/NotFoundPage";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: (failureCount, error) => {
        if (error instanceof ApiError && error.status >= 400 && error.status < 500) {
          return false;
        }
        return failureCount < 2;
      },
      staleTime: 30_000,
      refetchOnWindowFocus: false,
    },
  },
  queryCache: new QueryCache({
    onError: (error) => {
      if (error instanceof ApiError) {
        // 404 is handled per-page (we navigate to NotFoundPage); skip toast.
        if (error.status === 404) return;
        toast.error(error.problem.title, {
          description: error.problem.detail ?? undefined,
        });
        return;
      }
      toast.error("Unexpected error", { description: String(error) });
    },
  }),
});

function FallbackUI({
  error,
  resetErrorBoundary,
}: {
  error: Error;
  resetErrorBoundary: () => void;
}) {
  return (
    <div className="mx-auto max-w-2xl py-16 px-6">
      <h1 className="text-xl font-semibold mb-2">Something went wrong</h1>
      <p className="text-sm text-slate-600 mb-3">
        The interface hit an unexpected error and stopped rendering. Reloading will reset
        the view; if it persists, please copy the trace below.
      </p>
      <details className="rounded-md border border-slate-200 bg-slate-50 p-3 text-xs">
        <summary className="cursor-pointer text-slate-700">Error details</summary>
        <pre className="whitespace-pre-wrap break-words mt-2">{String(error.stack ?? error)}</pre>
      </details>
      <div className="mt-4 flex gap-2">
        <Button onClick={resetErrorBoundary} variant="outline">
          Try again
        </Button>
        <Button onClick={() => window.location.reload()}>Reload</Button>
      </div>
    </div>
  );
}

function AppShell() {
  return (
    <div className="min-h-dvh bg-slate-50">
      <header className="sticky top-0 z-30 border-b border-slate-200 bg-white">
        <div className="flex items-center gap-6 px-4 py-2">
          <Link to="/" className="font-semibold tracking-tight">
            agent-spec-kit
          </Link>
          <nav className="flex items-center gap-1 text-sm">
            <NavLink
              to="/"
              end
              className={({ isActive }) =>
                "px-2.5 py-1 rounded-md " +
                (isActive ? "bg-slate-900 text-white" : "text-slate-600 hover:bg-slate-100")
              }
            >
              Runs
            </NavLink>
            <NavLink
              to="/compare"
              className={({ isActive }) =>
                "px-2.5 py-1 rounded-md " +
                (isActive ? "bg-slate-900 text-white" : "text-slate-600 hover:bg-slate-100")
              }
            >
              Compare
            </NavLink>
          </nav>
        </div>
      </header>
      <main className="px-4 py-4">
        <ErrorBoundary FallbackComponent={FallbackUI}>
          <Outlet />
        </ErrorBoundary>
      </main>
    </div>
  );
}

export function App() {
  return (
    <ErrorBoundary FallbackComponent={FallbackUI}>
      <QueryClientProvider client={queryClient}>
        <TooltipProvider delayDuration={150}>
          <BrowserRouter>
            <Routes>
              <Route element={<AppShell />}>
                <Route index element={<RunsListPage />} />
                <Route path="runs/:runId" element={<RunDetailPage />} />
                <Route path="compare" element={<ComparePage />} />
                <Route path="*" element={<NotFoundPage />} />
              </Route>
            </Routes>
          </BrowserRouter>
          <Toaster position="top-right" richColors closeButton />
        </TooltipProvider>
      </QueryClientProvider>
    </ErrorBoundary>
  );
}
