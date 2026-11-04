"""
CardioIA - Fase 3 | Ir Além 1
API REST de sinais vitais (Flask + SQLite).

Endpoints (prefixo /api/v1, autenticação por header `X-API-Key`):
    GET  /health                          -> verificação de saúde (sem auth)
    POST /leituras                        -> recebe 1 leitura (obj) ou várias (lista)
    GET  /leituras?paciente=&desde_id=&limite=
    GET  /pacientes/<id>/ultima           -> última leitura + avaliação de risco
    GET  /pacientes/<id>/resumo           -> estatísticas do paciente
    POST /alertas                         -> registra alerta gerado pelo monitor
    GET  /alertas?paciente=&limite=

Execução:  python api_server.py
"""
from __future__ import annotations

import sqlite3
import time
from functools import wraps

from flask import Flask, g, jsonify, request

import config
from risco import Leitura, avaliar, validar_payload

app = Flask(__name__)
app.json.ensure_ascii = False
app.json.sort_keys = False

SCHEMA = """
CREATE TABLE IF NOT EXISTS leituras (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    paciente    TEXT    NOT NULL,
    device      TEXT,
    origem      TEXT,
    ts          REAL    NOT NULL,      -- epoch da coleta (UTC)
    recebido_em REAL    NOT NULL,      -- epoch de chegada na API
    bpm         INTEGER NOT NULL,
    temp        REAL,
    umid        REAL,
    mov         REAL,
    alertas_dispositivo TEXT
);
CREATE INDEX IF NOT EXISTS ix_leituras_pac ON leituras (paciente, id);
CREATE TABLE IF NOT EXISTS alertas (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    paciente   TEXT NOT NULL,
    leitura_id INTEGER,
    nivel      TEXT NOT NULL,
    codigos    TEXT NOT NULL,
    descricao  TEXT NOT NULL,
    email_enviado INTEGER DEFAULT 0,
    criado_em  REAL NOT NULL
);
"""


# ---------------------------------------------------------------- Banco
def get_db() -> sqlite3.Connection:
    if "db" not in g:
        config.DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        g.db = sqlite3.connect(config.DB_PATH)
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def fechar_db(_exc):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db() -> None:
    config.DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(config.DB_PATH) as con:
        con.executescript(SCHEMA)


def _row_leitura(r: sqlite3.Row) -> dict:
    d = dict(r)
    d["alertas_dispositivo"] = [a for a in (d.get("alertas_dispositivo") or "").split(",") if a]
    return d


# ---------------------------------------------------------------- Segurança
def requer_api_key(fn):
    """Autenticação simples por chave de API (em produção: OAuth2/JWT + HTTPS)."""
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if request.headers.get("X-API-Key") != config.API_KEY:
            return jsonify(erro="não autorizado: header X-API-Key ausente ou inválido"), 401
        return fn(*args, **kwargs)
    return wrapper


# ---------------------------------------------------------------- Rotas
@app.get("/api/v1/health")
def health():
    return jsonify(status="ok", servico="CardioIA API", versao="1.0", hora=time.time())


@app.post("/api/v1/leituras")
@requer_api_key
def criar_leituras():
    corpo = request.get_json(silent=True)
    if corpo is None:
        return jsonify(erro="corpo JSON inválido"), 400
    itens = corpo if isinstance(corpo, list) else [corpo]

    db = get_db()
    criadas, rejeitadas = [], []
    agora = time.time()
    for i, d in enumerate(itens):
        erros = validar_payload(d) if isinstance(d, dict) else ["item não é um objeto JSON"]
        if erros:
            rejeitadas.append({"indice": i, "erros": erros})
            continue
        l = Leitura.de_dict(d)
        cur = db.execute(
            "INSERT INTO leituras (paciente, device, origem, ts, recebido_em, bpm, temp, umid, mov, alertas_dispositivo)"
            " VALUES (?,?,?,?,?,?,?,?,?,?)",
            (l.paciente, l.device, l.origem, float(l.ts or agora), agora, l.bpm, l.temp, l.umid, l.mov,
             ",".join(l.alertas_dispositivo)),
        )
        criadas.append(cur.lastrowid)
    db.commit()

    status = 201 if criadas else 422
    return jsonify(criadas=criadas, rejeitadas=rejeitadas), status


@app.get("/api/v1/leituras")
@requer_api_key
def listar_leituras():
    paciente = request.args.get("paciente")
    desde_id = request.args.get("desde_id", 0, type=int)
    limite = min(request.args.get("limite", 100, type=int), 1000)
    sql = "SELECT * FROM leituras WHERE id > ?"
    params: list = [desde_id]
    if paciente:
        sql += " AND paciente = ?"
        params.append(paciente)
    sql += " ORDER BY id ASC LIMIT ?"
    params.append(limite)
    rows = get_db().execute(sql, params).fetchall()
    return jsonify(leituras=[_row_leitura(r) for r in rows], total=len(rows))


@app.get("/api/v1/pacientes/<paciente>/ultima")
@requer_api_key
def ultima_leitura(paciente):
    rows = get_db().execute(
        "SELECT * FROM leituras WHERE paciente = ? ORDER BY id DESC LIMIT 10", (paciente,)
    ).fetchall()
    if not rows:
        return jsonify(erro=f"nenhuma leitura para o paciente {paciente}"), 404
    historico = [Leitura.de_dict(_row_leitura(r)) for r in reversed(rows)]
    avaliacao = avaliar(historico[-1], historico)
    return jsonify(leitura=_row_leitura(rows[0]), avaliacao=avaliacao.to_dict())


@app.get("/api/v1/pacientes/<paciente>/resumo")
@requer_api_key
def resumo_paciente(paciente):
    db = get_db()
    r = db.execute(
        "SELECT COUNT(*) n, ROUND(AVG(bpm),1) bpm_medio, MIN(bpm) bpm_min, MAX(bpm) bpm_max,"
        " ROUND(AVG(temp),2) temp_media, MAX(temp) temp_max, MIN(ts) inicio, MAX(ts) fim"
        " FROM leituras WHERE paciente = ?", (paciente,)
    ).fetchone()
    if not r["n"]:
        return jsonify(erro=f"nenhuma leitura para o paciente {paciente}"), 404
    n_alertas = db.execute("SELECT COUNT(*) FROM alertas WHERE paciente = ?", (paciente,)).fetchone()[0]
    return jsonify(paciente=paciente, leituras=r["n"], alertas=n_alertas,
                   bpm={"medio": r["bpm_medio"], "min": r["bpm_min"], "max": r["bpm_max"]},
                   temperatura={"media": r["temp_media"], "max": r["temp_max"]},
                   periodo={"inicio": r["inicio"], "fim": r["fim"]})


@app.post("/api/v1/alertas")
@requer_api_key
def criar_alerta():
    d = request.get_json(silent=True) or {}
    faltando = [c for c in ("paciente", "nivel", "codigos", "descricao") if c not in d]
    if faltando:
        return jsonify(erro=f"campos obrigatórios ausentes: {faltando}"), 400
    db = get_db()
    cur = db.execute(
        "INSERT INTO alertas (paciente, leitura_id, nivel, codigos, descricao, email_enviado, criado_em)"
        " VALUES (?,?,?,?,?,?,?)",
        (d["paciente"], d.get("leitura_id"), d["nivel"], ",".join(d["codigos"]),
         d["descricao"], int(bool(d.get("email_enviado"))), time.time()),
    )
    db.commit()
    return jsonify(id=cur.lastrowid), 201


@app.get("/api/v1/alertas")
@requer_api_key
def listar_alertas():
    paciente = request.args.get("paciente")
    limite = min(request.args.get("limite", 50, type=int), 500)
    sql, params = "SELECT * FROM alertas", []
    if paciente:
        sql += " WHERE paciente = ?"
        params.append(paciente)
    sql += " ORDER BY id DESC LIMIT ?"
    params.append(limite)
    rows = get_db().execute(sql, params).fetchall()
    alertas = []
    for r in rows:
        a = dict(r)
        a["codigos"] = a["codigos"].split(",")
        a["email_enviado"] = bool(a["email_enviado"])
        alertas.append(a)
    return jsonify(alertas=alertas, total=len(alertas))


@app.errorhandler(404)
def nao_encontrado(_e):
    return jsonify(erro="rota não encontrada"), 404


init_db()

if __name__ == "__main__":
    print(f"CardioIA API em http://{config.API_HOST}:{config.API_PORT}/api/v1  (DB: {config.DB_PATH})")
    app.run(host=config.API_HOST, port=config.API_PORT, debug=False)

