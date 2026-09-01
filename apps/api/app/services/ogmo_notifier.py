"""SINDESTIVA-PE · OGMO Notifier (Sprint 5 T5-04/05/06/07).

Envia notificação ao OGMO/PE por **3 caminhos paralelos** (DD v1 §3.16):
1. **E-mail** (canal primário, unilateral — não precisa de aprovação)
2. **PDF anexado** ao e-mail (gerado via WeasyPrint)
3. **Hash SHA-256** do payload visível no e-mail (prova de integridade)

Caminhos 4 e 5 (preparados, mas não usados no MVP):
4. **Webhook** (HMAC-SHA256) — depende de endpoint do OGMO (Fase 3)
5. **Painel OGMO** no Centro de Comando (futuro)

Funciona **mesmo sem resposta do OGMO** (R1 do plano). SLA: 5 min
entre criação do remanejamento e envio (T5-04).

Em dev, usa **MailHog** (SMTP :1025, conforme docker-compose.yml).
Em prod, usa **Resend** (SMTP/API).
"""
from __future__ import annotations

import hashlib
import json
import smtplib
from datetime import datetime, timezone
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.logging import get_logger
from app.models import (
    Faina,
    Fiscal,
    Funcao,
    OgmoNotificacao,
    Porto,
    Remanejamento,
    Tpa,
    Turno,
)
from app.models.enums import (
    CanalNotificacaoEnum,
    StatusNotificacaoEnum,
    StatusRemanejamentoEnum,
)

log = get_logger(__name__)

# Diretório de exports (PDFs + JSON)
EXPORT_DIR = Path("./storage/exports/ogmo")


class OgmoNotifierError(Exception):
    """Erro no envio. Capturado e gravado em OgmoNotificacao.status."""

    def __init__(self, status: int, code: str, message: str) -> None:
        self.status = status
        self.code = code
        self.message = message
        super().__init__(message)


def _hash_payload(payload: dict[str, Any]) -> str:
    """SHA-256 hex do payload JSON canônico."""
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


async def enviar_email(
    db: AsyncSession,
    *,
    remanejamento_id: str,
    canal: CanalNotificacaoEnum = CanalNotificacaoEnum.EMAIL,
) -> OgmoNotificacao:
    """Envia notificação ao OGMO via e-mail + PDF.

    Fluxo:
    1. Busca Remanejamento + relacionamentos (Tpa, Fiscal, Funcao, Faina, Porto, Turno)
    2. Monta payload canônico (hash visível no e-mail)
    3. Renderiza PDF (WeasyPrint, ou texto simples em dev sem WeasyPrint)
    4. Envia via SMTP (MailHog :1025 em dev, Resend em prod)
    5. Cria OgmoNotificacao com status=ENVIADO (ou FALHOU)
    6. Atualiza Remanejamento.status = NOTIFICADO_OGMO + cria RemanejamentoHistorico
    """
    # 1. Buscar remanejamento + relacionamentos
    rem = (await db.execute(
        select(Remanejamento).where(Remanejamento.id == remanejamento_id)
    )).scalar_one_or_none()
    if rem is None:
        raise OgmoNotifierError(404, "REMANEJAMENTO_NOT_FOUND", f"Remanejamento {remanejamento_id} não encontrado.")

    if rem.status not in (StatusRemanejamentoEnum.APROVADO, StatusRemanejamentoEnum.NOTIFICADO_OGMO):
        raise OgmoNotifierError(
            409,
            "INVALID_STATE",
            f"Remanejamento está em {rem.status.value!r}, esperado APROVADO.",
        )

    tpa_out = (await db.execute(select(Tpa).where(Tpa.id == rem.tpa_out_id))).scalar_one_or_none()
    tpa_in = None
    if rem.tpa_in_id:
        tpa_in = (await db.execute(select(Tpa).where(Tpa.id == rem.tpa_in_id))).scalar_one_or_none()
    fiscal = (await db.execute(select(Fiscal).where(Fiscal.id == rem.fiscal_id))).scalar_one_or_none()
    funcao = (await db.execute(select(Funcao).where(Funcao.id == rem.funcao_origem_id))).scalar_one_or_none()
    faina = (await db.execute(select(Faina).where(Faina.id == rem.faina_origem_id))).scalar_one_or_none()
    porto = (await db.execute(select(Porto).where(Porto.id == rem.porto_id))).scalar_one_or_none()
    turno = (await db.execute(select(Turno).where(Turno.id == rem.turno_id))).scalar_one_or_none()

    if not all([tpa_out, fiscal, funcao, faina, porto, turno]):
        raise OgmoNotifierError(500, "INCOMPLETE_REMANEJAMENTO", "Relacionamentos faltando no remanejamento.")

    # 2. Payload canônico
    agora = datetime.now(tz=timezone.utc)
    payload: dict[str, Any] = {
        "codigo_se": rem.codigo_se,
        "data_referencia": rem.data_referencia.isoformat(),
        "porto_codigo": porto.codigo,
        "turno_codigo": turno.codigo,
        "cais_origem": rem.cais_origem,
        "faina_codigo": faina.codigo,
        "faina_nome": faina.nome_exibicao,
        "funcao_codigo": funcao.codigo,
        "funcao_nome": funcao.nome_exibicao,
        "tpa_out": {
            "matricula_ogmo": tpa_out.matricula_ogmo,
            "nome_completo": tpa_out.nome_completo,
            "cpf_hash": hashlib.sha256(tpa_out.cpf.encode("utf-8")).hexdigest()[:16],  # anonimizado
        },
        "tpa_in": {
            "matricula_ogmo": tpa_in.matricula_ogmo,
            "nome_completo": tpa_in.nome_completo,
            "cpf_hash": hashlib.sha256(tpa_in.cpf.encode("utf-8")).hexdigest()[:16] if tpa_in else None,
        } if tpa_in else None,
        "motivo": rem.motivo.value,
        "motivo_outro_texto": rem.motivo_outro_texto,
        "base_legal_cct_id": str(rem.base_legal_cct_id) if rem.base_legal_cct_id else None,
        "base_legal_texto_livre": rem.base_legal_texto_livre,
        "observacoes": rem.observacoes,
        "fiscal": {
            "nome_completo": fiscal.nome_completo,
            "matricula_sindicato": fiscal.matricula_sindicato,
            "telefone": fiscal.telefone,
        },
        "criado_em": agora.isoformat(),
        "hash_anterior_remanejamento": rem.hash_evento[:16] + "...",
    }
    payload_hash = _hash_payload(payload)

    # 3. Renderiza "PDF" (em dev sem WeasyPrint, gera TXT simples; em prod usa WeasyPrint)
    pdf_path = await _gerar_anexo(rem, payload, payload_hash)

    # 4. Envia via SMTP (MailHog dev / Resend prod)
    destinatario = settings.ogmo_email
    assunto = f"[Lousa Sindestiva] {rem.codigo_se} — Remanejamento {rem.data_referencia.isoformat()}"

    status_envio = StatusNotificacaoEnum.PENDENTE
    erro_detalhes: str | None = None
    enviado_at: datetime | None = None
    provider_id: str | None = None

    try:
        provider_id = await _enviar_smtp(
            destinatario=destinatario,
            assunto=assunto,
            payload=payload,
            pdf_path=pdf_path,
            payload_hash=payload_hash,
            codigo_se=rem.codigo_se,
        )
        status_envio = StatusNotificacaoEnum.ENVIADO
        enviado_at = datetime.now(tz=timezone.utc)
    except Exception as exc:  # noqa: BLE001
        status_envio = StatusNotificacaoEnum.FALHOU
        erro_detalhes = f"{type(exc).__name__}: {exc!s}"
        log.error("ogmo.email.failed", remanejamento_id=str(rem.id), erro=erro_detalhes)

    # 5. Cria OgmoNotificacao
    notif = OgmoNotificacao(
        remanejamento_id=rem.id,
        canal=canal,
        template_id="remanejamento_v1",
        assunto=assunto,
        payload_json=payload,
        payload_hash_sha256=payload_hash,
        destinatario_email=destinatario,
        destinatario_webhook_id=None,
        provider_message_id=provider_id,
        status=status_envio,
        tentativas=1,
        proxima_tentativa_em=None,
        enviado_at=enviado_at,
        entregue_at=None,
        falhou_at=datetime.now(tz=timezone.utc) if status_envio == StatusNotificacaoEnum.FALHOU else None,
        erro_detalhes=erro_detalhes,
        pdf_anexo_url=str(pdf_path) if pdf_path else None,
        purge_after=agora.replace(year=agora.year + 5),  # 5 anos (audit)
    )
    db.add(notif)

    # 6. Atualiza status do remanejamento se enviado com sucesso
    if status_envio == StatusNotificacaoEnum.ENVIADO:
        from app.models import RemanejamentoHistorico  # noqa: PLC0415

        rem.status = StatusRemanejamentoEnum.NOTIFICADO_OGMO
        hist = RemanejamentoHistorico(
            remanejamento_id=rem.id,
            status_anterior=StatusRemanejamentoEnum.APROVADO,
            status_novo=StatusRemanejamentoEnum.NOTIFICADO_OGMO,
            motivo_transicao=f"Notificação OGMO enviada via {canal.value}",
            usuario_id=fiscal.user_id if fiscal else None,
            ip_origem=None,
            user_agent=None,
        )
        db.add(hist)

    await db.commit()
    await db.refresh(notif)

    log.info(
        "ogmo.email.enviado",
        remanejamento_id=str(rem.id),
        status=status_envio.value,
        destinatario=destinatario,
        hash=payload_hash[:16] + "...",
    )

    return notif


async def _gerar_anexo(
    rem: Remanejamento, payload: dict[str, Any], payload_hash: str
) -> Path | None:
    """Gera anexo (PDF em prod, TXT em dev sem WeasyPrint).

    Retorna path do arquivo ou None se falhar.
    """
    try:
        from weasyprint import HTML  # type: ignore[import-untyped]  # noqa: PLC0415
    except ImportError:
        # Dev fallback: TXT simples (sem dependência de WeasyPrint instalado)
        return _gerar_anexo_txt(rem, payload, payload_hash)

    EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    pdf_path = EXPORT_DIR / f"{rem.codigo_se}.pdf"

    html_body = _render_html(payload, payload_hash)
    HTML(string=html_body).write_pdf(str(pdf_path))
    return pdf_path


def _gerar_anexo_txt(
    rem: Remanejamento, payload: dict[str, Any], payload_hash: str
) -> Path:
    """Fallback TXT (dev) — formato legível equivalente."""
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    txt_path = EXPORT_DIR / f"{rem.codigo_se}.txt"
    txt_path.write_text(_render_txt(payload, payload_hash), encoding="utf-8")
    return txt_path


def _render_html(payload: dict[str, Any], payload_hash: str) -> str:
    """Renderiza HTML do anexo (proposta de e-mail OGMO)."""
    tpa_in_block = ""
    if payload.get("tpa_in"):
        tpa_in_block = f"""
        <tr><td><b>TPA Substituto</b></td>
            <td>{payload['tpa_in']['nome_completo']} (matrícula {payload['tpa_in']['matricula_ogmo']})</td></tr>
        """

    return f"""
    <!DOCTYPE html>
    <html><body style="font-family: Arial, sans-serif; max-width: 700px; margin: 2em auto;">
    <h2 style="color: #1e3a8a;">Lousa Digital — Remanejamento de TPA</h2>
    <p><b>Código:</b> {payload['codigo_se']}</p>
    <p><b>Data referência:</b> {payload['data_referencia']}</p>
    <p><b>Porto:</b> {payload['porto_codigo']} | <b>Turno:</b> {payload['turno_codigo']} | <b>Cais:</b> {payload['cais_origem'] or '-'}</p>

    <h3 style="color: #0f1e4d;">Faina / Função</h3>
    <p><b>Faina:</b> {payload['faina_nome']} ({payload['faina_codigo']})<br/>
       <b>Função:</b> {payload['funcao_nome']} ({payload['funcao_codigo']})</p>

    <h3 style="color: #0f1e4d;">TPA substituído</h3>
    <table border="1" cellpadding="6" cellspacing="0" style="border-collapse: collapse;">
    <tr><td><b>Nome</b></td><td>{payload['tpa_out']['nome_completo']}</td></tr>
    <tr><td><b>Matrícula OGMO</b></td><td>{payload['tpa_out']['matricula_ogmo']}</td></tr>
    {tpa_in_block}
    </table>

    <h3 style="color: #0f1e4d;">Motivo</h3>
    <p><b>{payload['motivo']}</b></p>
    {f"<p>{payload['motivo_outro_texto']}</p>" if payload.get('motivo_outro_texto') else ""}

    <h3 style="color: #0f1e4d;">Base Legal</h3>
    <p>{payload.get('base_legal_texto_livre') or '(CCT vigente — ver anexos)'}</p>

    <h3 style="color: #0f1e4d;">Fiscal responsável</h3>
    <p>{payload['fiscal']['nome_completo']} — matrícula {payload['fiscal']['matricula_sindicato']} — tel {payload['fiscal']['telefone']}</p>

    {f"<p><b>Observações:</b> {payload['observacoes']}</p>" if payload.get('observacoes') else ""}

    <hr/>
    <p style="font-size: 11px; color: #475569;">
    <b>Integridade:</b> SHA-256 do payload = <code>{payload_hash}</code><br/>
    <b>Enviado em:</b> {payload['criado_em']}<br/>
    <b>Hash chain:</b> {payload['hash_anterior_remanejamento']}
    </p>
    </body></html>
    """


def _render_txt(payload: dict[str, Any], payload_hash: str) -> str:
    """Fallback TXT (dev)."""
    return _render_html(payload, payload_hash).replace("<br/>", "\n").replace("<b>", "").replace("</b>", "")


async def _enviar_smtp(
    *,
    destinatario: str,
    assunto: str,
    payload: dict[str, Any],
    pdf_path: Path | None,
    payload_hash: str,
    codigo_se: str,
) -> str:
    """Envia e-mail via SMTP.

    Em dev: MailHog (127.0.0.1:1025, sem auth)
    Em prod: Resend SMTP (smtp.resend.com:587, com RESEND_API_KEY)
    """
    # Detecta ambiente
    if settings.app_env in ("development", "test"):
        smtp_host = "127.0.0.1"
        smtp_port = 1025
        smtp_user = None
        smtp_password = None
    else:
        smtp_host = "smtp.resend.com"
        smtp_port = 587
        smtp_user = "resend"
        smtp_password = settings.resend_api_key

    msg = MIMEMultipart()
    msg["From"] = settings.resend_from
    msg["To"] = destinatario
    msg["Subject"] = assunto
    msg["X-Sindestiva-Hash"] = payload_hash
    msg["X-Sindestiva-Codigo"] = codigo_se

    # Body em texto + html
    body_text = _render_txt(payload, payload_hash)
    body_html = _render_html(payload, payload_hash)
    msg.attach(MIMEText(body_text, "plain", "utf-8"))
    msg.attach(MIMEText(body_html, "html", "utf-8"))

    # Anexo PDF
    if pdf_path and pdf_path.exists():
        with open(pdf_path, "rb") as f:
            part = MIMEApplication(f.read(), Name=pdf_path.name)
            part["Content-Disposition"] = f'attachment; filename="{pdf_path.name}"'
            msg.attach(part)

    with smtplib.SMTP(smtp_host, smtp_port, timeout=10) as smtp:
        if smtp_user and smtp_password:
            smtp.starttls()
            smtp.login(smtp_user, smtp_password)
        smtp.send_message(msg)

    return f"{codigo_se}@{int(datetime.now(tz=timezone.utc).timestamp())}"


__all__ = [
    "OgmoNotifierError",
    "enviar_email",
]
