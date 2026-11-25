"""
CardioIA — Fase 4 (Partes 1 e 2): Execução Completa de Pré-processamento, Treinamento e Avaliação.

Executa:
1. Auditoria e organização do dataset (Treino=240, Validação=60, Teste=120).
2. Geração dos gráficos da Parte 1 (distribuição, viés cromático, etapas do pré-processamento, split).
3. Treinamento e avaliação da CNN do Zero (CardioCNN) sobre imagens 128x128 binarizadas.
4. Treinamento em 2 estágios (Feature Extraction + Fine-Tuning) da ResNet18 pré-treinada (Transfer Learning)
   sobre imagens 224x224 binarizadas.
5. Avaliação rigorosa no conjunto de teste independente (Acurácia, Precisão, Recall, F1-score Macro/Weighted,
   Matriz de Confusão e Métricas por Classe).
6. Geração dos gráficos comparativos, mapas de explicabilidade Grad-CAM e salvamento dos pesos (.pt) e metadata JSON.
"""
from __future__ import annotations

import copy
import json
import random
import sys
import time
from pathlib import Path
from typing import Dict, List, Tuple

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
import torch
import torch.nn as nn
from PIL import Image
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
)
from torch.utils.data import DataLoader

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from Fase4.src.modelos import (  # noqa: E402
    CardioCNN,
    ECGDataset,
    GradCAM,
    ResNet18ECG,
    array_para_tensor,
    renderizar_gradcam_sobreposto,
)
from Fase4.src.preprocessamento import (  # noqa: E402
    CLASS_INFO,
    CLASSES,
    STD_ROI_BOX,
    auditar_e_organizar_dataset,
    compor_sobre_branco,
    extrair_mascara_traco_invariante_cor,
    get_project_root,
    preprocessar_imagem_ecg,
    recortar_roi_ecg,
)

plt.style.use("seaborn-v0_8-whitegrid" if "seaborn-v0_8-whitegrid" in plt.style.available else "default")


def set_seed(seed: int = 42) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


# ---------------------------------------------------------------------------
# Gráficos da Parte 1 — Pré-processamento e Organização
# ---------------------------------------------------------------------------
def gerar_figuras_parte1(df: pd.DataFrame, summary: Dict, assets_dir: Path) -> None:
    assets_dir.mkdir(parents=True, exist_ok=True)

    # Figura 1: Amostras originais por classe + evidência do viés cromático/luminância
    fig = plt.figure(figsize=(15, 7.5))
    gs = fig.add_gridspec(2, 6, height_ratios=[1.1, 1.0], hspace=0.45, wspace=0.25)

    for i, cls in enumerate(CLASSES):
        ax = fig.add_subplot(gs[0, i])
        sample_path = df[(df["label"] == cls) & (df["split"] == "train")].iloc[0]["abs_path"]
        im = compor_sobre_branco(Image.open(sample_path))
        ax.imshow(im)
        cor_nome = CLASS_INFO[cls]["cor_original_dataset"]
        lum = summary["chromatic_bias_audit"][cls]["median_luminance"]
        ax.set_title(f"Classe {cls}\n({cor_nome} | Lum={lum:.0f})", fontsize=9.5, fontweight="bold")
        ax.axis("off")

    ax_bar = fig.add_subplot(gs[1, :3])
    counts = [int((df["label"] == c).sum()) for c in CLASSES]
    bar_colors = [
        tuple(v / 255.0 for v in summary["chromatic_bias_audit"][c]["median_rgb"])
        for c in CLASSES
    ]
    bars = ax_bar.bar(CLASSES, counts, color=bar_colors, edgecolor="#1e293b", linewidth=1.2)
    for b, cnt in zip(bars, counts):
        ax_bar.text(b.get_x() + b.get_width() / 2, cnt + 1.5, str(cnt), ha="center", fontweight="bold")
    ax_bar.set_ylim(0, max(counts) + 15)
    ax_bar.set_title("Distribuição por Classe e Cor Fixa do Traço no Dataset Bruto", fontsize=11, fontweight="bold")
    ax_bar.set_xlabel("Classe AAMI (MIT-BIH)")
    ax_bar.set_ylabel("Quantidade de Imagens")

    ax_lum = fig.add_subplot(gs[1, 3:])
    lums = [summary["chromatic_bias_audit"][c]["median_luminance"] for c in CLASSES]
    bars2 = ax_lum.bar(CLASSES, lums, color="#475569", edgecolor="#0f172a", linewidth=1.1)
    for b, lv in zip(bars2, lums):
        ax_lum.text(b.get_x() + b.get_width() / 2, lv + 4, f"{lv:.1f}", ha="center", fontweight="bold")
    ax_lum.set_ylim(0, 210)
    ax_lum.set_title("Luminância Mediana do Traço em Grayscale Simples (Vazamento de Cor!)", fontsize=11, fontweight="bold")
    ax_lum.set_xlabel("Classe AAMI (MIT-BIH)")
    ax_lum.set_ylabel("Intensidade de Cinza (0=Preto, 255=Branco)")

    fig.suptitle(
        "CardioIA Fase 4 — Auditoria Visual do Dataset de ECG e Detecção de Viés Cromático",
        fontsize=13.5,
        fontweight="bold",
        y=0.98,
    )
    fig.savefig(assets_dir / "01_distribuicao_e_vies_cromatico.png", dpi=150, bbox_inches="tight")
    plt.close(fig)

    # Figura 2: Etapas passo a passo do Pipeline de Pré-processamento
    fig, axes = plt.subplots(3, 5, figsize=(15, 8.2))
    demo_classes = ["N", "M", "V"]
    col_titles = [
        "1. Original RGBA\n(432x288, Cor por Classe)",
        "2. Grayscale Ingênuo\n(Mantém Viés Luminância)",
        "3. Binarização Invariante\nà Cor (Distância ao Fundo)",
        f"4. Recorte ROI (-{summary['roi_area_reduction_pct']:.1f}% área)\n+ Redimensionamento 128x128",
        "5. Tensor Final Normalizado\n[0, 1] (Sinal Ativo = 1.0)",
    ]
    for r, cls in enumerate(demo_classes):
        sample_path = df[(df["label"] == cls) & (df["split"] == "train")].iloc[0]["abs_path"]
        raw = Image.open(sample_path)
        rgb = compor_sobre_branco(raw)
        gray = rgb.convert("L")
        mask = extrair_mascara_traco_invariante_cor(raw)
        roi = recortar_roi_ecg(mask, raw.size)
        final_arr = preprocessar_imagem_ecg(raw, target_size=(128, 128), modo="binarizado", para_transfer_learning=False)

        axes[r, 0].imshow(rgb)
        # Retângulo indicando ROI
        l, t, rx, b = STD_ROI_BOX
        rect = plt.Rectangle((l, t), rx - l, b - t, fill=False, edgecolor="#e11d48", linewidth=1.6, linestyle="--")
        axes[r, 0].add_patch(rect)
        axes[r, 0].set_ylabel(f"Classe {cls}\n({CLASS_INFO[cls]['name_pt'][:18]})", fontsize=9.5, fontweight="bold")

        axes[r, 1].imshow(gray, cmap="gray", vmin=0, vmax=255)
        axes[r, 2].imshow(1.0 - mask, cmap="gray", vmin=0, vmax=1)
        axes[r, 3].imshow(1.0 - roi, cmap="gray", vmin=0, vmax=1)
        axes[r, 4].imshow(final_arr[:, :, 0], cmap="inferno", vmin=0, vmax=1)

        for c in range(5):
            if r == 0:
                axes[r, c].set_title(col_titles[c], fontsize=9.5, fontweight="bold")
            axes[r, c].set_xticks([])
            axes[r, c].set_yticks([])

    fig.suptitle(
        "Pipeline de Pré-processamento Agnóstico à Cor (Remoção de Atalho Cromático + ROI + Normalização)",
        fontsize=13,
        fontweight="bold",
        y=0.99,
    )
    plt.tight_layout()
    fig.savefig(assets_dir / "02_pipeline_preprocessamento_etapas.png", dpi=150, bbox_inches="tight")
    plt.close(fig)

    # Figura 3: Divisão Estratificada Treino / Validação / Teste
    fig, ax = plt.subplots(figsize=(10, 4.8))
    x = np.arange(len(CLASSES))
    w = 0.25
    tr_cnt = [int(((df["split"] == "train") & (df["label"] == c)).sum()) for c in CLASSES]
    va_cnt = [int(((df["split"] == "val") & (df["label"] == c)).sum()) for c in CLASSES]
    te_cnt = [int(((df["split"] == "test") & (df["label"] == c)).sum()) for c in CLASSES]

    b1 = ax.bar(x - w, tr_cnt, width=w, label="Treino (240 | 57,1%)", color="#2563eb")
    b2 = ax.bar(x, va_cnt, width=w, label="Validação (60 | 14,3%)", color="#f59e0b")
    b3 = ax.bar(x + w, te_cnt, width=w, label="Teste Independente (120 | 28,6%)", color="#10b981")

    for bars in [b1, b2, b3]:
        for b in bars:
            h = b.get_height()
            ax.text(b.get_x() + b.get_width() / 2, h + 0.8, str(int(h)), ha="center", fontsize=9, fontweight="bold")

    ax.set_xticks(x)
    ax.set_xticklabels([f"{c}\n({CLASS_INFO[c]['name_en'].split()[0]})" for c in CLASSES], fontsize=9.5)
    ax.set_ylabel("Número de Imagens")
    ax.set_ylim(0, 50)
    ax.set_title("Particionamento Estratificado Sem Vazamento (Treino / Validação / Teste)", fontsize=12, fontweight="bold")
    ax.legend(frameon=True)
    plt.tight_layout()
    fig.savefig(assets_dir / "03_split_treino_val_teste.png", dpi=150, bbox_inches="tight")
    plt.close(fig)


# ---------------------------------------------------------------------------
# Loops de Treinamento e Avaliação
# ---------------------------------------------------------------------------
def avaliar_modelo(model: nn.Module, loader: DataLoader, device: torch.device) -> Dict:
    model.eval()
    all_preds, all_targets, all_probs = [], [], []
    criterion = nn.CrossEntropyLoss()
    total_loss, total_n = 0.0, 0

    with torch.no_grad():
        for xb, yb in loader:
            xb, yb = xb.to(device), yb.to(device)
            logits = model(xb)
            loss = criterion(logits, yb)
            probs = torch.softmax(logits, dim=1)
            preds = logits.argmax(dim=1)

            total_loss += float(loss.item()) * len(yb)
            total_n += len(yb)
            all_preds.extend(preds.cpu().numpy().tolist())
            all_targets.extend(yb.cpu().numpy().tolist())
            all_probs.extend(probs.cpu().numpy().tolist())

    y_true = np.array(all_targets)
    y_pred = np.array(all_preds)
    y_prob = np.array(all_probs)

    acc = float(accuracy_score(y_true, y_pred))
    prec_macro = float(precision_score(y_true, y_pred, average="macro", zero_division=0))
    rec_macro = float(recall_score(y_true, y_pred, average="macro", zero_division=0))
    f1_macro = float(f1_score(y_true, y_pred, average="macro", zero_division=0))
    f1_weighted = float(f1_score(y_true, y_pred, average="weighted", zero_division=0))
    cm_mat = confusion_matrix(y_true, y_pred, labels=list(range(len(CLASSES))))
    report = classification_report(
        y_true, y_pred, target_names=CLASSES, output_dict=True, zero_division=0
    )

    return {
        "loss": round(total_loss / max(total_n, 1), 4),
        "accuracy": round(acc, 4),
        "precision_macro": round(prec_macro, 4),
        "recall_macro": round(rec_macro, 4),
        "f1_macro": round(f1_macro, 4),
        "f1_weighted": round(f1_weighted, 4),
        "confusion_matrix": cm_mat.tolist(),
        "classification_report": report,
        "y_true": y_true.tolist(),
        "y_pred": y_pred.tolist(),
        "y_prob": y_prob.tolist(),
    }


def treinar_cnn_do_zero(
    df: pd.DataFrame,
    device: torch.device,
    epochs: int = 45,
    batch_size: int = 24,
    lr: float = 1.2e-3,
    seed: int = 42,
) -> Tuple[CardioCNN, Dict, Dict]:
    set_seed(seed)
    tr_df = df[df["split"] == "train"]
    va_df = df[df["split"] == "val"]
    te_df = df[df["split"] == "test"]

    ds_tr = ECGDataset(tr_df["abs_path"].tolist(), tr_df["label_idx"].tolist(), (128, 128), "binarizado", False, True, seed)
    ds_va = ECGDataset(va_df["abs_path"].tolist(), va_df["label_idx"].tolist(), (128, 128), "binarizado", False, False, seed)
    ds_te = ECGDataset(te_df["abs_path"].tolist(), te_df["label_idx"].tolist(), (128, 128), "binarizado", False, False, seed)

    dl_tr = DataLoader(ds_tr, batch_size=batch_size, shuffle=True)
    dl_va = DataLoader(ds_va, batch_size=batch_size, shuffle=False)
    dl_te = DataLoader(ds_te, batch_size=batch_size, shuffle=False)

    model = CardioCNN(num_classes=len(CLASSES), in_channels=1, dropout=0.35).to(device)
    criterion = nn.CrossEntropyLoss(label_smoothing=0.05)
    optimizer = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=1e-3)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=epochs, eta_min=1e-5)

    history = {"train_loss": [], "val_loss": [], "train_acc": [], "val_acc": [], "val_f1": []}
    best_state = copy.deepcopy(model.state_dict())
    best_score = -1.0
    best_epoch = 0

    t0 = time.perf_counter()
    for ep in range(1, epochs + 1):
        model.train()
        tr_loss, tr_correct, tr_n = 0.0, 0, 0
        for xb, yb in dl_tr:
            xb, yb = xb.to(device), yb.to(device)
            optimizer.zero_grad()
            logits = model(xb)
            loss = criterion(logits, yb)
            loss.backward()
            optimizer.step()

            tr_loss += float(loss.item()) * len(yb)
            tr_correct += int((logits.argmax(dim=1) == yb).sum().item())
            tr_n += len(yb)
        scheduler.step()

        va_eval = avaliar_modelo(model, dl_va, device)
        history["train_loss"].append(round(tr_loss / tr_n, 4))
        history["val_loss"].append(va_eval["loss"])
        history["train_acc"].append(round(tr_correct / tr_n, 4))
        history["val_acc"].append(va_eval["accuracy"])
        history["val_f1"].append(va_eval["f1_macro"])

        # Seleciona melhor checkpoint priorizando F1-macro em validação (desempate por menor val_loss)
        score = va_eval["f1_macro"] - 0.01 * va_eval["loss"]
        if score > best_score:
            best_score = score
            best_epoch = ep
            best_state = copy.deepcopy(model.state_dict())

        if ep % 10 == 0 or ep == 1 or ep == epochs:
            print(
                f"[CNN Zero] Época {ep:02d}/{epochs} | "
                f"train_loss={tr_loss/tr_n:.4f} acc={tr_correct/tr_n:.3f} | "
                f"val_loss={va_eval['loss']:.4f} val_acc={va_eval['accuracy']:.3f} val_f1={va_eval['f1_macro']:.3f}"
            )

    train_secs = round(time.perf_counter() - t0, 1)
    model.load_state_dict(best_state)
    val_metrics = avaliar_modelo(model, dl_va, device)
    test_metrics = avaliar_modelo(model, dl_te, device)

    results = {
        "name": "CardioCNN (Treinada do Zero)",
        "input_shape": [1, 128, 128],
        "num_params": int(sum(p.numel() for p in model.parameters())),
        "epochs": epochs,
        "best_epoch": best_epoch,
        "train_time_sec": train_secs,
        "history": history,
        "val_metrics": {k: v for k, v in val_metrics.items() if k not in ("y_true", "y_pred", "y_prob")},
        "test_metrics": test_metrics,
    }
    return model, results, history


def treinar_resnet18_transfer(
    df: pd.DataFrame,
    device: torch.device,
    epochs_stage1: int = 8,
    epochs_stage2: int = 24,
    batch_size: int = 20,
    seed: int = 42,
) -> Tuple[ResNet18ECG, Dict, Dict]:
    set_seed(seed)
    tr_df = df[df["split"] == "train"]
    va_df = df[df["split"] == "val"]
    te_df = df[df["split"] == "test"]

    ds_tr = ECGDataset(tr_df["abs_path"].tolist(), tr_df["label_idx"].tolist(), (224, 224), "binarizado", True, True, seed)
    ds_va = ECGDataset(va_df["abs_path"].tolist(), va_df["label_idx"].tolist(), (224, 224), "binarizado", True, False, seed)
    ds_te = ECGDataset(te_df["abs_path"].tolist(), te_df["label_idx"].tolist(), (224, 224), "binarizado", True, False, seed)

    dl_tr = DataLoader(ds_tr, batch_size=batch_size, shuffle=True)
    dl_va = DataLoader(ds_va, batch_size=batch_size, shuffle=False)
    dl_te = DataLoader(ds_te, batch_size=batch_size, shuffle=False)

    model = ResNet18ECG(num_classes=len(CLASSES), pretrained=True, dropout=0.35).to(device)
    criterion = nn.CrossEntropyLoss(label_smoothing=0.05)

    history = {"train_loss": [], "val_loss": [], "train_acc": [], "val_acc": [], "val_f1": [], "stage": []}
    best_state = copy.deepcopy(model.state_dict())
    best_score = -1.0
    best_epoch = 0
    total_epochs = epochs_stage1 + epochs_stage2

    t0 = time.perf_counter()

    # ----- Estágio 1: Feature Extraction (Backbone congelado) -----
    model.freeze_backbone()
    opt1 = torch.optim.AdamW(filter(lambda p: p.requires_grad, model.parameters()), lr=1.5e-3, weight_decay=1e-3)

    for ep in range(1, epochs_stage1 + 1):
        model.train()
        tr_loss, tr_correct, tr_n = 0.0, 0, 0
        for xb, yb in dl_tr:
            xb, yb = xb.to(device), yb.to(device)
            opt1.zero_grad()
            logits = model(xb)
            loss = criterion(logits, yb)
            loss.backward()
            opt1.step()
            tr_loss += float(loss.item()) * len(yb)
            tr_correct += int((logits.argmax(dim=1) == yb).sum().item())
            tr_n += len(yb)

        va_eval = avaliar_modelo(model, dl_va, device)
        history["train_loss"].append(round(tr_loss / tr_n, 4))
        history["val_loss"].append(va_eval["loss"])
        history["train_acc"].append(round(tr_correct / tr_n, 4))
        history["val_acc"].append(va_eval["accuracy"])
        history["val_f1"].append(va_eval["f1_macro"])
        history["stage"].append(1)

        score = va_eval["f1_macro"] - 0.01 * va_eval["loss"]
        if score > best_score:
            best_score = score
            best_epoch = ep
            best_state = copy.deepcopy(model.state_dict())

        if ep in (1, epochs_stage1):
            print(
                f"[ResNet18 S1] Época {ep:02d}/{total_epochs} | "
                f"train_loss={tr_loss/tr_n:.4f} acc={tr_correct/tr_n:.3f} | "
                f"val_loss={va_eval['loss']:.4f} val_acc={va_eval['accuracy']:.3f} val_f1={va_eval['f1_macro']:.3f}"
            )

    # ----- Estágio 2: Fine-Tuning (Descongela layer2, layer3, layer4 e fc com LR diferencial) -----
    model.unfreeze_for_finetuning(("layer2", "layer3", "layer4", "fc"))
    backbone_params = [p for n, p in model.backbone.named_parameters() if p.requires_grad and not n.startswith("fc.")]
    head_params = [p for n, p in model.backbone.named_parameters() if p.requires_grad and n.startswith("fc.")]
    opt2 = torch.optim.AdamW(
        [
            {"params": backbone_params, "lr": 1.5e-4, "weight_decay": 1e-3},
            {"params": head_params, "lr": 6.0e-4, "weight_decay": 1e-3},
        ]
    )
    sched2 = torch.optim.lr_scheduler.CosineAnnealingLR(opt2, T_max=epochs_stage2, eta_min=1e-6)

    for s2_ep in range(1, epochs_stage2 + 1):
        ep = epochs_stage1 + s2_ep
        model.train()
        tr_loss, tr_correct, tr_n = 0.0, 0, 0
        for xb, yb in dl_tr:
            xb, yb = xb.to(device), yb.to(device)
            opt2.zero_grad()
            logits = model(xb)
            loss = criterion(logits, yb)
            loss.backward()
            opt2.step()
            tr_loss += float(loss.item()) * len(yb)
            tr_correct += int((logits.argmax(dim=1) == yb).sum().item())
            tr_n += len(yb)
        sched2.step()

        va_eval = avaliar_modelo(model, dl_va, device)
        history["train_loss"].append(round(tr_loss / tr_n, 4))
        history["val_loss"].append(va_eval["loss"])
        history["train_acc"].append(round(tr_correct / tr_n, 4))
        history["val_acc"].append(va_eval["accuracy"])
        history["val_f1"].append(va_eval["f1_macro"])
        history["stage"].append(2)

        score = va_eval["f1_macro"] - 0.01 * va_eval["loss"]
        if score > best_score:
            best_score = score
            best_epoch = ep
            best_state = copy.deepcopy(model.state_dict())

        if s2_ep % 6 == 0 or s2_ep == 1 or s2_ep == epochs_stage2:
            print(
                f"[ResNet18 S2] Época {ep:02d}/{total_epochs} | "
                f"train_loss={tr_loss/tr_n:.4f} acc={tr_correct/tr_n:.3f} | "
                f"val_loss={va_eval['loss']:.4f} val_acc={va_eval['accuracy']:.3f} val_f1={va_eval['f1_macro']:.3f}"
            )

    train_secs = round(time.perf_counter() - t0, 1)
    model.load_state_dict(best_state)
    val_metrics = avaliar_modelo(model, dl_va, device)
    test_metrics = avaliar_modelo(model, dl_te, device)

    results = {
        "name": "ResNet18 (Transfer Learning - ImageNet)",
        "input_shape": [3, 224, 224],
        "num_params": int(sum(p.numel() for p in model.parameters())),
        "epochs_stage1": epochs_stage1,
        "epochs_stage2": epochs_stage2,
        "best_epoch": best_epoch,
        "train_time_sec": train_secs,
        "history": history,
        "val_metrics": {k: v for k, v in val_metrics.items() if k not in ("y_true", "y_pred", "y_prob")},
        "test_metrics": test_metrics,
    }
    return model, results, history


# ---------------------------------------------------------------------------
# Gráficos da Parte 2 — Curvas, Matrizes de Confusão, Métricas e Grad-CAM
# ---------------------------------------------------------------------------
def gerar_figuras_parte2(
    df: pd.DataFrame,
    cnn_model: CardioCNN,
    res_model: ResNet18ECG,
    cnn_res: Dict,
    res_res: Dict,
    device: torch.device,
    assets_dir: Path,
) -> None:
    assets_dir.mkdir(parents=True, exist_ok=True)

    # Figura 4: Curvas de Treinamento (Loss e Acurácia)
    fig, axes = plt.subplots(2, 2, figsize=(14, 8.5))
    h_cnn = cnn_res["history"]
    h_res = res_res["history"]
    ep_cnn = np.arange(1, len(h_cnn["train_loss"]) + 1)
    ep_res = np.arange(1, len(h_res["train_loss"]) + 1)

    axes[0, 0].plot(ep_cnn, h_cnn["train_loss"], label="Treino", color="#2563eb", lw=2)
    axes[0, 0].plot(ep_cnn, h_cnn["val_loss"], label="Validação", color="#dc2626", lw=2, ls="--")
    axes[0, 0].axvline(cnn_res["best_epoch"], color="#059669", ls=":", label=f"Melhor época ({cnn_res['best_epoch']})")
    axes[0, 0].set_title("CardioCNN (Do Zero) — Evolução da Perda (Loss)", fontweight="bold")
    axes[0, 0].set_xlabel("Época")
    axes[0, 0].set_ylabel("Cross-Entropy Loss")
    axes[0, 0].legend()

    axes[0, 1].plot(ep_cnn, h_cnn["train_acc"], label="Treino", color="#2563eb", lw=2)
    axes[0, 1].plot(ep_cnn, h_cnn["val_acc"], label="Validação", color="#059669", lw=2, ls="--")
    axes[0, 1].axvline(cnn_res["best_epoch"], color="#059669", ls=":", label=f"Melhor época ({cnn_res['best_epoch']})")
    axes[0, 1].set_title("CardioCNN (Do Zero) — Evolução da Acurácia", fontweight="bold")
    axes[0, 1].set_xlabel("Época")
    axes[0, 1].set_ylabel("Acurácia")
    axes[0, 1].set_ylim(0, 1.05)
    axes[0, 1].legend()

    s1_end = res_res["epochs_stage1"]
    axes[1, 0].plot(ep_res, h_res["train_loss"], label="Treino", color="#7c3aed", lw=2)
    axes[1, 0].plot(ep_res, h_res["val_loss"], label="Validação", color="#dc2626", lw=2, ls="--")
    axes[1, 0].axvline(s1_end + 0.5, color="#f59e0b", ls="-.", label="Início Fine-Tuning")
    axes[1, 0].axvline(res_res["best_epoch"], color="#059669", ls=":", label=f"Melhor época ({res_res['best_epoch']})")
    axes[1, 0].set_title("ResNet18 (Transfer Learning) — Evolução da Perda", fontweight="bold")
    axes[1, 0].set_xlabel("Época")
    axes[1, 0].set_ylabel("Cross-Entropy Loss")
    axes[1, 0].legend()

    axes[1, 1].plot(ep_res, h_res["train_acc"], label="Treino", color="#7c3aed", lw=2)
    axes[1, 1].plot(ep_res, h_res["val_acc"], label="Validação", color="#059669", lw=2, ls="--")
    axes[1, 1].axvline(s1_end + 0.5, color="#f59e0b", ls="-.", label="Início Fine-Tuning")
    axes[1, 1].axvline(res_res["best_epoch"], color="#059669", ls=":", label=f"Melhor época ({res_res['best_epoch']})")
    axes[1, 1].set_title("ResNet18 (Transfer Learning) — Evolução da Acurácia", fontweight="bold")
    axes[1, 1].set_xlabel("Época")
    axes[1, 1].set_ylabel("Acurácia")
    axes[1, 1].set_ylim(0, 1.05)
    axes[1, 1].legend()

    fig.suptitle("Comparativo das Curvas de Aprendizado — CNN do Zero vs. ResNet18 Transfer Learning", fontsize=13.5, fontweight="bold")
    plt.tight_layout()
    fig.savefig(assets_dir / "04_curvas_treinamento_comparativo.png", dpi=150, bbox_inches="tight")
    plt.close(fig)

    # Figura 5: Matrizes de Confusão lado a lado no Conjunto de Teste (120 imagens)
    fig, axes = plt.subplots(1, 2, figsize=(13.5, 5.5))
    cm_cnn = np.array(cnn_res["test_metrics"]["confusion_matrix"])
    cm_res = np.array(res_res["test_metrics"]["confusion_matrix"])

    sns.heatmap(cm_cnn, annot=True, fmt="d", cmap="Blues", xticklabels=CLASSES, yticklabels=CLASSES, ax=axes[0], cbar=False)
    axes[0].set_title(
        f"CardioCNN (Do Zero) — Teste (n=120)\n"
        f"Acurácia: {cnn_res['test_metrics']['accuracy']*100:.2f}% | F1-Macro: {cnn_res['test_metrics']['f1_macro']*100:.2f}%",
        fontweight="bold",
    )
    axes[0].set_xlabel("Classe Predita")
    axes[0].set_ylabel("Classe Real (AAMI)")

    sns.heatmap(cm_res, annot=True, fmt="d", cmap="Purples", xticklabels=CLASSES, yticklabels=CLASSES, ax=axes[1], cbar=False)
    axes[1].set_title(
        f"ResNet18 (Transfer Learning) — Teste (n=120)\n"
        f"Acurácia: {res_res['test_metrics']['accuracy']*100:.2f}% | F1-Macro: {res_res['test_metrics']['f1_macro']*100:.2f}%",
        fontweight="bold",
    )
    axes[1].set_xlabel("Classe Predita")
    axes[1].set_ylabel("Classe Real (AAMI)")

    fig.suptitle("Matrizes de Confusão no Conjunto de Teste Independente (Imagens Sem Viés Cromático)", fontsize=13, fontweight="bold")
    plt.tight_layout()
    fig.savefig(assets_dir / "05_matrizes_confusao_comparativo.png", dpi=150, bbox_inches="tight")
    plt.close(fig)

    # Figura 6: Comparativo de Métricas Globais e F1-Score por Classe
    fig, axes = plt.subplots(1, 2, figsize=(14, 5.2))
    metric_names = ["Acurácia", "Precisão\n(Macro)", "Recall\n(Macro)", "F1-Score\n(Macro)"]
    cnn_vals = [
        cnn_res["test_metrics"]["accuracy"] * 100,
        cnn_res["test_metrics"]["precision_macro"] * 100,
        cnn_res["test_metrics"]["recall_macro"] * 100,
        cnn_res["test_metrics"]["f1_macro"] * 100,
    ]
    res_vals = [
        res_res["test_metrics"]["accuracy"] * 100,
        res_res["test_metrics"]["precision_macro"] * 100,
        res_res["test_metrics"]["recall_macro"] * 100,
        res_res["test_metrics"]["f1_macro"] * 100,
    ]
    x = np.arange(len(metric_names))
    w = 0.34
    b1 = axes[0].bar(x - w / 2, cnn_vals, width=w, label="CardioCNN (Do Zero)", color="#2563eb")
    b2 = axes[0].bar(x + w / 2, res_vals, width=w, label="ResNet18 (Transfer Learning)", color="#7c3aed")
    for bars in [b1, b2]:
        for b in bars:
            axes[0].text(b.get_x() + b.get_width() / 2, b.get_height() + 1.2, f"{b.get_height():.1f}%", ha="center", fontsize=8.5, fontweight="bold")
    axes[0].set_xticks(x)
    axes[0].set_xticklabels(metric_names)
    axes[0].set_ylim(0, 112)
    axes[0].set_ylabel("Pontuação (%)")
    axes[0].set_title("Métricas Globais no Conjunto de Teste (n=120)", fontweight="bold")
    axes[0].legend()

    x2 = np.arange(len(CLASSES))
    f1_cnn_cls = [cnn_res["test_metrics"]["classification_report"][c]["f1-score"] * 100 for c in CLASSES]
    f1_res_cls = [res_res["test_metrics"]["classification_report"][c]["f1-score"] * 100 for c in CLASSES]
    b3 = axes[1].bar(x2 - w / 2, f1_cnn_cls, width=w, label="CardioCNN (Do Zero)", color="#2563eb")
    b4 = axes[1].bar(x2 + w / 2, f1_res_cls, width=w, label="ResNet18 (Transfer Learning)", color="#7c3aed")
    for bars in [b3, b4]:
        for b in bars:
            axes[1].text(b.get_x() + b.get_width() / 2, b.get_height() + 1.2, f"{b.get_height():.1f}%", ha="center", fontsize=8, fontweight="bold")
    axes[1].set_xticks(x2)
    axes[1].set_xticklabels(CLASSES)
    axes[1].set_ylim(0, 112)
    axes[1].set_xlabel("Classe AAMI")
    axes[1].set_ylabel("F1-Score (%)")
    axes[1].set_title("F1-Score por Classe Patológica de ECG", fontweight="bold")
    axes[1].legend()

    fig.suptitle("Avaliação Comparativa das Abordagens de Visão Computacional — CardioIA Fase 4", fontsize=13, fontweight="bold")
    plt.tight_layout()
    fig.savefig(assets_dir / "06_metricas_por_classe_comparativo.png", dpi=150, bbox_inches="tight")
    plt.close(fig)

    # Figura 7: Explicabilidade Grad-CAM (ResNet18) nas 6 classes do conjunto de teste
    fig, axes = plt.subplots(2, 6, figsize=(16, 5.8))
    for p in res_model.parameters():
        p.requires_grad_(True)
    gc = GradCAM(res_model, res_model.gradcam_layer)
    try:
        for i, cls in enumerate(CLASSES):
            sample_path = df[(df["label"] == cls) & (df["split"] == "test")].iloc[0]["abs_path"]
            arr = preprocessar_imagem_ecg(sample_path, target_size=(224, 224), modo="binarizado", para_transfer_learning=True)
            tensor = array_para_tensor(arr, normalizar_imagenet=True).unsqueeze(0).to(device)
            with torch.no_grad():
                probs = torch.softmax(res_model(tensor), dim=1).squeeze(0).cpu().numpy()
            pred_idx = int(np.argmax(probs))
            pred_cls = CLASSES[pred_idx]
            conf = probs[pred_idx] * 100.0
            cam = gc.generate(tensor, class_idx=pred_idx)
            overlay = renderizar_gradcam_sobreposto(arr[:, :, 0], cam, alpha=0.48)

            axes[0, i].imshow(arr[:, :, 0], cmap="gray", vmin=0, vmax=1)
            axes[0, i].set_title(f"Real: {cls} ({CLASS_INFO[cls]['name_en'].split()[0]})", fontsize=9.5, fontweight="bold")
            axes[0, i].axis("off")

            cor_titulo = "#059669" if pred_cls == cls else "#dc2626"
            axes[1, i].imshow(overlay)
            axes[1, i].set_title(f"Grad-CAM | Pred: {pred_cls} ({conf:.1f}%)", fontsize=9.5, fontweight="bold", color=cor_titulo)
            axes[1, i].axis("off")
    finally:
        gc.remove_hooks()

    fig.suptitle(
        "Explicabilidade Clínica (Grad-CAM — ResNet18): Regiões Morfológicas Ativadas no Traçado de ECG",
        fontsize=13,
        fontweight="bold",
        y=0.98,
    )
    plt.tight_layout()
    fig.savefig(assets_dir / "07_gradcam_explicabilidade.png", dpi=150, bbox_inches="tight")
    plt.close(fig)


# ---------------------------------------------------------------------------
# Pipeline Principal
# ---------------------------------------------------------------------------
def main() -> None:
    root = get_project_root()
    fase4_dir = root / "Fase4"
    processed_dir = fase4_dir / "data" / "processed"
    models_dir = fase4_dir / "models"
    assets_dir = fase4_dir / "assets"
    models_dir.mkdir(parents=True, exist_ok=True)
    assets_dir.mkdir(parents=True, exist_ok=True)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"=== CardioIA Fase 4 | Dispositivo: {device} ===")

    # Parte 1: Pré-processamento e Organização
    print("\n[1/4] Auditando e organizando dataset de ECG (Treino / Validação / Teste)...")
    df, prep_summary = auditar_e_organizar_dataset(save_dir=processed_dir)
    gerar_figuras_parte1(df, prep_summary, assets_dir)
    print(f"Split salvo: {prep_summary['splits']} | Duplicatas: {prep_summary['integrity']['duplicates_total']}")

    # Parte 2A: CNN do Zero
    print("\n[2/4] Treinando CardioCNN do zero (128x128 binarizado, 45 épocas)...")
    cnn_model, cnn_res, _ = treinar_cnn_do_zero(df, device=device, epochs=45, batch_size=24)
    torch.save(cnn_model.state_dict(), models_dir / "cnn_scratch_ecg.pt")
    print(
        f"--> CardioCNN Teste: Acc={cnn_res['test_metrics']['accuracy']*100:.2f}% | "
        f"Prec={cnn_res['test_metrics']['precision_macro']*100:.2f}% | "
        f"Rec={cnn_res['test_metrics']['recall_macro']*100:.2f}% | "
        f"F1={cnn_res['test_metrics']['f1_macro']*100:.2f}%"
    )

    # Parte 2B: Transfer Learning com ResNet18
    print("\n[3/4] Treinando ResNet18 Transfer Learning (224x224 binarizado, 2 estágios)...")
    res_model, res_res, _ = treinar_resnet18_transfer(df, device=device, epochs_stage1=8, epochs_stage2=24, batch_size=20)
    torch.save(res_model.state_dict(), models_dir / "resnet18_transfer_ecg.pt")
    print(
        f"--> ResNet18 Teste:  Acc={res_res['test_metrics']['accuracy']*100:.2f}% | "
        f"Prec={res_res['test_metrics']['precision_macro']*100:.2f}% | "
        f"Rec={res_res['test_metrics']['recall_macro']*100:.2f}% | "
        f"F1={res_res['test_metrics']['f1_macro']*100:.2f}%"
    )

    # Parte 2C: Gráficos e Metadados
    print("\n[4/4] Gerando gráficos comparativos, Grad-CAM e salvando metadados...")
    gerar_figuras_parte2(df, cnn_model, res_model, cnn_res, res_res, device, assets_dir)

    metadata = {
        "project": "CardioIA — Fase 4: Visão Computacional com CNNs",
        "dataset": prep_summary,
        "classes": CLASSES,
        "class_info": CLASS_INFO,
        "models": {
            "cnn_scratch": {
                k: v for k, v in cnn_res.items() if k != "test_metrics"
            } | {
                "test_metrics": {
                    k: v for k, v in cnn_res["test_metrics"].items() if k not in ("y_true", "y_pred", "y_prob")
                }
            },
            "resnet18_transfer": {
                k: v for k, v in res_res.items() if k != "test_metrics"
            } | {
                "test_metrics": {
                    k: v for k, v in res_res["test_metrics"].items() if k not in ("y_true", "y_pred", "y_prob")
                }
            },
        },
        "recommended_model": (
            "resnet18_transfer"
            if res_res["test_metrics"]["f1_macro"] >= cnn_res["test_metrics"]["f1_macro"]
            else "cnn_scratch"
        ),
    }
    with open(models_dir / "metadata_modelos.json", "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)

    print("\n=== Treinamento e Avaliação concluídos com sucesso! ===")
    print(f"Modelos salvos em: {models_dir}")
    print(f"Figuras salvas em: {assets_dir}")


if __name__ == "__main__":
    main()
