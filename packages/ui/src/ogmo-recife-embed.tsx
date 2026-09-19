"use client";

import {
  OGMO_RECIFE_IFRAME_SANDBOX,
  resolveOgmoRecifeUrl,
} from "@sindestiva/shared";
import React, { useCallback, useEffect, useId, useState, type ReactNode } from "react";

const LOAD_TIMEOUT_MS = 8_000;

export type OgmoRecifeEmbedVariant = "web" | "pwa";

export interface OgmoRecifeEmbedProps {
  variant?: OgmoRecifeEmbedVariant;
  /** Override explícito (tests); default = env + constante shared. */
  portalUrl?: string;
}

type LoadState = "pending" | "loaded" | "blocked";

export function OgmoRecifeEmbed({
  variant = "web",
  portalUrl,
}: OgmoRecifeEmbedProps): ReactNode {
  const url = portalUrl ?? resolveOgmoRecifeUrl();
  const [loadState, setLoadState] = useState<LoadState>("pending");
  const hintId = useId();

  useEffect(() => {
    setLoadState("pending");
    const timer = window.setTimeout(() => {
      setLoadState((prev) => (prev === "pending" ? "blocked" : prev));
    }, LOAD_TIMEOUT_MS);
    return () => window.clearTimeout(timer);
  }, [url]);

  const onIframeLoad = useCallback(() => {
    setLoadState("loaded");
  }, []);

  const onIframeError = useCallback(() => {
    setLoadState("blocked");
  }, []);

  const blocked = loadState === "blocked";
  const isWeb = variant === "web";

  return (
    <div
      className={
        isWeb
          ? "flex min-h-0 flex-1 flex-col gap-3"
          : "flex min-h-0 flex-1 flex-col gap-2"
      }
    >
      <div
        className={
          isWeb
            ? "flex flex-wrap items-center justify-between gap-3 rounded-md border border-[#1e3a52] bg-[#0f2438] px-4 py-3"
            : "flex flex-col gap-2 border-b border-[var(--border-soft)] bg-[var(--bg-raised)] px-4 py-3"
        }
      >
        <div>
          <h1
            className={
              isWeb
                ? "text-lg font-bold text-[#e8eef4]"
                : "text-base font-bold text-[var(--text-primary)]"
            }
          >
            OGMO Recife
          </h1>
          <p
            className={
              isWeb
                ? "text-[12px] text-[#94a8bd]"
                : "text-[11px] text-[var(--text-muted)]"
            }
          >
            Portal oficial do OGMO Recife · se o painel abaixo não carregar, use o botão ao lado.
          </p>
        </div>
        <a
          href={url}
          target="_blank"
          rel="noopener noreferrer"
          className={
            isWeb
              ? "inline-flex shrink-0 items-center justify-center rounded-md border border-[#d4a574] bg-[#d4a574]/10 px-4 py-2 text-[12px] font-semibold uppercase tracking-wide text-[#d4a574] transition-colors hover:bg-[#d4a574]/20"
              : "tpa-btn w-full text-center"
          }
          data-testid="ogmo-recife-fallback"
        >
          Abrir OGMO Recife
        </a>
      </div>

      {blocked && (
        <div
          id={hintId}
          role="status"
          className={
            isWeb
              ? "rounded-md border border-[#e8a33d]/50 bg-[#e8a33d]/10 px-4 py-3 text-[12px] text-[#e8a33d]"
              : "mx-4 rounded border border-[var(--accent-amber)]/50 bg-[var(--accent-amber)]/10 px-3 py-2 text-[11px] text-[var(--accent-amber)]"
          }
        >
          Não foi possível exibir o portal aqui (mixed content ou bloqueio de iframe). Use{" "}
          <strong>Abrir OGMO Recife</strong> para acessar em nova aba.
        </div>
      )}

      <iframe
        src={url}
        title="OGMO Recife"
        className={
          isWeb
            ? "min-h-[70vh] w-full flex-1 border-0 bg-white"
            : "min-h-[50vh] w-full flex-1 border-0 bg-white"
        }
        sandbox={OGMO_RECIFE_IFRAME_SANDBOX}
        referrerPolicy="no-referrer-when-downgrade"
        onLoad={onIframeLoad}
        onError={onIframeError}
        data-testid="ogmo-recife-iframe"
      />
    </div>
  );
}
