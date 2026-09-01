"""SINDESTIVA-PE · jobs assíncronos (APScheduler workers).

Convenção: cada job é um módulo top-level (sem classe wrapper) que
expõe `async def run() -> None`. O entrypoint do scheduler monta o
loop e registra o cron. Jobs rodam FORA do Turborepo (services/scraper)
ou dentro do lifespan do FastAPI (hash_chain_verifier, lgpd_purge).
"""
