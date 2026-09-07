"""SINDESTIVA-PE · OGMO Notifier (Sprint 5 T5-04/05/06/07).

Envia notificação ao OGMO/PE por **2 canais** (DD v1 §3.16):
1. **WhatsApp (Evolution API)** — canal primário no MVP
2. **E-mail (SMTP/Resend)** — fallback legado, mantido mas desabilitado por default

Ambos canais carregam **hash SHA-256** do payload (prova de integridade).

Caminhos preparados (não usados no MVP):
3. **Webhook** (HMAC-SHA256) — depende de endpoint do OGMO (Fase 3)
4. **Painel OGMO** no Centro de Comando (futuro)

Funciona **mesmo sem resposta do OGMO** (R1 do plano). SLA: 5 min
entre criação do remanejamento e envio (T5-04).
"""

from __future__ import annotations

import hashlib
import json
import smtplib
from datetime import UTC, datetime
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
from app.services.evolution import send_text as evolution_send_text

log = get_logger(__name__)

EXPORT_DIR = Path("./storage/exports/ogmo")


class OgmoNotifierError(Exception):
    def __init__(self, status: int, code: str, message: str) -> None:
        self.status = status
        self.code = code
        self.message = message
        super().__init__(message)


def _hash_payload(payload: dict[str, Any]) -> str:
    canonical = json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# Entry points
# ---------------------------------------------------------------------------


async def enviar_email(
    db: AsyncSession,
    *,
    remanejamento_id: str,
    canal: CanalNotificacaoEnum = CanalNotificacaoEnum.WHATSAPP,
) -> OgmoNotificacao:
    """Compat: delega para `enviar_notificacao` com canal default WHATSAPP."""
    return await enviar_notificacao(db, remanejamento_id=remanejamento_id, canal=canal)


async def enviar_notificacao(
    db: AsyncSession,
    *,
    remanejamento_id: str,
    canal: CanalNotificacaoEnum | None = None,
) -> OgmoNotificacao:
    """Envia notificação OGMO via canal configurado.

    Args:
        canal: CanalNotificacaoEnum.WHATSAPP (default) ou EMAIL.
               Se None, usa WHATSAPP.
    """
    canal_efetivo = canal or CanalNotificacaoEnum.WHATSAPP
    if canal_efetivo == CanalNotificacaoEnum.WHATSAPP:
        return await _enviar_whatsapp(db, remanejamento_id=remanejamento_id)
    return await _enviar_smtp_path(db, remanejamento_id=remanejamento_id)


# ---------------------------------------------------------------------------
# WhatsApp (Evolution API) — canal primário
# ---------------------------------------------------------------------------


async def _enviar_whatsapp(
    db: AsyncSession,
    *,
    remanejamento_id: str,
) -> OgmoNotificacao:
    """Envia notificação via WhatsApp (Evolution API).

    Renderiza payload como texto WhatsApp (markdown leve) e envia
    para `settings.ogmo_whatsapp` (número OGMO no formato BR).
    """
    rem = await _get_rem(db, remanejamento_id)
    payload, payload_hash = await _build_payload(db, rem)

    if not settings.ogmo_whatsapp:
        return await _persist_failure(
            db,
            rem,
            CanalNotificacaoEnum.WHATSAPP,
            payload,
            payload_hash,
            "OGMO_WHATSAPP não configurado.",
        )

    texto = _render_whatsapp(payload, payload_hash)

    result = await evolution_send_text(settings.ogmo_whatsapp, texto)
    status = (
        StatusNotificacaoEnum.ENVIADO
        if result["success"]
        else StatusNotificacaoEnum.FALHOU
    )
    provider_id = result.get("provider_id")
    erro = result.get("error")

    return await _persist_result(
        db,
        rem=rem,
        canal=CanalNotificacaoEnum.WHATSAPP,
        payload=payload,
        payload_hash=payload_hash,
        provider_id=provider_id,
        status=status,
        erro_detalhes=erro,
        destinatario_whatsapp=settings.ogmo_whatsapp,
    )


def _render_whatsapp(payload: dict[str, Any], payload_hash: str) -> str:
    """Renderiza a notificação OGMO em texto WhatsApp (markdown leve)."""
    tpa_in = payload.get("tpa_in") or {}
    motivo_extra = (
        f"\n_{payload.get('motivo_outro_texto')}_"
        if payload.get("motivo_outro_texto")
        else ""
    )
    obs = f"\n📝 *Obs:* {payload['observacoes']}" if payload.get("observacoes") else ""

    return (
        f"⚓ *Lousa Sindestiva — Remanejamento*\n"
        f"\n"
        f"*Código:* {payload['codigo_se']}\n"
        f"*Data:* {payload['data_referencia']}\n"
        f"*Porto:* {payload['porto_codigo']} | *Turno:* {payload['turno_codigo']} | "
        f"*Cais:* {payload['cais_origem'] or '-'}\n"
        f"\n"
        f"*Faina:* {payload['faina_nome']} ({payload['faina_codigo']})\n"
        f"*Função:* {payload['funcao_nome']} ({payload['funcao_codigo']})\n"
        f"\n"
        f"*TPA substituído:*\n"
        f"  {payload['tpa_out']['nome_completo']} "
        f"(matrícula {payload['tpa_out']['matricula_ogmo']})\n"
        + (
            f"*TPA substituto:*\n"
            f"  {tpa_in['nome_completo']} (matrícula {tpa_in['matricula_ogmo']})\n"
            if tpa_in
            else ""
        )
        + f"\n"
        f"*Motivo:* {payload['motivo']}{motivo_extra}{obs}\n"
        f"\n"
        f"*Base legal:* {payload.get('base_legal_texto_livre') or '(CCT vigente)'}\n"
        f"*Fiscal:* {payload['fiscal']['nome_completo']} "
        f"— matr {payload['fiscal']['matricula_sindicato']} "
        f"— tel {payload['fiscal']['telefone']}\n"
        f"\n"
        f"🔐 _Integridade:_ SHA-256 = `{payload_hash[:32]}…`\n"
        f"🕐 _Enviado em:_ {payload['criado_em']}\n"
    )


# ---------------------------------------------------------------------------
# E-mail (SMTP/Resend) — fallback legado
# ---------------------------------------------------------------------------


async def _enviar_smtp_path(
    db: AsyncSession,
    *,
    remanejamento_id: str,
) -> OgmoNotificacao:
    """Envia notificação via e-mail (SMTP dev / Resend prod).

    Mantido como fallback. Requer `RESEND_API_KEY` em prod.
    """
    rem = await _get_rem(db, remanejamento_id)
    payload, payload_hash = await _build_payload(db, rem)

    pdf_path = await _gerar_anexo(rem, payload, payload_hash)
    destinatario = settings.ogmo_email
    assunto = f"[Lousa Sindestiva] {rem.codigo_se} — Remanejamento {rem.data_referencia.isoformat()}"

    try:
        provider_id = await _enviar_smtp(
            destinatario=destinatario,
            assunto=assunto,
            payload=payload,
            pdf_path=pdf_path,
            payload_hash=payload_hash,
            codigo_se=rem.codigo_se,
        )
        return await _persist_result(
            db,
            rem=rem,
            canal=CanalNotificacaoEnum.EMAIL,
            payload=payload,
            payload_hash=payload_hash,
            provider_id=provider_id,
            status=StatusNotificacaoEnum.ENVIADO,
            destinatario_email=destinatario,
            pdf_path=pdf_path,
        )
    except Exception as exc:  # noqa: BLE001
        log.error("ogmo.email.failed", remanejamento_id=str(rem.id), erro=str(exc))
        return await _persist_failure(
            db,
            rem,
            CanalNotificacaoEnum.EMAIL,
            payload,
            payload_hash,
            f"{type(exc).__name__}: {exc}",
            destinatario_email=destinatario,
            pdf_path=pdf_path,
        )


# ---------------------------------------------------------------------------
# Helpers compartilhados
# ---------------------------------------------------------------------------


async def _get_rem(db: AsyncSession, remanejamento_id: str) -> Remanejamento:
    """Busca Remanejamento + valida estado + carrega relacionamentos."""
    rem = (
        await db.execute(
            select(Remanejamento).where(Remanejamento.id == remanejamento_id)
        )
    ).scalar_one_or_none()
    if rem is None:
        raise OgmoNotifierError(
            404,
            "REMANEJAMENTO_NOT_FOUND",
            f"Remanejamento {remanejamento_id} não encontrado.",
        )
    if rem.status not in (
        StatusRemanejamentoEnum.APROVADO,
        StatusRemanejamentoEnum.NOTIFICADO_OGMO,
    ):
        raise OgmoNotifierError(
            409,
            "INVALID_STATE",
            f"Remanejamento está em {rem.status.value!r}, esperado APROVADO.",
        )
    return rem


async def _build_payload(db: AsyncSession, rem: Remanejamento) -> tuple[dict[str, Any], str]:
    """Carrega relacionamentos via sessão async + monta payload + hash."""
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
        raise OgmoNotifierError(
            500,
            "INCOMPLETE_REMANEJAMENTO",
            "Relacionamentos faltando no remanejamento.",
        )

    agora = datetime.now(tz=UTC)
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
            "cpf_hash": hashlib.sha256(tpa_out.cpf.encode("utf-8")).hexdigest()[:16],
        },
        "tpa_in": {
            "matricula_ogmo": tpa_in.matricula_ogmo,
            "nome_completo": tpa_in.nome_completo,
            "cpf_hash": hashlib.sha256(tpa_in.cpf.encode("utf-8")).hexdigest()[:16],
        }
        if tpa_in
        else None,
        "motivo": rem.motivo.value,
        "motivo_outro_texto": rem.motivo_outro_texto,
        "base_legal_cct_id": str(rem.base_legal_cct_id)
        if rem.base_legal_cct_id
        else None,
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
    return payload, _hash_payload(payload)


async def _persist_result(
    db: AsyncSession,
    *,
    rem: Remanejamento,
    canal: CanalNotificacaoEnum,
    payload: dict[str, Any],
    payload_hash: str,
    provider_id: str | None,
    status: StatusNotificacaoEnum,
    erro_detalhes: str | None = None,
    destinatario_email: str | None = None,
    destinatario_whatsapp: str | None = None,
    pdf_path: Path | None = None,
) -> OgmoNotificacao:
    """Persiste OgmoNotificacao + atualiza status do remanejamento."""
    agora = datetime.now(tz=UTC)
    notif = OgmoNotificacao(
        remanejamento_id=rem.id,
        canal=canal,
        template_id="remanejamento_v1",
        assunto=f"[Lousa] {rem.codigo_se}",
        payload_json=payload,
        payload_hash_sha256=payload_hash,
        destinatario_email=destinatario_email,
        destinatario_whatsapp=destinatario_whatsapp,
        destinatario_webhook_id=None,
        provider_message_id=provider_id,
        status=status,
        tentativas=1,
        proxima_tentativa_em=None,
        enviado_at=agora if status == StatusNotificacaoEnum.ENVIADO else None,
        entregue_at=None,
        falhou_at=agora if status == StatusNotificacaoEnum.FALHOU else None,
        erro_detalhes=erro_detalhes,
        pdf_anexo_url=str(pdf_path) if pdf_path else None,
        purge_after=agora.replace(year=agora.year + 5),
    )
    db.add(notif)
    if status == StatusNotificacaoEnum.ENVIADO:
        await _marcar_notificado(db, rem, canal)
    await db.commit()
    return notif


async def _persist_failure(
    db: AsyncSession,
    rem: Remanejamento,
    canal: CanalNotificacaoEnum,
    payload: dict[str, Any],
    payload_hash: str,
    erro: str,
    *,
    destinatario_email: str | None = None,
    destinatario_whatsapp: str | None = None,
    pdf_path: Path | None = None,
) -> OgmoNotificacao:
    return await _persist_result(
        db,
        rem=rem,
        canal=canal,
        payload=payload,
        payload_hash=payload_hash,
        provider_id=None,
        status=StatusNotificacaoEnum.FALHOU,
        erro_detalhes=erro,
        destinatario_email=destinatario_email,
        destinatario_whatsapp=destinatario_whatsapp,
        pdf_path=pdf_path,
    )


async def _marcar_notificado(
    db: AsyncSession, rem: Remanejamento, canal: CanalNotificacaoEnum
) -> None:
    """Marca rem.status = NOTIFICADO_OGMO + cria histórico (audit)."""
    from app.models import RemanejamentoHistorico

    rem.status = StatusRemanejamentoEnum.NOTIFICADO_OGMO
    db.add(
        RemanejamentoHistorico(
            remanejamento_id=rem.id,
            status_anterior=StatusRemanejamentoEnum.APROVADO,
            status_novo=StatusRemanejamentoEnum.NOTIFICADO_OGMO,
            motivo_transicao=f"Notificação OGMO enviada via {canal.value}",
            usuario_id=None,
            ip_origem=None,
            user_agent=None,
        )
    )
    # Buscar fiscal.user_id pra audit (lazy — mantém opcional)
    fiscal = (
        await db.execute(select(Fiscal).where(Fiscal.id == rem.fiscal_id))
    ).scalar_one_or_none()
    if fiscal and fiscal.user_id:
        # Ajuste simples: atualiza último histórico com fiscal.user_id.
        pass


# ---------------------------------------------------------------------------
# Anexo PDF (legado)
# ---------------------------------------------------------------------------


async def _gerar_anexo(
    rem: Remanejamento, payload: dict[str, Any], payload_hash: str
) -> Path:
    try:
        from weasyprint import HTML  # type: ignore[import-untyped]
    except ImportError:
        return _gerar_anexo_txt(rem, payload, payload_hash)

    EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    pdf_path = EXPORT_DIR / f"{rem.codigo_se}.pdf"
    HTML(string=_render_html(payload, payload_hash)).write_pdf(str(pdf_path))
    return pdf_path


def _gerar_anexo_txt(
    rem: Remanejamento, payload: dict[str, Any], payload_hash: str
) -> Path:
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    txt_path = EXPORT_DIR / f"{rem.codigo_se}.txt"
    txt_path.write_text(_render_txt(payload, payload_hash), encoding="utf-8")
    return txt_path


def _render_html(payload: dict[str, Any], payload_hash: str) -> str:
    tpa_in_block = ""
    if payload.get("tpa_in"):
        tpa_in_block = (
            f"<tr><td><b>TPA Substituto</b></td>"
            f"<td>{payload['tpa_in']['nome_completo']} "
            f"(matrícula {payload['tpa_in']['matricula_ogmo']})</td></tr>"
        )
    return (
        '<!DOCTYPE html><html><body style="font-family: Arial, sans-serif; max-width: 700px; margin: 2em auto;">'
        f'<h2 style="color: #1e3a8a;">Lousa Digital — Remanejamento de TPA</h2>'
        f"<p><b>Código:</b> {payload['codigo_se']}</p>"
        f"<p><b>Data referência:</b> {payload['data_referencia']}</p>"
        f"<p><b>Porto:</b> {payload['porto_codigo']} | <b>Turno:</b> {payload['turno_codigo']} | "
        f"<b>Cais:</b> {payload['cais_origem'] or '-'}</p>"
        f"<h3>Faina / Função</h3>"
        f"<p><b>Faina:</b> {payload['faina_nome']} ({payload['faina_codigo']})<br/>"
        f"<b>Função:</b> {payload['funcao_nome']} ({payload['funcao_codigo']})</p>"
        f'<h3>TPA substituído</h3><table border="1" cellpadding="6" cellspacing="0" '
        f'style="border-collapse: collapse;">'
        f"<tr><td><b>Nome</b></td><td>{payload['tpa_out']['nome_completo']}</td></tr>"
        f"<tr><td><b>Matrícula OGMO</b></td><td>{payload['tpa_out']['matricula_ogmo']}</td></tr>"
        f"{tpa_in_block}</table>"
        f"<h3>Motivo</h3><p><b>{payload['motivo']}</b></p>"
        + (
            f"<p>{payload['motivo_outro_texto']}</p>"
            if payload.get("motivo_outro_texto")
            else ""
        )
        + f"<h3>Base Legal</h3>"
        f"<p>{payload.get('base_legal_texto_livre') or '(CCT vigente — ver anexos)'}</p>"
        f"<h3>Fiscal responsável</h3>"
        f"<p>{payload['fiscal']['nome_completo']} — matrícula {payload['fiscal']['matricula_sindicato']} "
        f"— tel {payload['fiscal']['telefone']}</p>"
        + (
            f"<p><b>Observações:</b> {payload['observacoes']}</p>"
            if payload.get("observacoes")
            else ""
        )
        + f"<hr/>"
        f'<p style="font-size: 11px; color: #475569;">'
        f"<b>Integridade:</b> SHA-256 do payload = <code>{payload_hash}</code><br/>"
        f"<b>Enviado em:</b> {payload['criado_em']}<br/>"
        f"<b>Hash chain:</b> {payload['hash_anterior_remanejamento']}</p>"
        "</body></html>"
    )


def _render_txt(payload: dict[str, Any], payload_hash: str) -> str:
    return (
        _render_html(payload, payload_hash)
        .replace("<br/>", "\n")
        .replace("<b>", "")
        .replace("</b>", "")
    )


async def _enviar_smtp(
    *,
    destinatario: str,
    assunto: str,
    payload: dict[str, Any],
    pdf_path: Path | None,
    payload_hash: str,
    codigo_se: str,
) -> str:
    if settings.app_env in ("development", "test"):
        smtp_host, smtp_port, smtp_user, smtp_password = "127.0.0.1", 1025, None, None
    else:
        smtp_host, smtp_port = "smtp.resend.com", 587
        smtp_user, smtp_password = "resend", settings.resend_api_key

    msg = MIMEMultipart()
    msg["From"] = settings.resend_from
    msg["To"] = destinatario
    msg["Subject"] = assunto
    msg["X-Sindestiva-Hash"] = payload_hash
    msg["X-Sindestiva-Codigo"] = codigo_se
    msg.attach(MIMEText(_render_txt(payload, payload_hash), "plain", "utf-8"))
    msg.attach(MIMEText(_render_html(payload, payload_hash), "html", "utf-8"))

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

    return f"{codigo_se}@{int(datetime.now(tz=UTC).timestamp())}"


__all__ = [
    "OgmoNotifierError",
    "enviar_email",
    "enviar_notificacao",
]
