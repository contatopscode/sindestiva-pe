"""SINDESTIVA-PE · serviços de domínio.

Convenção: services encapsulam regras que cruzam ≥ 2 models OU têm
efeito colateral externo (e-mail, PDF, Redis, hash chain). Routers
chamam services; services chamam models. Nada de SQL cru em router.
"""
