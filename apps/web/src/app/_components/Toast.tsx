// =============================================================================
// SINDESTIVA-PE · ToastProvider — container de feedback efêmero
//
// Container fixo top-right (`z-200`, Tailwind), máximo de 3 toasts visíveis
// (FIFO descarta o mais antigo ao chegar o 4º), gap de 8 px entre eles.
// Auto-hide em 4s; fechamento manual via botão ✕.
//
// Acessibilidade (E33):
//   - Container: `aria-live="polite"`, `aria-atomic="false"`.
//   - Cada toast: `role="alert"` (error) ou `role="status"` (success).
//
// Cliente: este componente é client-side (escuta eventos no `window`).
// Em `app/layout.tsx` é montado dentro do `<body>` sem `dynamic(..., { ssr: false })`
// porque o evento nunca dispara no SSR — a montagem client-only é
// garantida pelo `"use client"` no topo.
// =============================================================================

"use client";

import {
  useCallback,
  useEffect,
  useRef,
  useState,
  type ReactNode,
} from "react";
import {
  TOAST_EVENT,
  type ToastEventDetail,
  type ToastKind,
} from "@/lib/toast";

/** Máximo de toasts visíveis simultaneamente (E32). */
const MAX_VISIBLE = 3;
/** Gap vertical entre toasts em pixels (E32). */
const GAP_PX = 8;
/** Auto-hide em ms. */
const AUTO_HIDE_MS = 4_000;

interface ToastItem {
  /** ID único gerado no provider (estável para `key`). */
  id: number;
  kind: ToastKind;
  message: string;
}

const KIND_CLASS: Record<ToastKind, string> = {
  error: "bg-[#e04a4a]/20 border-[#e04a4a] text-[#e04a4a]",
  success: "bg-[#5dbb7d]/20 border-[#5dbb7d] text-[#5dbb7d]",
};

const KIND_ROLE: Record<ToastKind, "alert" | "status"> = {
  error: "alert",
  success: "status",
};

function ToastCard({
  item,
  onClose,
}: {
  item: ToastItem;
  onClose: (id: number) => void;
}): ReactNode {
  // Auto-hide independente por toast.
  useEffect(() => {
    const t = setTimeout(() => onClose(item.id), AUTO_HIDE_MS);
    return () => clearTimeout(t);
  }, [item.id, onClose]);

  return (
    <div
      role={KIND_ROLE[item.kind]}
      className={`flex items-start gap-2 rounded-md border px-3 py-2 text-[12px] shadow-lg backdrop-blur-sm ${KIND_CLASS[item.kind]}`}
      style={{ minWidth: 240, maxWidth: 360 }}
    >
      <span aria-hidden className="mt-0.5 text-[14px] font-bold">
        {item.kind === "error" ? "⚠" : "✓"}
      </span>
      <span className="flex-1 break-words text-[#e8eef4]">{item.message}</span>
      <button
        type="button"
        aria-label="Fechar notificação"
        onClick={() => onClose(item.id)}
        className="ml-1 -mr-1 rounded px-1 text-[14px] leading-none text-[#94a8bd] hover:bg-[#1e3a52] hover:text-[#e8eef4]"
      >
        ✕
      </button>
    </div>
  );
}

export function ToastProvider({ children }: { children: ReactNode }): ReactNode {
  const [items, setItems] = useState<ToastItem[]>([]);
  const nextId = useRef(0);

  const remove = useCallback((id: number) => {
    setItems((prev) => prev.filter((it) => it.id !== id));
  }, []);

  useEffect(() => {
    function onToast(ev: Event) {
      const detail = (ev as CustomEvent<ToastEventDetail>).detail;
      if (!detail || !detail.message) return;
      nextId.current += 1;
      const id = nextId.current;
      setItems((prev) => {
        const next = [...prev, { id, kind: detail.kind, message: detail.message }];
        // FIFO: descarta o mais antigo ao ultrapassar MAX_VISIBLE.
        return next.length > MAX_VISIBLE ? next.slice(next.length - MAX_VISIBLE) : next;
      });
    }
    window.addEventListener(TOAST_EVENT, onToast);
    return () => window.removeEventListener(TOAST_EVENT, onToast);
  }, []);

  return (
    <>
      {children}
      <div
        aria-live="polite"
        aria-atomic="false"
        className="pointer-events-none fixed top-4 right-4 z-200 flex flex-col"
        style={{ gap: `${GAP_PX}px` }}
      >
        {items.map((it) => (
          <div key={it.id} className="pointer-events-auto">
            <ToastCard item={it} onClose={remove} />
          </div>
        ))}
      </div>
    </>
  );
}
