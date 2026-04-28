import type { ProblemDetail } from "@/lib/types";

export class ApiError extends Error {
  status: number;
  problem: ProblemDetail;
  constructor(problem: ProblemDetail) {
    super(problem.title);
    this.status = problem.status;
    this.problem = problem;
  }
}

export async function fetchJson<T>(
  input: string,
  init?: RequestInit,
): Promise<T> {
  let res: Response;
  try {
    res = await fetch(input, {
      ...init,
      headers: {
        Accept: "application/json",
        ...(init?.headers ?? {}),
      },
    });
  } catch (e) {
    throw new ApiError({
      type: "about:blank",
      title: "Network error",
      status: 0,
      detail: e instanceof Error ? e.message : String(e),
      instance: input,
    });
  }
  if (!res.ok) {
    let problem: ProblemDetail = {
      type: "about:blank",
      title: res.statusText || "Request failed",
      status: res.status,
      detail: null,
      instance: input,
    };
    const ct = res.headers.get("content-type") ?? "";
    if (ct.includes("application/problem+json") || ct.includes("application/json")) {
      try {
        const body = (await res.json()) as Partial<ProblemDetail>;
        problem = {
          type: body.type ?? problem.type,
          title: body.title ?? problem.title,
          status: body.status ?? res.status,
          detail: body.detail ?? null,
          instance: body.instance ?? input,
        };
      } catch {
        // fall through with default problem
      }
    }
    throw new ApiError(problem);
  }
  return (await res.json()) as T;
}
