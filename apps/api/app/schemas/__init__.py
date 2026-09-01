"""SINDESTIVA-PE · Pydantic v2 schemas (request/response).

Convenção por entidade (DD v1):
  - XBase: campos comuns
  - XCreate: payload de POST (sem id, sem timestamps)
  - XUpdate: payload de PATCH (tudo opcional)
  - XRead: response com id + timestamps
  - XInDB: alias de XRead + relacionamentos (uso interno)

Schemas NÃO devem importar de app.models. Dependência é mão única.
"""
