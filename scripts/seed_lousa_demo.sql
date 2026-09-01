-- =============================================================================
-- SINDESTIVA-PE · Seed de DEMO (Sprint 0) - v2 corrigida
-- Cria 30 users TPA + 30 tpas profiles + 1 LousaSnapshot + 192 LousaCells
-- pra demonstrar a Lousa no Centro de Comando end-to-end.
--
-- Execute: PGPASSWORD=sindestiva psql -h 127.0.0.1 -p 5433 -U sindestiva
--                -d sindestiva -f scripts/seed_lousa_demo.sql
-- =============================================================================

SET search_path TO lousa_main, public;

-- -----------------------------------------------------------------------------
-- Limpa estado anterior
-- -----------------------------------------------------------------------------
DELETE FROM lousa_main.lousa_cells
 WHERE snapshot_id IN (
   SELECT id FROM lousa_main.lousa_snapshots WHERE fonte = 'DEMO_SPRINT0'
 );
DELETE FROM lousa_main.lousa_snapshots WHERE fonte = 'DEMO_SPRINT0';
DELETE FROM lousa_main.tpas WHERE matricula_ogmo LIKE 'DEMO-%';
DELETE FROM lousa_main.users WHERE email LIKE 'demo-tpa-%@sindestiva-pe.com.br';

-- -----------------------------------------------------------------------------
-- 30 users TPA + 30 tpas profiles
-- -----------------------------------------------------------------------------
WITH novos_users AS (
  INSERT INTO lousa_main.users (email, telefone, role, status, accepted_terms_at)
  SELECT
    'demo-tpa-' || lpad(n::text, 3, '0') || '@sindestiva-pe.com.br',
    '+55819' || lpad((90000000 + n * 137)::text, 8, '0'),
    'TPA'::role_enum,
    'ATIVO'::user_status_enum,
    now()
  FROM generate_series(1, 30) AS n
  RETURNING id, email
)
INSERT INTO lousa_main.tpas (
  user_id, cpf, nome_completo, matricula_ogmo, telefone,
  data_nascimento, funcao_base_id, categoria, status_cadastro,
  data_admissao, consentimento_at, consentimento_versao
)
SELECT
  nu.id,
  lpad((10000000000 + n * 137)::text, 11, '0'),
  (ARRAY['José','Antônio','Manoel','João','Francisco','Carlos','Paulo','Pedro',
         'Lucas','Luiz','Marcos','Luís','Gabriel','Rafael','Daniel','Marcelo',
         'Bruno','Eduardo','Felipe','Raimundo','Rodrigo','Márcio','Edson','Sandro',
         'Marlon','Davi','Sergio','Walter','Roberto','Cesar'])[n]
    || ' ' ||
    (ARRAY['Silva','Santos','Oliveira','Souza','Pereira','Lima','Costa','Rodrigues',
           'Almeida','Nascimento','Carvalho','Araújo','Ribeiro','Gomes','Martins',
           'Rocha','Dias','Barbosa','Pinto','Moreira'])[((n * 7) % 20) + 1],
  'DEMO-' || lpad(n::text, 3, '0'),
  '+55819' || lpad((90000000 + n * 137)::text, 8, '0'),
  DATE '1970-01-01' + ((n * 367)::int) * INTERVAL '1 day',
  (SELECT id FROM lousa_main.funcoes WHERE categoria = 'TECNICA' ORDER BY ordem_lousa LIMIT 1),
  'TECNICA',
  'ATIVO'::tpa_status_enum,
  CURRENT_DATE - ((n * 30 + 90)::int) * INTERVAL '1 day',
  now(),
  'v1.0'
FROM generate_series(1, 30) AS n
JOIN novos_users nu ON nu.email = 'demo-tpa-' || lpad(n::text, 3, '0') || '@sindestiva-pe.com.br';

-- -----------------------------------------------------------------------------
-- 1 LousaSnapshot (SUAPE, DIURNO)
-- -----------------------------------------------------------------------------
INSERT INTO lousa_main.lousa_snapshots (
  porto_id, turno_id, fonte, url_origem, html_hash_sha256,
  total_celulas, total_tpas_escalados, duracao_scrape_ms, status
)
VALUES (
  (SELECT id FROM lousa_main.portos WHERE codigo = 'SUAPE'),
  (SELECT id FROM lousa_main.turnos WHERE codigo = 'DIURNO'),
  'DEMO_SPRINT0',
  'http://localhost/seed',
  repeat('a', 64),
  0, 0, 235,
  'OK'::snapshot_status_enum
);

-- -----------------------------------------------------------------------------
-- Cells: 8 fainas × 18 funcoes (MANDO+TERNO+TECNICA) = 144; vamos popular
-- as 144 + adicionar algumas em ALTURA pra teste
-- -----------------------------------------------------------------------------
WITH snap AS (
  SELECT id AS snapshot_id, porto_id, turno_id
  FROM lousa_main.lousa_snapshots
  WHERE fonte = 'DEMO_SPRINT0'
  LIMIT 1
),
tpa_pool AS (
  SELECT id, row_number() OVER (ORDER BY matricula_ogmo) AS rn
  FROM lousa_main.tpas
  WHERE matricula_ogmo LIKE 'DEMO-%'
)
INSERT INTO lousa_main.lousa_cells (
  snapshot_id, porto_id, turno_id, funcao_id, faina_id, cais,
  navio_id, tpa_id, status_celula, data_referencia
)
SELECT
  s.snapshot_id,
  s.porto_id,
  s.turno_id,
  fn.id AS funcao_id,
  fi.id AS faina_id,
  (ARRAY['CAIS 1','CAIS 2','CAIS 3','CAIS 4'])[((fn.ordem_lousa + fi.ordem_lousa) % 4) + 1] AS cais,
  NULL::uuid AS navio_id,
  CASE
    WHEN ((fn.ordem_lousa * 7 + fi.ordem_lousa * 3) % 5) = 0 THEN NULL  -- 20% vazias
    WHEN ((fn.ordem_lousa * 11 + fi.ordem_lousa * 5) % 13) = 0 THEN NULL  -- algumas sem TPA
    ELSE (SELECT id FROM tpa_pool WHERE rn = ((fn.ordem_lousa * 7 + fi.ordem_lousa * 3) % 30) + 1)
  END AS tpa_id,
  CASE
    WHEN ((fn.ordem_lousa * 11 + fi.ordem_lousa * 5) % 13) = 0 THEN 'AUSENTE'::cell_status_enum
    WHEN ((fn.ordem_lousa * 13 + fi.ordem_lousa * 7) % 17) = 0 THEN 'REMANEJADO'::cell_status_enum
    WHEN ((fn.ordem_lousa * 17 + fi.ordem_lousa * 11) % 23) = 0 THEN 'CONFIRMADO'::cell_status_enum
    ELSE 'NORMAL'::cell_status_enum
  END AS status_celula,
  CURRENT_DATE AS data_referencia
FROM lousa_main.funcoes fn
CROSS JOIN lousa_main.fainas fi
CROSS JOIN snap s
WHERE fi.codigo IN ('PRODUCAO','SALARIO','SACARIA','VEICULO','DIVERSOS','CADASTRO','SUPLEMENTAR','ALTURA')
  AND fn.categoria IN ('MANDO','TERNO','TECNICA')
ON CONFLICT (snapshot_id, funcao_id, faina_id) DO NOTHING;

-- Atualiza totais
UPDATE lousa_main.lousa_snapshots s
SET total_celulas = (SELECT count(*) FROM lousa_main.lousa_cells WHERE snapshot_id = s.id),
    total_tpas_escalados = (SELECT count(*) FROM lousa_main.lousa_cells WHERE snapshot_id = s.id AND tpa_id IS NOT NULL)
WHERE fonte = 'DEMO_SPRINT0';

-- Sumário
SELECT 'snapshot_demo' AS item, count(*)::text AS total
FROM lousa_main.lousa_snapshots WHERE fonte = 'DEMO_SPRINT0'
UNION ALL SELECT 'cells_demo', count(*)::text FROM lousa_main.lousa_cells c
  JOIN lousa_main.lousa_snapshots s ON s.id = c.snapshot_id WHERE s.fonte = 'DEMO_SPRINT0'
UNION ALL SELECT 'cells_com_tpa', count(*)::text FROM lousa_main.lousa_cells c
  JOIN lousa_main.lousa_snapshots s ON s.id = c.snapshot_id WHERE s.fonte = 'DEMO_SPRINT0' AND tpa_id IS NOT NULL
UNION ALL SELECT 'tpas_demo', count(*)::text FROM lousa_main.tpas WHERE matricula_ogmo LIKE 'DEMO-%'
UNION ALL SELECT 'tpas_total', count(*)::text FROM lousa_main.tpas
UNION ALL SELECT 'cells_total', count(*)::text FROM lousa_main.lousa_cells;
