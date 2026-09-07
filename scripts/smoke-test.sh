#!/usr/bin/env bash
# =============================================================================
# SINDESTIVA-PE · Smoke test completo (Caminho B — sem setup local)
#
# Roda contra a **API de produção** em https://api.lousa.pscode.ia.br.
# Cobre TODOS os fluxos: auth, scraping, lousa, BI, LGPD, admin, WhatsApp.
#
# Uso:
#   bash scripts/smoke-test.sh           # roda tudo
#   bash scripts/smoke-test.sh rapido    # só health + scraping status
#
# Requisitos: bash 3.2+, curl, python3 (para parsing de JSON).
# =============================================================================
set -u

# ---- Configuração ------------------------------------------------------------

API="${API:-https://api.lousa.pscode.ia.br}"
ADMIN_TOKEN="${ADMIN_TOKEN:-sindestiva-admin-ibVauR6mAaw26kw6D2BcPNhJmyxfsyX7}"
PAULO_EMAIL="paulo@pscode.ia.br"
MANOEL_EMAIL="manoel@sindestiva-pe.com.br"
PASSWORD="sindestiva-dev-2026"
NUMERO_TESTE="5581999990001"

# ---- Cores ------------------------------------------------------------------

GREEN="\033[0;32m"
RED="\033[0;31m"
YELLOW="\033[0;33m"
CYAN="\033[0;36m"
BOLD="\033[1m"
RESET="\033[0m"

PASS=0
FAIL=0

# ---- Helpers ----------------------------------------------------------------

hr()    { printf "${CYAN}${BOLD}%s${RESET}\n" "────────────────────────────────────────────────────────────"; }
title() { echo; hr; printf "${BOLD}▶ %s${RESET}\n" "$1"; hr; }
ok()    { printf "${GREEN}✅ %s${RESET}\n" "$1"; PASS=$((PASS+1)); }
bad()   { printf "${RED}❌ %s${RESET}\n" "$1"; FAIL=$((FAIL+1)); }

# http_get <path> [token]
http_get() {
  local path="$1" token="${2:-}"
  local args=(-sS --max-time 30)
  [ -n "$token" ] && args+=(-H "Authorization: Bearer $token")
  args+=("$API$path")
  curl "${args[@]}"
}

# http_post <path> <body_or_empty> [jwt_token]
http_post() {
  local path="$1" data="$2" token="${3:-}"
  local args=(-sS --max-time 30 -X POST -H "Content-Type: application/json")
  [ -n "$token" ] && args+=(-H "Authorization: Bearer $token")
  [ -n "$data" ] && args+=(--data-raw "$data")
  args+=("$API$path")
  curl "${args[@]}"
}

# admin_post <path> [body_or_empty] [admin_token]
# Envia X-Admin-Token em vez de Authorization (rotas /admin/* usam este header).
admin_post() {
  local path="$1" data="${2:-}" token="${3:-$ADMIN_TOKEN}"
  local args=(-sS --max-time 30 -X POST -H "Content-Type: application/json" -H "X-Admin-Token: $token")
  [ -n "$data" ] && args+=(--data-raw "$data")
  args+=("$API$path")
  curl "${args[@]}"
}

# admin_get <path> [admin_token]
admin_get() {
  local path="$1" token="${2:-$ADMIN_TOKEN}"
  curl -sS --max-time 30 -H "X-Admin-Token: $token" "$API$path"
}

# status <method> <path> [body] [token] [auth_header_name]
status() {
  local method="$1" path="$2" data="${3:-}" token="${4:-}" header="${5:-Authorization}"
  local args=(-sS --max-time 30 -o /dev/null -w "%{http_code}" -X "$method" -H "Content-Type: application/json")
  [ -n "$token" ] && args+=(-H "${header}: Bearer $token")
  [ -n "$data" ] && args+=(--data-raw "$data")
  args+=("$API$path")
  curl "${args[@]}"
}

# status <method> <path> [body] [token]
status() {
  local method="$1" path="$2" data="${3:-}" token="${4:-}"
  local args=(-sS --max-time 30 -o /dev/null -w "%{http_code}" -X "$method" -H "Content-Type: application/json")
  [ -n "$token" ] && args+=(-H "Authorization: Bearer $token")
  [ -n "$data" ] && args+=(--data-raw "$data")
  args+=("$API$path")
  curl "${args[@]}"
}

# jget <chave1.chave2> <json>
jget() {
  python3 -c "
import sys, json
try:
    d = json.loads(sys.argv[2] or '{}')
    for k in sys.argv[1].split('.'):
        if isinstance(d, list):
            d = d[0] if d else None
        if not isinstance(d, dict):
            d = None
            break
        d = d.get(k)
    print(d if d is not None and d != '' else '(vazio)')
except Exception as e:
    print(f'(erro parse: {e})')
" "$1" "$2"
}

# check <nome> <esperado> <atual>
check() {
  if [ "$3" = "$2" ]; then
    ok "$1  ($3)"
  else
    bad "$1  esperado=$2  atual=$3"
  fi
}

# ---- Modo rápido -------------------------------------------------------------

if [ "${1:-}" = "rapido" ]; then
  title "MODO RÁPIDO (health + scraping)"
  check "API /health"           "200" "$(status GET /health)"
  check "API /api/v1/health"    "200" "$(status GET /api/v1/health)"
  check "Docs Swagger"          "200" "$(status GET /docs)"
  out=$(http_get "/api/v1/scraping/status?limit=5")
  echo "  scraping: total=$(jget total "$out") sucessos=$(jget sucessos "$out") falhas=$(jget falhas "$out")"
  exit 0
fi

# ---- 1. HEALTH + DB ---------------------------------------------------------

title "1. HEALTH + DB"
check "GET /health"        "200" "$(status GET /health)"
check "GET /api/v1/health" "200" "$(status GET /api/v1/health)"
check "GET /docs"          "200" "$(status GET /docs)"
check "GET /openapi.json"  "200" "$(status GET /openapi.json)"
out=$(http_get /api/v1/health)
check "DB status" "ok" "$(jget db "$out")"

# ---- 2. ADMIN · DEBUG ENV ---------------------------------------------------

title "2. ADMIN · DEBUG ENV (GET)"
out=$(admin_get /api/v1/admin/debug/env)
echo "$out" | python3 -m json.tool 2>/dev/null || echo "$out"
check "evolution_api_key_set" "True"  "$(jget evolution_api_key_set "$out")"
check "nextauth_secret_set"    "True"  "$(jget nextauth_secret_set "$out")"
check "resend_api_key_set"     "False" "$(jget resend_api_key_set "$out")"
check "ogmo_webhook_url_set"   "False" "$(jget ogmo_webhook_url_set "$out")"

# ---- 3. AUTH · LOGIN --------------------------------------------------------

title "3. AUTH · LOGIN"
login_paulo_body="{\"email\":\"$PAULO_EMAIL\",\"password\":\"$PASSWORD\"}"
out=$(http_post /api/v1/auth/login "$login_paulo_body")
PAULO_TOKEN=$(jget access_token "$out")
check "Login Paulo · role"  "DIRIGENTE" "$(jget user.role "$out")"
check "POST /auth/login Paulo" "200"     "$(status POST /api/v1/auth/login "$login_paulo_body")"

login_manoel_body="{\"email\":\"$MANOEL_EMAIL\",\"password\":\"$PASSWORD\"}"
out=$(http_post /api/v1/auth/login "$login_manoel_body")
MANOEL_TOKEN=$(jget access_token "$out")
check "Login Manoel · role" "FISCAL" "$(jget user.role "$out")"

# Senha errada → 401 (corpo em variável p/ evitar escape gymnastics)
bad_body=$(printf '{"email":"%s","password":"errada"}' "$PAULO_EMAIL")
check "Login inválido · 401"  "401" "$(status POST /api/v1/auth/login "$bad_body")"

# Sem body → 422
check "Login sem body · 422" "422" "$(status POST /api/v1/auth/login "")"

[ -n "$PAULO_TOKEN" ] || { echo "ERRO: token Paulo vazio"; exit 1; }

# ---- 4. PÚBLICOS · LOUSA + LGPD ---------------------------------------------

title "4. PÚBLICOS · LOUSA + LGPD"
check "Lousa preview SUAPE"   "200" "$(status GET /api/v1/lousa/public/preview)"
check "Lousa preview RECIFE"  "200" "$(status GET /api/v1/lousa/public/preview)"
check "TPA-001 escala"        "200" "$(status GET /api/v1/lousa/public/tpa/TPA-001/escala)"
check "TPA-002 escala"        "200" "$(status GET /api/v1/lousa/public/tpa/TPA-002/escala)"
check "Matrícula inexistente · 404"  "404" "$(status GET /api/v1/lousa/public/tpa/INEXISTENTE/escala)"
check "LGPD termo texto · 200"       "200" "$(status GET /api/v1/lgpd/termo-consentimento/texto)"

out=$(http_get /api/v1/lousa/public/preview)
echo "  preview: $(echo "$out" | python3 -c "import sys,json; d=json.load(sys.stdin); print(f'cells={len(d.get(\"cells\",[]))} fainas={len(d.get(\"fainas\",[]))} funcoes={len(d.get(\"funcoes\",[]))} total_tpas_escalados={d.get(\"stats\",{}).get(\"total_tpas_escalados\",0)}')")"

# ---- 5. PROTEGIDOS · 401 SEM TOKEN -------------------------------------------

title "5. PROTEGIDOS · 401 SEM TOKEN"
check "Remanejamentos"     "401" "$(status GET /api/v1/remanejamentos)"
check "Auditoria"          "401" "$(status GET /api/v1/auditoria/eventos)"
check "BI KPIs"            "401" "$(status GET /api/v1/bi/kpis)"
check "DPO checkpoints"    "401" "$(status GET /api/v1/dpo/hash-chain-checkpoints)"
check "DPO access log"     "401" "$(status GET /api/v1/dpo/access-log)"
check "LGPD solicitacao"   "401" "$(status POST /api/v1/lgpd/solicitacoes '{"tipo":"EXCLUSAO"}')"

title "6. PROTEGIDOS · 200 COM TOKEN"
check "Remanejamentos"     "200" "$(status GET /api/v1/remanejamentos "" "$PAULO_TOKEN")"
check "Auditoria"          "200" "$(status GET /api/v1/auditoria/eventos "" "$PAULO_TOKEN")"
check "BI KPIs"            "200" "$(status GET /api/v1/bi/kpis "" "$PAULO_TOKEN")"
check "BI top cards"       "200" "$(status GET /api/v1/bi/top-cards "" "$PAULO_TOKEN")"
check "BI insights"        "200" "$(status GET /api/v1/bi/insights "" "$PAULO_TOKEN")"
check "DPO checkpoints"    "200" "$(status GET /api/v1/dpo/hash-chain-checkpoints "" "$PAULO_TOKEN")"

# ---- 7. SCRAPING STATUS ----------------------------------------------------

title "7. SCRAPING STATUS"
out=$(http_get "/api/v1/scraping/status?limit=10")
echo "$out" | python3 -c "
import sys, json
d = json.load(sys.stdin)
print(f'  total={d[\"total\"]} sucessos={d[\"sucessos\"]} falhas={d[\"falhas\"]}')
for i in d['itens'][:5]:
  err = i.get('erro_detalhes') or ''
  if err and 'Name or service' not in err:
    err = ' · ' + err[:60]
  print(f'  {i[\"fonte\"]:10} {i[\"status\"]:14} cells={i[\"total_celulas\"]:4}{err}')
"

title "8. SCRAPING · TRIGGER (4 combinações válidas)"
for fonte in TPA ESCALANET; do
  for turno in DIURNO NOTURNO; do
    for porto in SUAPE RECIFE; do
      # Pula combinações inválidas
      if [ "$fonte" = "TPA" ] && [ "$porto" = "RECIFE" ]; then continue; fi
      if [ "$fonte" = "ESCALANET" ] && [ "$porto" = "SUAPE" ]; then continue; fi
      body="{\"fonte\":\"$fonte\",\"porto\":\"$porto\",\"turno\":\"$turno\"}"
      out=$(http_post /api/v1/scraping/disparar "$body")
      stat=$(jget status "$out")
      cells=$(jget total_celulas "$out")
      check "scrape $fonte $porto $turno" "SUCESSO" "$stat"
      echo "    cells=$cells"
    done
  done
done

# ---- 9. WHATSAPP END-TO-END -----------------------------------------------

title "9. WHATSAPP · TEST END-TO-END"
out=$(admin_post /api/v1/admin/test-whatsapp "")
success=$(jget success "$out")
provider=$(jget provider_id "$out")
remotejid=$(jget "raw.key.remoteJid" "$out")
erro=$(jget error "$out")
check "WhatsApp · success" "True" "$success"
echo "  provider_id: $provider"
echo "  remoteJid:   $remotejid"
[ "$success" = "True" ] && ok "MSG WhatsApp ENVIADA pra $NUMERO_TESTE" \
                          || bad "Falhou: $erro"

# ---- 10. HASH CHAIN ---------------------------------------------------------

title "10. AUDITORIA · HASH CHAIN"
out=$(http_post /api/v1/auditoria/verificar-hash-chain "" "$PAULO_TOKEN")
check "Hash chain íntegro" "True" "$(jget integro "$out")"
echo "  total_eventos: $(jget total_eventos "$out")"
echo "  duracao_ms:    $(jget duracao_ms "$out")"

# ---- 11. LGPD CONSENTIMENTO -------------------------------------------------

title "11. LGPD · TERMO"
out=$(http_get /api/v1/lgpd/termo-consentimento/texto)
echo "  versão: $(jget versao "$out")"
echo "  hash:  $(jget texto_hash_sha256 "$out" | head -c 16)..."
# Sem TPA autenticado, esperar 401
out=$(http_post /api/v1/lgpd/termo-consentimento/aceitar '{"versao":"1.0","aceito":true}')
check "Aceitar termo s/ TPA · 401" "401" "$(status POST /api/v1/lgpd/termo-consentimento/aceitar '{"versao":"1.0","aceito":true}')"

# ---- 12. BI ----------------------------------------------------------------

title "12. BI · KPIs (30d)"
out=$(http_get "/api/v1/bi/kpis?periodo_dias=30" "$PAULO_TOKEN")
echo "$out" | python3 -c "
import sys, json
d = json.load(sys.stdin)
c = d['comparecimento']
f = d['folha_paga']
p = d['percentual_nack']
print(f'  comparecimento: {c[\"total_confirmados\"]}/{c[\"total_escalados\"]} ({c[\"percentual\"]:.1f}%)')
print(f'  folha:          R\$ {f[\"valor_total_brl\"]:.2f} ({f[\"total_remanejamentos\"]} remanejamentos)')
print(f'  NACK:           {p[\"total_nack\"]}/{p[\"total_notificados\"]} ({p[\"percentual\"]:.1f}%)')
"

# Remanejamentos por dia
out=$(http_get "/api/v1/bi/remanejamentos-por-dia?periodo_dias=30" "$PAULO_TOKEN")
echo "  remanejamentos/dia: $(jget total "$out") total · média/dia: $(jget media_diaria "$out")"

# Top remanejados
out=$(http_get "/api/v1/bi/top-remanejados?n=5&periodo_dias=30" "$PAULO_TOKEN")
top_count=$(python3 -c "
import sys, json
try:
    d = json.loads('''$out''')
    items = d.get('items', [])
    print(len(items))
    if items:
        top = items[0]
        print(f'    1º: {top.get(\"tpa_nome\",\"?\")} ({top.get(\"tpa_matricula\",\"?\")}) — {top.get(\"total_remanejamentos\",0)} rem.')
except Exception:
    print(0)
" 2>&1 | head -1)
echo "  top remanejados: $top_count TPA(s)"

# ---- 13. RESUMO -----------------------------------------------------------

title "13. RESUMO"
printf "${BOLD}Resultado: %d ok · %d falhas${RESET}\n" "$PASS" "$FAIL"
hr
if [ "$FAIL" -eq 0 ]; then
  ok "TUDO PASSOU"
else
  bad "$FAIL TESTE(S) FALHARAM — revise acima"
  exit 1
fi
echo
echo "Para detalhes do admin/whatsapp, abra o Swagger:"
echo "  ${API}/docs"
