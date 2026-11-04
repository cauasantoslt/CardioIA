"""
CardioIA - Fase 3 | Ir Além 1
Robô de monitoramento contínuo (RPA aplicado à saúde digital).

Ciclo de operação:
  1. Consome novas leituras na API REST via `CardioIAClient` (GET /leituras?desde_id=...).
  2. Mantém uma janela deslizante das últimas leituras de cada paciente.
  3. Executa o motor de verificação de risco (`risco.avaliar`).
  4. Quando detecta risco (ATENÇÃO ou CRÍTICO), verifica o cooldown por código de
     risco para não inundar a equipe médica com e-mails repetidos.
  5. Dispara o e-mail automatizado (`notificador_email.enviar_email`) e registra
     a ocorrência de volta na API REST (POST /alertas).

Execução contínua:  python monitor_rpa.py
Ciclo único:        python monitor_rpa.py --once
"""
from __future__ import annotations

import argparse
import time
from collections import defaultdict, deque

import config
from cliente_rest import CardioIAApiError, CardioIAClient
from notificador_email import enviar_email
from risco import NORMAL, Avaliacao, Leitura, avaliar


class MonitorRPA:
    """Agente de monitoramento que consome a API REST, avalia riscos clínicos
    e aciona a automação de e-mail com controle de cooldown."""

    def __init__(
        self,
        cliente: CardioIAClient | None = None,
        cooldown_s: int = config.COOLDOWN_ALERTA_S,
        tamanho_janela: int = 10,
    ):
        self.cliente = cliente or CardioIAClient()
        self.cooldown_s = cooldown_s
        self.ultimo_id = 0
        self.historico: dict[str, deque[Leitura]] = defaultdict(lambda: deque(maxlen=tamanho_janela))
        # (paciente, codigo_risco) -> timestamp do último disparo de e-mail
        self.ultimo_disparo: dict[tuple[str, str], float] = {}

    def _filtrar_cooldown(self, paciente: str, avaliacao: Avaliacao, agora: float) -> list[str]:
        """Retorna os códigos de risco cujo tempo de cooldown já expirou."""
        notificar: list[str] = []
        for r in avaliacao.riscos:
            chave = (paciente, r.codigo)
            ultimo = self.ultimo_disparo.get(chave, 0.0)
            if agora - ultimo >= self.cooldown_s:
                notificar.append(r.codigo)
                self.ultimo_disparo[chave] = agora
        return notificar

    def processar_novas_leituras(self) -> list[dict]:
        """Busca leituras ainda não processadas, avalia riscos e dispara alertas."""
        leituras_raw = self.cliente.listar_leituras(desde_id=self.ultimo_id, limite=200)
        eventos_gerados: list[dict] = []

        for item in leituras_raw:
            leitura_id = int(item["id"])
            if leitura_id > self.ultimo_id:
                self.ultimo_id = leitura_id

            leitura = Leitura.de_dict(item)
            janela = self.historico[leitura.paciente]
            janela.append(leitura)

            avaliacao = avaliar(leitura, janela)
            if avaliacao.nivel == NORMAL:
                print(
                    f"[RPA] #{leitura_id:03d} | {leitura.paciente} | "
                    f"FC={leitura.bpm:3d} bpm | Temp={leitura.temp or 0:4.1f}°C | "
                    f"Mov={leitura.mov:.2f}g -> NORMAL"
                )
                continue

            codigos = [r.codigo for r in avaliacao.riscos]
            descricao = "; ".join(f"{r.codigo}: {r.descricao}" for r in avaliacao.riscos)
            agora = time.time()
            codigos_notificar = self._filtrar_cooldown(leitura.paciente, avaliacao, agora)

            email_ok = False
            destino_info = "suprimido por cooldown anti-spam"
            if codigos_notificar:
                email_ok, destino_info = enviar_email(avaliacao, leitura)

            alerta_id = self.cliente.registrar_alerta(
                {
                    "paciente": leitura.paciente,
                    "leitura_id": leitura_id,
                    "nivel": avaliacao.nivel,
                    "codigos": codigos,
                    "descricao": descricao,
                    "email_enviado": email_ok,
                }
            )

            print(
                f"[RPA] #{leitura_id:03d} | {leitura.paciente} | "
                f"FC={leitura.bpm:3d} bpm | Temp={leitura.temp or 0:4.1f}°C | "
                f"Mov={leitura.mov:.2f}g -> [{avaliacao.nivel}] {', '.join(codigos)} "
                f"(alerta #{alerta_id} | e-mail: {destino_info})"
            )
            eventos_gerados.append(
                {
                    "alerta_id": alerta_id,
                    "leitura_id": leitura_id,
                    "paciente": leitura.paciente,
                    "nivel": avaliacao.nivel,
                    "codigos": codigos,
                    "email_enviado": email_ok,
                    "destino": destino_info,
                }
            )

        return eventos_gerados

    def executar_loop(self, intervalo_s: float = config.INTERVALO_POLLING_S) -> None:
        print(f"[RPA] Monitor CardioIA iniciado (polling a cada {intervalo_s}s em {self.cliente.base_url})")
        try:
            while True:
                try:
                    self.processar_novas_leituras()
                except CardioIAApiError as e:
                    print(f"[RPA] Aviso de comunicação com a API: {e}")
                time.sleep(intervalo_s)
        except KeyboardInterrupt:
            print("\n[RPA] Monitor encerrado pelo usuário.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Monitor RPA de sinais vitais CardioIA")
    parser.add_argument("--once", action="store_true", help="Processa as leituras pendentes uma única vez e encerra")
    args = parser.parse_args()

    monitor = MonitorRPA()
    if args.once:
        monitor.processar_novas_leituras()
    else:
        monitor.executar_loop()

