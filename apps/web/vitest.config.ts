// =============================================================================
// SINDESTIVA-PE · Vitest (apps/web)
// Ambiente `node`: os testes de `lib/` não tocam DOM — `lib/api.ts` já
// guarda `typeof window === "undefined"` antes de usar localStorage.
// =============================================================================

import { fileURLToPath } from "node:url";
import { defineConfig } from "vitest/config";

const r = (p: string) => fileURLToPath(new URL(p, import.meta.url));

export default defineConfig({
  resolve: {
    alias: {
      "@sindestiva/shared": r("../../packages/shared/src/index.ts"),
      "@sindestiva/ui": r("../../packages/ui/src/index.ts"),
      "@": r("./src"),
    },
  },
  test: {
    environment: "node",
    include: ["src/**/*.test.ts", "src/**/*.test.tsx"],
    restoreMocks: true,
  },
});
