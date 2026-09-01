# SINDESTIVA-PE — Plano de Solução Digital para a Lousa de Estiva

> **Documento gerado em 12/08/2026** · **Patrocinador:** SINDESTIVA-PE (Sindicato dos Estivadores nos Portos de Pernambuco) · **Sponsor técnico:** Paulo Siqueira · **Base da análise:** navegação em http://tpa.ogmosuape.com.br/web/lousa_estiva + pesquisa institucional/legal/jurisprudência.

---

## 0. TL;DR (resumo executivo)

Hoje o SINDESTIVA-PE opera uma **lousa manual de remanejamento de estivadores** controlada por fiscais nos Portos de Recife e Suape. A informação flui por **telefone/rádio** entre o Fiscal do Sindicato e o OGMO, com defasagem e risco de erro humano. Você quer um sistema digital que mostre **status online** e que, na ocorrência de remanejamento, **atualize o OGMO em tempo real**.

A solução **não pode substituir o OGMO** (escalação é prerrogativa legal exclusiva do OGMO, conforme Lei 9.719/98 art. 5º e Lei 12.815/13 art. 32). Mas há um espaço enorme, inexplorado e juridicamente seguro, para o Sindicato construir uma **camada digital própria** que (a) **replica e complementa a lousa oficial**, (b) **digitaliza o remanejamento interno**, e (c) **sincroniza com o OGMO via notificação formal** (webhook, e-mail auditável, ou API se houver acordo).

**Recomendação:** combinar **Opção A (Espelho Inteligente)** + **Opção C (PWA do Trabalhador)** como MVP de 90 dias, deixando a **Opção B (Hub B2B oficial)** como roadmap de 12-18 meses, condicionada a negociação tripartite Sindicato + OGMO + Operadores.

**Investimento estimado do MVP:** 1 dev full-stack (você) por ~10-12 semanas + R$ 200-400/mês de infra. **Custo evitado:** horas-fiscais + autuações trabalhistas por falha de comunicação.

---

## 1. Modelo de Negócio AS-IS (OGMO × Sindicato)

### 1.1 Os 3 atores do porto

| Ator | Quem é | Papel legal | Sistema de TI atual |
|---|---|---|---|
| **OGMO/PE** (Recife + Suape, mesma entidade) | Constituído pelos Operadores Portuários (Lei 8.630/93 art. 18). CNPJ 01.149.631/0001-? (Suape). Tem exclusividade do **cadastro, registro, seleção, escalação, treinamento, arrecadação e repasse** dos TPAs. | Escalar TPAs em sistema de **rodízio sequencial e numérico**; manter cadastro; expedir documentos; zelar por NR-29. | TPA (tpa.ogmosuape.com.br) — AngularJS legado, v1.24.0, mostra **lousa de ponteiros** e **listagem de turno**. Site institucional: www.ogmo-suape.com.br (Angular SPA + JWT). Recife tem o "EscalaNet" (ogmo-recife.org.br/EscalaNet). |
| **SINDESTIVA-PE** (Sindicato dos Estivadores nos Portos de Pernambuco) | Fundado em **19/03/1891** (mais antigo da América Latina). Presidente: **Josias Martins Santiago**. Defende direitos, negocia CCT, fiscaliza operações, faz o **remanejamento operacional** dos estivadores nos portos. | Após 1993, perdeu a **escalação** pro OGMO, mas mantém: **gestão interna do quadro, presença, remanejamento operacional, fiscalização, comunicação com o TPA, negociação de CCT**. | **Não tem sistema.** Lousa física/quadro no porto + telefone/rádio + caderno do fiscal. |
| **Operadores Portuários** (Tecon, CMA CGM, Maersk, BTP etc.) | Empresas que operam os terminais. | Contratam o OGMO (que escala) e pagam o Sindicato (contribuição). | Cada um tem o seu (TOS — Terminal Operating System). |

### 1.2 O fluxo AS-IS (o que você descreveu na reunião)

```
1. Navio atraca no Porto (Recife ou Suape)
2. Operador Portuário requisa MO ao OGMO (por formulário/online)
3. OGMO escala, em rodízio, na sua LOUSA OFICIAL (tpa.ogmosuape.com.br)
4. Fiscais do SINDICATO, no porto, conferem quem compareceu
5. Se alguém falta ou há remanejamento (ex: TPA veio bêbado,
   apareceu um navio extra, mudou a composição de terno):
   o FISCAL LIGA/CHAMA POR RÁDIO o OGMO
6. OGMO altera a escala manualmente (ou anota em papel) e,
   eventualmente, atualiza a lousa
7. No fim do turno, OGMO emite a LISTAGEM DE TURNO
   (tpa.ogmosuape.com.br/web/listagem_turno?d=...&t=...)
8. Lista vai pra folha de pagamento, FGTS, contribuição sindical
```

**Pontos de falha atuais:**
- ❌ **Passo 5 é por telefone/rádio** — sem registro auditável, sem SLA
- ❌ A lousa oficial do OGMO mostra **ponteiros** (nº 058, 070, 811), não nomes — quem vai pro cais precisa decodificar mentalmente
- ❌ Se o OGMO não consegue atualizar a lousa, o Fiscal do Sindicato não sabe quem está escalado de fato
- ❌ Histórico perdido (cada turno vira PDF, sem base consolidada)
- ❌ Recife e Suape rodam sistemas diferentes (EscalaNet vs TPA) — visão unificada não existe
- ❌ Trabalhador (TPA) só sabe se está escalado indo ao porto ou ligando

### 1.3 O que o OGMO Suape mostra (dados colhidos hoje)

URL: `http://tpa.ogmosuape.com.br/web/lousa_estiva`

- **2 turnos publicados lado a lado:** Diurno (08-14/14-20/08-16/16-00) e Noturno (20-02/02-08/00-08)
- **Colunas (26):** Funções de Mando (C/M Geral, C/M Porão, C/M Bloco, C/M Rechego, C/M Consertador, Supervisor) + Terno (Porão, Bloco MAX, Bloco, Rechego, Consertador, Ship Loader Porão) + Funções Técnicas (Sinaleiro, Guincho A, Guincho B, Empilhador GP, Empilhador PP, Veículo Pesado, Veículo Leve, Manobrista, Transportador, Pá Mecânica, Retro Escavadeira, PC) + Vigia (Rodízio, Contra Bordo)
- **Linhas (10 fainas):** Produção, Salário, Sacaria Solta, Sacaria Pré-Lingada, Ro-Ro Veículo Leve, Ro-Ro Veículo Leve até 400, Ro-Ro Veículo Pesado, Diversos e Equip. Eólicos, Cadastro, Suplementar, Trabalho em Altura NR-35
- **Célula = "ponteiro"** (3 dígitos) = **nº do agulhado** (posição na fila de rodízio) do TPA escalado
- **Versão:** 1.24.0 (legado, sem HTTPS, AngularJS + jQuery + keyboard)

URL: `http://tpa.ogmosuape.com.br/web/listagem_turno?d=YYYY-MM-DD&t=N`

- Retorna: Nome, Matrícula, Função, Cais, Navio dos escalados
- Exemplo: turno `t=5` = 08-16; `d=2026-07-14` mostrou lista gerada às 04:10 do dia
- **Hoje retorna "Listagem vazia!"** (Paulo navegou em 12/08/2026 e não tem turno aberto — confirma que o sistema gera lista sob demanda por turno)

### 1.4 Modelo de referência — OGMO Santos (o mais maduro do Brasil)

- App **"OGMO Santos Digital"** (iOS+Android) desde 2018
- **Escala Digital** desde julho/2019 — 6.000+ TPAs
- **2 modos:** *por chamada* (TPA aguarda ser chamado pelo nº de agulhado) e *por escolha* (TPA escolhe vagas)
- **Sincronização** entre escala presencial e remota (mesma regra de rodízio, mesmo resultado)
- **Resistência política:** estivadores protestaram em 2019 contra instabilidade e contra cumprimento do intervalo de 11h (TST manteve a escala digital válida; OGMO conseguiu liminar obrigando 70% de atendimento)
- **Lição:** sistema digital é viável, mas é **travado politicamente** e exige **sindicato dentro do barco** (8 sindicatos laborais no Conselho de Supervisão)

### 1.5 Modelo de referência — OGMO Rio Grande

- **TCAC com MPT** (2014) obrigando sistema eletrônico de escalação em rodízio
- Sistema online: `ogmo-rg.com.br/escalacao/estiva_pedra` (mostra "Escala NORMAL" e "Escala B")
- Modelo mais simples, sem app

### 1.6 Modelo de referência — OGMO Recife (o "irmão" do Suape)

- **EscalaNet:** `ogmo-recife.org.br/EscalaNet` (PHP, simples)
- Edital 2025 do OGMO/PE explicitamente diz "OGMOs Recife e Suape" como **a mesma entidade** (edital unificado 2025 abriu 257 vagas pros dois portos)
- **Implicação:** qualquer integração com OGMO/PE precisa cobrir os 2 portos de uma vez (não dá pra fazer só Suape)

---

## 2. Diagnóstico da Dor (o problema real)

### 2.1 A dor declarada (reunião)

> "Quando há atualização de remanejamento de Estivadores, as informações do OGMO não são atualizadas em tempo real — o Fiscal liga por telefone para alguém do OGMO. Preciso de uma solução Digital com status on-line que, ao atualizar no Sindicato, atualize o OGMO."

### 2.2 As dores NÃO declaradas (que estão lá, mesmo se ninguém falou)

- **D1 — Falta de auditoria:** não há registro de quem remanejou, quando, por quê, com base em qual regra
- **D2 — Assimetria de informação:** o OGMO tem dados; o Sindicato não. Trabalhador idem. Cada um opera no escuro
- **D3 — Risco jurídico:** falha no remanejamento gera passivo trabalhista (TPA que deveria ter sido chamado e não foi → ação por perdas e danos; TPA errado escalado → NULIDADE do engajamento)
- **D4 — Risco político:** o OGMO pode negar, adiar ou boicotar. Em Santos, a entrada da Escala Digital foi precedida de **greve de estivadores** e **liminar do TRT**. É um campo minado
- **D5 — Recife e Suape têm sistemas diferentes** (EscalaNet vs TPA) — a gestão é fragmentada
- **D6 — Sem visão pro trabalhador:** o TPA não sabe se está escalado, não recebe comunicado, não tem canal
- **D7 — Sem BI/dashboard:** presidente/diretoria do Sindicato não tem dados consolidados pra negociar CCT, fiscalizar operação, cobrar do OGMO
- **D8 — Continuidade de negócio:** se o Fiscal do Sindicato faltar (greve, doença), ninguém sabe operar a lousa

### 2.3 A dor do OGMO (que pouca gente enxerga)

O OGMO **também sofre**. Ele é auditado pela ANTAQ, controlado pelo MPT, e precisa cumprir a Lei 9.719/98 art. 5º §1º ("escalação por meio eletrônico, inviolável e tecnicamente seguro") e §3º ("vedada a escalação presencial"). Eles **têm obrigação legal** de ter sistema digital e **também querem** uma interface melhor. Hoje eles usam TPA (legado) e o site é lento, sem API documentada, sem HTTPS, sem mobile. **A Suporte Gerencial tem uma janela de venda B2B aqui.**

---

## 3. Restrições Legais (o que NÃO pode)

| ❌ Não pode | Por quê |
|---|---|
| Sindicato **escalar** TPAs (rodízio numérico oficial) | Lei 8.630/93 art. 18, Lei 12.815/13 art. 32, Lei 9.719/98 art. 5º — prerrogativa **exclusiva** do OGMO. TST: "qualquer interpretação que permita a escalação dos trabalhadores avulsos diretamente pelos sindicatos representa retrocesso". |
| Sindicato **cadastrar/registrar** TPA | Idem — exclusividade do OGMO. |
| Sindicato **arrecadar** remuneração do TPA e repassar | Idem — art. 18, VII. |
| Sistema próprio substituir a Lousa oficial do OGMO | Viola Lei 9.719/98 art. 5º e gera NULIDADE dos engajamentos. |
| Exigir exclusividade de TPA no cadastro do Sindicato para trabalhar | Viola art. 40, §2º da Lei 12.815/13 (exclusividade é do OGMO). |

| ✅ Pode | Base legal / Como |
|---|---|
| Sindicato **fiscalizar** a operação portuária e reportar ao OGMO | Convenção 137 OIT, Recomendação 145, art. 8º da Lei 8.630/93 |
| Sindicato **fazer gestão interna** do seu quadro de associados | Liberdade associativa (art. 8º CF/88) + CCT |
| Sindicato **construir sistema próprio** que **replica** a lousa (consulta) e **notifica** o OGMO (push) | Lei 9.719/98 art. 5º §2º ("meio eletrônico inviolável e seguro") + CCT |
| Sindicato **criar canal de comunicação** com TPA (app/PWA/SMS/WhatsApp) | Liberdade de comunicação; LGPD exige consentimento |
| Sindicato **construir BI/dashboard** de operação | Idem |
| Sindicato **negociar API/webhook** com OGMO | Acordo operacional bilateral (não viola monopólio) |
| Sindicato **oferecer a solução ao OGMO** como serviço (B2B) | Livre iniciativa, desde que a escalação **oficial** continue sendo do OGMO |

---

## 4. As 3 Opções (A / B / C)

### Opção A — "Espelho Inteligente" ⭐ RECOMENDADA PARA O MVP

**O que é:** o Sindicato constrói um sistema que **replica** a lousa do OGMO, **complementa** com dados próprios (nome, matrícula, presença), e **envia notificação** pro OGMO quando há remanejamento (via webhook, e-mail auditável, ou, na melhor das hipóteses, API se OGMO topar).

**Funcionalidades:**
1. **Lousa espelhada em tempo real** (raspagem/integração com TPA + entrada manual) — Recife E Suape, 2 turnos, 26 funções × 10 fainas
2. **Remanejamento digital** com motivo, autor, timestamp, base legal (qual artigo da CCT autorizou)
3. **Push pro OGMO** (3 caminhos: webhook → app deles / e-mail com PDF assinado / integração humana via painel de "pendências OGMO")
4. **Histórico auditável** de tudo (quem remanejou, quando, por quê, hash de integridade)
5. **Listagem de turno espelhada** (Nome/Matrícula/Função/Cais/Navio)
6. **Mapa de calor de remanejamentos** (quais funções/cais dão mais problema — base pra negociação de CCT)
7. **BI para diretoria do Sindicato** (KPIs: % comparecimento, % remanejamentos por turno, ranking de TPAs, custo de remanejamento)

**Stack sugerida (reaproveitando padrão Becker/Suporte Gerencial):**
- Next.js + TS + Tailwind (front)
- FastAPI + Postgres (back) — multi-tenant já preparado se virar B2B
- PWA mobile-first (funciona offline pro Fiscal no cais)
- WebSocket pro push real-time
- Integração inicial: scraping do TPA (robusto contra mudança de layout) → upgrade pra API quando OGMO topar
- LGPD: retenção 24m de logs de remanejamento, consentimento explícito dos TPAs associados

**Investimento:**
- 1 dev full-time (você) por **10-12 semanas**
- Infra: R$ 200-400/mês (VPS Hetzner + Postgres + Redis)
- Custo de equipe: zero (você mesmo)
- **Total cash: ~R$ 5-8k no ano 1** (só infra)

**Prós:**
- ✅ Resolve a dor central (status online + notificação ao OGMO)
- ✅ Juridicamente seguro (sindicato pode construir sistema próprio, desde que não substitua a escalação oficial)
- ✅ Reaproveita o **exato mesmo stack** que você já domina (Becker, Córtex, Sinapse, FaceGate)
- ✅ Gera base de dados que vira arma política (CCT, fiscalização, MPT)
- ✅ Pode evoluir pra Opção B (Hub B2B) sem refazer
- ✅ Diferencial competitivo real: **nenhum Sindicato do Brasil tem isso hoje**

**Contras:**
- ⚠️ Risco de o OGMO receber notificação e ignorar (depende da governança)
- ⚠️ Scraping do TPA é frágil (eles podem mudar layout a qualquer momento)
- ⚠️ Resistência política do OGMO (vão ver como ameaça)
- ⚠️ Você vai ser o "João de Barro" do OGMO — se a TPA Tecnologia fechar com OGMO um upgrade, sua integração quebra

**Timeline:** MVP em 8-10 semanas, produção em 12 semanas.

**Quem precisa ser convencido:**
- Presidente Josias Santiago (interno) — fácil, é o cliente
- TI do OGMO/PE (TPA Tecnologia, parece fornecedor) — difícil
- Operadores Portuários (SINDOPE) — irrelevante no MVP
- ANTAQ / MPT — só no roadmap (Opção B)

---

### Opção B — "Hub B2B Oficial" (ROADMAP 12-18 MESES)

**O que é:** Sindicato negocia com OGMO/PE e Operadores Portuários a construção **conjunta** de um sistema único, com **API oficial bidirecional**, em que:
- OGMO mantém a escalação oficial (não abre mão)
- Sindicato opera o remanejamento, presença, comunicação
- Operadores consultam requisições
- Tudo auditável pela ANTAQ e MPT

**Funcionalidades (acima da Opção A):**
- API REST oficial OGMO ↔ Sindicato (OAuth 2.0 + mTLS)
- Webhook assinado (HMAC-SHA256) pra remanejamentos
- BI compartilhado tripartite
- App único com 3 níveis de acesso (OGMO, Sindicato, Operador)
- Painel ANTAQ/MPT (acesso leitura, log de tudo)
- Termo de Ajustamento de Conduta (TAC) com MPT (modelo Rio Grande) — blindagem jurídica

**Stack:** mesma da Opção A, mais API Gateway (Kong ou Tyk), assinatura digital ICP-Brasil, cofre de chaves.

**Investimento:**
- 1 dev full-time por **6-9 meses adicionais** (depois do MVP da Opção A)
- 1 PO dedicado (você, meio período)
- Custo de integração: viagens Recife ↔ Suape ↔ Brasília (ANTAQ) ~R$ 5-10k
- Assessoria jurídica para CCT/TAC: R$ 15-30k
- **Total cash: ~R$ 50-80k no ano 2**

**Prós:**
- ✅ Solução definitiva, oficial, juridicamente blindada
- ✅ Receita recorrente possível (Operadores pagam pelo sistema)
- ✅ Posiciona a Suporte Gerencial como referência nacional em port-tech
- ✅ Caso de uso replicável pra outros 25 OGMOs do Brasil
- ✅ Convocação por MPT vira aliada (eles QUEREM isso — vide OGMO-RG)

**Contras:**
- ⚠️ Depende de **3 stakeholders** (OGMO, Operadores, MPT) — risco político altíssimo
- ⚠️ OGMO pode ter fornecedor de TI (TPA Tecnologia) com contrato exclusivo
- ⚠️ Demora 12-18 meses pra assinar TAC e começar
- ⚠️ Pode ser que o OGMO diga "não" — e você gastou dinheiro à toa
- ⚠️ Conflito de interesse potencial (você fornece pra Sindicato e OGMO)

**Timeline:** 12-18 meses até operação, mais 6-12 meses até tração comercial.

**Quem precisa ser convencido:** OGMO (Luís/Marcos — direção), Operadores (SINDOPE), MPT-PE, ANTAQ.

---

### Opção C — "PWA do Trabalhador" (MVP RÁPIDO, 6-8 SEMANAS)

**O que é:** Sindicato cria um **PWA mobile-first** (instalável no celular) pro TPA ver: minha escala de hoje, próxima chamada, histórico, comunicados, presença, e **botão de WhatsApp** pro Fiscal. Não toca na lousa oficial.

**Funcionalidades:**
1. Login com CPF + matrícula OGMO
2. "Minha escala hoje" — puxa do TPA (mesma raspagem)
3. "Minha próxima chamada" — countdown
4. Comunicados do Sindicato (push notification)
5. Botão "Estou no porto" / "Não vou" (registra intenção, não vincula)
6. FAQ, contato, CCT em PDF
7. Mapa do cais (qual navio, qual cais)
8. Canal direto com Fiscal (WhatsApp deep link)

**Stack:** Next.js PWA, IndexedDB pra offline, mesma infra.

**Investimento:**
- 1 dev **6-8 semanas**
- Infra: R$ 100-200/mês
- **Total cash: ~R$ 2-3k no ano 1**

**Prós:**
- ✅ Risco legal zero (só consulta e comunicação)
- ✅ Resolve 30% da dor (a do TRABALHADOR, não do Sindicato)
- ✅ Excelente pra testar aderência antes de partir pra A ou B
- ✅ Pode virar **braço de comunicação de campanha** do Sindicato (filiação, mobilização)

**Contras:**
- ❌ **Não resolve a dor central** que você descreveu (remanejamento → OGMO)
- ❌ Não tem status online da lousa
- ❌ Não notifica OGMO
- ❌ Pode ser visto pelo OGMO como "invasão" (estão coletando dados dos TPAs sem acordo)

**Timeline:** MVP em 4-6 semanas, produção em 6-8 semanas.

---

## 5. Comparativo das 3 Opções

| Critério | A — Espelho | B — Hub B2B | C — PWA TPA |
|---|---|---|---|
| Resolve a dor central | ✅ Sim | ✅ Sim (definitivo) | ⚠️ Parcial |
| Tempo até MVP | 8-12 sem | 12-18 meses | 4-8 sem |
| Custo total ano 1 | R$ 5-8k | R$ 50-80k | R$ 2-3k |
| Risco legal | Baixo | Médio (depende de TAC) | Zero |
| Risco político | Médio | Alto | Baixo |
| Risco técnico | Baixo (stack conhecido) | Médio (integração tripartite) | Baixo |
| Receita recorrente possível | Baixa | Alta | Baixa |
| Diferenciação Suporte Gerencial | Alta | Altíssima | Média |
| Reaproveita stack Becker/Córtex | 100% | 100% | 100% |
| Dependência de terceiros | TPA Tecnologia (raspagem) | OGMO, Operadores, MPT | TPA Tecnologia |
| Bloqueio se der errado | 1-2 meses | 6+ meses | 1-2 semanas |

---

## 6. MVP Recomendado: A + C combinadas (Fase 1)

**Estratégia:** Construir A (Espelho) e C (PWA) **em paralelo**, mas com módulos compartilhados.

### Fase 1 — Sprint 1-4 (8 semanas): C primeiro (rápido), A em paralelo

**Sprint 1-2 (sem 1-2): Fundação compartilhada**
- Setup monorepo (Turborepo) — mesmo padrão Becker/Córtex
- Backend FastAPI + Postgres + Redis
- Módulo de scraping TPA/OGMO (parser tolerante a mudança de layout, v1.24.0)
- Módulo de scraping EscalaNet (Recife)
- Auth (CPF + matrícula OGMO) + RBAC (TPA, Fiscal, Dirigente, Admin)
- LGPD: consentimento, retenção 24m, direito ao esquecimento

**Sprint 3-4 (sem 3-4): PWA do Trabalhador (C)**
- Front Next.js PWA (offline-first, instalável)
- Telas: Login, Minha Escala Hoje, Próxima Chamada, Comunicados, Botão Presença, FAQ
- Push notification (Firebase Cloud Messaging)
- Deep link WhatsApp pro Fiscal
- Deploy em VPS self-hosted (mesmo padrão dos outros projetos)

**Sprint 5-8 (sem 5-8): Espelho do Sindicato (A)**
- Lousa espelhada (visualização das 26 colunas × 10 fainas × 2 turnos × 2 portos)
- Remanejamento digital (modal com motivo + base legal + log)
- Push pro OGMO (3 caminhos: webhook, e-mail, painel)
- Dashboard do Fiscal
- BI básico pra diretoria
- Auditoria com hash chain

**Critérios de aceite do MVP (definição de "pronto"):**
- ✅ Fiscal acessa a lousa espelhada de Recife e Suape no celular
- ✅ Fiscal remaneja 1 TPA com 1 motivo em < 30 segundos
- ✅ OGMO recebe notificação por e-mail com PDF assinado em < 2 min
- ✅ TPA vê sua escala no PWA sem precisar ir ao porto
- ✅ 100% das ações auditáveis (quem, quando, por quê, hash)
- ✅ LGPD: TPA pode pedir exclusão e o sistema cumpre em 15 dias
- ✅ Suite de testes: 200+ testes (padrão dos seus outros projetos)
- ✅ Documentado: manual do Fiscal, manual do TPA, manual do OGMO

### Fase 2 — Sprint 9-12 (sem 9-12, meses 3-4): Polimento + Apresentação

- Apresentar resultado ao OGMO (proposta de Opção B)
- Apresentar resultado ao MPT-PE (alicerce pro TAC)
- Apresentar resultado aos Operadores (SINDOPE)
- Onboarding de fiscais (treinamento 1:1, vídeo-aulas)
- Campanha de instalação do PWA com os TPAs
- Ajustes de UX baseados em uso real

### Fase 3 — Sprint 13+ (meses 4-12): Roadmap

- **Fase 3a (mês 4-6):** Integração bidirecional com WhatsApp Business (confirmação de presença, remanejamento)
- **Fase 3b (mês 6-9):** BI avançado + relatórios pra CCT
- **Fase 3c (mês 9-12):** Migração pra modelo B (B2B) com API oficial
- **Fase 3d (mês 12+):** Expansão pra outros OGMOs (Itajaí, Paranaguá, Vitória, Manaus)

---

## 7. Riscos e Mitigações

| Risco | Probabilidade | Impacto | Mitigação |
|---|---|---|---|
| OGMO/PE boicota a integração | Alta | Alto | A entrega via e-mail + painel é unilateral; não precisa de aprovação deles. Perseguir B só depois de ter dados de uso real |
| TPA Tecnologia troca layout do site | Média | Médio | Parser tolerante + alertas de mudança + scraper com retry/backoff |
| TPA processo o Sindicato por coletar dados | Baixa | Alto | LGPD compliance + consentimento explícito + DPO (pode ser você mesmo) |
| MPT-PE vê como invasão de prerrogativa do OGMO | Baixa | Alto | Documentação desde o dia 1: deixar claro que **não escala**; **replica e notifica**. Carta formal ao MPT no mês 1 |
| Resistência interna (fiscais não adotam) | Média | Alto | Onboarding 1:1, vídeo de 3min, "primeira vitória" em 7 dias. Fiscal como co-designer |
| Presidente Josias muda de ideia | Baixa | Alto | **Apresentar este documento e travar alinhamento antes de codar 1 linha** |
| Falta de tempo do Paulo (você) | Média | Alto | **Fase 1 em 8 sem, não 12**. Cuidar do escopo. Dizer NÃO a features que não estão no MVP |
| Córtex/Becker/FaceGate/Sinapse competem por tempo | Alta | Alto | Regra: este projeto **só anda nos primeiros 90 dias**. Depois volta pra fila |
| Fornecedor de TI do OGMO (TPA Tecnologia) processa por concorrência desleal | Baixa | Médio | Solução **do Sindicato, em favor do Sindicato**, não comercializa sem acordo. Livre concorrência |

---

## 8. Por que isso é uma boa ideia para a Suporte Gerencial

- **Blue ocean nacional:** NENHUM Sindicato de Estivadores do Brasil tem um sistema próprio digital. OGMO Santos tem (mas é do OGMO). A Suporte Gerencial entra num mercado **vazio**.
- **Replicável:** OGMO-RG, OGMO-Itajaí, OGMO-Paranaguá, OGMO-Vitória, OGMO-Manaus, OGMO-Rio, OGMO-Salvador, OGMO-Fortaleza, OGMO-Belém, OGMO-São Luís, OGMO-Maceió… **25+ OGMOs no Brasil**, todos com o mesmo problema, todos com um Sindicato parceiro.
- **Caso de referência:** se o SINDESTIVA-PE virar case de sucesso, abre porta pra **5+ novos contratos** em 18 meses.
- **Padrão Becker/Córtex reaproveitado:** 100% do stack que você já domina. Sem curva de aprendizado. Sua velocidade de entrega é o diferencial.
- **Missão do Suporte Gerencial:** resolver problemas de gestão pública/portuária/sindical. Isso é EXATAMENTE o core.

---

## 9. Próximos passos (a fazer AGORA, antes da próxima reunião)

1. **Marcar 2ª reunião com Josias Santiago** (SINDESTIVA-PE) — alinhar este plano, travar escopo do MVP
2. **Pedir acesso/contato do TI do OGMO/PE** (provavelmente alguém da TPA Tecnologia) — pra mapear viabilidade de scraping/integração
3. **Pedir ao SINDESTIVA a CCT atual** (Convenção Coletiva de Trabalho 2024-2026) — base pra regras de remanejamento
4. **Visitar fisicamente o Porto de Suape** (1 turno) com o Fiscal — capturar fotos, entender a dinâmica, identificar casos de uso reais
5. **Definir o "gatekeeper" do projeto** no Sindicato (quem aprova mudanças, quem opera o sistema, quem fala com OGMO)
6. **Sprint 0 (1 semana, antes da Fase 1):** validar LGPD, levantar números reais (quantos TPAs, quantos fiscais, quantos turnos/dia, volume de remanejamentos)
7. **Trazer o MPT-PE pra dentro cedo** (reunião de apresentação, sem pedir nada — só mostrar a intenção)

---

## 10. Perguntas em aberto (pra fechar na próxima reunião com Josias)

1. **Quem opera a lousa hoje no cais?** (1 fiscal por turno? Mais? Quem?)
2. **Quantos TPAs o SINDESTIVA representa em Recife + Suape?**
3. **Qual o volume médio de remanejamentos por turno/dia?**
4. **Existe TI no Sindicato hoje?** (alguém mantém site? banco de dados?)
5. **Qual o orçamento disponível** (ou é projeto "investimento da Suporte Gerencial com retorno futuro")?
6. **O SINDESTIVA tem estatutariamente permissão de construir/explorar tecnologia?** (precisa ver o estatuto)
7. **Qual a relação política atual com o OGMO/PE** (parceiro, neutro, conflito)?
8. **Existe algum contato com TPA Tecnologia** (fornecedor do OGMO)?
9. **Qual o prazo de eleição do Sindicato** (impacta janela de decisão)?
10. **O SINDESTIVA quer só o software ou quer virar um produto (revender pra outros Sindicatos)?**

---

## 11. Stack e padrão técnico (referência rápida)

Reaproveitando **exatamente** o padrão dos seus outros projetos:

| Camada | Stack | Projeto de referência |
|---|---|---|
| Monorepo | Turborepo | Córtex |
| Front | Next.js + TS + Tailwind + shadcn | Córtex / Becker |
| Back | FastAPI + SQLAlchemy + Pydantic | Sinapse / FaceGate |
| DB | PostgreSQL multi-tenant (se B2B) ou simples | Sinapse |
| Auth | NextAuth + JWT + RBAC | Córtex |
| Mobile | PWA (mesma base Next) | — |
| Push | Firebase Cloud Messaging | — |
| Scraping | Playwright + BeautifulSoup (com fallback HTTPX) | — |
| Real-time | WebSocket (FastAPI nativo) | — |
| Infra | VPS Hetzner self-hosted (mesmo do Becker/Suape) | Becker |
| CI | GitHub Actions | Todos |
| LGPD | Mesmo padrão FaceGate (12m retenção, SHA-256) | FaceGate |
| Mensageria | WhatsApp Business via Evolution API | Córtex |
| Pagamento (se virar B2B) | Mercado Pago | Becker |

---

## 12. Disclaimer jurídico

> Este documento é uma **análise técnica e operacional**. **Não é parecer jurídico.** Antes de iniciar a Fase 1, é recomendável 1 reunião com advogado trabalhista (especialmente em CCT de portos) para validar que a solução **do Sindicato, que replica a lousa do OGMO e notifica o OGMO**, está dentro da legalidade. Custo estimado: R$ 2-5k por uma opinião formal escrita. Recomendação: **Cristiano Oliveira** (tributarista) ou **Nathalia Santos** (trabalhista), se for da rede do Paulo. Caso contrário, OAB-PE seção de direito do trabalho.

---

*Documento gerado por Mavis em 12/08/2026. Próxima revisão: pós-reunião com Josias Santiago.*
