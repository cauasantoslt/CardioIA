"""
CardioIA - Fase 3 | Parte 2 (Fog/Cloud Computing)
Publicador MQTT que simula o ESP32 enviando telemetria, alertas, status e
sincronização de backlog para o broker `broker.hivemq.com`.

Permite testar e demonstrar o dashboard no Node-RED mesmo sem abrir o Wokwi.

Execução contínua:  python simulador_mqtt.py
Ciclo rápido (demo): python simulador_mqtt.py --demo
"""
from __future__ import annotations

import argparse
import json
import math
import random
import time

import paho.mqtt.client as mqtt

BROKER = "broker.hivemq.com"
PORT = 1883
TOPIC_BASE = "cardioia/rm566599/wear01"


def montar_payload(seq: int, bpm: int, temp: float, umid: float, mov: float, origem: str = "live") -> dict:
    alertas: list[str] = []
    critico = False
    if bpm > 120:
        alertas.append("TAQUICARDIA")
        critico = True
    elif 0 < bpm < 50:
        alertas.append("BRADICARDIA")
        critico = True
    elif bpm == 0:
        alertas.append("SEM_PULSO")
        critico = True

    if temp > 38.0:
        alertas.append("FEBRE")
        critico = True
    elif temp < 35.0:
        alertas.append("HIPOTERMIA")
        critico = True

    if mov > 2.5:
        alertas.append("QUEDA")
        critico = True
    elif mov < 0.03 and seq % 8 == 0:
        alertas.append("IMOBILIDADE")

    sev = 2 if critico else (1 if alertas else 0)
    nivel = ["NORMAL", "ATENCAO", "CRITICO"][sev]
    return {
        "device": "wear01",
        "paciente": "PAC-0001",
        "origem": origem,
        "ts": int(time.time()),
        "uptime_s": seq * 2,
        "bpm": bpm,
        "temp": round(temp, 1),
        "umid": round(umid, 1),
        "mov": round(mov, 2),
        "sev": sev,
        "nivel": nivel,
        "alertas": alertas,
        "flags": sev,
    }


def publicar_status(cli: mqtt.Client, estado: str, buf_n: int = 0, buf_c: int = 0, sync: int = 0) -> None:
    status = {
        "device": "wear01",
        "estado": estado,
        "backend": "SPIFFS",
        "buffer_normal": buf_n,
        "buffer_critico": buf_c,
        "capacidade": 6600,
        "descartadas": 0,
        "sincronizadas": sync,
        "modo": "AUTO",
        "rssi": -58,
        "uptime_s": int(time.time()) % 3600,
    }
    cli.publish(f"{TOPIC_BASE}/status", json.dumps(status), qos=1, retain=True)


def executar(demo: bool = False) -> None:
    cli = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    cli.connect(BROKER, PORT, keepalive=60)
    cli.loop_start()

    try:
        publicar_status(cli, "online", sync=3)
        roteiro = [
            (74, 36.5, 54.0, 0.22),
            (78, 36.6, 55.0, 0.28),
            (82, 36.7, 55.0, 0.31),
            (128, 38.4, 68.0, 0.18),  # taquicardia + febre
            (135, 38.7, 72.0, 0.15),  # taquicardia + febre
            (76, 36.6, 56.0, 0.25),   # normalização
        ]
        seq = 1
        while True:
            for bpm, temp, umid, mov in roteiro:
                if not demo:
                    bpm += random.randint(-2, 2)
                    temp += math.sin(seq / 3) * 0.1
                amostra = montar_payload(seq, bpm, temp, umid, mov, origem="live")
                cli.publish(f"{TOPIC_BASE}/telemetria", json.dumps(amostra), qos=0)
                print(
                    f"[MQTT->{BROKER}] #{seq:03d} | FC={amostra['bpm']:3d} bpm | "
                    f"Temp={amostra['temp']:.1f}°C | Nível={amostra['nivel']} {amostra['alertas']}"
                )
                if amostra["sev"] == 2:
                    alerta = {"evento": "ALERTA", "atrasado": False, "amostra": amostra}
                    cli.publish(f"{TOPIC_BASE}/alerta", json.dumps(alerta), qos=1)
                seq += 1
                time.sleep(0.4 if demo else 2.0)
            if demo:
                break
    finally:
        cli.loop_stop()
        cli.disconnect()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Simulador MQTT do wearable CardioIA")
    parser.add_argument("--demo", action="store_true", help="Publica 6 amostras de demonstração e encerra")
    args = parser.parse_args()
    executar(demo=args.demo)

