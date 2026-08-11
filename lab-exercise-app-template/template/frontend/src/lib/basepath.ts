// Runtime router base-path resolution (Addendum A §A1) — CHASSIS.
//
// AdaLab serves apps at `/apps/<app_url>/…` with `stripped_prefix: true`: the reverse proxy
// strips the prefix before forwarding to the container (so the backend sees `/api/…`), but
// the BROWSER's URL still carries `/apps/<app_url>/`. So the frontend can discover its own
// base path at runtime from `window.location.pathname` — no build-time env var, one build
// runs at `/` locally and under any `/apps/<slug>/` prefix on AdaLab.

/** Pure, testable core: derive the base path (always ending in `/`) from a pathname. */
export function resolveBasePath(pathname: string): string {
  const match = pathname.match(/^\/apps\/[^/]+\//);
  return match ? match[0] : "/";
}

/** The app's base path at runtime, e.g. `/` or `/apps/absorbance-lab/`. */
export function getBasePath(): string {
  if (typeof window === "undefined") return "/";
  return resolveBasePath(window.location.pathname);
}

/** Base path without a trailing slash, for React Router's `basename` (undefined at root). */
export function getRouterBasename(): string | undefined {
  const base = getBasePath();
  return base === "/" ? undefined : base.replace(/\/$/, "");
}
