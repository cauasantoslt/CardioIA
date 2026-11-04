"""
CardioIA - Fase 3 | Ir Além 1
Motor de verificação de risco clínico.

Duas camadas de regras:
  1. Regras INSTANTÂNEAS  - avaliam uma única leitura (ex.: taquicardia, febre).
  2. Regras de JANELA     - avaliam o histórico recente do paciente
                            (ex.: ausência de movimento, taquicardia sustentada).

Os limiares são os mesmos usados no firmware do ESP32 (Edge) e no Node-RED
(Fog), garantindo consistência entre as camadas da arquitetura.

Aviso: protótipo acadêmico de apoio à decisão. Não substitui avaliação médica.
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Iterable, Optional

# ---------------------------------------------------------------- Limiares
LIMITES = {
    "bpm_taquicardia": 120,      # > 120 bpm
    "bpm_bradicardia": 50,       # < 50 bpm
    "temp_febre": 38.0,          # > 38,0 °C
    "temp_hipotermia": 35.0,     # < 35,0 °C
    "sirs_bpm": 90,              # critério SIRS de FC
    "mov_imobilidade_g": 0.05,   # desvio de 1 g abaixo disso = parado
    "janela_imobilidade": 6,     # nº de leituras consecutivas paradas
    "janela_taqui_sustentada": 3,
}

CRITICO = "CRITICO"
ATENCAO = "ATENCAO"
NORMAL = "NORMAL"
_PESO = {NORMAL: 0, ATENCAO: 1, CRITICO: 2}


@dataclass
class Leitura:
    """Uma amostra de sinais vitais enviada pelo wearable."""
    paciente: str
    bpm: int
    temp: Optional[float]
    umid: Optional[float] = None
    mov: float = 0.0
    ts: Optional[float] = None
    device: str = "wear01"
    origem: str = "live"
    alertas_dispositivo: list[str] = field(default_factory=list)

    @classmethod
    def de_dict(cls, d: dict) -> "Leitura":
        """Aceita tanto o payload REST quanto o JSON publicado pelo ESP32."""
        return cls(
            paciente=str(d.get("paciente", "")),
            bpm=int(d.get("bpm", 0)),
            temp=None if d.get("temp") is None else float(d["temp"]),
            umid=None if d.get("umid") is None else float(d["umid"]),
            mov=float(d.get("mov", 0.0) or 0.0),
            ts=d.get("ts") or None,
            device=str(d.get("device", "wear01")),
            origem=str(d.get("origem", "live")),
            alertas_dispositivo=list(d.get("alertas_dispositivo", d.get("alertas", [])) or []),
        )


@dataclass
class Risco:
    codigo: str
    nivel: str
    descricao: str

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class Avaliacao:
    paciente: str
    nivel: str
    riscos: list[Risco]

    @property
    def critica(self) -> bool:
        return self.nivel == CRITICO

    def to_dict(self) -> dict:
        return {"paciente": self.paciente, "nivel": self.nivel,
                "riscos": [r.to_dict() for r in self.riscos]}


# ---------------------------------------------------------------- Validação
def validar_payload(d: dict) -> list[str]:
    """Valida faixas fisicamente plausíveis (rejeita lixo antes de persistir)."""
    erros = []
    if not d.get("paciente"):
        erros.append("campo 'paciente' é obrigatório")
    bpm = d.get("bpm")
    if not isinstance(bpm, (int, float)) or not 0 <= bpm <= 300:
        erros.append("'bpm' deve ser numérico entre 0 e 300")
    temp = d.get("temp")
    if temp is not None and (not isinstance(temp, (int, float)) or not 25 <= temp <= 45):
        erros.append("'temp' deve ser null ou numérico entre 25 e 45 °C")
    umid = d.get("umid")
    if umid is not None and (not isinstance(umid, (int, float)) or not 0 <= umid <= 100):
        erros.append("'umid' deve ser null ou numérico entre 0 e 100 %")
    mov = d.get("mov", 0)
    if not isinstance(mov, (int, float)) or mov < 0:
        erros.append("'mov' deve ser numérico >= 0")
    return erros


# ---------------------------------------------------------------- Regras
def regras_instantaneas(l: Leitura) -> list[Risco]:
    L = LIMITES
    riscos: list[Risco] = []

    if l.bpm > L["bpm_taquicardia"]:
        riscos.append(Risco("TAQUICARDIA", CRITICO, f"Frequência cardíaca de {l.bpm} bpm (> {L['bpm_taquicardia']})"))
    elif 0 < l.bpm < L["bpm_bradicardia"]:
        riscos.append(Risco("BRADICARDIA", CRITICO, f"Frequência cardíaca de {l.bpm} bpm (< {L['bpm_bradicardia']})"))
    elif l.bpm == 0 or "SEM_PULSO" in l.alertas_dispositivo:
        riscos.append(Risco("SEM_PULSO", CRITICO, "Nenhum batimento detectado pelo sensor"))

    if l.temp is not None:
        if l.temp > L["temp_febre"]:
            riscos.append(Risco("FEBRE", CRITICO, f"Temperatura de {l.temp:.1f} °C (> {L['temp_febre']})"))
        elif l.temp < L["temp_hipotermia"]:
            riscos.append(Risco("HIPOTERMIA", CRITICO, f"Temperatura de {l.temp:.1f} °C (< {L['temp_hipotermia']})"))

    # Regra combinada: critérios SIRS (FC > 90 + T > 38) => suspeita de quadro infeccioso sistêmico
    if l.temp is not None and l.temp > L["temp_febre"] and l.bpm > L["sirs_bpm"]:
        riscos.append(Risco("SUSPEITA_SEPSE", CRITICO,
                            f"Febre + FC elevada ({l.bpm} bpm, {l.temp:.1f} °C) - critérios SIRS"))

    if "QUEDA" in l.alertas_dispositivo:
        riscos.append(Risco("QUEDA", CRITICO, "Pico de aceleração compatível com queda"))
    if "FALHA_SENSOR" in l.alertas_dispositivo or l.temp is None:
        riscos.append(Risco("FALHA_SENSOR", ATENCAO, "Leitura de temperatura indisponível"))
    return riscos


def regras_janela(historico: list[Leitura]) -> list[Risco]:
    """`historico` em ordem cronológica, com a leitura atual por último."""
    L = LIMITES
    riscos: list[Risco] = []
    if not historico:
        return riscos

    n = L["janela_imobilidade"]
    ultimas = historico[-n:]
    imovel = len(ultimas) == n and all(x.mov < L["mov_imobilidade_g"] for x in ultimas)
    if imovel or "IMOBILIDADE" in historico[-1].alertas_dispositivo:
        atual = historico[-1]
        # Ausência de movimento + FC baixa/ausente = possível síncope/PCR
        if atual.bpm < L["bpm_bradicardia"]:
            riscos.append(Risco("IMOBILIDADE_COM_FC_BAIXA", CRITICO,
                                f"Paciente imóvel há {n} leituras com FC de {atual.bpm} bpm - possível síncope"))
        else:
            riscos.append(Risco("AUSENCIA_MOVIMENTO", ATENCAO,
                                f"Sem movimento nas últimas {n} leituras"))

    k = L["janela_taqui_sustentada"]
    if len(historico) >= k and all(x.bpm > L["bpm_taquicardia"] for x in historico[-k:]):
        riscos.append(Risco("TAQUICARDIA_SUSTENTADA", CRITICO,
                            f"FC > {L['bpm_taquicardia']} bpm em {k} leituras consecutivas"))
    return riscos


def avaliar(leitura: Leitura, historico: Optional[Iterable[Leitura]] = None) -> Avaliacao:
    """Avalia a leitura atual + o histórico recente e devolve o nível consolidado."""
    hist = list(historico or [])
    if not hist or hist[-1] is not leitura:
        hist.append(leitura)
    riscos = regras_instantaneas(leitura) + regras_janela(hist)
    nivel = max((r.nivel for r in riscos), key=_PESO.get, default=NORMAL)
    return Avaliacao(leitura.paciente, nivel, riscos)

