---
id: KICKOFF-PAUTA
versao: 1
status: rascunho
data_criacao: 2026-09-01
data_evento: 2026-09-04
participantes:
  - Josias Martins Santiago (Presidente SINDESTIVA-PE) — sponsor cliente
  - Paulo Siqueira (Diretor de Tecnologia e Operação · Suporte Gerencial) — sponsor técnico + dev
local: Sede do SINDESTIVA-PE (Recife) ou Google Meet
duracao: 90 min
---

# Pauta · Reunião de Kickoff · SINDESTIVA-PE · Lousa Digital

> Marco M0 do plano ("Premissas validadas"). É a porta de entrada da Fase 1.
> Esta reunião encerra o Sprint 0 e libera a entrada no Sprint 1 (Fundação).

---

## 1. Abertura (5 min) · Paulo

- Boas-vindas, agradecimento pelo aceite do projeto
- Reforçar o **porquê** do projeto: falhas de comunicação geram passivo
  trabalhista e assimetria OGMO/Sindicato/TPA
- Combinar a regra de ouro: **decisões por escrito** (e-mail ou ata),
  nada de combinado "no telefone"

## 2. Apresentação do plano (15 min) · Paulo

- Resumo executivo do `SINDESTIVA-PE-PLANO-IMPLEMENTACAO-2026-09-01.md`
  (1 página):
  - 5 funcionalidades centrais (Lousa Espelhada, Remanejamento Digital,
    Notif OGMO tripla via, PWA TPA, BI)
  - Marcos M0 → M10 (Sprint 0 → 18)
  - 86 HUs, ~452h, 18 semanas solo + Manoel
  - Investimento total ano 1: **R$ 9,5–13 mil** (infra + advogado + viagem)
  - Mão de obra Paulo = custo interno Suporte Gerencial
- Cronograma de 45 dias (resumo executivo) — janela apertada mas viável
  com Manoel dedicado

## 3. Decisões a tomar NESTA reunião (30 min) · Paulo modera, Josias decide

| # | Decisão | Opções | Recomendação | Quem decide |
|---|---|---|---|---|
| D-K0-1 | Multi-posto de Suape no MVP ou só 1 turno-piloto? | (a) só 1 turno · (b) 2 turnos · (c) porto inteiro | (a) 1 turno-piloto | Josias |
| D-K0-2 | Quando enviar a carta ao OGMO/PE? | (a) agora (Sprint 0) · (b) após Sprint 1 ter prototipo · (c) Sprint 3 | (a) agora | Josias |
| D-K0-3 | Quem é o interlocutor do OGMO? | Josias indica nome + telefone/email | — | Josias |
| D-K0-4 | Advogado trabalhista para revisar termo LGPD | (a) rede Paulo · (b) indicação Josias · (c) OAB-PE | (b) Josias indica (rede do Porto) | Josias |
| D-K0-5 | Manoel Costa é mesmo o Fiscal-piloto? | confirmar | sim | Josias confirma |
| D-K0-6 | Estagiário de TI a partir do Sprint 10? | (a) sim · (b) só após Go-Live | (a) sim (R$ 800-1.200/mês) | Josias |
| D-K0-7 | Assinatura digital (termo LGPD) via | (a) Gov.br · (b) e-mail com link · (c) escrito no PWA | (c) PWA (mais simples, juridicamente válido) | Josias |
| D-K0-8 | Go-Live em 1 turno ou 100% Suape? | (a) 1 turno · (b) 100% | (a) 1 turno (S10) → 100% S11 | Josias |

## 4. Papéis e governança (10 min) · Paulo

- **Sponsor cliente (Josias):** decisões estratégicas, carta ao OGMO,
  alinhamento político, 2-4h/mês
- **Sponsor técnico (Paulo):** código, deploy, DPO, product owner
- **Usuário-chave (Manoel):** testar, validar, treinar colegas, 4h/sem
  nas semanas-chave
- **DPO (Paulo acumulado):** política de privacidade, exclusões LGPD
- **Steering committee** mensal a partir do Sprint 5: Josias + Paulo +
  advogado (LGPD)

Cadência de reportes:
- **Daily** (mensagem WhatsApp, 1 linha): Paulo + Manoel
- **Weekly** (e-mail 1 página, sexta): Paulo → Josias
- **Sprint review** quinzenal (1h): Manoel + fiscais + Josias
- **Steering committee** mensal (1h, a partir S5): Josias + Paulo + adv

## 5. Materiais a entregar AGORA pelo Josias (10 min)

- [ ] CCT 2024-2026 vigente (cópia digitalizada) — K-2
- [ ] Carta branca para OGMO/PE (Paulo redige, Josias assina) — K-7
- [ ] Indicação de advogado trabalhista (contato) — K-5
- [ ] Confirmação Manoel Costa como Fiscal-piloto — K-3
- [ ] Lista de fiscais ativos em Suape (nome + telefone) — K-3
- [ ] E-mail institucional `contato@sindestiva-pe.org.br` (criar/alocar) — §8.1
- [ ] Acesso ao grupo WhatsApp "Lousa Digital" (criar) — §8.1

## 6. Riscos & plano B (5 min) · Paulo

Os 3 riscos mais críticos do MVP:
- **R1:** OGMO boicota (não responde, proíbe sistema) → mitigado porque
  integração é unilateral (réplica fiel + e-mail formal, sem precisar de
  API OGMO)
- **R2:** Layout OGMO muda e quebra scraper → fingerprint + alerta em
  até 60s, fallback pra última versão válida
- **R5:** LGPD/MPT reprova → DPO Paulo, advogado trabalhista, termo
  Art. 7º + 11

## 7. Próximos passos e encerramento (5 min)

- Sprint 0 termina em **07/09/2026** (esta semana)
- Sprint 1 começa em **08/09/2026** (Fundação: repo, auth, RBAC, LGPD)
- Próxima weekly sync: **sexta 11/09 às 10h** (Google Meet, 30 min)
- Próximo sprint review: **sexta 25/09 às 10h** (1h, presencial ou Meet)

**Ata lavrada por Paulo em até 24h.** Todos os participantes assinam
via e-mail confirmando aceite.

---

*Mantido por Paulo Siqueira · SINDESTIVA Bot · 2026-09-01 · v1.*
