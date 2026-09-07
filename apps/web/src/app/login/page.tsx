"use client";

import { Suspense, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";

export default function LoginPage() {
  return (
    <Suspense fallback={<div className="login-shell" />}>
      <LoginInner />
    </Suspense>
  );
}

function LoginInner() {
  const router = useRouter();
  const search = useSearchParams();
  const next = search.get("next") || "/centro-comando";

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError(null);

    const r = await fetch("/api/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password }),
      credentials: "include",
    });

    if (!r.ok) {
      const data = await r.json().catch(() => ({ error: "Falha de rede" }));
      setError(data.error || `Erro ${r.status}`);
      setLoading(false);
      return;
    }

    router.push(next);
    router.refresh();
  }

  return (
    <main className="login-shell">
      <div className="login-card">
        <div className="brand">
          <span className="brand-mark">⚓</span>
          <h1>Lousa Digital</h1>
          <p className="brand-sub">SINDESTIVA-PE · Centro de Comando</p>
        </div>

        <form onSubmit={handleSubmit} className="login-form" autoComplete="on">
          <label className="field">
            <span>E-mail</span>
            <input
              type="email"
              name="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="paulo@pscode.ia.br"
              required
              disabled={loading}
              autoComplete="username"
            />
          </label>

          <label className="field">
            <span>Senha</span>
            <input
              type="password"
              name="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••"
              required
              disabled={loading}
              autoComplete="current-password"
            />
          </label>

          {error && (
            <div className="login-error" role="alert">
              ⚠ {error}
            </div>
          )}

          <button type="submit" disabled={loading} className="login-cta">
            {loading ? "Autenticando…" : "Entrar"}
          </button>

          <p className="login-hint">
            Demo: <code>paulo@pscode.ia.br</code> ·{" "}
            <code>manoel@sindestiva-pe.com.br</code> ·{" "}
            <code>josias@sindestiva-pe.com.br</code>
            <br />
            Senha: <code>sindestiva-dev-2026</code>
          </p>
        </form>
      </div>

      <style>{`
        .login-shell {
          min-height: 100vh;
          display: flex;
          align-items: center;
          justify-content: center;
          background: linear-gradient(180deg, #0a1429 0%, #142239 60%, #1a2942 100%);
          font-family: system-ui, sans-serif;
          color: #e8eef4;
          padding: 16px;
        }
        .login-card {
          width: 100%;
          max-width: 420px;
          background: rgba(8, 15, 30, 0.85);
          border: 1px solid #1d2d4a;
          border-radius: 16px;
          padding: 36px 32px;
          box-shadow: 0 18px 48px rgba(0, 0, 0, 0.55);
          backdrop-filter: blur(6px);
        }
        .brand { text-align: center; margin-bottom: 24px; }
        .brand-mark { font-size: 40px; }
        .brand h1 { font-size: 22px; margin: 6px 0 2px; letter-spacing: 0.4px; }
        .brand-sub { color: #94a8bd; font-size: 12px; text-transform: uppercase; letter-spacing: 1px; }
        .login-form { display: flex; flex-direction: column; gap: 16px; }
        .field { display: flex; flex-direction: column; gap: 6px; }
        .field > span { font-size: 12px; color: #94a8bd; text-transform: uppercase; letter-spacing: 0.6px; }
        .field input {
          background: #0d1729;
          border: 1px solid #2a3a55;
          color: #e8eef4;
          padding: 12px 14px;
          border-radius: 8px;
          font-size: 14px;
          outline: none;
          transition: border 0.15s;
        }
        .field input:focus { border-color: #6da3ff; }
        .field input:disabled { opacity: 0.6; }
        .login-error {
          background: rgba(220, 80, 80, 0.12);
          border: 1px solid #dc5050;
          color: #ffb9b9;
          padding: 10px 14px;
          border-radius: 8px;
          font-size: 13px;
        }
        .login-cta {
          background: linear-gradient(180deg, #2563eb 0%, #1d4ed8 100%);
          color: white;
          border: none;
          padding: 14px;
          border-radius: 8px;
          font-weight: 600;
          font-size: 14px;
          cursor: pointer;
          transition: filter 0.15s, transform 0.15s;
          margin-top: 4px;
        }
        .login-cta:hover:not(:disabled) { filter: brightness(1.1); }
        .login-cta:disabled { opacity: 0.6; cursor: wait; }
        .login-hint {
          margin-top: 16px;
          color: #7b8ba5;
          font-size: 11px;
          line-height: 1.7;
          text-align: center;
        }
        .login-hint code {
          background: #1a2942;
          padding: 1px 5px;
          border-radius: 3px;
          font-size: 10px;
        }
      `}</style>
    </main>
  );
}
