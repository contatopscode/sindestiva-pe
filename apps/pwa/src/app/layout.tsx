import type { Metadata, Viewport } from "next";
import type { ReactNode } from "react";
import "./globals.css";

export const metadata: Metadata = {
  title: "Lousa Digital · TPA",
  description: "App do Trabalhador Portuário Avulso — SINDESTIVA-PE",
  // P0.5: Next 15 gera /manifest.webmanifest via src/app/manifest.ts.
  // vercel.json já tem headers corretos pra esse path.
  manifest: "/manifest.webmanifest",
  applicationName: "TPA SINDESTIVA",
  appleWebApp: {
    capable: true,
    statusBarStyle: "black-translucent",
    title: "Lousa TPA",
  },
  icons: {
    icon: [
      { url: "/icon-192.png", sizes: "192x192", type: "image/png" },
      { url: "/icon-512.png", sizes: "512x512", type: "image/png" },
    ],
    apple: [
      { url: "/apple-touch-icon.png", sizes: "180x180", type: "image/png" },
    ],
  },
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  maximumScale: 1,
  userScalable: false,
  themeColor: "#0a1929",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="pt-BR">
      <body>{children}</body>
    </html>
  );
}
