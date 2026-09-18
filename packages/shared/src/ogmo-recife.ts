/**
 * FSW-2026-009 · Portal OGMO Recife (embed iframe + fallback).
 * URL canônica com barra final — alinhada ao PRD/SPEC.
 */
export const OGMO_RECIFE_DEFAULT_URL = "http://www.ogmo-recife.org.br/ogmo/" as const;

export const OGMO_RECIFE_IFRAME_SANDBOX =
  "allow-scripts allow-same-origin allow-forms allow-popups allow-top-navigation-by-user-activation" as const;

/** Resolve URL do portal (env opcional no build Next.js). */
export function resolveOgmoRecifeUrl(
  envUrl: string | undefined = process.env.NEXT_PUBLIC_OGMO_RECIFE_URL,
): string {
  const trimmed = envUrl?.trim();
  return trimmed && trimmed.length > 0 ? trimmed : OGMO_RECIFE_DEFAULT_URL;
}

/** Atributos estáveis para smoke tests (iframe src === fallback href). */
export function ogmoRecifeEmbedTargets(url: string = resolveOgmoRecifeUrl()): {
  iframeSrc: string;
  fallbackHref: string;
} {
  return { iframeSrc: url, fallbackHref: url };
}
