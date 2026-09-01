---
id: CARTA-OGMO-DRAFT
versao: 1 (DRAFT — Josias assina)
status: rascunho
data_criacao: 2026-09-01
remetente: Josias Martins Santiago (Presidente SINDESTIVA-PE)
destinatario: OGMO/PE (Órgão Gestor de Mão de Obra do Trabalho Portuário Avulso de Pernambuco)
canal: AR digital + e-mail + protocolo presencial
---

# Carta ao OGMO/PE · Solicitação de Interlocução Técnica

> **DRAFT para assinatura do Josias.** Paulo redige, Josias revisa e
> assina. Enviar por AR digital (impreterível) + e-mail + protocolo
> presencial (capa do OGMO).

---

**SINDESTIVA-PE — SINDICATO DOS ESTIVADORES NOS PORTOS DE PERNAMBUCO**
CNPJ: `[a preencher]` · Endereço: `[a preencher]`

Recife, **_[a preencher]_** de **_[mês]_** de 2026.

**Ao**
**OGMO/PE — Órgão Gestor de Mão de Obra do Trabalho Portuário Avulso**
A/C: Sr(a). `[nome do interlocutor a indicar pelo Josias]`
Endereço: `[a confirmar]`

**Assunto:** Solicitação de interlocução técnica para modernização do registro de remanejamentos operacionais no Porto de Suape

---

Prezado(a) Senhor(a),

O **SINDESTIVA-PE** — Sindicato dos Estivadores nos Portos de
Pernambuco, representante da categoria dos Trabalhadores Portuários
Avulsos (TPAs) nos Portos de Recife e Suape, vem, por meio de seu
Presidente, **solicitar interlocução técnica** com esse Órgão Gestor
com o objetivo de apresentar e alinhar a **Lousa Digital** — sistema
interno do Sindicato que moderniza o registro de **remanejamentos
operacionais** (substituição de TPA avulso) e a **notificação formal**
dessas substituições ao OGMO.

## 1. Contexto

A operação portuária em Suape sustenta-se hoje em lousa física,
telefone e rádio entre fiscais do Sindicato e o OGMO. **Falhas de
comunicação** nesse processo geram:

- Horas-fiscais perdidas (retrabalho de confirmação)
- Passivo trabalhista (substituições sem registro formal adequado)
- Assimetria de informação entre OGMO, Sindicato e TPA
- Dificuldade de auditoria pela Secretaria de Portos, MPT e Receita

A CCT 2024-2026 (cláusula `[a confirmar]`) já prevê a modernização
do registro de substituições, e esse Sindicato entende que a Lousa
Digital é o caminho para entregar isso **sem dependência de nenhuma
mudança em sistema do OGMO**.

## 2. O que é a Lousa Digital (visão geral)

A Lousa Digital é uma plataforma **própria do Sindicato** que:

- **Replica fielmente a lousa oficial do OGMO** (raspagem tolerante da
  página do TPA/OGMO, com detecção automática de mudança de layout)
- **Registra cada remanejamento** com motivo, base legal, TPA
  substituído, TPA substituto, fiscal responsável, anexo opcional e
  **hash de integridade SHA-256**
- **Notifica o OGMO em tempo real por três caminhos paralelos**:
  1. **E-mail formal** com PDF do remanejamento anexado
  2. **Painel de pendências OGMO** (URL autenticada por token, em
     leitura apenas) no próprio Centro de Comando do Sindicato
  3. **Webhook HMAC-SHA256** (quando o OGMO prover endpoint — sem
     urgência)
- **Mantém trilha de auditoria imutável** com hash chain validado
  diariamente
- **Permite que o TPA consulte a escala dele no celular** (PWA),
  reduzindo telefonemas

**Importante:** a Lousa Digital **não interfere** no escalonamento
oficial do OGMO. Ela é uma **réplica** do que o OGMO já publica, mais
a camada de registro e notificação do Sindicato. A fonte da verdade
continua sendo a lousa oficial do OGMO.

## 3. Conformidade legal e operacional

- **LGPD:** termo de consentimento assinado por cada TPA, retenção de
  24 meses, DPO nomeado, atendimento aos Art. 7º, 11 e 18
- **Auditoria:** todas as ações registradas, hash chain íntegro,
  exportável em PDF/CSV a qualquer momento
- **CCT 2024-2026:** alinhada com as cláusulas de substituição
  (`[indicar cláusulas]`)
- **MPT:** Sindicato se coloca à disposição para apresentar o sistema
  preventivamente

## 4. O que solicitamos ao OGMO

1. **Indicação de um interlocutor técnico** (nome, e-mail, telefone)
   para alinhamento operacional durante o desenvolvimento
2. **Confirmação do e-mail institucional** que receberá as
   notificações de remanejamento (`escalacao@ogmo-pe.com.br` está
   correto? Outro?)
3. **Disponibilidade para 1 reunião técnica de 1h** (presencial em
   Recife ou Google Meet), na semana de **_[a confirmar]_**, para
   apresentação do sistema, demonstração ao vivo do fluxo de
   notificação e esclarecimento de dúvidas
4. **Caso o OGMO tenha interesse**, abertura de prazo para avaliação
   interna de **endpoint de webhook** (HMAC-SHA256) que receberia
   notificações em tempo real — sem urgência e sem precondição para o
   início da operação

## 5. Cronograma proposto

- **Setembro/2026:** desenvolvimento inicial + homologação interna
  com 1 fiscal-piloto (Manoel Costa, Suape)
- **Outubro/2026:** entrada em operação-piloto em 1 turno de Suape
- **Janeiro/2027:** Go-Live oficial em 100% dos turnos de Suape
- **Março/2027 (se aplicável):** expansão para Recife

A operação-piloto (set-out/2026) **não exige nenhuma ação do OGMO** —
o Sindicato operará com base na lousa oficial + e-mail de notificação.
A interlocução que solicitamos é para **alinhamento e transparência**,
não para autorização.

## 6. Contatos

| Papel | Nome | E-mail | Telefone |
|---|---|---|---|
| Presidente SINDESTIVA-PE | Josias Martins Santiago | `presidente@sindestiva-pe.org.br` | `[a preencher]` |
| Sponsor técnico + DPO | Paulo Siqueira | `paulo@pscode.ia.br` | `[a preencher]` |
| Fiscal-piloto Suape | Manoel Costa | `[a preencher]` | `[a preencher]` |

## 7. Encerramento

O SINDESTIVA-PE reitera seu compromisso com a **modernização
operacional**, com a **transparência junto ao OGMO** e com a
**defesa dos direitos da categoria** que representa. A Lousa Digital
nasce desse tripé e se coloca como ferramenta de colaboração, não de
contenção.

Colocamo-nos à inteira disposição para a reunião técnica sugerida e
para qualquer esclarecimento adicional.

Atenciosamente,

---

**_______________________________**
**Josias Martins Santiago**
Presidente
SINDESTIVA-PE — Sindicato dos Estivadores nos Portos de Pernambuco

---

*Cópia:*
- *Manoel Costa — Fiscal-piloto (conhecimento)*
- *Paulo Siqueira — Sponsor técnico (coordenação)*
- *Advogado do Sindicato (assessoria)*
- *Arquivo SINDESTIVA-PE*

---

*Draft redigido por Paulo Siqueira · 2026-09-01 · v1.*
*Versão final após assinatura do Josias substituirá este arquivo.*
