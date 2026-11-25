"""
CardioIA — Fase 4 (Parte 2 & Ir Além 2): Backend REST em Flask + Protótipo Web Interativo.

Serve:
1. Interface Web do Assistente Cardiológico Virtual (GET /) — Protótipo Parte 2.
2. API REST JSON com CORS para integração com o App Mobile em React Native (Ir Além 2):
   - GET  /api/v1/health            -> status do serviço, modelos carregados e resumo de métricas
   - GET  /api/v1/models/metrics    -> métricas completas (CNN do Zero vs. ResNet18 Transfer Learning)
   - GET  /api/v1/samples           -> lista de exames de ECG reais do conjunto de teste (com preview)
   - POST /api/v1/predict           -> classifica imagem enviada (multipart 'image', base64 ou 'sample_id')
   - GET  /api/v1/history           -> histórico persistido em SQLite das classificações realizadas

Execução:
    python Fase4/backend/app.py
"""
from __future__ import annotations

import base64
import io
import os
import sqlite3
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
from flask import Flask, jsonify, render_template, request
from flask.json.provider import DefaultJSONProvider
from flask_cors import CORS
from PIL import Image

# Garante resolução do pacote Fase4 tanto via CLI direto quanto no Pylance/VS Code
BACKEND_DIR = Path(__file__).resolve().parent
FASE4_DIR = BACKEND_DIR.parent
PROJECT_ROOT = FASE4_DIR.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from Fase4.src.modelos import (  # noqa: E402
    CardioPredictor,
    pil_para_base64_png,
    preparar_roi_original_e_auditoria,
)
from Fase4.src.preprocessamento import (  # noqa: E402
    CLASS_INFO,
    CLASSES,
    compor_sobre_branco,
    localizar_dataset_ecg,
    preprocessar_imagem_ecg,
)

MODELS_DIR = FASE4_DIR / "models"
DB_PATH = BACKEND_DIR / "data" / "cardioia_vision.db"

app = Flask(__name__, template_folder=str(BACKEND_DIR / "templates"))
if isinstance(app.json, DefaultJSONProvider):
    app.json.ensure_ascii = False
    app.json.sort_keys = False
CORS(app)  # Habilita chamadas do App Mobile React Native / Expo Web

_predictor: Optional[CardioPredictor] = None
_samples_cache: Optional[List[Dict[str, Any]]] = None


# ---------------------------------------------------------------------------
# Banco de Dados SQLite (Histórico de Análises)
# ---------------------------------------------------------------------------
def init_db() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB_PATH) as con:
        con.execute(
            """
            CREATE TABLE IF NOT EXISTS predicoes (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                criado_em       REAL NOT NULL,
                paciente_id     TEXT NOT NULL,
                origem          TEXT NOT NULL,
                arquivo         TEXT,
                modelo          TEXT NOT NULL,
                classe_predita  TEXT NOT NULL,
                nome_classe     TEXT NOT NULL,
                risco           TEXT NOT NULL,
                confianca_pct   REAL NOT NULL,
                tempo_ms        REAL NOT NULL
            )
            """
        )


def salvar_historico(
    paciente_id: str,
    origem: str,
    arquivo: str,
    resultado: Dict,
) -> int:
    with sqlite3.connect(DB_PATH) as con:
        cur = con.execute(
            """
            INSERT INTO predicoes (
                criado_em, paciente_id, origem, arquivo, modelo,
                classe_predita, nome_classe, risco, confianca_pct, tempo_ms
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                time.time(),
                paciente_id,
                origem,
                arquivo,
                resultado["model_used"],
                resultado["predicted_class"],
                resultado["class_name_pt"],
                resultado["risk_level"],
                resultado["confidence_pct"],
                resultado["inference_time_ms"],
            ),
        )
        con.commit()
        return int(cur.lastrowid or 0)


# ---------------------------------------------------------------------------
# Carregamento Preguiçoso (Lazy Load) do Preditor e Amostras de Teste
# ---------------------------------------------------------------------------
def get_predictor() -> CardioPredictor:
    global _predictor
    if _predictor is None:
        _predictor = CardioPredictor(MODELS_DIR)
    return _predictor


def listar_amostras_teste() -> List[Dict]:
    global _samples_cache
    if _samples_cache is not None:
        return _samples_cache

    dataset_dir = localizar_dataset_ecg()
    pred = get_predictor()
    samples: List[Dict] = []
    for cls in CLASSES:
        cls_dir = dataset_dir / "test" / cls
        if not cls_dir.exists():
            continue
        all_files = sorted(cls_dir.glob("*.png"))
        # Seleciona até 2 amostras reais do teste, priorizando a primeira com morfologia típica clara
        chosen: List[Path] = []
        for fpath in all_files[:8]:
            if len(chosen) == 0:
                res_chk = pred.predict(fpath, model_key="resnet18_transfer", include_gradcam=False)
                if res_chk["predicted_class"] == cls:
                    chosen.append(fpath)
                    break
        if not chosen and all_files:
            chosen.append(all_files[0])
        for fpath in all_files:
            if fpath not in chosen:
                chosen.append(fpath)
                break

        for idx, fpath in enumerate(chosen, start=1):
            with Image.open(fpath) as im:
                thumb = compor_sobre_branco(im).resize((180, 120), Image.Resampling.LANCZOS)
                thumb_b64 = pil_para_base64_png(thumb)
            samples.append(
                {
                    "sample_id": f"test/{cls}/{fpath.name}",
                    "filename": fpath.name,
                    "true_class": cls,
                    "label_display": f"Amostra {cls} #{idx} — {CLASS_INFO[cls]['name_pt']}",
                    "risk_level": CLASS_INFO[cls]["risk_level"],
                    "risk_color": CLASS_INFO[cls]["risk_color"],
                    "cor_original": CLASS_INFO[cls]["cor_original_dataset"],
                    "thumbnail_b64": thumb_b64,
                }
            )
    _samples_cache = samples
    return samples


def resolver_sample_path(sample_id: str) -> Optional[Path]:
    dataset_dir = localizar_dataset_ecg().resolve()
    candidate = (dataset_dir / sample_id).resolve()
    try:
        candidate.relative_to(dataset_dir)
    except ValueError:
        return None
    return candidate if candidate.exists() and candidate.is_file() else None


# ---------------------------------------------------------------------------
# Rotas Web e API REST
# ---------------------------------------------------------------------------
@app.get("/")
def index():
    return render_template("index.html")


@app.get("/api/v1/health")
def health():
    pred = get_predictor()
    meta_models = pred.metadata.get("models", {})
    summary = {}
    for k, v in meta_models.items():
        tm = v.get("test_metrics", {})
        summary[k] = {
            "name": v.get("name", k),
            "accuracy": tm.get("accuracy"),
            "f1_macro": tm.get("f1_macro"),
            "precision_macro": tm.get("precision_macro"),
            "recall_macro": tm.get("recall_macro"),
        }
    return jsonify(
        status="ok",
        service="CardioIA Fase 4 — Assistente Cardiológico Virtual (Visão Computacional)",
        version="4.0.0",
        available_models=pred.available_models(),
        recommended_model=pred.metadata.get("recommended_model", "resnet18_transfer"),
        models_summary=summary,
        classes=CLASSES,
        class_info=CLASS_INFO,
        timestamp=time.time(),
    )


@app.get("/api/v1/models/metrics")
def models_metrics():
    pred = get_predictor()
    return jsonify(pred.metadata)


@app.get("/api/v1/samples")
def get_samples():
    return jsonify(samples=listar_amostras_teste(), total=len(listar_amostras_teste()))


@app.post("/api/v1/predict")
def predict():
    pred = get_predictor()
    model_key = request.form.get("model") or request.args.get("model") or "resnet18_transfer"
    patient_id = (request.form.get("patient_id") or "PAC-DEMO").strip() or "PAC-DEMO"
    origem = (request.form.get("source") or "upload").strip()
    include_gradcam = str(request.form.get("gradcam", "true")).lower() != "false"

    img_pil: Optional[Image.Image] = None
    arquivo_nome = "upload.png"
    true_class_ref: Optional[str] = None

    # Caso 1: Upload multipart/form-data (usado pelo formulário Web e pelo App React Native)
    if "image" in request.files and request.files["image"].filename:
        f = request.files["image"]
        arquivo_nome = f.filename or "ecg_upload.png"
        try:
            img_pil = Image.open(f.stream).convert("RGBA")
        except Exception as exc:
            return jsonify(erro=f"Não foi possível ler a imagem enviada: {exc}"), 400
    else:
        # Caso 2: JSON (sample_id ou image_base64)
        body = request.get_json(silent=True) or {}
        model_key = body.get("model", model_key)
        patient_id = str(body.get("patient_id", patient_id)).strip() or "PAC-DEMO"
        origem = str(body.get("source", origem)).strip() or "api_json"
        include_gradcam = bool(body.get("gradcam", True))

        if "sample_id" in body:
            sample_path = resolver_sample_path(str(body["sample_id"]))
            if sample_path is None:
                return jsonify(erro="sample_id inválido ou não encontrado"), 404
            arquivo_nome = sample_path.name
            true_class_ref = sample_path.parent.name
            img_pil = Image.open(sample_path).convert("RGBA")
        elif "image_base64" in body:
            raw_b64 = str(body["image_base64"])
            if "," in raw_b64:
                raw_b64 = raw_b64.split(",", 1)[1]
            try:
                img_bytes = base64.b64decode(raw_b64)
                img_pil = Image.open(io.BytesIO(img_bytes)).convert("RGBA")
                arquivo_nome = str(body.get("filename", "ecg_mobile.png"))
            except Exception as exc:
                return jsonify(erro=f"Imagem base64 inválida: {exc}"), 400
        else:
            return jsonify(
                erro="Envie uma imagem no campo multipart 'image', ou JSON com 'sample_id' ou 'image_base64'."
            ), 400

    if img_pil is None:
        return jsonify(erro="Imagem não fornecida."), 400

    resultado = pred.predict(img_pil, model_key=model_key, include_gradcam=include_gradcam)
    registro_id = salvar_historico(patient_id, origem, arquivo_nome, resultado)

    resultado["analysis_id"] = registro_id
    resultado["patient_id"] = patient_id
    resultado["filename"] = arquivo_nome
    if true_class_ref:
        resultado["ground_truth_class"] = true_class_ref
        resultado["match_ground_truth"] = true_class_ref == resultado["predicted_class"]

    return jsonify(resultado), 200


@app.post("/api/v1/preview-filter")
def preview_filter():
    """Aplica o filtro Color-Invariant ao vivo sobre uma imagem enviada sem rodar inferência."""
    img_pil: Optional[Image.Image] = None
    if "image" in request.files and request.files["image"].filename:
        try:
            img_pil = Image.open(request.files["image"].stream).convert("RGBA")
        except Exception as exc:
            return jsonify(erro=f"Imagem inválida: {exc}"), 400
    else:
        body = request.get_json(silent=True) or {}
        if "image_base64" in body:
            raw_b64 = str(body["image_base64"])
            if "," in raw_b64:
                raw_b64 = raw_b64.split(",", 1)[1]
            try:
                img_pil = Image.open(io.BytesIO(base64.b64decode(raw_b64))).convert("RGBA")
            except Exception as exc:
                return jsonify(erro=f"Base64 inválido: {exc}"), 400
        elif "sample_id" in body:
            sp = resolver_sample_path(str(body["sample_id"]))
            if sp is None:
                return jsonify(erro="sample_id não encontrado"), 404
            img_pil = Image.open(sp).convert("RGBA")
        else:
            return jsonify(erro="Envie 'image', 'image_base64' ou 'sample_id'."), 400

    if img_pil is None:
        return jsonify(erro="Imagem não fornecida."), 400

    orig_roi, audit = preparar_roi_original_e_auditoria(img_pil, target_size=(224, 224))
    arr_bin = preprocessar_imagem_ecg(img_pil, target_size=(224, 224), modo="binarizado", para_transfer_learning=True)
    bin_pil = Image.fromarray(np.clip(arr_bin[:, :, 0] * 255.0, 0, 255).astype(np.uint8), mode="L").convert("RGB")
    return jsonify(
        original_roi_image_b64=pil_para_base64_png(orig_roi),
        preprocessed_image_b64=pil_para_base64_png(bin_pil),
        chromatic_audit=audit,
    )


@app.get("/api/v1/history")
def get_history():
    limite = min(request.args.get("limit", 20, type=int), 100)
    with sqlite3.connect(DB_PATH) as con:
        con.row_factory = sqlite3.Row
        rows = con.execute(
            "SELECT * FROM predicoes ORDER BY id DESC LIMIT ?", (limite,)
        ).fetchall()
    return jsonify(history=[dict(r) for r in rows], total=len(rows))


init_db()

if __name__ == "__main__":
    host = os.environ.get("CARDIOIA_HOST", "0.0.0.0")
    port = int(os.environ.get("CARDIOIA_PORT", "5000"))
    print(f"CardioIA Fase 4 API + Protótipo Web em http://127.0.0.1:{port}  (LAN: http://{host}:{port})")
    app.run(host=host, port=port, debug=False)
