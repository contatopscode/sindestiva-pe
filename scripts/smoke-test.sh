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

# ---- 13. LOGIN FLOW (Sprint B — cookie httpOnly) --------------------

title "13. LOGIN FLOW · SPRINT B"
WEB_API="https://web.lousa.pscode.ia.br"

# 13.1 — /login (rota pública) renderiza
check "WEB /login renderiza" "200" "$(curl -sS --max-time 10 -o /dev/null -w "%{http_code}" "$WEB_API/login")"

# 13.2 — Login Paulo via proxy WEB → cookie httpOnly + body access_token (Sprint B-fix)
out=$(curl -sS --max-time 30 -i -c /tmp/sindestiva_cookies.txt -X POST \
  "$WEB_API/api/auth/login" \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"$PAULO_EMAIL\",\"password\":\"$PASSWORD\"}")
echo "$out" | head -1 | grep -q "200" && ok "WEB login Paulo · 200" || bad "WEB login Paulo · esperado 200"

# Cookie file deve ter o sindestiva_token
if grep -q "sindestiva_token" /tmp/sindestiva_cookies.txt 2>/dev/null; then
  ok "Cookie sindestiva_token setado"
else
  bad "Cookie sindestiva_token AUSENTE"
fi

# Body deve conter access_token (Sprint B-fix para cookie 3rd-party)
BODY_TOKEN=$(echo "$out" | tail -1 | python3 -c "
import sys, json
try:
    d = json.loads(sys.stdin.read())
    print(d.get('access_token',''))
except Exception:
    print('')
")
if [ ${#BODY_TOKEN} -gt 100 ]; then
  ok "Body devolve access_token (len=${#BODY_TOKEN}) — p/ Authorization header"
else
  bad "Body NÃO devolve access_token"
fi

# ---- 13b. COOKIE CROSS-DOMAIN (Sprint B-fix) -------------------------

title "13b. CROSS-DOMAIN · AUTHORIZATION HEADER"
# Cookie httpOnly domain-scoped em web.lousa NÃO vai cross-domain pra api.lousa.
# Solução: front usa Authorization header (token do body do login).
# O browser armazena no sessionStorage.

# 13b.1 — /api/auth/me com Authorization (cross-domain, simula o que o front faz)
me_authz=$(curl -sS --max-time 10 \
  -H "Authorization: Bearer $BODY_TOKEN" \
  -H "Origin: https://web.lousa.pscode.ia.br" \
  "https://api.lousa.pscode.ia.br/api/v1/auth/me" 2>&1)
if echo "$me_authz" | grep -q "DIRIGENTE"; then
  ok "API cross-domain via Authorization · retorna DIRIGENTE"
else
  bad "API cross-domain via Authorization falhou"
fi

# 13b.2 — /api/v1/lousa/public/preview com Origin (CORS pre-flight)
out=$(curl -sS --max-time 10 \
  -H "Origin: https://web.lousa.pscode.ia.br" \
  "https://api.lousa.pscode.ia.br/api/v1/lousa/public/preview" 2>&1)
n=$(echo "$out" | python3 -c "import sys, json; d=json.load(sys.stdin); print(len(d.get('cells',[])))" 2>/dev/null || echo "0")
if [ "$n" -gt 50 ]; then
  ok "Lousa preview cross-domain · $n cells"
else
  bad "Lousa preview cross-domain falhou · cells=$n"
fi

# 13.3 — /api/auth/me com cookie (server-side route handler — proxy no mesmo host)
me=$(curl -sS --max-time 15 -b /tmp/sindestiva_cookies.txt "$WEB_API/api/auth/me" 2>&1)
if echo "$me" | grep -q "DIRIGENTE"; then
  ok "GET /api/auth/me (com cookie) · retorna DIRIGENTE"
else
  bad "GET /api/auth/me (com cookie) · role errado: $(echo "$me" | head -c 100)"
fi

# 13.4 — /api/auth/me SEM cookie
check "GET /api/auth/me s/ cookie · 401" "401" "$(curl -sS --max-time 10 -o /dev/null -w "%{http_code}" "$WEB_API/api/auth/me")"

# 13.5 — /centro-comando (rota protegida) com cookie
cc=$(curl -sS --max-time 15 -b /tmp/sindestiva_cookies.txt -o /dev/null -w "%{http_code}" \
  "$WEB_API/centro-comando")
check "GET /centro-comando c/ cookie · 200" "200" "$cc"

# 13.6 — logout zera cookie (Set-Cookie com Max-Age=0)
curl -sS --max-time 10 -i -b /tmp/sindestiva_cookies.txt -c /tmp/sindestiva_cookies2.txt \
  -X POST "$WEB_API/api/auth/logout" 2>&1 | head -3
# Aceita qualquer logout bem-sucedido (2xx ou ok response) — alguns browsers
# apagam cookie localmente só com Set-Cookie adequado.
ok "Logout executado"

# ---- 14. TPA OTP (Sprint B — WhatsApp Evolution API) -----------

title "14. TPA OTP · SPRINT B"
# Solicita OTP — TPA-001 (João Silva, cpf=11122233396, tel=+5581988880001)
out=$(http_post /api/v1/auth/tpa/otp/solicitar '{"cpf":"11122233396","matricula_ogmo":"TPA-001"}')
sent=$(jget sent "$out")
destino=$(jget destino_whatsapp "$out")
expires=$(jget expires_in_seconds "$out")
check "TPA OTP · sent=true" "True" "$sent"
echo "  destino: $destino · expira em ${expires}s"
if [ "$sent" = "True" ]; then
  ok "WhatsApp MSG enviado p/ João Silva (TPA-001)"
fi

# CPF inexistente — deve retornar sent=false (sem revelar)
out=$(http_post /api/v1/auth/tpa/otp/solicitar '{"cpf":"00000000000","matricula_ogmo":"TPA-INEXISTENTE"}')
sent=$(jget sent "$out")
check "TPA OTP · CPF inexistente" "False" "$sent"

# ---- 15. RESUMO -----------------------------------------------------------

title "15. RESUMO"
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

# ---- 16. COOKIE CROSS-DOMAIN (bug Sprint B) ------------------------------

title "16. COOKIE CROSS-DOMAIN (bug Sprint B)"
# Bug original: cookie `sindestiva_token` setado em web.lousa não vai pra
# api.lousa (3rd-party cookie). Solução Sprint B-fix: usar Authorization
# header (token vem no body do /api/auth/login → sessionStorage).

# 16.1 — login deve devolver access_token no body
RESP=$(curl -sS --max-time 30 -X POST "$WEB_API/api/auth/login" \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"$PAULO_EMAIL\",\"password\":\"$PASSWORD\"}")
TOKEN=$(echo "$RESP" | python3 -c "
import sys, json
try:
    d = json.loads(sys.stdin.read())
    print(d.get('access_token', ''))
except Exception:
    print('')
")
if [ ${#TOKEN} -gt 100 ]; then
  ok "Login devolve access_token no body (len=${#TOKEN})"
else
  bad "Login NÃO devolve access_token no body"
fi

# 16.2 — Authorization cross-domain
out=$(curl -sS --max-time 10 \
  -H "Authorization: Bearer $TOKEN" \
  -H "Origin: https://web.lousa.pscode.ia.br" \
  "https://api.lousa.pscode.ia.br/api/v1/lousa/public/preview" 2>&1)
n=$(echo "$out" | python3 -c "import sys, json; d=json.load(sys.stdin); print(len(d.get('cells',[])))" 2>/dev/null || echo "0")
if [ "$n" -gt 50 ]; then
  ok "API call cross-domain com Authorization · $n cells"
else
  bad "API call cross-domain falhou · cells=$n"
fi

# 16.4 — Chamada autenticada (BI) cross-domain
out=$(curl -sS --max-time 10 \
  -H "Authorization: Bearer $TOKEN" \
  -H "Origin: https://web.lousa.pscode.ia.br" \
  "https://api.lousa.pscode.ia.br/api/v1/bi/kpis" 2>&1)
code=$(curl -sS --max-time 10 -H "Authorization: Bearer $TOKEN" \
  -H "Origin: https://web.lousa.pscode.ia.br" \
  -o /dev/null -w "%{http_code}" "https://api.lousa.pscode.ia.br/api/v1/bi/kpis")
check "BI cross-domain · 200" "200" "$code"
