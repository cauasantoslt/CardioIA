"""
CardioIA - Fase 3 | Ir Além 1
Configurações centralizadas (lidas de variáveis de ambiente ou do arquivo .env).

Nenhuma credencial fica no código: copie `.env.example` para `.env` e preencha.
"""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent


def _carregar_env(caminho: Path) -> None:
    """Loader minimalista de .env (sem dependência externa). Não sobrescreve
    variáveis que já existam no ambiente do sistema operacional."""
    if not caminho.exists():
        return
    for linha in caminho.read_text(encoding="utf-8").splitlines():
        linha = linha.strip()
        if not linha or linha.startswith("#") or "=" not in linha:
            continue
        chave, valor = linha.split("=", 1)
        os.environ.setdefault(chave.strip(), valor.strip().strip('"').strip("'"))


_carregar_env(BASE_DIR / ".env")

# ---------------------------------------------------------------- API REST
API_HOST = os.getenv("CARDIOIA_API_HOST", "127.0.0.1")
API_PORT = int(os.getenv("CARDIOIA_API_PORT", "5000"))
API_URL = os.getenv("CARDIOIA_API_URL", f"http://{API_HOST}:{API_PORT}/api/v1")
API_KEY = os.getenv("CARDIOIA_API_KEY", "cardioia-dev-key")   # header X-API-Key
DB_PATH = Path(os.getenv("CARDIOIA_DB_PATH", BASE_DIR / "data" / "cardioia.db"))

# ---------------------------------------------------------------- E-mail
# Sem SMTP_HOST configurado => modo SIMULADO (gera arquivos .eml em outbox/).
SMTP_HOST = os.getenv("SMTP_HOST", "")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASS = os.getenv("SMTP_PASS", "")
SMTP_SSL = os.getenv("SMTP_SSL", "0") == "1"          # 1 = SMTPS (porta 465)
EMAIL_REMETENTE = os.getenv("EMAIL_REMETENTE", "alertas@cardioia.local")
EMAIL_DESTINO = [e.strip() for e in os.getenv("EMAIL_DESTINO", "plantao.cardiologia@cardioia.local").split(",") if e.strip()]
OUTBOX_DIR = Path(os.getenv("CARDIOIA_OUTBOX", BASE_DIR / "outbox"))

# ---------------------------------------------------------------- Monitor (RPA)
INTERVALO_POLLING_S = float(os.getenv("CARDIOIA_POLLING_S", "2"))
COOLDOWN_ALERTA_S = int(os.getenv("CARDIOIA_COOLDOWN_S", "600"))   # 1 e-mail por risco a cada 10 min

# ---------------------------------------------------------------- MQTT (ponte com o ESP32)
MQTT_HOST = os.getenv("MQTT_HOST", "broker.hivemq.com")
MQTT_PORT = int(os.getenv("MQTT_PORT", "1883"))
MQTT_TOPIC_BASE = os.getenv("MQTT_TOPIC_BASE", "cardioia/rm566599/wear01")

