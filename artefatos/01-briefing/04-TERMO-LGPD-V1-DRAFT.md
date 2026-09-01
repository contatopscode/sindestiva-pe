---
id: TERMO-LGPD-V1-DRAFT
versao: 1 (DRAFT — para revisão de advogado trabalhista)
status: rascunho
data_criacao: 2026-09-01
revisor_legal: a definir (indicação Josias)
base_legal_draft: Art. 7º, V (execução de contrato) + Art. 11, II e V (dado sensível)
retensao: 24 meses (Art. 16 LGPD + CCT)
---

# Termo de Consentimento Livre e Esclarecido · Lousa Digital

> **DRAFT para revisão de advogado trabalhista** — não usar em produção
> sem o sign-off escrito do advogado + registro da versão aprovada.
> Versão final aprovada substituirá este arquivo e moverá o draft para
> `historico/`.

---

## Quem somos

**SINDESTIVA-PE** — Sindicato dos Estivadores nos Portos de Pernambuco,
CNPJ `[a preencher]`, com operação em Recife e Suape.

**Encarregado de Proteção de Dados (DPO):** Paulo Siqueira, e-mail
`dpo@sindestiva-pe.org.br`, telefone `[a definir]`.

## O que é a Lousa Digital

A Lousa Digital é uma plataforma interna do Sindicato que **replica a
lousa oficial do OGMO/PE**, **digitaliza o remanejamento operacional**
(substituição de TPA avulso) e **notifica formalmente o OGMO** sobre
cada remanejamento, com **trilha de auditoria imutável** (hash chain
SHA-256).

**Ela não:**
- Vende seus dados
- Compartilha com terceiros sem sua autorização
- Toma decisão trabalhista no seu lugar (decisão é sempre do Fiscal)
- Substitui a lousa oficial do OGMO (essa continua sendo a verdade)

## Quais dados pessoais coletamos

| Dado | Por que coletamos | Obrigatório? |
|---|---|---|
| **Nome completo** | Identificação no painel e na notificação ao OGMO | Sim |
| **CPF** | Cruzamento com a matrícula OGMO e unicidade | Sim |
| **Matrícula OGMO** | Identificação funcional no cais | Sim |
| **Telefone (WhatsApp)** | Confirmação de presença + canal com o Fiscal | Sim |
| **E-mail** | Recuperação de senha (Fiscal/Dirigente) | Sim (se aplicável) |
| **Data de nascimento** | Validação de maioridade e tempo de registro | Sim |
| **Função/cais/turno escalado** | Operação da lousa e remanejamento | Sim (operacional) |
| **Histórico de engajamentos** | BI, prova para próxima CCT | Sim (operacional) |
| **Pessoa com deficiência (PCD)** | Lei de cotas (Art. 93 Lei 8.213/91) | Sim (se aplicável) |

**Não coletamos:** dados de saúde, opiniões políticas, orientação
sexual, origem racial/étnica, convicção religiosa, dado biométrico
(vamos usar foto no PWA? **decidir com advogado**).

## Para que usamos seus dados (finalidade)

1. Operar a lousa digital (réplica da lousa oficial)
2. Registrar remanejamentos com motivo, base legal e auditoria
3. Notificar o OGMO/PE em < 1 minuto após cada remanejamento
4. Permitir que você (TPA) consulte sua escala no celular
5. Gerar relatórios agregados (BI) para a diretoria negociar a próxima
   CCT — **dados sempre agregados, nunca individuais identificáveis**
6. Cumprir obrigação legal/regulatória (CCT, MPT, fiscalização)

## Base legal (LGPD)

Tratamos seus dados com base em:

- **Art. 7º, V** — execução de contrato (CCT vigente) e de
  procedimentos preliminares relacionados ao contrato de trabalho
  portuário avulso
- **Art. 7º, VI** — exercício regular de direitos (sindicato exerce
  representação da categoria)
- **Art. 11, II** — tratamento de dado pessoal sensível (PCD) quando
  aplicável, para cumprimento de obrigação legal
- **Art. 11, V** — exercício regular de direitos em contrato

## Com quem compartilhamos

| Destinatário | O que | Por quê |
|---|---|---|
| **OGMO/PE** | Nome, matrícula, função, cais, turno, remanejamentos | Notificação formal de operação portuária (obrigação regulatória) |
| **MPT-PE** (se solicitado) | Relatórios agregados + auditoria | Atendimento a requisição legal |
| **Advogado do Sindicato** | Nome, matrícula, histórico | Defesa em ação trabalhista |
| **Fornecedor de infra (Hetzner)** | Nada (eles não têm acesso aos dados, só hospedam) | Operação do servidor |

**Não vendemos, não compartilhamos com marketing, não cruzamos com
redes sociais.**

## Por quanto tempo guardamos

| Dado | Retenção | Justificativa |
|---|---|---|
| Auditoria de remanejamento | **24 meses** | Art. 7º, XXIX CLT (prescrição bienal) + Art. 16 LGPD |
| Cadastro pessoal (TPA) | Enquanto vinculado ao Sindicato + 24m após desligamento | Mesma justificativa |
| Logs de acesso | 12 meses | Art. 37 LGPD + boas práticas |
| CCT, contratos, documentos jurídicos | 5 anos | Art. 173 CTN + obrigação sindical |

Após o prazo: **deleção automática com log em `lgpd_purge_log`**
(job diário S6-06). Você pode pedir exclusão **antes** desse prazo —
ver seção "Seus direitos".

## Seus direitos (Art. 18 LGPD)

Você pode, a qualquer momento, pedir:

- [ ] **Confirmação da existência de tratamento** (resposta em 15 dias)
- [ ] **Acesso aos seus dados** (resposta em 15 dias)
- [ ] **Correção de dados incompletos ou incorretos**
- [ ] **Anonimização, bloqueio ou eliminação** de dados desnecessários
- [ ] **Portabilidade** (em formato estruturado, JSON/CSV)
- [ ] **Eliminação dos dados** tratados com base em consentimento
- [ ] **Revogação do consentimento** (sem efeito retroativo)
- [ ] **Oposição ao tratamento** se irregular

**Como pedir:** pelo PWA (botão "Solicitar exclusão" no perfil) ou
e-mail `dpo@sindestiva-pe.org.br`. Resposta em até **15 dias corridos**
(Art. 18 §5º LGPD).

## Segurança

- Senhas com bcrypt (12+ caracteres, 1 maiúscula, 1 número, 1 símbolo)
- Sessão expira em 8h
- Todas as ações registradas em log com **hash chain SHA-256** (qualquer
  adulteração é detectada em até 24h)
- Backup diário criptografado, retido 30 dias
- Acesso restrito por perfil (RBAC: FISCAL, DIRIGENTE, TPA)
- Conexão HTTPS obrigatória (TLS 1.3)

## Cookies e rastreamento

- **Cookies estritamente necessários** (sessão autenticada) — não podem
  ser desativados
- **Sem cookies de marketing, sem analytics de terceiros, sem pixel
  de rede social**

## Onde seus dados ficam

Servidores próprios do Sindicato, hospedados na **Hetzner Cloud**
(data center em Frankfurt, Alemanha), com **criptografia em disco**
(LUKS) e em trânsito (TLS 1.3). Backup criptografado em bucket
separado (região diferente). **Não usamos AWS, GCP, Azure, nem
datacenter fora da UE/Hetzner.**

## Mudanças neste termo

Qualquer alteração será comunicada por **e-mail + push no PWA** com
30 dias de antecedência. Se você discordar, pode pedir exclusão dos
seus dados sem custo.

## Aceite

Ao marcar "Li e aceito" e prosseguir, você declara que:

1. Leu e entendeu este termo
2. Está ciente dos dados coletados, finalidade, base legal, retenção
3. Sabe como exercer seus direitos Art. 18 LGPD
4. Está ciente de que a negativa impede o uso da Lousa Digital
   (alternativa: papel/caneta, processo atual)

**Versão do termo:** v1.0 (data: `[a preencher após aprovação]`)
**Hash SHA-256 deste termo:** `[gerado pelo sistema na publicação]`

---

## Checklist do advogado (campos a preencher)

- [ ] CNPJ do SINDESTIVA-PE preenchido
- [ ] E-mail e telefone do DPO preenchidos
- [ ] Decisão sobre PCD: confirmar se é Art. 11, II ou outro
- [ ] Decisão sobre foto/biometria no PWA: incluir ou não
- [ ] Decisão sobre geolocalização (turno noturno em cais): LGPD
      considera? Art. 11?
- [ ] Prazos de resposta Art. 18 OK? (15 dias é o mínimo legal, mas
      CCT pode apertar)
- [ ] Texto de revogação de consentimento OK?
- [ ] Jurisprudência do TST sobre tratamento de dados de TPA?
- [ ] LGPD Pro (MP 869/2019) — ainda em vigor ou revogada? (conferir
      atualização legislativa)

---

*Draft lavrado por Paulo Siqueira (DPO) · 2026-09-01 · v1.*
*Substituir pelo termo assinado pelo advogado antes do Go-Live.*
