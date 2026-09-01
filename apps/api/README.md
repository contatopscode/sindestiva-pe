# apps/api

API FastAPI do SINDESTIVA-PE. Veja `SINDESTIVA-PE-PLANO-IMPLEMENTACAO-2026-09-01.md` seção 3.1 para o stack completo.

## Run local

```bash
pnpm db:up
cp .env.example .env  # ajustar
uvicorn app.main:app --reload --port 8000
```

Swagger: <http://localhost:8000/docs>
