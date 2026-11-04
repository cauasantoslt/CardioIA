"""
CardioIA - Fase 3 | Ir Além 1
Automação de envio de e-mail de alerta clínico.

Modos de operação:
  - REAL     : se SMTP_HOST estiver configurado no .env (Gmail com senha de app,
               Outlook, Mailtrap, etc.), envia via SMTP com STARTTLS/SSL.
  - SIMULADO : padrão. Gera o e-mail completo (MIME, texto + HTML) e salva como
               arquivo .eml na pasta outbox/ - pode ser aberto no Outlook/Thunderbird.
"""
from __future__ import annotations

import smtplib
import ssl
from datetime import datetime
from email.message import EmailMessage
from pathlib import Path

import config
from risco import Avaliacao, Leitura


def montar_email(avaliacao: Avaliacao, leitura: Leitura) -> EmailMessage:
    codigos = ", ".join(r.codigo for r in avaliacao.riscos)
    quando = datetime.fromtimestamp(leitura.ts).strftime("%d/%m/%Y %H:%M:%S") if leitura.ts else "agora"
    temp = f"{leitura.temp:.1f} °C" if leitura.temp is not None else "indisponível"

    msg = EmailMessage()
    msg["Subject"] = f"[CardioIA] ALERTA {avaliacao.nivel} - {leitura.paciente} - {codigos}"
    msg["From"] = config.EMAIL_REMETENTE
    msg["To"] = ", ".join(config.EMAIL_DESTINO)
    msg["X-Priority"] = "1" if avaliacao.critica else "3"

    linhas = "\n".join(f"  - [{r.nivel}] {r.codigo}: {r.descricao}" for r in avaliacao.riscos)
    msg.set_content(
        f"ALERTA CardioIA - Monitoramento Contínuo\n\n"
        f"Paciente: {leitura.paciente}  (dispositivo {leitura.device})\n"
        f"Coleta:   {quando}  (origem: {leitura.origem})\n\n"
        f"Sinais vitais:\n  FC: {leitura.bpm} bpm | Temperatura: {temp} | Movimento: {leitura.mov:.2f} g\n\n"
        f"Riscos identificados:\n{linhas}\n\n"
        f"Ação sugerida: contatar o paciente e avaliar necessidade de atendimento.\n"
        f"Mensagem automática - protótipo acadêmico, não substitui avaliação médica.\n"
    )

    itens = "".join(
        f"<li><b style='color:{'#c0392b' if r.nivel == 'CRITICO' else '#d68910'}'>{r.codigo}</b> - {r.descricao}</li>"
        for r in avaliacao.riscos
    )
    cor = "#c0392b" if avaliacao.critica else "#d68910"
    msg.add_alternative(f"""\
<html><body style="font-family:Segoe UI,Arial,sans-serif;color:#222">
  <div style="max-width:560px;border:1px solid #ddd;border-radius:8px;overflow:hidden">
    <div style="background:{cor};color:#fff;padding:14px 18px;font-size:18px">
      &#10084; CardioIA &mdash; ALERTA {avaliacao.nivel}
    </div>
    <div style="padding:16px 18px">
      <p><b>Paciente:</b> {leitura.paciente} &nbsp; <b>Dispositivo:</b> {leitura.device}<br>
         <b>Coleta:</b> {quando} ({leitura.origem})</p>
      <table style="border-collapse:collapse;width:100%;margin:8px 0">
        <tr><td style="padding:6px;border:1px solid #eee">Frequência cardíaca</td><td style="padding:6px;border:1px solid #eee"><b>{leitura.bpm} bpm</b></td></tr>
        <tr><td style="padding:6px;border:1px solid #eee">Temperatura</td><td style="padding:6px;border:1px solid #eee"><b>{temp}</b></td></tr>
        <tr><td style="padding:6px;border:1px solid #eee">Movimento</td><td style="padding:6px;border:1px solid #eee"><b>{leitura.mov:.2f} g</b></td></tr>
      </table>
      <p><b>Riscos identificados:</b></p><ul>{itens}</ul>
      <p style="font-size:12px;color:#777">Ação sugerida: contatar o paciente e avaliar necessidade de atendimento.<br>
      Mensagem automática &mdash; protótipo acadêmico FIAP, não substitui avaliação médica.</p>
    </div>
  </div>
</body></html>""", subtype="html")
    return msg


def enviar_email(avaliacao: Avaliacao, leitura: Leitura) -> tuple[bool, str]:
    """Envia (ou simula) o e-mail. Retorna (sucesso, descrição do destino)."""
    msg = montar_email(avaliacao, leitura)

    if not config.SMTP_HOST:
        config.OUTBOX_DIR.mkdir(parents=True, exist_ok=True)
        nome = f"{datetime.now():%Y%m%d_%H%M%S_%f}_{leitura.paciente}_{avaliacao.nivel}.eml"
        caminho = Path(config.OUTBOX_DIR) / nome
        caminho.write_bytes(bytes(msg))
        return True, f"SIMULADO -> {caminho}"

    try:
        contexto = ssl.create_default_context()
        if config.SMTP_SSL:
            servidor = smtplib.SMTP_SSL(config.SMTP_HOST, config.SMTP_PORT, context=contexto, timeout=15)
        else:
            servidor = smtplib.SMTP(config.SMTP_HOST, config.SMTP_PORT, timeout=15)
            servidor.starttls(context=contexto)
        with servidor:
            if config.SMTP_USER:
                servidor.login(config.SMTP_USER, config.SMTP_PASS)
            servidor.send_message(msg)
        return True, f"SMTP {config.SMTP_HOST} -> {msg['To']}"
    except (smtplib.SMTPException, OSError) as e:
        return False, f"falha SMTP: {e}"

