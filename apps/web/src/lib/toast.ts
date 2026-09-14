// =============================================================================
// SINDESTIVA-PE · Hook useToast — feedback efêmero para a UI
//
// O hook expõe `showError(msg)` e `showSuccess(msg)`. A comunicação com o
// `ToastProvider` (server-rendered `app/_components/Toast.tsx`) usa um
// `CustomEvent` no `window` — assim o hook funciona em qualquer client
// component sem precisar propagar props/Context manualmente por várias
// camadas.
//
// Fluxo:
//   1. Componente cliente chama `useToast().showError("…")`.
//   2. O hook dispara `window.dispatchEvent(new CustomEvent("sindestiva:toast", { detail }))`.
//   3. `ToastProvider` (registrado em `layout.tsx`) escuta o evento e
//      adiciona o toast à pilha com FIFO e auto-hide 4s.
//
// Esta estratégia preserva a fronteira server/client (ToastProvider é
// client component, layout raiz continua server component).
// =============================================================================

"use client";

import { useCallback, useMemo } from "react";

/** Tipos válidos de toast. */
export type ToastKind = "error" | "success";

/** Detalhe do evento emitido no `window`. */
export interface ToastEventDetail {
  kind: ToastKind;
  message: string;
}

/** Nome do evento `window` usado para emitir toasts. */
export const TOAST_EVENT = "sindestiva:toast";

export interface UseToast {
  showError: (message: string) => void;
  showSuccess: (message: string) => void;
}

export function useToast(): UseToast {
  const showError = useCallback((message: string) => {
    if (typeof window === "undefined") return;
    window.dispatchEvent(
      new CustomEvent<ToastEventDetail>(TOAST_EVENT, {
        detail: { kind: "error", message },
      }),
    );
  }, []);

  const showSuccess = useCallback((message: string) => {
    if (typeof window === "undefined") return;
    window.dispatchEvent(
      new CustomEvent<ToastEventDetail>(TOAST_EVENT, {
        detail: { kind: "success", message },
      }),
    );
  }, []);

  return useMemo(() => ({ showError, showSuccess }), [showError, showSuccess]);
}
