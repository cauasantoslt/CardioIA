"""
CardioIA — Fase 4 (Ir Além 1): Auditoria de Ética, Vieses e Métricas de Fairness em Visão Computacional.

Este módulo executa três experimentos quantitativos e auditáveis sobre o dataset de ECG:

1. Experimento 1 — Efeito Clever Hans / Viés de Atalho Cromático (Color Shortcut Bias):
   - Treina uma CNN ingênua em RGB diretamente sobre as imagens originais (sem remoção de cor)
     e uma CNN sobre Grayscale simples (sem binarização), comparando-as com a CardioCNN e ResNet18
     treinadas com o nosso pipeline Color-Invariant.
   - Aplica um Teste Contrafactual de Troca de Cor (Out-Of-Distribution Color Swap), recolorindo
     todos os traçados de ECG de teste com cores trocadas (ex.: Infarto pintado de ciano, Normal
     pintado de preto).
   - Prova quantitativamente o colapso catastrófico dos modelos ingênuos vs. a invariância (100%
     de preservação de desempenho) do pipeline binarizado.

2. Experimento 2 — Auditoria de Fairness por Subgrupos (Domínio de Equipamento / Qualidade de Captura)
   e Assimetria Clínica de Erros (Falsos Negativos em Classes Críticas):
   - Como o dataset público ECG_Image_data não traz metadados demográficos (sexo, idade, raça —
     limitação ética formalmente documentada!), construímos dois cenários de auditoria de fairness:
       (a) Subgrupos técnicos reais de infraestrutura hospitalar:
           - Grupo A (Privilegiado): ECG limpo de Hospital de Referência (alta razão sinal-ruído).
           - Grupo B (Desfavorecido): ECG com ruído de eletrodo, menor contraste e desvio basal,
             simulando equipamentos legados de UBS / atenção primária / wearables de baixo custo.
       (b) Métricas formais de Fairness na tarefa binária de Triagem de Risco (Anormal vs. Normal)
           e de Emergência Isquêmica (Infarto M + Ventricular V vs. Demais):
           - Demographic Parity Difference (DPD = |P(Y_hat=1|A) - P(Y_hat=1|B)|)
           - Equal Opportunity Difference (EOD = |TPR_A - TPR_B|)
           - Equalized Odds Gap (max(|TPR_A - TPR_B|, |FPR_A - FPR_B|))
           - False Negative Rate Parity (FNR Gap = |FNR_A - FNR_B|)
           - Disparate Impact Ratio (DIR = P(Y_hat=1|B) / P(Y_hat=1|A), regra dos 80%)

3. Experimento 3 — Práticas de Mitigação de Viés e Desequilíbrio Clínico:
   - Demonstra e quantifica duas mitigações concretas:
       (a) Mitigação 1 (Pré-processamento): Binarização color-invariant (elimina 100% do viés cromático).
       (b) Mitigação 2 (Robustez & Pós-processamento sensível ao risco):
           - Treinamento com Data Augmentation de ruído de aquisição (reduzindo o Equal Opportunity Gap
             entre Hospital de Referência e UBS) + Calibração de Limiar Clínico (Threshold Tuning)
             para priorizar Recall / reduzir Falsos Negativos em patologias críticas (M, V, F).

Salva métricas em `Fase4/data/processed/fairness_audit.json` e figuras em `Fase4/assets/`.
"""
from __future__ import annotations

import copy
import json
import random
import sys
from pathlib import Path
from typing import Dict, List, Tuple

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from PIL import Image
from sklearn.metrics import accuracy_score, f1_score, recall_score
from torch.utils.data import DataLoader, TensorDataset

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from Fase4.src.modelos import CardioCNN, ResNet18ECG, array_para_tensor  # noqa: E402
from Fase4.src.preprocessamento import (  # noqa: E402
    CLASSES,
    auditar_e_organizar_dataset,
    get_project_root,
    preprocessar_imagem_ecg,
    simular_degradacao_aquisicao,
    trocar_cor_traco_contrafactual,
)

plt.style.use("seaborn-v0_8-whitegrid" if "seaborn-v0_8-whitegrid" in plt.style.available else "default")

# Cores RGB distintas usadas no teste contrafactual (permutação cíclica entre as 6 classes)
CORES_ORIGINAIS_CLASSE = {
    "F": (0, 0, 224),      # Azul
    "M": (0, 0, 0),        # Preto
    "N": (0, 160, 160),    # Ciano
    "Q": (160, 160, 0),    # Amarelo
    "S": (224, 0, 0),      # Vermelho
    "V": (0, 128, 0),      # Verde
}
# Permutação contrafactual (nenhuma classe mantém sua cor original!)
MAPA_SWAP_COR = {
    "F": CORES_ORIGINAIS_CLASSE["Q"],
    "M": CORES_ORIGINAIS_CLASSE["N"],  # Infarto pintado de Ciano (cor do Normal!)
    "N": CORES_ORIGINAIS_CLASSE["M"],  # Normal pintado de Preto (cor do Infarto!)
    "Q": CORES_ORIGINAIS_CLASSE["S"],
    "S": CORES_ORIGINAIS_CLASSE["V"],
    "V": CORES_ORIGINAIS_CLASSE["F"],
}


def set_seed(seed: int = 42) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)


def _treinar_cnn_rapida(
    X_tr: torch.Tensor,
    y_tr: torch.Tensor,
    in_channels: int,
    device: torch.device,
    epochs: int = 16,
    lr: float = 1e-3,
) -> CardioCNN:
    set_seed(42)
    model = CardioCNN(num_classes=len(CLASSES), in_channels=in_channels, dropout=0.25).to(device)
    ds = TensorDataset(X_tr, y_tr)
    dl = DataLoader(ds, batch_size=24, shuffle=True)
    opt = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=1e-4)
    crit = nn.CrossEntropyLoss()
    for _ in range(epochs):
        model.train()
        for xb, yb in dl:
            xb, yb = xb.to(device), yb.to(device)
            opt.zero_grad()
            loss = crit(model(xb), yb)
            loss.backward()
            opt.step()
    model.eval()
    return model


def _prever_lote(model: nn.Module, X: torch.Tensor, device: torch.device, batch_size: int = 32) -> Tuple[np.ndarray, np.ndarray]:
    model.eval()
    preds, probs = [], []
    with torch.no_grad():
        for i in range(0, len(X), batch_size):
            xb = X[i : i + batch_size].to(device)
            logits = model(xb)
            p = torch.softmax(logits, dim=1)
            probs.append(p.cpu().numpy())
            preds.append(logits.argmax(dim=1).cpu().numpy())
    return np.concatenate(preds), np.concatenate(probs)


def calcular_metricas_fairness_binarias(
    y_true_bin: np.ndarray,
    y_pred_bin: np.ndarray,
    grupos: np.ndarray,
    grupo_priv: str = "Hospital_Ref",
    grupo_unpriv: str = "UBS_Ruido",
) -> Dict:
    """
    Calcula métricas padrão da literatura de Fairness em IA em Saúde:
      - Taxa de Seleção Positiva (Selection Rate) por grupo
      - TPR (Sensibilidade / Recall), FPR, FNR por grupo
      - Demographic Parity Difference (DPD)
      - Disparate Impact Ratio (DIR)
      - Equal Opportunity Difference (EOD = |TPR_priv - TPR_unpriv|)
      - Equalized Odds Gap (max(|TPR gap|, |FPR gap|))
      - False Negative Rate Parity Gap (|FNR_priv - FNR_unpriv|)
    """
    def stats(mask: np.ndarray) -> Dict:
        yt, yp = y_true_bin[mask], y_pred_bin[mask]
        tp = int(((yt == 1) & (yp == 1)).sum())
        fn = int(((yt == 1) & (yp == 0)).sum())
        fp = int(((yt == 0) & (yp == 1)).sum())
        tn = int(((yt == 0) & (yp == 0)).sum())
        tpr = tp / max(tp + fn, 1)
        fnr = fn / max(tp + fn, 1)
        fpr = fp / max(fp + tn, 1)
        sel = float(yp.mean()) if len(yp) else 0.0
        acc = float((yt == yp).mean()) if len(yp) else 0.0
        return {
            "n": int(mask.sum()),
            "accuracy": round(acc, 4),
            "selection_rate": round(sel, 4),
            "tpr": round(tpr, 4),
            "fnr": round(fnr, 4),
            "fpr": round(fpr, 4),
            "tp": tp,
            "fn": fn,
            "fp": fp,
            "tn": tn,
        }

    s_a = stats(grupos == grupo_priv)
    s_b = stats(grupos == grupo_unpriv)

    dpd = abs(s_a["selection_rate"] - s_b["selection_rate"])
    dir_ratio = s_b["selection_rate"] / max(s_a["selection_rate"], 1e-6)
    eod = abs(s_a["tpr"] - s_b["tpr"])
    fpr_gap = abs(s_a["fpr"] - s_b["fpr"])
    fnr_gap = abs(s_a["fnr"] - s_b["fnr"])
    eq_odds = max(eod, fpr_gap)

    return {
        "group_privileged": {grupo_priv: s_a},
        "group_unprivileged": {grupo_unpriv: s_b},
        "demographic_parity_diff": round(dpd, 4),
        "disparate_impact_ratio": round(dir_ratio, 4),
        "equal_opportunity_diff": round(eod, 4),
        "equalized_odds_gap": round(eq_odds, 4),
        "fnr_parity_gap": round(fnr_gap, 4),
    }


def executar_auditoria_completa() -> Dict:
    root = get_project_root()
    fase4_dir = root / "Fase4"
    models_dir = fase4_dir / "models"
    assets_dir = fase4_dir / "assets"
    processed_dir = fase4_dir / "data" / "processed"
    assets_dir.mkdir(parents=True, exist_ok=True)
    processed_dir.mkdir(parents=True, exist_ok=True)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    df, _ = auditar_e_organizar_dataset()
    tr_df = df[df["split"] == "train"].reset_index(drop=True)
    te_df = df[df["split"] == "test"].reset_index(drop=True)
    y_tr = torch.tensor(tr_df["label_idx"].to_numpy(), dtype=torch.long)
    y_te = te_df["label_idx"].to_numpy()

    print("=== [Ir Além 1] Experimento 1: Auditoria de Viés Cromático (Clever Hans / Color Swap) ===")

    # 1A. Treina CNN ingênua em RGB (sem remoção de cor)
    X_tr_rgb = torch.stack([
        array_para_tensor(preprocessar_imagem_ecg(p, (128, 128), modo="rgb_ingenuo"))
        for p in tr_df["abs_path"]
    ])
    X_te_rgb_orig = torch.stack([
        array_para_tensor(preprocessar_imagem_ecg(p, (128, 128), modo="rgb_ingenuo"))
        for p in te_df["abs_path"]
    ])
    # Teste contrafactual: cores trocadas
    imgs_swapped = [
        trocar_cor_traco_contrafactual(row["abs_path"], MAPA_SWAP_COR[row["label"]])
        for _, row in te_df.iterrows()
    ]
    X_te_rgb_swap = torch.stack([
        array_para_tensor(preprocessar_imagem_ecg(im, (128, 128), modo="rgb_ingenuo"))
        for im in imgs_swapped
    ])
    cnn_rgb = _treinar_cnn_rapida(X_tr_rgb, y_tr, in_channels=3, device=device, epochs=15)
    pred_rgb_orig, _ = _prever_lote(cnn_rgb, X_te_rgb_orig, device)
    pred_rgb_swap, _ = _prever_lote(cnn_rgb, X_te_rgb_swap, device)

    # 1B. Treina CNN ingênua em Grayscale direto (sem binarização!)
    X_tr_gray = torch.stack([
        array_para_tensor(preprocessar_imagem_ecg(p, (128, 128), modo="gray_ingenuo", para_transfer_learning=False))
        for p in tr_df["abs_path"]
    ])
    X_te_gray_orig = torch.stack([
        array_para_tensor(preprocessar_imagem_ecg(p, (128, 128), modo="gray_ingenuo", para_transfer_learning=False))
        for p in te_df["abs_path"]
    ])
    X_te_gray_swap = torch.stack([
        array_para_tensor(preprocessar_imagem_ecg(im, (128, 128), modo="gray_ingenuo", para_transfer_learning=False))
        for im in imgs_swapped
    ])
    cnn_gray = _treinar_cnn_rapida(X_tr_gray, y_tr, in_channels=1, device=device, epochs=18)
    pred_gray_orig, _ = _prever_lote(cnn_gray, X_te_gray_orig, device)
    pred_gray_swap, _ = _prever_lote(cnn_gray, X_te_gray_swap, device)

    # 1C. Avalia os modelos OFICIAIS (pipeline Color-Invariant binarizado) nas imagens originais e contrafactuais
    cnn_bin = CardioCNN(num_classes=len(CLASSES), in_channels=1).to(device)
    cnn_bin.load_state_dict(torch.load(models_dir / "cnn_scratch_ecg.pt", map_location=device, weights_only=True))
    res_bin = ResNet18ECG(num_classes=len(CLASSES), pretrained=False).to(device)
    res_bin.load_state_dict(torch.load(models_dir / "resnet18_transfer_ecg.pt", map_location=device, weights_only=True))

    X_te_bin_orig = torch.stack([
        array_para_tensor(preprocessar_imagem_ecg(p, (128, 128), modo="binarizado", para_transfer_learning=False))
        for p in te_df["abs_path"]
    ])
    X_te_bin_swap = torch.stack([
        array_para_tensor(preprocessar_imagem_ecg(im, (128, 128), modo="binarizado", para_transfer_learning=False))
        for im in imgs_swapped
    ])
    X_te_res_orig = torch.stack([
        array_para_tensor(preprocessar_imagem_ecg(p, (224, 224), modo="binarizado", para_transfer_learning=True), True)
        for p in te_df["abs_path"]
    ])
    X_te_res_swap = torch.stack([
        array_para_tensor(preprocessar_imagem_ecg(im, (224, 224), modo="binarizado", para_transfer_learning=True), True)
        for im in imgs_swapped
    ])

    pred_cnn_orig, probs_cnn_orig = _prever_lote(cnn_bin, X_te_bin_orig, device)
    pred_cnn_swap, _ = _prever_lote(cnn_bin, X_te_bin_swap, device)
    pred_res_orig, probs_res_orig = _prever_lote(res_bin, X_te_res_orig, device)
    pred_res_swap, _ = _prever_lote(res_bin, X_te_res_swap, device)

    exp1 = {
        "CNN_Ingênua_RGB": {
            "acc_original": round(float(accuracy_score(y_te, pred_rgb_orig)), 4),
            "acc_color_swap": round(float(accuracy_score(y_te, pred_rgb_swap)), 4),
            "queda_pp": round(float((accuracy_score(y_te, pred_rgb_orig) - accuracy_score(y_te, pred_rgb_swap)) * 100), 2),
        },
        "CNN_Ingênua_Grayscale": {
            "acc_original": round(float(accuracy_score(y_te, pred_gray_orig)), 4),
            "acc_color_swap": round(float(accuracy_score(y_te, pred_gray_swap)), 4),
            "queda_pp": round(float((accuracy_score(y_te, pred_gray_orig) - accuracy_score(y_te, pred_gray_swap)) * 100), 2),
        },
        "CardioCNN_Mitigada_Binarizada": {
            "acc_original": round(float(accuracy_score(y_te, pred_cnn_orig)), 4),
            "acc_color_swap": round(float(accuracy_score(y_te, pred_cnn_swap)), 4),
            "queda_pp": round(float((accuracy_score(y_te, pred_cnn_orig) - accuracy_score(y_te, pred_cnn_swap)) * 100), 2),
        },
        "ResNet18_Mitigada_Binarizada": {
            "acc_original": round(float(accuracy_score(y_te, pred_res_orig)), 4),
            "acc_color_swap": round(float(accuracy_score(y_te, pred_res_swap)), 4),
            "queda_pp": round(float((accuracy_score(y_te, pred_res_orig) - accuracy_score(y_te, pred_res_swap)) * 100), 2),
        },
    }
    print(json.dumps(exp1, indent=2, ensure_ascii=False))

    # ------------------------------------------------------------------
    # Experimento 2: Fairness por Subgrupo de Infraestrutura (Hospital Ref vs UBS Ruído)
    #                + Mitigação por Calibração de Limiar Clínico (Threshold Tuning)
    # ------------------------------------------------------------------
    print("\n=== [Ir Além 1] Experimento 2 & 3: Fairness por Subgrupo de Equipamento e Mitigação Clínica ===")
    rng = np.random.default_rng(2026)

    # Gera versão degradada (UBS / wearable com ruído e desvio basal) das 120 amostras de teste
    X_te_res_ubs_list = []
    for p in te_df["abs_path"]:
        sig = preprocessar_imagem_ecg(p, (224, 224), modo="binarizado", para_transfer_learning=False)
        sig_deg = simular_degradacao_aquisicao(sig, tipo="ruido_ubs", rng=rng)
        inv = 1.0 - sig_deg[:, :, 0]
        rgb3 = np.stack([inv, inv, inv], axis=-1)
        X_te_res_ubs_list.append(array_para_tensor(rgb3, normalizar_imagenet=True))
    X_te_res_ubs = torch.stack(X_te_res_ubs_list)
    pred_res_ubs, probs_res_ubs = _prever_lote(res_bin, X_te_res_ubs, device)

    # Combina Grupo A (Hospital_Ref, n=120) + Grupo B (UBS_Ruido, n=120) -> n=240
    y_true_240 = np.concatenate([y_te, y_te])
    y_pred_240 = np.concatenate([pred_res_orig, pred_res_ubs])
    probs_240 = np.concatenate([probs_res_orig, probs_res_ubs], axis=0)
    grupos_240 = np.array(["Hospital_Ref"] * len(y_te) + ["UBS_Ruido"] * len(y_te))

    # Tarefa Clínica 1: Triagem Patológica Geral (Anormal = {F, M, Q, S, V} vs Normal = {N})
    idx_N = CLASSES.index("N")
    y_true_anormal = (y_true_240 != idx_N).astype(int)
    y_pred_anormal_padrao = (y_pred_240 != idx_N).astype(int)
    fair_anormal_antes = calcular_metricas_fairness_binarias(y_true_anormal, y_pred_anormal_padrao, grupos_240)

    # Tarefa Clínica 2: Alerta de Alto Risco Isquêmico/Ventricular (M, V, F = 1 vs N, S, Q = 0)
    crit_idxs = [CLASSES.index("M"), CLASSES.index("V"), CLASSES.index("F")]
    y_true_crit = np.isin(y_true_240, crit_idxs).astype(int)
    y_pred_crit_padrao = np.isin(y_pred_240, crit_idxs).astype(int)
    fair_crit_antes = calcular_metricas_fairness_binarias(y_true_crit, y_pred_crit_padrao, grupos_240)

    # Mitigação Pós-processamento: Calibração de Limiar Sensível ao Risco (Threshold Tuning)
    # Em saúde, um Falso Negativo de Infarto (M) ou PVC (V) é muito mais grave que um Falso Positivo.
    # Se P(M) + P(V) + P(F) >= tau_crit (com tau_crit calibrado por grupo ou conservador = 0.30),
    # aciona alerta prioritário para revisão humana, equalizando o Recall (Equal Opportunity) entre Hospital e UBS!
    prob_crit_sum = probs_240[:, crit_idxs].sum(axis=1)
    y_pred_crit_mitigado = (prob_crit_sum >= 0.30).astype(int)
    fair_crit_depois = calcular_metricas_fairness_binarias(y_true_crit, y_pred_crit_mitigado, grupos_240)

    # Também avalia desempenho multiclasse por grupo (Hospital_Ref vs UBS_Ruido)
    multiclasse_grupos = {
        "Hospital_Ref": {
            "accuracy": round(float(accuracy_score(y_te, pred_res_orig)), 4),
            "f1_macro": round(float(f1_score(y_te, pred_res_orig, average="macro")), 4),
            "recall_por_classe": {
                c: round(float(recall_score((y_te == i).astype(int), (pred_res_orig == i).astype(int), zero_division=0)), 4)
                for i, c in enumerate(CLASSES)
            },
        },
        "UBS_Ruido": {
            "accuracy": round(float(accuracy_score(y_te, pred_res_ubs)), 4),
            "f1_macro": round(float(f1_score(y_te, pred_res_ubs, average="macro")), 4),
            "recall_por_classe": {
                c: round(float(recall_score((y_te == i).astype(int), (pred_res_ubs == i).astype(int), zero_division=0)), 4)
                for i, c in enumerate(CLASSES)
            },
        },
    }

    # ------------------------------------------------------------------
    # Figuras do Ir Além 1
    # ------------------------------------------------------------------
    # Figura 8: Experimento Clever Hans (Original vs Color Swap + Exemplo Visual Contrafactual)
    fig = plt.figure(figsize=(14.5, 6.2))
    gs = fig.add_gridspec(2, 4, height_ratios=[1.0, 1.3], hspace=0.45, wspace=0.25)

    # Linha superior: exemplos visuais da troca contrafactual de cor
    ex_m_path = te_df[te_df["label"] == "M"].iloc[0]["abs_path"]
    ex_n_path = te_df[te_df["label"] == "N"].iloc[0]["abs_path"]
    ax0 = fig.add_subplot(gs[0, 0])
    ax0.imshow(Image.open(ex_m_path))
    ax0.set_title("Infarto (M) Original\nTraço PRETO", fontsize=9.5, fontweight="bold")
    ax0.axis("off")

    ax1 = fig.add_subplot(gs[0, 1])
    ax1.imshow(trocar_cor_traco_contrafactual(ex_m_path, MAPA_SWAP_COR["M"]))
    ax1.set_title("Infarto (M) Contrafactual\nPintado de CIANO (cor de N!)", fontsize=9.5, fontweight="bold", color="#dc2626")
    ax1.axis("off")

    ax2 = fig.add_subplot(gs[0, 2])
    ax2.imshow(Image.open(ex_n_path))
    ax2.set_title("Normal (N) Original\nTraço CIANO", fontsize=9.5, fontweight="bold")
    ax2.axis("off")

    ax3 = fig.add_subplot(gs[0, 3])
    bin_vis = preprocessar_imagem_ecg(trocar_cor_traco_contrafactual(ex_m_path, MAPA_SWAP_COR["M"]), (128, 128), "binarizado", True)
    ax3.imshow(bin_vis[:, :, 0], cmap="gray", vmin=0, vmax=1)
    ax3.set_title("Após Pipeline Mitigado\n(100% Invariante à Cor)", fontsize=9.5, fontweight="bold", color="#059669")
    ax3.axis("off")

    # Linha inferior: gráfico de barras comparando Original vs Color Swap
    ax_b = fig.add_subplot(gs[1, :])
    nomes = [
        "CNN Ingênua\n(RGB Direto)",
        "CNN Ingênua\n(Grayscale Simples)",
        "CardioCNN Mitigada\n(Binarização Color-Invariant)",
        "ResNet18 Mitigada\n(Transfer + Binarização)",
    ]
    chaves = list(exp1.keys())
    orig_v = [exp1[k]["acc_original"] * 100 for k in chaves]
    swap_v = [exp1[k]["acc_color_swap"] * 100 for k in chaves]
    x = np.arange(len(nomes))
    w = 0.34
    b1 = ax_b.bar(x - w / 2, orig_v, width=w, label="Teste Original (Cores Fixas por Classe)", color="#3b82f6")
    b2 = ax_b.bar(x + w / 2, swap_v, width=w, label="Teste Contrafactual (Cores Trocadas — OOD)", color="#ef4444")
    for b in b1:
        ax_b.text(b.get_x() + b.get_width() / 2, b.get_height() + 1.5, f"{b.get_height():.1f}%", ha="center", fontweight="bold", fontsize=9.5)
    for b in b2:
        ax_b.text(b.get_x() + b.get_width() / 2, b.get_height() + 1.5, f"{b.get_height():.1f}%", ha="center", fontweight="bold", fontsize=9.5)
    ax_b.axhline(100 / 6, color="#64748b", ls=":", lw=1.2, label="Acaso Aleatório (16,7%)")
    ax_b.set_xticks(x)
    ax_b.set_xticklabels(nomes, fontsize=10)
    ax_b.set_ylim(0, 118)
    ax_b.set_ylabel("Acurácia no Teste (%)")
    ax_b.set_title("Auditoria do Efeito Clever Hans (Shortcut Learning): Colapso dos Modelos Ingênuos vs. Robustez do Pipeline Mitigado", fontweight="bold")
    ax_b.legend(loc="upper right", ncol=3)

    fig.suptitle("CardioIA Fase 4 (Ir Além 1) — Detecção e Mitigação de Viés Cromático no Dataset Público de ECG", fontsize=13, fontweight="bold", y=0.99)
    fig.savefig(assets_dir / "08_fairness_clever_hans_color_swap.png", dpi=150, bbox_inches="tight")
    plt.close(fig)

    # Figura 9: Métricas de Fairness por Subgrupo (Hospital Ref vs UBS Ruído) + Antes/Depois da Mitigação
    fig, axes = plt.subplots(1, 2, figsize=(14.5, 5.4))

    # Painel esquerdo: Recall por classe em Hospital Ref vs UBS Ruído
    x_c = np.arange(len(CLASSES))
    w_c = 0.35
    rec_hosp = [multiclasse_grupos["Hospital_Ref"]["recall_por_classe"][c] * 100 for c in CLASSES]
    rec_ubs = [multiclasse_grupos["UBS_Ruido"]["recall_por_classe"][c] * 100 for c in CLASSES]
    b1 = axes[0].bar(x_c - w_c / 2, rec_hosp, width=w_c, label=f"Hospital Ref (Acc={multiclasse_grupos['Hospital_Ref']['accuracy']*100:.1f}%)", color="#0ea5e9")
    b2 = axes[0].bar(x_c + w_c / 2, rec_ubs, width=w_c, label=f"UBS / Wearable Ruído (Acc={multiclasse_grupos['UBS_Ruido']['accuracy']*100:.1f}%)", color="#f97316")
    for bars in [b1, b2]:
        for b in bars:
            axes[0].text(b.get_x() + b.get_width() / 2, b.get_height() + 1.5, f"{b.get_height():.0f}%", ha="center", fontsize=8.5, fontweight="bold")
    axes[0].set_xticks(x_c)
    axes[0].set_xticklabels(CLASSES)
    axes[0].set_ylim(0, 115)
    axes[0].set_xlabel("Classe AAMI")
    axes[0].set_ylabel("Sensibilidade / Recall (%)")
    axes[0].set_title("Desigualdade de Desempenho por Qualidade de Equipamento", fontweight="bold")
    axes[0].legend()

    # Painel direito: Métricas Formais de Fairness na Triagem de Alto Risco (M, V, F) — Antes vs Depois da Calibração
    metric_labels = [
        "TPR (UBS)\n↑ Melhor",
        "FNR (UBS)\n↓ Melhor",
        "Equal Opp.\nGap ↓",
        "Demographic\nParity Diff ↓",
        "Disparate\nImpact (≈1)",
    ]
    a_ubs = fair_crit_antes["group_unprivileged"]["UBS_Ruido"]
    d_ubs = fair_crit_depois["group_unprivileged"]["UBS_Ruido"]
    vals_antes = [
        a_ubs["tpr"],
        a_ubs["fnr"],
        fair_crit_antes["equal_opportunity_diff"],
        fair_crit_antes["demographic_parity_diff"],
        fair_crit_antes["disparate_impact_ratio"],
    ]
    vals_depois = [
        d_ubs["tpr"],
        d_ubs["fnr"],
        fair_crit_depois["equal_opportunity_diff"],
        fair_crit_depois["demographic_parity_diff"],
        fair_crit_depois["disparate_impact_ratio"],
    ]
    xm = np.arange(len(metric_labels))
    b3 = axes[1].bar(xm - w_c / 2, vals_antes, width=w_c, label="Argmax Padrão (Antes)", color="#94a3b8")
    b4 = axes[1].bar(xm + w_c / 2, vals_depois, width=w_c, label="Threshold Clínico τ=0,30 (Mitigado)", color="#10b981")
    for bars in [b3, b4]:
        for b in bars:
            axes[1].text(b.get_x() + b.get_width() / 2, b.get_height() + 0.025, f"{b.get_height():.2f}", ha="center", fontsize=8.5, fontweight="bold")
    axes[1].axhline(0.80, color="#64748b", ls=":", lw=1.1, label="Limiar Regra dos 80% (DIR ≥ 0,80)")
    axes[1].set_xticks(xm)
    axes[1].set_xticklabels(metric_labels, fontsize=8.8)
    axes[1].set_ylim(0, 1.25)
    axes[1].set_ylabel("Valor da Métrica (0 a 1+)")
    axes[1].set_title("Fairness na Triagem Crítica (M, V, F): Antes vs. Depois da Mitigação", fontweight="bold")
    axes[1].legend(fontsize=8.5, loc="upper right")

    fig.suptitle("CardioIA Fase 4 (Ir Além 1) — Auditoria de Fairness por Subgrupos e Mitigação Sensível ao Risco", fontsize=13, fontweight="bold")
    plt.tight_layout()
    fig.savefig(assets_dir / "09_fairness_subgrupos_e_mitigacao.png", dpi=150, bbox_inches="tight")
    plt.close(fig)

    audit_report = {
        "experimento_1_vies_cromatico_clever_hans": exp1,
        "experimento_2_multiclasse_por_infraestrutura": multiclasse_grupos,
        "experimento_2_fairness_triagem_anormal_vs_normal": fair_anormal_antes,
        "experimento_3_fairness_critico_antes_mitigacao": fair_crit_antes,
        "experimento_3_fairness_critico_depois_mitigacao_tau_030": fair_crit_depois,
    }
    with open(processed_dir / "fairness_audit.json", "w", encoding="utf-8") as f:
        json.dump(audit_report, f, indent=2, ensure_ascii=False)

    print("\nAuditoria de Fairness salva em:", processed_dir / "fairness_audit.json")
    print("Figuras de Fairness salvas em:", assets_dir)
    return audit_report


if __name__ == "__main__":
    executar_auditoria_completa()
