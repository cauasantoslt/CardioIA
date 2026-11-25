"""
CardioIA — Fase 4 (Parte 1): Pipeline de Pré-processamento e Organização de Imagens de ECG.

Responsabilidades:
1. Localização e auditoria do dataset público de ECG (MIT-BIH / AAMI — 6 classes: F, M, N, Q, S, V).
2. Remoção de viés cromático (Color-Invariant Binarization / Masking):
   No dataset original, cada classe foi renderizada com uma cor fixa de linha (ex.: N=ciano,
   M=preto, S=vermelho, V=verde, F=azul, Q=amarelo). Sem binarização agnóstica à cor,
   qualquer CNN (mesmo em escala de cinza simples!) sofre de Shortcut Learning / Clever Hans,
   aprendendo a cor/luminância da linha em vez da morfologia do ECG.
3. Recorte da Região de Interesse (ROI), padronização morfológica, redimensionamento e normalização.
4. Divisão estratificada sem vazamento em Treino (240), Validação (60) e Teste independente (120).
5. Data Augmentation clinicamente seguro (sem flips verticais/horizontais que inverteriam polaridade ST/QRS).
"""
from __future__ import annotations

import glob
import hashlib
import json
import os
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from PIL import Image, ImageFilter
from scipy.ndimage import binary_dilation
from sklearn.model_selection import train_test_split

# ---------------------------------------------------------------------------
# Constantes Clínicas (Padrão Internacional AAMI / MIT-BIH)
# ---------------------------------------------------------------------------
CLASSES: List[str] = ["F", "M", "N", "Q", "S", "V"]
CLASS_TO_IDX: Dict[str, int] = {c: i for i, c in enumerate(CLASSES)}
IDX_TO_CLASS: Dict[int, str] = {i: c for i, c in enumerate(CLASSES)}

# Estatísticas ImageNet para Transfer Learning (ResNet18)
IMAGENET_MEAN = [0.485, 0.456, 0.406]
IMAGENET_STD = [0.229, 0.224, 0.225]

# ROI fixa para imagens padrão 432x288 do dataset (elimina ~47% de margens brancas vazias
# preservando integralmente a posição temporal e a escala de amplitude dos batimentos)
STD_RAW_SIZE = (432, 288)
STD_ROI_BOX = (52, 28, 388, 258)  # (left, top, right, bottom) -> 336 x 230

CLASS_INFO: Dict[str, Dict[str, str]] = {
    "N": {
        "code": "N",
        "name_en": "Normal Beat",
        "name_pt": "Batimento Sinusal Normal",
        "risk_level": "BAIXO",
        "risk_color": "#059669",
        "cor_original_dataset": "Ciano",
        "morphology": "Complexo QRS estreito, onda P fisiológica precedente e segmento ST isoelétrico.",
        "recommendation": (
            "Padrão compatível com ritmo sinusal fisiológico. Manter acompanhamento preventivo "
            "de rotina e correlacionar com sintomas clínicos e sinais vitais."
        ),
    },
    "S": {
        "code": "S",
        "name_en": "Supraventricular Ectopic Beat",
        "name_pt": "Extrassístole Supraventricular",
        "risk_level": "MODERADO",
        "risk_color": "#D97706",
        "cor_original_dataset": "Vermelho",
        "morphology": "Batimento prematuro de origem atrial/juncional com QRS geralmente estreito e onda P alterada.",
        "recommendation": (
            "Avaliar frequência das ectopias, fatores desencadeantes (estresse, cafeína, distúrbios "
            "eletrolíticos) e rastrear risco de taquiarritmias supraventriculares (ex.: Fibrilação Atrial)."
        ),
    },
    "V": {
        "code": "V",
        "name_en": "Ventricular Ectopic Beat",
        "name_pt": "Extrassístole Ventricular (PVC)",
        "risk_level": "ALTO",
        "risk_color": "#EA580C",
        "cor_original_dataset": "Verde",
        "morphology": "Complexo QRS alargado (>120 ms) e bizarro, sem onda P precedente, com alteração secundária de ST-T.",
        "recommendation": (
            "Encaminhar para avaliação cardiológica prioritária (Holter 24h, eletrólitos e ecocardiograma). "
            "Monitorar carga arrítmica quanto ao risco de taquicardia ventricular."
        ),
    },
    "F": {
        "code": "F",
        "name_en": "Fusion Beat",
        "name_pt": "Batimento de Fusão Ventricular",
        "risk_level": "ALTO",
        "risk_color": "#EA580C",
        "cor_original_dataset": "Azul",
        "morphology": "Morfologia híbrida resultante da ativação simultânea por estímulo supraventricular e foco ventricular.",
        "recommendation": (
            "Sinal de coexistência de ritmo sinusal e foco ectópico ventricular. Requer revisão por "
            "cardiologista e monitoramento contínuo de ECG para descartar arritmia sustentada."
        ),
    },
    "M": {
        "code": "M",
        "name_en": "Myocardial Infarction / Pathological",
        "name_pt": "Infarto do Miocárdio / Alteração Isquêmica",
        "risk_level": "CRITICO",
        "risk_color": "#DC2626",
        "cor_original_dataset": "Preto",
        "morphology": "Alteração marcante de repolarização (supradesnivelamento/infradesnivelamento de ST e/ou onda Q patológica).",
        "recommendation": (
            "ALERTA CLÍNICO PRIORITÁRIO: Padrão sugestivo de isquemia/injúria miocárdica. "
            "Acionar protocolo de Síndrome Coronariana Aguda, ECG de 12 derivações imediato e dosagem de troponina."
        ),
    },
    "Q": {
        "code": "Q",
        "name_en": "Unknown / Paced Beat",
        "name_pt": "Batimento de Marca-passo ou Inclassificável",
        "risk_level": "MODERADO",
        "risk_color": "#7C3AED",
        "cor_original_dataset": "Amarelo",
        "morphology": "Traçado compatível com estimulação artificial (marca-passo) ou morfologia atípica/ruído acentuado.",
        "recommendation": (
            "Confirmar histórico de dispositivo cardíaco implantável (marca-passo/CDI) ou repetir aquisição "
            "do exame verificando contato dos eletrodos e interferência de linha de base."
        ),
    },
}


# ---------------------------------------------------------------------------
# Localização de Caminhos
# ---------------------------------------------------------------------------
def get_project_root() -> Path:
    """Retorna a raiz do repositório CardioIA."""
    here = Path(__file__).resolve()
    # Fase4/src/preprocessamento.py -> parents[2] = CardioIA
    for candidate in [here.parents[2], Path.cwd(), Path.cwd().parent, Path.cwd().parent.parent]:
        if (candidate / "Fase1" / "assets" / "images" / "ECG_Image_data").exists():
            return candidate
    return here.parents[2]


def localizar_dataset_ecg(base_dir: Optional[str | Path] = None) -> Path:
    """Encontra a pasta ECG_Image_data da Fase 1 em ambiente local ou Google Colab."""
    if base_dir is not None:
        p = Path(base_dir)
        if p.exists():
            return p
    root = get_project_root()
    candidates = [
        root / "Fase1" / "assets" / "images" / "ECG_Image_data",
        Path("Fase1/assets/images/ECG_Image_data"),
        Path("../Fase1/assets/images/ECG_Image_data"),
        Path("../../Fase1/assets/images/ECG_Image_data"),
        Path("/content/CardioIA/Fase1/assets/images/ECG_Image_data"),
    ]
    for c in candidates:
        if c.exists():
            return c.resolve()
    raise FileNotFoundError(
        "Dataset ECG_Image_data não encontrado. Certifique-se de que a pasta "
        "'Fase1/assets/images/ECG_Image_data' existe no repositório."
    )


# ---------------------------------------------------------------------------
# Pipeline de Pré-processamento Agnóstico à Cor (Color-Invariant)
# ---------------------------------------------------------------------------
def compor_sobre_branco(img: Image.Image) -> Image.Image:
    """Converte imagens RGBA/P/L para RGB sobre fundo branco puro (255, 255, 255)."""
    if img.mode == "RGBA":
        bg = Image.new("RGBA", img.size, (255, 255, 255, 255))
        return Image.alpha_composite(bg, img).convert("RGB")
    return img.convert("RGB")


def extrair_mascara_traco_invariante_cor(
    img: Image.Image,
    limiar_tinta: float = 0.18,
    dilatar_px: int = 1,
) -> np.ndarray:
    """
    Remove completamente a informação de cor e luminância específica de classe.

    Princípio físico-matemático:
    Em gráficos de ECG sobre fundo claro, qualquer pixel colorido (ciano, vermelho,
    verde, azul, amarelo ou preto) reduz pelo menos um canal RGB em relação ao fundo.
    Definimos a intensidade de tinta pela distância ao fundo branco (ou cor de fundo
    estimada via percentil 95 de cada canal):
        d(x, y) = max_c(bg_c - I_c(x, y))
    Em seguida normalizamos d pelo percentil 98 dos pixels de traço e aplicamos
    binarização rigorosa (0.0 = fundo, 1.0 = traço), eliminando 100% do viés cromático
    (Shortcut Learning) entre as 6 classes AAMI.
    """
    rgb = np.asarray(compor_sobre_branco(img), dtype=np.float32)

    # Estima cor do fundo (robusto mesmo para fotos de ECG com fundo levemente creme/cinza)
    bg_color = np.percentile(rgb.reshape(-1, 3), 95, axis=0)
    # Diferença máxima abaixo do fundo em qualquer canal RGB
    diff = np.max(np.clip(bg_color[None, None, :] - rgb, 0.0, 255.0), axis=2)

    # Limiar adaptativo mínimo para descartar ruído de compressão JPEG/fundo
    cand = diff[diff > 20.0]
    if cand.size == 0:
        return np.zeros(diff.shape, dtype=np.float32)

    scale = float(np.percentile(cand, 95))
    scale = max(scale, 30.0)
    norm = np.clip(diff / scale, 0.0, 1.0)

    # Binarização estrita: impede vazamento de luminância entre classes
    mask = norm >= limiar_tinta

    # Leve dilatação opcional (1 px) para garantir continuidade do traço após downsampling
    if dilatar_px > 0:
        mask = binary_dilation(mask, iterations=dilatar_px)

    return mask.astype(np.float32)


def recortar_roi_ecg(mask: np.ndarray, raw_size: Tuple[int, int]) -> np.ndarray:
    """
    Recorta margens brancas excessivas preservando a escala temporal e vertical do ECG.
    - Para imagens no formato padrão 432x288 do dataset, usa ROI fixa (52, 28, 388, 258),
      garantindo alinhamento consistente da linha de base e duração do batimento.
    - Para imagens externas (ex.: upload via app mobile), faz auto-crop com padding de 8%.
    """
    h, w = mask.shape
    if raw_size == STD_RAW_SIZE and (w, h) == STD_RAW_SIZE:
        l, t, r, b = STD_ROI_BOX
        return mask[t:b, l:r]

    ys, xs = np.where(mask > 0.5)
    if ys.size == 0:
        return mask
    y0, y1 = int(ys.min()), int(ys.max())
    x0, x1 = int(xs.min()), int(xs.max())
    pad_y = max(8, int(0.08 * (y1 - y0 + 1)))
    pad_x = max(8, int(0.08 * (x1 - x0 + 1)))
    y0 = max(0, y0 - pad_y)
    y1 = min(h, y1 + pad_y)
    x0 = max(0, x0 - pad_x)
    x1 = min(w, x1 + pad_x)
    return mask[y0:y1, x0:x1]


def preprocessar_imagem_ecg(
    img_input: str | Path | Image.Image,
    target_size: Tuple[int, int] = (128, 128),
    modo: str = "binarizado",
    para_transfer_learning: bool = False,
) -> np.ndarray:
    """
    Executa o pipeline completo de pré-processamento de uma imagem de ECG.

    Parâmetros:
        img_input: caminho do arquivo ou objeto PIL.Image.
        target_size: resolução alvo (W, H), ex.: (128, 128) ou (224, 224).
        modo:
            - "binarizado": pipeline oficial (invariante à cor, ROI crop, binarização rigorosa).
            - "rgb_ingenuo": sem remoção de cor (usado APENAS para auditoria de viés no Ir Além 1).
            - "gray_ingenuo": escala de cinza direta sem binarização (também preserva viés de luminância).
        para_transfer_learning:
            - Se True, retorna array float32 shape (H, W, 3) em [0, 1] (traço escuro sobre fundo claro,
              pronto para normalização ImageNet).
            - Se False, retorna array float32 shape (H, W, 1) em [0, 1] (traço=1.0 sobre fundo=0.0,
              otimizado para ativações convolucionais da CNN do zero).
    """
    img = Image.open(img_input) if not isinstance(img_input, Image.Image) else img_input
    raw_size = img.size

    if modo == "rgb_ingenuo":
        rgb = compor_sobre_branco(img)
        if raw_size == STD_RAW_SIZE:
            rgb = rgb.crop(STD_ROI_BOX)
        rgb = rgb.resize(target_size, Image.Resampling.LANCZOS)
        return np.asarray(rgb, dtype=np.float32) / 255.0

    if modo == "gray_ingenuo":
        gray = compor_sobre_branco(img).convert("L")
        if raw_size == STD_RAW_SIZE:
            gray = gray.crop(STD_ROI_BOX)
        gray = gray.resize(target_size, Image.Resampling.LANCZOS)
        arr = np.asarray(gray, dtype=np.float32) / 255.0
        if para_transfer_learning:
            return np.stack([arr, arr, arr], axis=-1)
        return (1.0 - arr)[..., None]

    # Modo oficial: "binarizado" (Color-Invariant)
    mask = extrair_mascara_traco_invariante_cor(img, limiar_tinta=0.18, dilatar_px=1)
    roi = recortar_roi_ecg(mask, raw_size)

    # Converte máscara [0, 1] para PIL uint8 e redimensiona preservando nitidez
    roi_pil = Image.fromarray((roi * 255.0).astype(np.uint8), mode="L")
    resized = roi_pil.resize(target_size, Image.Resampling.BILINEAR)
    arr = np.asarray(resized, dtype=np.float32) / 255.0

    # Re-reforço suave de contraste para manter traço nítido e fundo estritamente limpo
    arr = np.clip((arr - 0.10) / 0.70, 0.0, 1.0)

    if para_transfer_learning:
        # Traço escuro (0.0) sobre fundo branco (1.0), replicado em 3 canais RGB idênticos
        inv = 1.0 - arr
        return np.stack([inv, inv, inv], axis=-1)

    # Para CNN do zero: sinal ativo = 1.0, fundo = 0.0
    return arr[..., None]


def trocar_cor_traco_contrafactual(
    img_input: str | Path | Image.Image,
    nova_cor_rgb: Tuple[int, int, int],
) -> Image.Image:
    """
    Gera versão contrafactual da imagem de ECG pintando o traçado com outra cor RGB.
    Usado no Ir Além 1 (Auditoria de Ética e Governança) para provar experimentalmente
    o colapso de modelos que dependem do atalho cromático (Clever Hans).
    """
    img = Image.open(img_input) if not isinstance(img_input, Image.Image) else img_input
    rgb = np.asarray(compor_sobre_branco(img), dtype=np.float32)
    bg = np.array([255.0, 255.0, 255.0], dtype=np.float32)
    diff = np.max(np.clip(bg[None, None, :] - rgb, 0.0, 255.0), axis=2)
    cand = diff[diff > 15.0]
    scale = max(float(np.percentile(cand, 95)) if cand.size else 1.0, 30.0)
    alpha = np.clip(diff / scale, 0.0, 1.0)[..., None]

    target = np.array(nova_cor_rgb, dtype=np.float32)[None, None, :]
    out = (1.0 - alpha) * bg + alpha * target
    return Image.fromarray(np.clip(out, 0, 255).astype(np.uint8), mode="RGB")


def simular_degradacao_aquisicao(
    img_arr_signal: np.ndarray,
    tipo: str = "ruido_ubs",
    rng: Optional[np.random.Generator] = None,
) -> np.ndarray:
    """
    Simula condições reais de aquisição em equipamentos heterogêneos (ex.: UBS / wearable)
    sobre a imagem pré-processada (shape HxWx1, traço=1, fundo=0):
      - "ruido_ubs": ruído gaussiano de eletrodo + leve atenuação de contraste + micro-deslocamento
      - "deslocamento_basal": deslocamento vertical/horizontal moderado (drift de linha de base)
    Usado para auditoria de robustez e fairness por subgrupo técnico no Ir Além 1.
    """
    if rng is None:
        rng = np.random.default_rng(42)
    x = img_arr_signal.copy()
    h, w = x.shape[:2]

    if tipo == "ruido_ubs":
        # Atenuação de contraste + ruído de eletrodo + pequeno shift
        dx = int(rng.integers(-4, 5))
        dy = int(rng.integers(-4, 5))
        x = np.roll(np.roll(x, dy, axis=0), dx, axis=1)
        x = x * float(rng.uniform(0.68, 0.85))
        noise = rng.normal(0.0, 0.06, size=x.shape).astype(np.float32)
        x = np.clip(x + noise, 0.0, 1.0)
    elif tipo == "deslocamento_basal":
        dx = int(rng.integers(-8, 9))
        dy = int(rng.integers(-6, 7))
        x = np.roll(np.roll(x, dy, axis=0), dx, axis=1)
    return x.astype(np.float32)


# ---------------------------------------------------------------------------
# Organização do Dataset: Auditoria e Split Treino / Validação / Teste
# ---------------------------------------------------------------------------
def auditar_e_organizar_dataset(
    dataset_dir: Optional[str | Path] = None,
    val_ratio: float = 0.20,
    seed: int = 42,
    save_dir: Optional[str | Path] = None,
) -> Tuple[pd.DataFrame, Dict]:
    """
    Varre o dataset original, audita integridade (dimensões, canais, hashes, cores por classe)
    e constrói a partição estratificada definitiva:
      - train: 240 imagens (40 por classe, 57,1%)
      - val:    60 imagens (10 por classe, 14,3%)
      - test:  120 imagens (20 por classe, 28,6% — diretório 'test/' original mantido intacto)
    """
    base = localizar_dataset_ecg(dataset_dir)
    rows: List[Dict] = []

    for orig_split in ["train", "test"]:
        split_dir = base / orig_split
        for cls in CLASSES:
            cls_dir = split_dir / cls
            if not cls_dir.exists():
                continue
            for fpath in sorted(cls_dir.glob("*.png")):
                raw_bytes = fpath.read_bytes()
                md5 = hashlib.md5(raw_bytes).hexdigest()
                with Image.open(fpath) as im:
                    w, h = im.size
                    mode = im.mode
                    arr = np.asarray(compor_sobre_branco(im), dtype=np.uint8)
                # Cor mediana dos pixels de traço (auditoria de viés cromático)
                non_white = (arr[:, :, 0] < 235) | (arr[:, :, 1] < 235) | (arr[:, :, 2] < 235)
                if non_white.any():
                    med_rgb = [int(v) for v in np.median(arr[non_white], axis=0)]
                    med_gray = float(0.299 * med_rgb[0] + 0.587 * med_rgb[1] + 0.114 * med_rgb[2])
                    ink_ratio = float(non_white.mean())
                else:
                    med_rgb = [255, 255, 255]
                    med_gray = 255.0
                    ink_ratio = 0.0

                rows.append(
                    {
                        "filename": fpath.name,
                        "rel_path": str(fpath.relative_to(base)).replace("\\", "/"),
                        "abs_path": str(fpath),
                        "orig_split": orig_split,
                        "label": cls,
                        "label_idx": CLASS_TO_IDX[cls],
                        "width": w,
                        "height": h,
                        "mode": mode,
                        "md5": md5,
                        "med_r": med_rgb[0],
                        "med_g": med_rgb[1],
                        "med_b": med_rgb[2],
                        "med_luminance": round(med_gray, 2),
                        "ink_ratio": round(ink_ratio, 5),
                    }
                )

    df = pd.DataFrame(rows)

    # Divide apenas orig_split == "train" em train (80%) e val (20%) estratificado
    df_train_full = df[df["orig_split"] == "train"].copy()
    df_test = df[df["orig_split"] == "test"].copy()
    df_test["split"] = "test"

    idx_tr, idx_va = train_test_split(
        df_train_full.index.to_numpy(),
        test_size=val_ratio,
        stratify=df_train_full["label"].to_numpy(),
        random_state=seed,
    )
    df_train_full.loc[idx_tr, "split"] = "train"
    df_train_full.loc[idx_va, "split"] = "val"

    df_final = pd.concat([df_train_full, df_test], ignore_index=True)

    # Estatísticas de auditoria
    hashes_tr = set(df_final[df_final["split"] == "train"]["md5"])
    hashes_va = set(df_final[df_final["split"] == "val"]["md5"])
    hashes_te = set(df_final[df_final["split"] == "test"]["md5"])

    color_summary = {}
    for cls in CLASSES:
        sub = df_final[df_final["label"] == cls]
        color_summary[cls] = {
            "count_total": int(len(sub)),
            "median_rgb": [
                int(sub["med_r"].median()),
                int(sub["med_g"].median()),
                int(sub["med_b"].median()),
            ],
            "median_luminance": round(float(sub["med_luminance"].median()), 1),
            "mean_ink_ratio": round(float(sub["ink_ratio"].mean()), 5),
        }

    summary = {
        "dataset_source": "ECG Image Data (MIT-BIH Arrhythmia / AAMI Standard — Fase 1 CardioIA)",
        "total_images": int(len(df_final)),
        "classes": CLASSES,
        "num_classes": len(CLASSES),
        "raw_resolution": f"{STD_RAW_SIZE[0]}x{STD_RAW_SIZE[1]}",
        "raw_mode": "RGBA",
        "roi_box": list(STD_ROI_BOX),
        "roi_area_reduction_pct": round(
            (1.0 - ((STD_ROI_BOX[2] - STD_ROI_BOX[0]) * (STD_ROI_BOX[3] - STD_ROI_BOX[1])) / (432 * 288)) * 100.0,
            1,
        ),
        "splits": {
            "train": int((df_final["split"] == "train").sum()),
            "val": int((df_final["split"] == "val").sum()),
            "test": int((df_final["split"] == "test").sum()),
        },
        "integrity": {
            "unique_hashes": int(df_final["md5"].nunique()),
            "duplicates_total": int(len(df_final) - df_final["md5"].nunique()),
            "overlap_train_val": len(hashes_tr & hashes_va),
            "overlap_train_test": len(hashes_tr & hashes_te),
            "overlap_val_test": len(hashes_va & hashes_te),
        },
        "chromatic_bias_audit": color_summary,
    }

    if save_dir is not None:
        out = Path(save_dir)
        out.mkdir(parents=True, exist_ok=True)
        # Salva manifesto com caminhos relativos portáveis (sem depender do sistema local)
        df_export = df_final.drop(columns=["abs_path"]).copy()
        df_export.to_csv(out / "manifest_dataset.csv", index=False, encoding="utf-8")
        with open(out / "preprocessing_summary.json", "w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)

    return df_final, summary


if __name__ == "__main__":
    root = get_project_root()
    df_manifest, info = auditar_e_organizar_dataset(
        save_dir=root / "Fase4" / "data" / "processed"
    )
    print(json.dumps(info, indent=2, ensure_ascii=False))
