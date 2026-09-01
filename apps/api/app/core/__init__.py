"""SINDESTIVA-PE · core (config, db, security, logging).

Convenção: este pacote expõe APENAS as peças estáveis. Importers
devem fazer `from app.core.database import get_db`, `from app.core.config
import settings`, etc. Nada de re-export preguiçoso que vaze ORM para
cima.
"""
