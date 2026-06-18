/** Next.js middleware — server-side auth guard.
 *  Runs before any page HTML is sent, preventing dashboard flash on unauthenticated visits.
 */

import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

const PUBLIC_PATHS = ["/login", "/_next", "/favicon", "/api"];

/** Add no-cache + anti-prerender headers to prevent browser from serving stale HTML. */
function protectedResponse(response: NextResponse): NextResponse {
  // Prevent browser disk cache
  response.headers.set("Cache-Control", "no-store, no-cache, must-revalidate, proxy-revalidate");
  response.headers.set("Pragma", "no-cache");
  response.headers.set("Expires", "0");
  // Prevent Chrome speculative prerendering
  response.headers.set("X-Robots-Tag", "noindex");
  return response;
}

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;

  // Allow public paths through
  if (PUBLIC_PATHS.some((p) => pathname.startsWith(p))) {
    return NextResponse.next();
  }

  // Check for auth token in cookie (set by login page alongside localStorage)
  const token = request.cookies.get("access_token")?.value;

  if (!token) {
    // Also check if this is a prefetch/prerender request — block it entirely
    const purpose = request.headers.get("Purpose") || request.headers.get("Sec-Purpose") || "";
    if (purpose.toLowerCase().includes("prefetch") || purpose.toLowerCase().includes("prerender")) {
      return new NextResponse(null, { status: 204 });
    }

    const loginUrl = new URL("/login", request.url);
    loginUrl.searchParams.set("redirect", pathname);
    return NextResponse.redirect(loginUrl);
  }

  // Authenticated — serve with no-cache headers to prevent stale HTML flash
  return protectedResponse(NextResponse.next());
}

export const config = {
  matcher: [
    /*
     * Match all request paths except:
     * - _next/static (static files)
     * - _next/image (image optimization)
     * - favicon.ico, sitemap.xml, robots.txt
     */
    "/((?!_next/static|_next/image|favicon.ico|sitemap.xml|robots.txt).*)",
  ],
};
