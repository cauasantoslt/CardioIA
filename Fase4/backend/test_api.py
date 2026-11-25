"""
CardioIA — Fase 4: Teste Automatizado Ponta a Ponta do Backend Flask (Parte 2 & Ir Além 2).

Valida:
  - GET / (Protótipo Web HTML)
  - GET /api/v1/health (status + modelos carregados)
  - GET /api/v1/samples (listagem de amostras reais)
  - POST /api/v1/predict via JSON sample_id (ResNet18)
  - POST /api/v1/predict via multipart/form-data upload real de PNG (CardioCNN e ResNet18)
  - POST /api/v1/predict via JSON image_base64 (fluxo Web/Mobile)
  - GET /api/v1/history (persistência SQLite)
"""
from __future__ import annotations

import base64
import io
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent
FASE4_DIR = BACKEND_DIR.parent
ROOT_DIR = FASE4_DIR.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from Fase4.backend.app import app  # noqa: E402


def main() -> None:
    client = app.test_client()

    # 1. Página Web
    r_web = client.get("/")
    assert r_web.status_code == 200 and "CardioIA" in r_web.get_data(as_text=True), "Falha na rota Web /"
    print("[OK] GET / (Protótipo Web Flask)")

    # 2. Health
    r_h = client.get("/api/v1/health")
    assert r_h.status_code == 200
    dh = r_h.get_json()
    assert dh["status"] == "ok" and len(dh["available_models"]) == 2
    print(f"[OK] GET /api/v1/health -> modelos={dh['available_models']}")

    # 3. Samples
    r_s = client.get("/api/v1/samples")
    assert r_s.status_code == 200
    samples = r_s.get_json()["samples"]
    assert len(samples) >= 6
    print(f"[OK] GET /api/v1/samples -> {len(samples)} amostras disponíveis")

    # 4. Predict via sample_id (ResNet18)
    sample_m = next(s for s in samples if s["true_class"] == "M")
    r_p1 = client.post(
        "/api/v1/predict",
        json={"sample_id": sample_m["sample_id"], "model": "resnet18_transfer", "patient_id": "PAC-TEST-01"},
    )
    assert r_p1.status_code == 200
    d1 = r_p1.get_json()
    assert d1["gradcam_image_b64"].startswith("data:image/png;base64,")
    assert d1["gradcam_heatmap_b64"].startswith("data:image/png;base64,")
    assert d1["original_roi_image_b64"].startswith("data:image/png;base64,")
    assert d1["chromatic_audit"]["color_bias_removed"] is True
    assert "critical_alert_triggered" in d1["fairness_triage"]
    assert len(d1["probabilities"]) == 6
    print(
        f"[OK] POST /api/v1/predict (sample M, ResNet18) -> Pred={d1['predicted_class']} "
        f"({d1['confidence_pct']}%, {d1['inference_time_ms']} ms, cor_orig={d1['chromatic_audit']['hex_color']})"
    )

    # 4b. Preview Filter Color-Invariant ao vivo
    r_pf = client.post("/api/v1/preview-filter", json={"sample_id": sample_m["sample_id"]})
    assert r_pf.status_code == 200
    dpf = r_pf.get_json()
    assert dpf["preprocessed_image_b64"].startswith("data:image/png;base64,")
    print(f"[OK] POST /api/v1/preview-filter -> lum_orig={dpf['chromatic_audit']['median_luminance']}")

    # 5. Predict via multipart upload (simulando App Mobile React Native)
    sample_file = ROOT_DIR / "Fase1" / "assets" / "images" / "ECG_Image_data" / "test" / "N" / sorted(
        (ROOT_DIR / "Fase1" / "assets" / "images" / "ECG_Image_data" / "test" / "N").glob("*.png")
    )[0].name
    raw_bytes = sample_file.read_bytes()
    r_p2 = client.post(
        "/api/v1/predict",
        data={
            "image": (io.BytesIO(raw_bytes), sample_file.name),
            "model": "cnn_scratch",
            "patient_id": "PAC-MOBILE-02",
            "source": "mobile_react_native",
        },
        content_type="multipart/form-data",
    )
    assert r_p2.status_code == 200
    d2 = r_p2.get_json()
    print(
        f"[OK] POST /api/v1/predict (multipart N, CardioCNN) -> Pred={d2['predicted_class']} "
        f"({d2['confidence_pct']}%, {d2['inference_time_ms']} ms)"
    )

    # 6. Predict via base64 JSON (fluxo Expo Web)
    b64_str = base64.b64encode(raw_bytes).decode("ascii")
    r_p3 = client.post(
        "/api/v1/predict",
        json={
            "image_base64": b64_str,
            "filename": sample_file.name,
            "model": "resnet18_transfer",
            "patient_id": "PAC-WEB-03",
        },
    )
    assert r_p3.status_code == 200
    d3 = r_p3.get_json()
    print(
        f"[OK] POST /api/v1/predict (base64 N, ResNet18) -> Pred={d3['predicted_class']} "
        f"({d3['confidence_pct']}%, {d3['inference_time_ms']} ms)"
    )

    # 7. History SQLite
    r_hist = client.get("/api/v1/history?limit=5")
    assert r_hist.status_code == 200
    hist = r_hist.get_json()["history"]
    assert len(hist) >= 3
    print(f"[OK] GET /api/v1/history -> {len(hist)} registros persistidos em SQLite")
    print("\n=== Todos os testes da API Flask passaram com sucesso! ===")


if __name__ == "__main__":
    main()
