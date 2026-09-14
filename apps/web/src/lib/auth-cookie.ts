/**
 * Cookie httpOnly `sindestiva_token` — nome e Domain por ambiente (HOM ≠ prod).
 *
 * HOM: não usar Domain=.pscode.ia.br (cookie legado compartilhado com prod).
 * Prod lousa: Domain=.pscode.ia.br para subdomínios web/api.
 */

export const AUTH_COOKIE_NAME =
  process.env.SINDESTIVA_AUTH_COOKIE_NAME?.trim() || "sindestiva_token";

/** Domain do cookie legado que vazava sessão entre HOM e prod. */
export const LEGACY_SHARED_COOKIE_DOMAIN = ".pscode.ia.br";

export const HOM_LOUSA_COOKIE_DOMAIN = ".hom.lousa.pscode.ia.br";

const COOKIE_MAX_AGE_DEFAULT = 8 * 60 * 60;

export function isProductionSecureCookie(): boolean {
  return process.env.NODE_ENV === "production";
}

/**
 * Resolve o atributo Domain do Set-Cookie a partir do Host da request.
 * Host-only (sem Domain) em localhost; HOM usa `.hom.lousa.pscode.ia.br`.
 */
export function resolveAuthCookieDomain(host: string): string | undefined {
  const hostname = host.split(":")[0]?.toLowerCase() ?? "";
  if (!hostname || hostname === "localhost" || hostname.endsWith(".localhost")) {
    return undefined;
  }
  if (hostname.includes(".hom.lousa.pscode.ia.br") || hostname.includes(".hom.")) {
    return HOM_LOUSA_COOKIE_DOMAIN;
  }
  if (
    hostname.endsWith(".lousa.pscode.ia.br") ||
    hostname === "lousa.pscode.ia.br"
  ) {
    return LEGACY_SHARED_COOKIE_DOMAIN;
  }
  if (hostname.endsWith(".pscode.ia.br")) {
    return LEGACY_SHARED_COOKIE_DOMAIN;
  }
  return undefined;
}

function appendSecure(parts: string[]): void {
  if (isProductionSecureCookie()) {
    parts.push("Secure");
  }
}

export function buildAuthSetCookieHeader(
  token: string,
  host: string,
  maxAge = COOKIE_MAX_AGE_DEFAULT,
): string {
  const parts = [
    `${AUTH_COOKIE_NAME}=${token}`,
    "Path=/",
    `Max-Age=${maxAge}`,
    "HttpOnly",
    "SameSite=Lax",
  ];
  appendSecure(parts);
  const domain = resolveAuthCookieDomain(host);
  if (domain) {
    parts.push(`Domain=${domain}`);
  }
  return parts.join("; ");
}

export function buildAuthClearCookieHeader(host: string): string {
  const parts = [
    `${AUTH_COOKIE_NAME}=`,
    "Path=/",
    "Max-Age=0",
    "HttpOnly",
    "SameSite=Lax",
  ];
  appendSecure(parts);
  const domain = resolveAuthCookieDomain(host);
  if (domain) {
    parts.push(`Domain=${domain}`);
  }
  return parts.join("; ");
}

/** Expira cookie antigo com Domain=.pscode.ia.br (nome padrão legado). */
export function buildLegacySharedClearCookieHeader(
  cookieName = "sindestiva_token",
): string {
  const parts = [
    `${cookieName}=`,
    "Path=/",
    "Max-Age=0",
    "HttpOnly",
    "SameSite=Lax",
    `Domain=${LEGACY_SHARED_COOKIE_DOMAIN}`,
  ];
  appendSecure(parts);
  return parts.join("; ");
}

/** Headers Set-Cookie para logout: limpa cookie do host + legado compartilhado. */
export function buildLogoutSetCookieHeaders(host: string): string[] {
  const headers = [buildAuthClearCookieHeader(host)];
  if (resolveAuthCookieDomain(host) !== LEGACY_SHARED_COOKIE_DOMAIN) {
    headers.push(buildLegacySharedClearCookieHeader("sindestiva_token"));
    if (AUTH_COOKIE_NAME !== "sindestiva_token") {
      headers.push(buildLegacySharedClearCookieHeader(AUTH_COOKIE_NAME));
    }
  }
  return headers;
}

/** Login HOM: seta cookie correto + expira legado `.pscode.ia.br`. */
export function buildLoginSetCookieHeaders(
  token: string,
  host: string,
  maxAge = COOKIE_MAX_AGE_DEFAULT,
): string[] {
  const headers = [buildAuthSetCookieHeader(token, host, maxAge)];
  if (resolveAuthCookieDomain(host) !== LEGACY_SHARED_COOKIE_DOMAIN) {
    headers.push(buildLegacySharedClearCookieHeader("sindestiva_token"));
    if (AUTH_COOKIE_NAME !== "sindestiva_token") {
      headers.push(buildLegacySharedClearCookieHeader(AUTH_COOKIE_NAME));
    }
  }
  return headers;
}
