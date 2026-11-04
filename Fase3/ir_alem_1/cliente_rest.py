"""
CardioIA - Fase 3 | Ir Além 1
Cliente REST da API CardioIA (envio e recebimento de dados via HTTP/JSON).

Usado pelo simulador do wearable, pela ponte MQTT e pelo monitor RPA.
"""
from __future__ import annotations

from typing import Iterable, Optional

import requests

import config


class CardioIAApiError(RuntimeError):
    pass


class CardioIAClient:
    """Wrapper fino sobre `requests` com sessão HTTP reutilizável, timeout,
    autenticação por chave de API e tratamento uniforme de erros."""

    def __init__(self, base_url: str = config.API_URL, api_key: str = config.API_KEY, timeout: float = 5.0):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.sessao = requests.Session()
        self.sessao.headers.update({"X-API-Key": api_key, "Content-Type": "application/json",
                                    "User-Agent": "CardioIA-Client/1.0"})

    # ------------------------------------------------------------ infraestrutura
    def _req(self, metodo: str, rota: str, **kwargs) -> dict:
        url = f"{self.base_url}{rota}"
        try:
            resp = self.sessao.request(metodo, url, timeout=self.timeout, **kwargs)
        except requests.RequestException as e:
            raise CardioIAApiError(f"falha de comunicação com {url}: {e}") from e
        try:
            dados = resp.json()
        except ValueError:
            dados = {"erro": resp.text}
        if resp.status_code >= 400:
            raise CardioIAApiError(f"HTTP {resp.status_code} em {metodo} {rota}: {dados.get('erro', dados)}")
        return dados

    # ------------------------------------------------------------ endpoints
    def health(self) -> dict:
        return self._req("GET", "/health")

    def enviar_leitura(self, leitura: dict) -> int:
        """POST de uma leitura. Retorna o id criado."""
        return self._req("POST", "/leituras", json=leitura)["criadas"][0]

    def enviar_lote(self, leituras: Iterable[dict]) -> dict:
        """POST de várias leituras (ex.: backlog sincronizado do Edge)."""
        return self._req("POST", "/leituras", json=list(leituras))

    def listar_leituras(self, paciente: Optional[str] = None, desde_id: int = 0, limite: int = 100) -> list[dict]:
        params = {"desde_id": desde_id, "limite": limite}
        if paciente:
            params["paciente"] = paciente
        return self._req("GET", "/leituras", params=params)["leituras"]

    def ultima_leitura(self, paciente: str) -> dict:
        return self._req("GET", f"/pacientes/{paciente}/ultima")

    def resumo(self, paciente: str) -> dict:
        return self._req("GET", f"/pacientes/{paciente}/resumo")

    def registrar_alerta(self, alerta: dict) -> int:
        return self._req("POST", "/alertas", json=alerta)["id"]

    def listar_alertas(self, paciente: Optional[str] = None, limite: int = 50) -> list[dict]:
        params = {"limite": limite}
        if paciente:
            params["paciente"] = paciente
        return self._req("GET", "/alertas", params=params)["alertas"]


if __name__ == "__main__":
    # Teste rápido de consumo: python cliente_rest.py  (com a API rodando)
    cli = CardioIAClient()
    print("Health:", cli.health())
    novo_id = cli.enviar_leitura({"paciente": "PAC-0001", "bpm": 82, "temp": 36.7, "umid": 52, "mov": 0.3})
    print("Leitura criada id:", novo_id)
    print("Última leitura + avaliação:", cli.ultima_leitura("PAC-0001"))
    print("Resumo:", cli.resumo("PAC-0001"))

