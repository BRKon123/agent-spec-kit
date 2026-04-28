import { Link, useLocation } from "react-router-dom";
import { Button } from "@/components/ui/button";

export function NotFoundPage({
  title = "Page not found",
  detail,
}: {
  title?: string;
  detail?: string;
}) {
  const loc = useLocation();
  return (
    <div className="mx-auto max-w-xl py-16 px-6 text-center">
      <h1 className="text-2xl font-semibold mb-2">{title}</h1>
      <p className="text-sm text-slate-600 mb-1">
        {detail ?? `We couldn't find anything at ${loc.pathname}.`}
      </p>
      <div className="mt-6 flex items-center justify-center gap-2">
        <Button asChild variant="outline">
          <Link to="/">Back to runs</Link>
        </Button>
        <Button asChild>
          <Link to="/compare">Compare experiments</Link>
        </Button>
      </div>
    </div>
  );
}
