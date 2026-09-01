"""SINDESTIVA-PE · Scrapers da lousa (Sprint 2).

Cada módulo expõe `raspar_por_data(porto_slug, data, *, http_client=None)`
que retorna uma `EscalaBruta`. O orquestrador
`app.jobs.scraping_job` itera fontes × portos × turnos × datas.

Fontes:
  - tpa        → TPA Tecnologia (SUAPE — http://tpa.ogmosuape.com.br)
  - escalanet  → EscalaNet (RECIFE — http://escalanet.recife.gov.br)
"""
from app.scrapers.base import CelulaBruta, EscalaBruta, hash_conteudo
from app.scrapers.escalanet import raspar_por_data as raspar_escalanet
from app.scrapers.tpa import raspar_por_data as raspar_tpa

__all__ = [
    "CelulaBruta",
    "EscalaBruta",
    "hash_conteudo",
    "raspar_escalanet",
    "raspar_tpa",
]
