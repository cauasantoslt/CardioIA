"""
CardioIA - Fase 3 | Ir Além 1
Simulador do wearable + Ponte MQTT -> REST.

Dois modos de uso:
  1. `--cenario` (padrão): simula uma sequência clínica completa de leituras
     enviadas via cliente REST (`CardioIAClient`), cobrindo:
       - Estado basal normal (repouso e caminhada leve)
       - Episódio de febre + taquicardia sustentada (critérios SIRS / sepse)
       - Ausência prolongada de movimento (atenção) seguida de bradicardia (síncope)
       - Queda detectada pelo acelerômetro
       - Sincronização em lote de leituras coletadas offline (Edge backlog)
  2. `--mqtt-bridge`: assina os tópicos MQTT do ESP32 (`telemetria` e `backlog`)
     no broker HiveMQ e encaminha cada leitura recebida para a API REST.
"""
from __future__ import annotations

import argparse
import json
import time

import config
from cliente_rest import CardioIAClient


def construir_cenario_clinico(paciente: str = "PAC-0001") -> list[dict]:
    """Gera uma sequência realista de leituras cobrindo todos os perfis de risco."""
    base_ts = time.time() - 60
    amostras = [
        # 1-2: basal normal
        {"bpm": 74, "temp": 36.5, "umid": 52.0, "mov": 0.22, "origem": "live", "alertas": []},
        {"bpm": 78, "temp": 36.6, "umid": 53.0, "mov": 0.30, "origem": "live", "alertas": []},
        # 3-5: episódio de febre + taquicardia sustentada (3 leituras > 120 bpm + T > 38 °C)
        {"bpm": 128, "temp": 38.4, "umid": 68.0, "mov": 0.18, "origem": "live", "alertas": ["TAQUICARDIA", "FEBRE"]},
        {"bpm": 134, "temp": 38.7, "umid": 72.0, "mov": 0.15, "origem": "live", "alertas": ["TAQUICARDIA", "FEBRE"]},
        {"bpm": 138, "temp": 38.9, "umid": 75.0, "mov": 0.12, "origem": "live", "alertas": ["TAQUICARDIA", "FEBRE"]},
        # 6: retorno gradual + início de imobilidade (6 leituras com mov < 0.05 g)
        {"bpm": 76, "temp": 36.8, "umid": 55.0, "mov": 0.01, "origem": "live", "alertas": []},
        {"bpm": 72, "temp": 36.7, "umid": 54.0, "mov": 0.01, "origem": "live", "alertas": []},
        {"bpm": 70, "temp": 36.6, "umid": 54.0, "mov": 0.00, "origem": "live", "alertas": []},
        {"bpm": 68, "temp": 36.6, "umid": 53.0, "mov": 0.01, "origem": "live", "alertas": []},
        {"bpm": 66, "temp": 36.5, "umid": 53.0, "mov": 0.00, "origem": "live", "alertas": []},
        # 11: 6ª leitura imóvel com FC normal -> AUSENCIA_MOVIMENTO (ATENCAO)
        {"bpm": 65, "temp": 36.5, "umid": 53.0, "mov": 0.00, "origem": "live", "alertas": ["IMOBILIDADE"]},
        # 12: ainda imóvel + bradicardia acentuada -> IMOBILIDADE_COM_FC_BAIXA + BRADICARDIA (CRITICO)
        {"bpm": 42, "temp": 36.2, "umid": 54.0, "mov": 0.00, "origem": "live", "alertas": ["BRADICARDIA", "IMOBILIDADE"]},
        # 13: pico de aceleração no MPU6050 -> QUEDA
        {"bpm": 96, "temp": 36.6, "umid": 58.0, "mov": 1.85, "origem": "live", "alertas": ["QUEDA"]},
    ]
    for i, a in enumerate(amostras):
        a["paciente"] = paciente
        a["device"] = "wear01"
        a["ts"] = round(base_ts + i * 5, 2)
    return amostras


def executar_cenario(cliente: CardioIAClient, intervalo_s: float = 0.2) -> list[int]:
    """Envia o cenário clínico leitura por leitura + um lote offline (Edge sync)."""
    amostras = construir_cenario_clinico()
    ids_criados: list[int] = []
    print(f"[SIMULADOR] Enviando {len(amostras)} leituras em tempo real para {cliente.base_url} ...")
    for a in amostras:
        lid = cliente.enviar_leitura(a)
        ids_criados.append(lid)
        print(
            f"  -> POST /leituras id={lid:03d} | FC={a['bpm']:3d} bpm | "
            f"Temp={a['temp']:.1f}°C | Mov={a['mov']:.2f}g | origem={a['origem']}"
        )
        if intervalo_s > 0:
            time.sleep(intervalo_s)

    # Simula sincronização em lote de 3 amostras gravadas offline no SPIFFS/RAM do ESP32
    lote_offline = [
        {
            "paciente": "PAC-0001",
            "device": "wear01",
            "origem": "buffer",
            "ts": round(time.time() - 120 + k * 5, 2),
            "bpm": bpm,
            "temp": temp,
            "umid": 56.0,
            "mov": 0.20,
            "alertas": ["HIPOTERMIA"] if temp < 35.0 else [],
        }
        for k, (bpm, temp) in enumerate([(74, 36.5), (75, 36.4), (58, 34.6)])
    ]
    res_lote = cliente.enviar_lote(lote_offline)
    ids_criados.extend(res_lote["criadas"])
    print(f"  -> POST /leituras (lote offline do Edge): criadas={res_lote['criadas']}")
    return ids_criados


def executar_ponte_mqtt(cliente: CardioIAClient) -> None:
    """Ouve os tópicos MQTT do ESP32 e replica cada amostra na API REST."""
    import paho.mqtt.client as mqtt

    topico = f"{config.MQTT_TOPIC_BASE}/#"

    def on_connect( mqttc, _userdata, _flags, rc, _props=None):
        print(f"[PONTE MQTT->REST] Conectado a {config.MQTT_HOST}:{config.MQTT_PORT} (rc={rc}). Assinando {topico}")
        mqttc.subscribe([(f"{config.MQTT_TOPIC_BASE}/telemetria", 0), (f"{config.MQTT_TOPIC_BASE}/backlog", 0)])

    def on_message(_mqttc, _userdata, msg):
        try:
            payload = json.loads(msg.payload.decode("utf-8"))
            lid = cliente.enviar_leitura(payload)
            print(f"[PONTE] {msg.topic} -> POST /leituras id={lid} (FC={payload.get('bpm')} bpm)")
        except Exception as e:
            print(f"[PONTE] Erro ao encaminhar mensagem de {msg.topic}: {e}")

    mqttc = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    mqttc.on_connect = on_connect
    mqttc.on_message = on_message
    mqttc.connect(config.MQTT_HOST, config.MQTT_PORT, keepalive=60)
    mqttc.loop_forever()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Simulador de wearable e ponte MQTT -> REST")
    parser.add_argument("--mqtt-bridge", action="store_true", help="Escuta o broker MQTT e encaminha para a API REST")
    parser.add_argument("--intervalo", type=float, default=0.2, help="Intervalo entre envios no modo cenário (s)")
    args = parser.parse_args()

    cli = CardioIAClient()
    if args.mqtt_bridge:
        executar_ponte_mqtt(cli)
    else:
        executar_cenario(cli, intervalo_s=args.intervalo)

