"""SINDESTIVA-PE · Job scheduler de scraping (Sprint 2).

Loop asyncio que:
  1. A cada `settings.scraper_interval_seconds` (15min), itera
     (fonte × porto × turno) e dispara `executar_scraping`.
  2. Persiste em `lousa_escala_origem` + `lousa_alocacao` (UPSERT).
  3. Loga sucesso/falha por execução.

Convenção cross-projeto (Sinapse, MEMORY): `asyncio.create_task` no
lifespan > APScheduler. Scheduler dedicado não roda aqui — é loop
simples. Falha de 1 iteração não derruba as outras (try/except por
combinação).

Startup: o lifespan de `app/main.py` faz `asyncio.create_task(start())`
e guarda a task em `app.state.scraping_task`. Shutdown cancela a task
com `task.cancel()`.
"""
from __future__ import annotations

import asyncio
from datetime import UTC, date, datetime
from typing import Any

from app.core.config import settings
from app.core.database import session_scope
from app.core.logging import get_logger
from app.models.enums import FonteEscalaEnum
from app.services.scraping_service import executar_scraping

log = get_logger(__name__)


# Mapeamento fonte → porto (DD v1 §3.27 + decisão de escopo).
_FONTE_PORTO: dict[FonteEscalaEnum, str] = {
    FonteEscalaEnum.TPA: "SUAPE",
    FonteEscalaEnum.ESCALANET: "RECIFE",
}

_TURNOS: tuple[str, ...] = ("DIURNO", "NOTURNO")


class ScrapingScheduler:
    """Orquestra o loop de scraping."""

    def __init__(self, interval_seconds: int | None = None) -> None:
        self.interval_seconds = interval_seconds or settings.scraper_interval_seconds
        self._task: asyncio.Task[None] | None = None
        self._stop_event = asyncio.Event()

    def start(self) -> asyncio.Task[None]:
        """Inicia o loop em background. Idempotente."""
        if self._task is not None and not self._task.done():
            log.info("scraping_job.already_running")
            return self._task
        self._stop_event.clear()
        self._task = asyncio.create_task(self._run(), name="scraping-job")
        log.info("scraping_job.started", interval_seconds=self.interval_seconds)
        return self._task

    async def stop(self) -> None:
        """Para o loop (cancela a task)."""
        if self._task is None:
            return
        self._stop_event.set()
        self._task.cancel()
        try:
            await self._task
        except asyncio.CancelledError:
            pass
        except Exception as exc:  # noqa: BLE001
            # Shutdown não pode crashar o app — só loga.
            log.warning("scraping_job.stop_error", erro=str(exc))
        self._task = None
        log.info("scraping_job.stopped")

    async def _run(self) -> None:
        """Loop principal. Roda 1x imediatamente, depois a cada N segundos."""
        await self._ciclo_completo()
        while not self._stop_event.is_set():
            try:
                await asyncio.wait_for(
                    self._stop_event.wait(),
                    timeout=self.interval_seconds,
                )
                # Se acordou por stop_event, sai.
                break
            except TimeoutError:
                # Timeout = hora de rodar de novo.
                await self._ciclo_completo()

    async def _ciclo_completo(self) -> None:
        """1 ciclo = todos os (fonte, porto, turno) do dia atual."""
        # `date.today()` retorna local-naive — usa `datetime.now(tz=utc).date()`
        # pra alinhar com a convenção timezone-aware do projeto.
        hoje = datetime.now(tz=UTC).date()
        log.info("scraping_job.ciclo_inicio", data=hoje.isoformat())
        for fonte, porto in _FONTE_PORTO.items():
            for turno in _TURNOS:
                await self._executar_uma(fonte, porto, turno, hoje)
        log.info("scraping_job.ciclo_fim", data=hoje.isoformat())

    async def _executar_uma(
        self,
        fonte: FonteEscalaEnum,
        porto: str,
        turno: str,
        data: date,
    ) -> None:
        """1 execução de scraping (1 fonte × 1 porto × 1 turno × 1 data)."""
        try:
            async with session_scope() as db:
                resultado = await executar_scraping(
                    db,
                    fonte=fonte,
                    porto_slug=porto,
                    turno_codigo=turno,
                    data=data,
                )
            log.info(
                "scraping_job.execucao",
                fonte=fonte.value,
                porto=porto,
                turno=turno,
                data=data.isoformat(),
                status=resultado.status.value,
                celulas=resultado.total_celulas,
                duracao_ms=resultado.duracao_ms,
                layout_mudou=resultado.layout_mudou,
            )
        except Exception as exc:  # noqa: BLE001
            # Falha de 1 iteração NÃO derruba o ciclo.
            log.error(
                "scraping_job.execucao_falhou",
                fonte=fonte.value,
                porto=porto,
                turno=turno,
                data=data.isoformat(),
                erro=str(exc),
            )


# Singleton usado pelo lifespan.
_scheduler: ScrapingScheduler | None = None


def get_scheduler() -> ScrapingScheduler:
    """Retorna o singleton (lazy)."""
    global _scheduler
    if _scheduler is None:
        _scheduler = ScrapingScheduler()
    return _scheduler


# ---------------------------------------------------------------------------
# Entry point standalone (para `python -m app.jobs.scraping_job`)
# ---------------------------------------------------------------------------

async def run() -> None:
    """Roda 1 ciclo e sai. Para debug/CI."""
    scheduler = get_scheduler()
    await scheduler._ciclo_completo()


if __name__ == "__main__":
    asyncio.run(run())


__all__ = ["ScrapingScheduler", "get_scheduler", "run"]


# Ignora type[Any] import não usado (mantido pra extensões futuras).
_ = Any
