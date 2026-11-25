"""
CardioIA — Fase 4 (Parte 2): Arquiteturas CNN do Zero, Transfer Learning (ResNet18) e Grad-CAM.

Contém:
- CardioCNN: rede convolucional de 4 blocos treinada do zero sobre tensores (1, 128, 128) binarizados.
- build_resnet18_transfer: ResNet18 pré-treinada no ImageNet adaptada para classificação de 6 classes AAMI.
- ECGDataset: Dataset PyTorch com Data Augmentation clinicamente seguro (shift temporal/vertical,
  leve variação de escala de amplitude e ruído gaussiano — sem flips verticais/horizontais).
- GradCAM: explicabilidade visual sobre a última camada convolucional.
- CardioPredictor: motor de inferência pronto para produção (Backend Flask e App Mobile React Native).
"""
from __future__ import annotations

import base64
import io
import json
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import matplotlib
matplotlib.use("Agg")
import matplotlib.cm as cm
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from PIL import Image
from torch.utils.data import Dataset
from torchvision import models

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from Fase4.src.preprocessamento import (  # noqa: E402
    CLASS_INFO,
    CLASSES,
    IMAGENET_MEAN,
    IMAGENET_STD,
    STD_RAW_SIZE,
    STD_ROI_BOX,
    compor_sobre_branco,
    extrair_mascara_traco_invariante_cor,
    preprocessar_imagem_ecg,
)


# ---------------------------------------------------------------------------
# 1. Arquitetura CNN do Zero (CardioCNN)
# ---------------------------------------------------------------------------
class CardioCNN(nn.Module):
    """
    Rede Neural Convolucional construída do zero para classificação morfológica de ECG.
    Entrada: (B, 1, 128, 128) — sinal binarizado normalizado em [0, 1] (traço=1, fundo=0).
    """

    def __init__(self, num_classes: int = 6, in_channels: int = 1, dropout: float = 0.35):
        super().__init__()
        self.block1 = nn.Sequential(
            nn.Conv2d(in_channels, 32, kernel_size=5, padding=2, bias=False),
            nn.BatchNorm2d(32),
            nn.ReLU(inplace=True),
            nn.MaxPool2d(2),  # 64x64
        )
        self.block2 = nn.Sequential(
            nn.Conv2d(32, 64, kernel_size=3, padding=1, bias=False),
            nn.BatchNorm2d(64),
            nn.ReLU(inplace=True),
            nn.MaxPool2d(2),  # 32x32
        )
        self.block3 = nn.Sequential(
            nn.Conv2d(64, 128, kernel_size=3, padding=1, bias=False),
            nn.BatchNorm2d(128),
            nn.ReLU(inplace=True),
            nn.MaxPool2d(2),  # 16x16
        )
        self.block4 = nn.Sequential(
            nn.Conv2d(128, 256, kernel_size=3, padding=1, bias=False),
            nn.BatchNorm2d(256),
            nn.ReLU(inplace=True),
            nn.MaxPool2d(2),  # 8x8
        )
        # Global Average + Global Max Pooling preservam tanto energia global quanto picos QRS
        self.gap = nn.AdaptiveAvgPool2d(1)
        self.gmp = nn.AdaptiveMaxPool2d(1)
        self.classifier = nn.Sequential(
            nn.Dropout(dropout),
            nn.Linear(512, 128),
            nn.ReLU(inplace=True),
            nn.Dropout(dropout * 0.7),
            nn.Linear(128, num_classes),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = self.block1(x)
        x = self.block2(x)
        x = self.block3(x)
        x = self.block4(x)
        feat = torch.cat([self.gap(x).flatten(1), self.gmp(x).flatten(1)], dim=1)
        return self.classifier(feat)

    @property
    def gradcam_layer(self) -> nn.Module:
        return self.block4[0]


# ---------------------------------------------------------------------------
# 2. Transfer Learning com ResNet18 (Pré-treinada no ImageNet)
# ---------------------------------------------------------------------------
class ResNet18ECG(nn.Module):
    """
    Wrapper sobre torchvision ResNet18 pré-treinada (ImageNet-1K) com cabeça
    classificadora customizada para as 6 classes AAMI de ECG.
    """

    def __init__(self, num_classes: int = 6, pretrained: bool = True, dropout: float = 0.35):
        super().__init__()
        weights = models.ResNet18_Weights.DEFAULT if pretrained else None
        self.backbone = models.resnet18(weights=weights)
        in_features = self.backbone.fc.in_features
        self.backbone.fc = nn.Sequential(
            nn.Dropout(dropout),
            nn.Linear(in_features, 128),
            nn.ReLU(inplace=True),
            nn.Dropout(dropout * 0.6),
            nn.Linear(128, num_classes),
        )

    def freeze_backbone(self) -> None:
        """Estágio 1 (Feature Extraction): congela camadas convolucionais e treina apenas a cabeça."""
        for name, param in self.backbone.named_parameters():
            param.requires_grad = name.startswith("fc.")

    def unfreeze_for_finetuning(self, layers_to_unfreeze: Tuple[str, ...] = ("layer2", "layer3", "layer4", "fc")) -> None:
        """Estágio 2 (Fine-Tuning): libera blocos profundos para adaptação morfológica ao domínio ECG."""
        for name, param in self.backbone.named_parameters():
            param.requires_grad = any(name.startswith(prefix) for prefix in layers_to_unfreeze)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.backbone(x)

    @property
    def gradcam_layer(self) -> nn.Module:
        return self.backbone.layer4[-1].conv2


# ---------------------------------------------------------------------------
# 3. Dataset PyTorch com Data Augmentation Clinicamente Válido
# ---------------------------------------------------------------------------
def _shift_array(arr: np.ndarray, dx: int, dy: int, fill_val: float) -> np.ndarray:
    """Desloca imagem 2D/3D preenchendo bordas com valor de fundo (sem wrap-around)."""
    out = np.full_like(arr, fill_val)
    h, w = arr.shape[:2]
    src_y0 = max(0, -dy)
    src_y1 = min(h, h - dy)
    src_x0 = max(0, -dx)
    src_x1 = min(w, w - dx)
    dst_y0 = max(0, dy)
    dst_y1 = dst_y0 + (src_y1 - src_y0)
    dst_x0 = max(0, dx)
    dst_x1 = dst_x0 + (src_x1 - src_x0)
    if src_y1 > src_y0 and src_x1 > src_x0:
        out[dst_y0:dst_y1, dst_x0:dst_x1] = arr[src_y0:src_y1, src_x0:src_x1]
    return out


def augmentar_ecg_clinico(
    arr: np.ndarray,
    para_transfer: bool = False,
    rng: Optional[np.random.Generator] = None,
) -> np.ndarray:
    """
    Aplica transformações que preservam integralmente a validade clínica do traçado ECG:
      - Pequeno deslocamento temporal horizontal (±5% da largura) e vertical (±4% da altura)
      - Leve variação de contraste / espessura simulando calibragem de eletrocardiógrafo
      - Ruído gaussiano sutil simulando interferência de eletrodo
      - NÃO aplica flip horizontal (inverteria sequência P->QRS->T no tempo) nem flip vertical
        (transformaria supradesnivelamento de ST em infradesnivelamento!).
    """
    if rng is None:
        rng = np.random.default_rng()

    x = arr.copy()
    h, w = x.shape[:2]
    bg_fill = 1.0 if para_transfer else 0.0

    # 1. Deslocamento translacional moderado
    if rng.random() < 0.75:
        dx = int(rng.integers(-max(2, int(w * 0.05)), max(3, int(w * 0.05) + 1)))
        dy = int(rng.integers(-max(2, int(h * 0.04)), max(3, int(h * 0.04) + 1)))
        x = _shift_array(x, dx=dx, dy=dy, fill_val=bg_fill)

    # 2. Variação leve de contraste/ganho do traço
    if rng.random() < 0.5:
        gain = float(rng.uniform(0.85, 1.15))
        if para_transfer:
            # Traço está próximo de 0, fundo próximo de 1
            ink = 1.0 - x
            x = 1.0 - np.clip(ink * gain, 0.0, 1.0)
        else:
            x = np.clip(x * gain, 0.0, 1.0)

    # 3. Ruído gaussiano leve (interferência de pele/eletrodo)
    if rng.random() < 0.5:
        sigma = float(rng.uniform(0.01, 0.035))
        noise = rng.normal(0.0, sigma, size=x.shape).astype(np.float32)
        x = np.clip(x + noise, 0.0, 1.0)

    return x.astype(np.float32)


def array_para_tensor(arr: np.ndarray, normalizar_imagenet: bool = False) -> torch.Tensor:
    """Converte array (H, W, C) em tensor PyTorch (C, H, W) com normalização opcional ImageNet."""
    t = torch.from_numpy(np.transpose(arr, (2, 0, 1)).copy()).float()
    if normalizar_imagenet:
        mean = torch.tensor(IMAGENET_MEAN, dtype=torch.float32).view(3, 1, 1)
        std = torch.tensor(IMAGENET_STD, dtype=torch.float32).view(3, 1, 1)
        t = (t - mean) / std
    return t


class ECGDataset(Dataset):
    """Dataset em memória com pré-processamento cacheado para treino rápido e reproduzível."""

    def __init__(
        self,
        paths: List[str],
        labels: List[int],
        target_size: Tuple[int, int] = (128, 128),
        modo: str = "binarizado",
        para_transfer: bool = False,
        augment: bool = False,
        seed: int = 42,
    ):
        self.paths = list(paths)
        self.labels = list(labels)
        self.target_size = target_size
        self.modo = modo
        self.para_transfer = para_transfer
        self.augment = augment
        self.rng = np.random.default_rng(seed)

        # Pré-carrega em RAM (420 imagens ocupam < 60 MB, acelerando épocas em CPU)
        self.images: List[np.ndarray] = [
            preprocessar_imagem_ecg(
                p,
                target_size=target_size,
                modo=modo,
                para_transfer_learning=para_transfer,
            )
            for p in self.paths
        ]

    def __len__(self) -> int:
        return len(self.labels)

    def __getitem__(self, idx: int) -> Tuple[torch.Tensor, int]:
        arr = self.images[idx]
        if self.augment:
            arr = augmentar_ecg_clinico(arr, para_transfer=self.para_transfer, rng=self.rng)
        tensor = array_para_tensor(arr, normalizar_imagenet=self.para_transfer)
        return tensor, int(self.labels[idx])


# ---------------------------------------------------------------------------
# 4. Explicabilidade Visual: Grad-CAM
# ---------------------------------------------------------------------------
class GradCAM:
    """Calcula mapa de ativação de classe (Grad-CAM) na última camada convolucional."""

    def __init__(self, model: nn.Module, target_layer: nn.Module):
        self.model = model
        self.target_layer = target_layer
        self.activations: Optional[torch.Tensor] = None
        self.gradients: Optional[torch.Tensor] = None
        self._handles = [
            target_layer.register_forward_hook(self._save_activation),
            target_layer.register_full_backward_hook(self._save_gradient),
        ]

    def _save_activation(self, _module, _inp, out):
        self.activations = out.detach()

    def _save_gradient(self, _module, _grad_in, grad_out):
        self.gradients = grad_out[0].detach()

    def generate(self, input_tensor: torch.Tensor, class_idx: Optional[int] = None) -> np.ndarray:
        self.model.eval()
        inp = input_tensor.clone().detach().requires_grad_(True)
        logits = self.model(inp)
        if class_idx is None:
            class_idx = int(logits.argmax(dim=1).item())

        self.model.zero_grad()
        score = logits[0, class_idx]
        score.backward()

        assert self.activations is not None and self.gradients is not None
        weights = self.gradients.mean(dim=(2, 3), keepdim=True)
        cam = (weights * self.activations).sum(dim=1, keepdim=True)
        cam = F.relu(cam)
        cam = F.interpolate(cam, size=input_tensor.shape[2:], mode="bilinear", align_corners=False)
        cam_np = cam.squeeze().cpu().numpy()
        cam_min, cam_max = cam_np.min(), cam_np.max()
        if cam_max > cam_min:
            cam_np = (cam_np - cam_min) / (cam_max - cam_min)
        else:
            cam_np = np.zeros_like(cam_np)
        return cam_np.astype(np.float32)

    def remove_hooks(self) -> None:
        for h in self._handles:
            h.remove()


def renderizar_gradcam_sobreposto(
    ecg_base_gray: np.ndarray,
    cam_map: np.ndarray,
    alpha: float = 0.45,
) -> Image.Image:
    """
    Sobrepõe o mapa de calor Grad-CAM (colormap jet) à imagem de ECG binarizada
    (ecg_base_gray em [0, 1], onde 1.0 = fundo branco e 0.0 = traço preto).
    """
    base_rgb = np.stack([ecg_base_gray, ecg_base_gray, ecg_base_gray], axis=-1)
    heat_rgb = cm.get_cmap("jet")(cam_map)[..., :3]
    blended = (1.0 - alpha) * base_rgb + alpha * heat_rgb
    # Realça o traço do ECG por cima para clareza clínica
    trace_mask = ecg_base_gray < 0.35
    blended[trace_mask] = blended[trace_mask] * 0.45
    return Image.fromarray(np.clip(blended * 255.0, 0, 255).astype(np.uint8), mode="RGB")


def renderizar_heatmap_rgba(cam_map: np.ndarray) -> Image.Image:
    """
    Gera camada Grad-CAM em PNG RGBA transparente para sobreposição interativa em tempo real
    (slider de opacidade 0%..100% e zoom no Web Flask e no App Mobile React Native).
    Regiões de baixa ativação permanecem translúcidas para preservar o traçado do ECG nítido.
    """
    rgba = cm.get_cmap("turbo")(cam_map)  # (H, W, 4) float in [0, 1]
    # Canal alfa suavizado: ativações < 0.08 quase transparentes, picos bem destacados
    alpha = np.clip((cam_map - 0.06) / 0.94, 0.0, 1.0) ** 0.85
    rgba[..., 3] = np.clip(alpha * 0.92, 0.0, 0.92)
    return Image.fromarray(np.clip(rgba * 255.0, 0, 255).astype(np.uint8), mode="RGBA")


def preparar_roi_original_e_auditoria(
    img_input: str | Path | Image.Image,
    target_size: Tuple[int, int] = (224, 224),
) -> Tuple[Image.Image, Dict]:
    """
    Recorta a imagem RGB original na MESMA ROI do pipeline Color-Invariant (alinhamento pixel a pixel
    para comparador Antes/Depois e toggle ao vivo) e extrai a auditoria cromática do traço recebido.
    """
    img = Image.open(img_input) if not isinstance(img_input, Image.Image) else img_input
    raw_size = img.size
    rgb_img = compor_sobre_branco(img)
    rgb_arr = np.asarray(rgb_img, dtype=np.uint8)

    # Auditoria da cor dominante do traçado original
    bg = np.percentile(rgb_arr.reshape(-1, 3), 95, axis=0)
    diff = np.max(np.clip(bg[None, None, :].astype(np.float32) - rgb_arr.astype(np.float32), 0.0, 255.0), axis=2)
    ink_mask = diff > 25.0
    if ink_mask.any():
        med_rgb = [int(v) for v in np.median(rgb_arr[ink_mask], axis=0)]
        med_lum = round(float(0.299 * med_rgb[0] + 0.587 * med_rgb[1] + 0.114 * med_rgb[2]), 1)
    else:
        med_rgb = [0, 0, 0]
        med_lum = 0.0

    # Recorte alinhado com recortar_roi_ecg()
    if raw_size == STD_RAW_SIZE:
        roi_rgb = rgb_img.crop(STD_ROI_BOX)
    else:
        mask = extrair_mascara_traco_invariante_cor(img, limiar_tinta=0.18, dilatar_px=1)
        ys, xs = np.where(mask > 0.5)
        if ys.size > 0:
            h, w = mask.shape
            y0, y1 = int(ys.min()), int(ys.max())
            x0, x1 = int(xs.min()), int(xs.max())
            pad_y = max(8, int(0.08 * (y1 - y0 + 1)))
            pad_x = max(8, int(0.08 * (x1 - x0 + 1)))
            roi_rgb = rgb_img.crop((max(0, x0 - pad_x), max(0, y0 - pad_y), min(w, x1 + pad_x), min(h, y1 + pad_y)))
        else:
            roi_rgb = rgb_img

    roi_resized = roi_rgb.resize(target_size, Image.Resampling.LANCZOS)
    hex_color = "#{:02x}{:02x}{:02x}".format(*med_rgb)
    audit = {
        "median_rgb": med_rgb,
        "hex_color": hex_color,
        "median_luminance": med_lum,
        "color_bias_removed": True,
    }
    return roi_resized, audit


def pil_para_base64_png(img: Image.Image) -> str:
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode("ascii")


# ---------------------------------------------------------------------------
# 5. Wrapper de Inferência para Produção (Flask + App Mobile React Native)
# ---------------------------------------------------------------------------
class CardioPredictor:
    """Carrega os modelos salvos (.pt) e executa classificação + Grad-CAM em imagens de ECG."""

    def __init__(self, models_dir: str | Path):
        self.models_dir = Path(models_dir)
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

        meta_path = self.models_dir / "metadata_modelos.json"
        self.metadata = json.loads(meta_path.read_text(encoding="utf-8")) if meta_path.exists() else {}

        self.models: Dict[str, nn.Module] = {}

        # Carrega CNN do zero
        cnn_path = self.models_dir / "cnn_scratch_ecg.pt"
        if cnn_path.exists():
            m_cnn = CardioCNN(num_classes=len(CLASSES), in_channels=1)
            m_cnn.load_state_dict(torch.load(cnn_path, map_location=self.device, weights_only=True))
            m_cnn.to(self.device).eval()
            self.models["cnn_scratch"] = m_cnn

        # Carrega Transfer Learning ResNet18
        res_path = self.models_dir / "resnet18_transfer_ecg.pt"
        if res_path.exists():
            m_res = ResNet18ECG(num_classes=len(CLASSES), pretrained=False)
            m_res.load_state_dict(torch.load(res_path, map_location=self.device, weights_only=True))
            m_res.to(self.device).eval()
            self.models["resnet18_transfer"] = m_res

        if not self.models:
            raise RuntimeError(f"Nenhum modelo treinado (.pt) encontrado em {self.models_dir}")

    def available_models(self) -> List[str]:
        return list(self.models.keys())

    def predict(
        self,
        img_input: str | Path | Image.Image,
        model_key: str = "resnet18_transfer",
        include_gradcam: bool = True,
    ) -> Dict:
        t0 = time.perf_counter()
        if model_key not in self.models:
            model_key = "resnet18_transfer" if "resnet18_transfer" in self.models else next(iter(self.models))
        model = self.models[model_key]
        is_transfer = model_key == "resnet18_transfer"
        target_size = (224, 224) if is_transfer else (128, 128)

        arr = preprocessar_imagem_ecg(
            img_input,
            target_size=target_size,
            modo="binarizado",
            para_transfer_learning=is_transfer,
        )
        tensor = array_para_tensor(arr, normalizar_imagenet=is_transfer).unsqueeze(0).to(self.device)

        with torch.no_grad():
            logits = model(tensor)
            probs = F.softmax(logits, dim=1).squeeze(0).cpu().numpy()

        top_idx = int(np.argmax(probs))
        top_code = CLASSES[top_idx]
        info = CLASS_INFO[top_code]

        # Prepara imagem original na mesma ROI + auditoria cromática + pré-processada
        orig_roi_pil, chromatic_audit = preparar_roi_original_e_auditoria(img_input, target_size=target_size)
        gray_for_vis = arr[:, :, 0] if is_transfer else (1.0 - arr[:, :, 0])
        preproc_pil = Image.fromarray(np.clip(gray_for_vis * 255.0, 0, 255).astype(np.uint8), mode="L").convert("RGB")

        gradcam_b64 = None
        gradcam_heatmap_b64 = None
        if include_gradcam:
            # Habilita gradientes temporariamente apenas para Grad-CAM
            prev_grads = [p.requires_grad for p in model.parameters()]
            for p in model.parameters():
                p.requires_grad_(True)
            gc = GradCAM(model, model.gradcam_layer)
            try:
                cam_map = gc.generate(tensor, class_idx=top_idx)
                overlay = renderizar_gradcam_sobreposto(gray_for_vis, cam_map, alpha=0.45)
                heatmap_rgba = renderizar_heatmap_rgba(cam_map)
                gradcam_b64 = pil_para_base64_png(overlay)
                gradcam_heatmap_b64 = pil_para_base64_png(heatmap_rgba)
            finally:
                gc.remove_hooks()
                for p, req in zip(model.parameters(), prev_grads):
                    p.requires_grad_(req)

        elapsed_ms = round((time.perf_counter() - t0) * 1000.0, 1)

        # Regra de Fairness / Triagem Crítica do Ir Além 1: P(M) + P(V) + P(F) >= 0.30
        crit_idxs = [CLASSES.index("M"), CLASSES.index("V"), CLASSES.index("F")]
        crit_prob = float(sum(probs[idx] for idx in crit_idxs))
        fairness_triage = {
            "critical_classes": ["M", "V", "F"],
            "critical_prob_pct": round(crit_prob * 100.0, 2),
            "threshold_tau": 0.30,
            "critical_alert_triggered": crit_prob >= 0.30,
        }

        probabilities = [
            {
                "code": c,
                "name_pt": CLASS_INFO[c]["name_pt"],
                "name_en": CLASS_INFO[c]["name_en"],
                "risk_level": CLASS_INFO[c]["risk_level"],
                "risk_color": CLASS_INFO[c]["risk_color"],
                "probability": round(float(probs[i]), 4),
                "probability_pct": round(float(probs[i] * 100.0), 2),
            }
            for i, c in enumerate(CLASSES)
        ]
        probabilities_sorted = sorted(probabilities, key=lambda d: d["probability"], reverse=True)

        return {
            "model_used": model_key,
            "model_label": (
                "ResNet18 (Transfer Learning)" if is_transfer else "CardioCNN (Treinada do Zero)"
            ),
            "predicted_class": top_code,
            "class_name_pt": info["name_pt"],
            "class_name_en": info["name_en"],
            "confidence": round(float(probs[top_idx]), 4),
            "confidence_pct": round(float(probs[top_idx] * 100.0), 2),
            "risk_level": info["risk_level"],
            "risk_color": info["risk_color"],
            "morphology": info["morphology"],
            "recommendation": info["recommendation"],
            "inference_time_ms": elapsed_ms,
            "probabilities": probabilities_sorted,
            "chromatic_audit": chromatic_audit,
            "fairness_triage": fairness_triage,
            "original_roi_image_b64": pil_para_base64_png(orig_roi_pil),
            "preprocessed_image_b64": pil_para_base64_png(preproc_pil),
            "gradcam_heatmap_b64": gradcam_heatmap_b64,
            "gradcam_image_b64": gradcam_b64,
            "clinical_disclaimer": (
                "AVISO CLÍNICO: Protótipo acadêmico de apoio à decisão (CardioIA - FIAP). "
                "Não substitui laudo médico cardiológico nem diagnóstico clínico definitivo."
            ),
        }
