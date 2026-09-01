"""SINDESTIVA-PE · LGPD service (Sprint 1 T1-10).

Constantes e helpers relacionados a LGPD:
- Texto do termo de consentimento v1.0 (DR: advogado valida na S0 K-5)
- Gerador de protocolo único pra solicitações Art. 18

Pega-dica: termo é IMUTÁVEL após publicação. Pra mudar, bumpa a versão
(1.0 → 1.1) e atualiza o seed + o hash.
"""
from __future__ import annotations

import hashlib
import secrets
from datetime import datetime


# ----------------------------------------------------------------------------
# Termo de Consentimento v1.0 (DR: advogado valida antes de virar oficial)
# ----------------------------------------------------------------------------

TERMO_V1: str = """# Termo de Consentimento para Tratamento de Dados Pessoais
## SINDESTIVA-PE · Lousa Digital · v1.0

**Última atualização:** 01/09/2026

Ao aceitar este termo, você (TPA — Trabalhador Portuário Avulso)
autoriza o **SINDESTIVA-PE** (Sindicato dos Estivadores nos Portos de
Pernambuco) a tratar seus dados pessoais para as finalidades descritas
abaixo, em conformidade com a **Lei nº 13.709/2018 (LGPD)**.

### 1. Controlador

SINDESTIVA-PE — Sindicato dos Estivadores nos Portos de Pernambuco
CNPJ: XX.XXX.XXX/0001-XX
Endereço: [endereço do Sindicato]
Encarregado de Proteção de Dados (DPO): Paulo Siqueira
E-mail do DPO: paulo@pscode.ia.br

### 2. Dados pessoais tratados

- **Identificação:** nome completo, CPF, matrícula OGMO, data de nascimento
- **Contato:** telefone (WhatsApp), e-mail
- **Operacionais:** função portuária, fainas realizadas, turnos,
  remanejamentos, confirmações de presença
- **Auditoria:** logs de acesso (IP, user agent, timestamp), ações no
  sistema (criação de remanejamento, aceite de termo, etc)

**Dados sensíveis (Art. 5º, II LGPD):** este sistema **NÃO** trata dados
biométricos, religiosos, raciais, de opinião política ou de saúde.

### 3. Finalidades de tratamento

| Finalidade | Base legal | Retenção |
|---|---|---|
| Gestão de escalas portuárias (lousa digital) | Art. 7º, VI — exercício regular de direitos | 24 meses |
| Notificação ao OGMO/PE sobre remanejamentos | Art. 7º, VI — exercício regular de direitos | 5 anos (audit) |
| Cumprimento de obrigação legal/regulatória (CCT, MPT) | Art. 7º, II — cumprimento de obrigação legal | 5 anos |
| Auditoria interna (hash chain SHA-256) | Art. 7º, VI | 5 anos (audit) |
| Comunicação via WhatsApp (escala, remanejamentos) | Consentimento (Art. 7º, I) | até revogação |

### 4. Compartilhamento

Seus dados podem ser compartilhados com:
- **OGMO/PE** (notificações de remanejamento, com hash de integridade)
- **MPT-PE / ANTAQ** (em caso de auditoria, mediante solicitação formal)
- **CCT vigente** (mediante requisição de fiscalização)
- **NÃO** compartilhamos com terceiros para fins comerciais.

### 5. Seus direitos (Art. 18 LGPD)

Você tem direito a:
- **Confirmação da existência de tratamento** (sempre disponível via /api/v1/me)
- **Acesso aos dados** (export PDF/JSON via /api/v1/lgpd/solicitacoes + tipo=PORTABILIDADE)
- **Correção de dados incompletos ou incorretos**
- **Anonimização, bloqueio ou eliminação** de dados desnecessários
- **Portabilidade** dos dados a outro sistema
- **Revogação do consentimento** (a qualquer momento, sem efeito retroativo)

Pra exercer qualquer direito, faça uma solicitação via
`POST /api/v1/lgpd/solicitacoes`. Prazo de resposta: **15 dias** (Art. 18, §5º).

### 6. Segurança

- **Senha:** bcrypt (12 rounds), nunca armazenada em texto plano
- **Autenticação:** JWT HS256 com expiração de 8h
- **Transporte:** HTTPS obrigatório em produção (HSTS, CSP)
- **Auditoria:** hash chain SHA-256 (cada evento inclui o hash do anterior)
- **Verificação diária:** job às 03:00 detecta adulterações
- **Retenção:** logs de auditoria por 5 anos (Art. 37 LGPD + Art. 7º CLT)

### 7. Encarregado de Proteção de Dados (DPO)

**Paulo Siqueira** (acumulado — DPO da Suporte Gerencial)
E-mail: paulo@pscode.ia.br
Telefone: +55 81 9XXXX-XXXX

### 8. Foro

Fica eleito o foro de Recife/PE para dirimir quaisquer questões
relativas a este termo, sem prejuízo do direito do titular de
recorrer à ANPD (Autoridade Nacional de Proteção de Dados).

---

## Aceite

Ao clicar em **"Aceito"**, você declara ter lido, compreendido e
consentido com todas as cláusulas acima, em especial com o tratamento
dos seus dados pessoais para as finalidades descritas no item 3.

Você pode revogar este consentimento a qualquer momento, sem efeito
retroativo, conforme Art. 8º, §5º da LGPD.
"""


def gerar_protocolo() -> str:
    """Gera protocolo único pra solicitação Art. 18 (formato: LGPD-YYYY-NNNN)."""
    ano = datetime.now().year
    sufixo = secrets.token_hex(2).upper()  # 4 chars hex
    return f"LGPD-{ano}-{sufixo}"


def hash_termo(texto: str) -> str:
    """SHA-256 hex do texto do termo. Estável se texto não mudar."""
    return hashlib.sha256(texto.encode("utf-8")).hexdigest()


__all__ = ["TERMO_V1", "gerar_protocolo", "hash_termo"]
