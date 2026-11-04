"""
CardioIA - Fase 3 | Ir Além 1
Demonstração integrada ponta a ponta (API REST + Cliente + Motor de Risco + E-mail RPA).

Este script executa todo o ciclo de forma autônoma em um único comando:
  1. Inicializa um banco SQLite limpo de demonstração e sobe o servidor Flask
     (`api_server.app`) em uma thread em segundo plano.
  2. Usa o `CardioIAClient` (`simulador_wearable.executar_cenario`) para enviar
     leituras individuais e em lote (simulando tempo real + sincronização offline).
  3. Executa o `MonitorRPA` para consumir as leituras via GET, aplicar as regras
     clínicas (instantâneas e de janela deslizante), gerar os e-mails `.eml` em
     `outbox/` e registrar os alertas via POST.
  4. Consulta os endpoints de resumo (`/pacientes/PAC-0001/resumo`,
     `/pacientes/PAC-0001/ultima` e `/alertas`) e exibe o relatório final.

Execução:  python demo_completa.py
"""
from __future__ import annotations

import shutil
import threading
import time
from werkzeug.serving import make_server

import api_server
import config
from cliente_rest import CardioIAClient
from monitor_rpa import MonitorRPA
from simulador_wearable import executar_cenario


class _ServidorThread(threading.Thread):
    def __init__(self, host: str, port: int):
        super().__init__(daemon=True)
        self.srv = make_server(host, port, api_server.app)

    def run(self) -> None:
        self.srv.serve_forever()

    def parar(self) -> None:
        self.srv.shutdown()


def main() -> None:
    print("=" * 78)
    print("  CardioIA - Fase 3 (Ir Além 1): Comunicação REST, Risco Clínico e E-mail RPA")
    print("=" * 78)

    # Limpa artefatos de execuções anteriores para reprodutibilidade
    if config.DB_PATH.exists():
        config.DB_PATH.unlink()
    if config.OUTBOX_DIR.exists():
        shutil.rmtree(config.OUTBOX_DIR)
    api_server.init_db()

    servidor = _ServidorThread(config.API_HOST, config.API_PORT)
    servidor.start()
    time.sleep(0.3)

    try:
        cliente = CardioIAClient()
        saude = cliente.health()
        print(f"\n[1/4] API REST online em {cliente.base_url} -> status={saude['status']}\n")

        print("[2/4] Executando simulador do wearable (envio HTTP POST individual + lote offline)...")
        ids = executar_cenario(cliente, intervalo_s=0.05)
        print(f"      Total de leituras persistidas: {len(ids)}\n")

        print("[3/4] Executando ciclo do Monitor RPA (consumo HTTP GET + avaliação + disparo de e-mail)...")
        monitor = MonitorRPA(cliente=cliente, cooldown_s=600)
        eventos = monitor.processar_novas_leituras()
        print(f"      Total de eventos de risco detectados: {len(eventos)}\n")

        print("[4/4] Consultando consolidação clínica na API REST...")
        resumo = cliente.resumo("PAC-0001")
        ultima = cliente.ultima_leitura("PAC-0001")
        alertas = cliente.listar_alertas("PAC-0001")
        emls = sorted(config.OUTBOX_DIR.glob("*.eml")) if config.OUTBOX_DIR.exists() else []

        print("\n" + "-" * 78)
        print("  RESUMO CONSOLIDADO DO PACIENTE (GET /api/v1/pacientes/PAC-0001/resumo)")
        print("-" * 78)
        print(f"  Paciente ..........: {resumo['paciente']}")
        print(f"  Leituras recebidas : {resumo['leituras']}")
        print(f"  Alertas registrados: {resumo['alertas']}")
        print(
            f"  Frequência cardíaca: média={resumo['bpm']['medio']} bpm "
            f"(mín={resumo['bpm']['min']} | máx={resumo['bpm']['max']})"
        )
        print(
            f"  Temperatura .......: média={resumo['temperatura']['media']} °C "
            f"(máx={resumo['temperatura']['max']} °C)"
        )
        print(f"  Última avaliação ..: nível={ultima['avaliacao']['nivel']}")
        print(f"  E-mails em outbox/ : {len(emls)} arquivo(s) .eml gerado(s)")
        for arq in emls:
            print(f"    * {arq.name}")
        print("-" * 78)

        # Verificações automatizadas de integridade
        assert resumo["leituras"] == 16, f"Esperado 16 leituras, obteve {resumo['leituras']}"
        assert len(alertas) >= 5, f"Esperado ao menos 5 alertas, obteve {len(alertas)}"
        assert len(emls) >= 4, f"Esperado ao menos 4 e-mails em outbox/, obteve {len(emls)}"
        print("[OK] Todas as verificações de ponta a ponta passaram com sucesso!")
    finally:
        servidor.parar()


if __name__ == "__main__":
    main()

