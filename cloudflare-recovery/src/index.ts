const SOURCE_RELEASE = "1ce7c35975a4011fa844e8b39ccbc950c8c0f398";

const SECURITY_HEADERS = {
  "Content-Security-Policy":
    "default-src 'self'; base-uri 'self'; object-src 'none'; frame-ancestors 'none'; form-action 'self'; img-src 'self' data:; font-src 'self' data: https://fonts.gstatic.com; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; connect-src 'self'; worker-src 'self' blob:; media-src 'self'; frame-src 'none'; upgrade-insecure-requests",
  "Permissions-Policy":
    "accelerometer=(), autoplay=(), camera=(), geolocation=(), gyroscope=(), magnetometer=(), microphone=(), payment=(), usb=()",
  "Referrer-Policy": "strict-origin-when-cross-origin",
  "Strict-Transport-Security": "max-age=31536000",
  "X-Content-Type-Options": "nosniff",
  "X-Frame-Options": "DENY",
  "X-Robots-Tag": "noindex, nofollow, noarchive"
} as const;

function addSecurityHeaders(response: Response): Response {
  const headers = new Headers(response.headers);
  for (const [name, value] of Object.entries(SECURITY_HEADERS)) {
    headers.set(name, value);
  }
  return new Response(response.body, {
    status: response.status,
    statusText: response.statusText,
    headers
  });
}

function isDynamicPath(pathname: string): boolean {
  return (
    pathname === "/health" ||
    pathname === "/api" ||
    pathname.startsWith("/api/") ||
    pathname === "/auth" ||
    pathname.startsWith("/auth/") ||
    pathname.startsWith("/ws")
  );
}

function recoveryHoldResponse(): Response {
  const response = Response.json(
    {
      status: "hold",
      service: "lumencore-static-recovery",
      public_surface: "static_only",
      dynamic_gateway: "unavailable",
      operator_access: "unavailable",
      reason: "origin_backend_not_migrated",
      source_release: SOURCE_RELEASE
    },
    {
      status: 503,
      headers: {
        "Cache-Control": "no-store",
        "Retry-After": "300"
      }
    }
  );
  return addSecurityHeaders(response);
}

function methodNotAllowedResponse(): Response {
  const response = Response.json(
    { status: "error", error: "method_not_allowed" },
    {
      status: 405,
      headers: {
        Allow: "GET, HEAD",
        "Cache-Control": "no-store"
      }
    }
  );
  return addSecurityHeaders(response);
}

function mappedAssetPath(pathname: string): string | null {
  if (pathname === "/") return "/operator_home.html";
  if (pathname === "/evidence/") return "/evidence/index_bounded.html";
  if (pathname === "/build_week/prooflock_console/") {
    return "/build_week/prooflock_console/index.html";
  }
  return null;
}

function assetRequest(request: Request, pathname: string): Request {
  const url = new URL(request.url);
  url.pathname = pathname;
  return new Request(url, request);
}

export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    const url = new URL(request.url);

    if (isDynamicPath(url.pathname)) {
      return recoveryHoldResponse();
    }
    if (request.method !== "GET" && request.method !== "HEAD") {
      return methodNotAllowedResponse();
    }

    try {
      const mappedPath = mappedAssetPath(url.pathname);
      const response = await env.ASSETS.fetch(
        mappedPath === null ? request : assetRequest(request, mappedPath)
      );
      return addSecurityHeaders(response);
    } catch (error) {
      console.error(
        JSON.stringify({
          message: "static recovery request failed",
          error: error instanceof Error ? error.message : String(error),
          path: url.pathname
        })
      );
      return addSecurityHeaders(
        Response.json(
          { status: "error", error: "internal_server_error" },
          { status: 500, headers: { "Cache-Control": "no-store" } }
        )
      );
    }
  }
} satisfies ExportedHandler<Env>;
