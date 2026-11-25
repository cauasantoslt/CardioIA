"""
CardioIA — Fase 4: Gerador e Executor de Notebooks (.ipynb) para Google Colab e Jupyter.

Gera os três notebooks oficiais da Fase 4 com:
  1. `Fase4/notebooks/01_preprocessamento_ecg.ipynb` (Parte 1 — Pré-processamento e Organização)
  2. `Fase4/notebooks/02_classificacao_cnn_transfer_learning.ipynb` (Parte 2 — CNN Zero vs ResNet18 + Grad-CAM + Protótipo)
  3. `Fase4/notebooks/03_etica_governanca_fairness.ipynb` (Ir Além 1 — Ética, Viés Cromático e Fairness)

Cada notebook:
- Possui célula inicial de compatibilidade automática com Google Colab (clona o repositório
  `https://github.com/cauasantoslt/CardioIA.git` automaticamente caso `Fase1/assets/images/ECG_Image_data`
  não exista no diretório atual).
- É executado de ponta a ponta em um ambiente Python isolado durante a geração, embutindo
  as saídas REAIS (stdout e figuras PNG em base64) diretamente no JSON `.ipynb`, garantindo
  que o arquivo abra pronto para leitura e avaliação no GitHub, VS Code ou Google Colab.
"""
from __future__ import annotations

import base64
import contextlib
import io
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

SRC_DIR = Path(__file__).resolve().parent
FASE4_DIR = SRC_DIR.parent
ROOT_DIR = FASE4_DIR.parent
NOTEBOOKS_DIR = FASE4_DIR / "notebooks"


def md_cell(text: str) -> Dict[str, Any]:
    lines = text.strip("\n").splitlines(keepends=True)
    return {"cell_type": "markdown", "metadata": {}, "source": lines}


def code_cell(code: str) -> Dict[str, Any]:
    lines = code.strip("\n").splitlines(keepends=True)
    return {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": lines,
    }


def _fig_to_b64_png(fig) -> str:
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=130, bbox_inches="tight")
    return base64.b64encode(buf.getvalue()).decode("ascii")


def execute_and_save_notebook(cells: List[Dict[str, Any]], out_path: Path) -> None:
    """Executa todas as células de código em sequência, capturando stdout e gráficos matplotlib."""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    prev_cwd = os.getcwd()
    os.chdir(out_path.parent)

    ns: Dict[str, Any] = {"__name__": "__main__"}
    exec_counter = 1

    # Intercepta plt.show() para capturar figuras como outputs image/png do notebook
    captured_figs: List[str] = []
    orig_show = plt.show

    def _capture_show(*_args, **_kwargs):
        for num in plt.get_fignums():
            fig = plt.figure(num)
            captured_figs.append(_fig_to_b64_png(fig))
            plt.close(fig)

    plt.show = _capture_show
    try:
        for cell in cells:
            if cell["cell_type"] != "code":
                continue
            code = "".join(cell["source"])
            captured_figs.clear()
            stdout_buf = io.StringIO()
            with contextlib.redirect_stdout(stdout_buf):
                exec(compile(code, str(out_path.name), "exec"), ns)

            # Caso a célula tenha criado figura sem chamar plt.show()
            if plt.get_fignums():
                _capture_show()

            outputs: List[Dict[str, Any]] = []
            text_out = stdout_buf.getvalue()
            if text_out:
                outputs.append(
                    {
                        "name": "stdout",
                        "output_type": "stream",
                        "text": text_out.splitlines(keepends=True),
                    }
                )
            for img_b64 in captured_figs:
                outputs.append(
                    {
                        "data": {
                            "image/png": img_b64,
                            "text/plain": ["<Figure>"],
                        },
                        "metadata": {},
                        "output_type": "display_data",
                    }
                )

            cell["execution_count"] = exec_counter
            cell["outputs"] = outputs
            exec_counter += 1
    finally:
        plt.show = orig_show
        os.chdir(prev_cwd)

    nb = {
        "cells": cells,
        "metadata": {
            "colab": {"name": out_path.name, "provenance": []},
            "kernelspec": {
                "display_name": "Python 3",
                "language": "python",
                "name": "python3",
            },
            "language_info": {"name": "python", "version": "3.11"},
        },
        "nbformat": 4,
        "nbformat_minor": 5,
    }
    out_path.write_text(json.dumps(nb, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"[OK] Notebook gerado e executado: {out_path} ({exec_counter - 1} células de código)")


# ---------------------------------------------------------------------------
# NOTEBOOK 1 — PARTE 1: Pré-processamento e Organização das Imagens de ECG
# ---------------------------------------------------------------------------
def build_notebook_1() -> List[Dict[str, Any]]:
    return [
        md_cell(
            r"""
# FIAP — Inteligência Artificial (PBL · 2º Ano)
## CardioIA: A Nova Era da Cardiologia Inteligente
### Fase 4 (Parte 1) — Pré-processamento e Organização de Imagens Médicas de ECG

* **Aluno:** Cauã Santos — **RM:** 566599
* **Dataset:** *ECG Image Data (MIT-BIH Arrhythmia / Padrão AAMI — 6 Classes)* disponível em `Fase1/assets/images/ECG_Image_data/`
* **Objetivo:** Implementar e documentar um pipeline completo e clinicamente seguro de pré-processamento de imagens de Eletrocardiograma (ECG), incluindo auditoria de integridade, **detecção e remoção de viés cromático**, recorte da Região de Interesse (ROI), redimensionamento, normalização, divisão estratificada (Treino, Validação e Teste) e *Data Augmentation* válido para sinais cardiológicos.
            """
        ),
        md_cell(
            r"""
---
## 1. Configuração do Ambiente (Compatível com Google Colab e Execução Local)

Caso o notebook seja aberto diretamente no **Google Colab**, a célula abaixo clona automaticamente o repositório oficial do projeto `CardioIA` para disponibilizar o dataset de ECG e os módulos reutilizáveis em `Fase4/src/`.
            """
        ),
        code_cell(
            r"""
import os
import sys
import json
from pathlib import Path

# Detecta se está no Google Colab sem o repositório clonado
if "google.colab" in sys.modules and not Path("/content/CardioIA").exists():
    os.system("git clone https://github.com/cauasantoslt/CardioIA.git /content/CardioIA")

# Localiza raiz do projeto CardioIA
candidates = [Path.cwd(), Path.cwd().parent, Path.cwd().parent.parent, Path("/content/CardioIA")]
PROJECT_ROOT = next((p for p in candidates if (p / "Fase1" / "assets" / "images" / "ECG_Image_data").exists()), None)
assert PROJECT_ROOT is not None, "Repositório CardioIA não encontrado."

SRC_DIR = PROJECT_ROOT / "Fase4" / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from PIL import Image

from preprocessamento import (
    CLASSES,
    CLASS_INFO,
    STD_ROI_BOX,
    auditar_e_organizar_dataset,
    compor_sobre_branco,
    extrair_mascara_traco_invariante_cor,
    preprocessar_imagem_ecg,
    recortar_roi_ecg,
)
from modelos import augmentar_ecg_clinico

plt.style.use("seaborn-v0_8-whitegrid" if "seaborn-v0_8-whitegrid" in plt.style.available else "default")
print(f"Projeto localizado em: {PROJECT_ROOT}")
print(f"Classes AAMI configuradas ({len(CLASSES)}): {CLASSES}")
            """
        ),
        md_cell(
            r"""
---
## 2. Auditoria do Dataset Bruto e Descoberta Crítica de Viés Cromático

Antes de aplicar qualquer transformação, auditamos as **420 imagens** do dataset (`train/` + `test/`):
1. **Resolução e Canais:** Todas as imagens estão em `432×288` píxeis no formato `RGBA` (4 canais com canal alfa de transparência).
2. **Integridade / Duplicatas:** Verificação por hash criptográfico `MD5` para garantir **zero imagens duplicadas** e **zero vazamento** entre Treino, Validação e Teste.
3. **Achado Crítico (Shortcut Bias):** Cada uma das 6 classes AAMI foi originalmente plotada com uma **cor fixa exclusiva** (`F`=Azul, `M`=Preto, `N`=Ciano, `Q`=Amarelo, `S`=Vermelho, `V`=Verde). Mesmo uma conversão ingênua para escala de cinza (`convert('L')`) preserva **luminâncias distintas por classe** (0 a 169), permitindo que uma CNN "trapaceie" decorando a cor em vez da morfologia do complexo QRS/ST!
            """
        ),
        code_cell(
            r"""
processed_dir = PROJECT_ROOT / "Fase4" / "data" / "processed"
df_manifest, summary = auditar_e_organizar_dataset(val_ratio=0.20, seed=42, save_dir=processed_dir)

print("=== RESUMO DA AUDITORIA DO DATASET ===")
print(f"Total de imagens:       {summary['total_images']}")
print(f"Resolução/Formato raw:  {summary['raw_resolution']} ({summary['raw_mode']})")
print(f"Hashes MD5 únicos:      {summary['integrity']['unique_hashes']} (duplicatas = {summary['integrity']['duplicates_total']})")
print(f"Sobreposição Train/Val: {summary['integrity']['overlap_train_val']} | Train/Test: {summary['integrity']['overlap_train_test']}")
print(f"Partição final:         Train={summary['splits']['train']} | Val={summary['splits']['val']} | Test={summary['splits']['test']}")

audit_rows = []
for cls in CLASSES:
    cinfo = summary["chromatic_bias_audit"][cls]
    audit_rows.append({
        "Classe": cls,
        "Significado Clínico": CLASS_INFO[cls]["name_pt"],
        "Risco": CLASS_INFO[cls]["risk_level"],
        "Amostras": cinfo["count_total"],
        "Cor Original": CLASS_INFO[cls]["cor_original_dataset"],
        "RGB Mediano": str(cinfo["median_rgb"]),
        "Luminância Grayscale": cinfo["median_luminance"],
    })
df_audit = pd.DataFrame(audit_rows)
print("\nTabela de Auditoria Cromática por Classe:")
print(df_audit.to_string(index=False))
            """
        ),
        code_cell(
            r"""
# Visualização das 6 classes originais e evidência do viés de cor/luminância
fig, axes = plt.subplots(2, 6, figsize=(15, 5.8))
for i, cls in enumerate(CLASSES):
    fpath = df_manifest[(df_manifest["label"] == cls) & (df_manifest["split"] == "train")].iloc[0]["abs_path"]
    raw_rgb = compor_sobre_branco(Image.open(fpath))
    bin_arr = preprocessar_imagem_ecg(fpath, target_size=(128, 128), modo="binarizado", para_transfer_learning=True)

    axes[0, i].imshow(raw_rgb)
    lum = summary["chromatic_bias_audit"][cls]["median_luminance"]
    axes[0, i].set_title(f"{cls} — {CLASS_INFO[cls]['cor_original_dataset']}\n(Lum={lum:.0f})", fontsize=9.5, fontweight="bold")
    axes[0, i].axis("off")

    axes[1, i].imshow(bin_arr[:, :, 0], cmap="gray", vmin=0, vmax=1)
    axes[1, i].set_title(f"{cls} — Pós-Pipeline\n(Invariante à Cor)", fontsize=9.5, fontweight="bold", color="#059669")
    axes[1, i].axis("off")

fig.suptitle("Antes vs. Depois da Remoção de Viés Cromático e Recorte ROI (6 Classes AAMI)", fontsize=13, fontweight="bold")
plt.tight_layout()
plt.show()
            """
        ),
        md_cell(
            r"""
---
## 3. Etapas Detalhadas do Pipeline de Pré-processamento

Cada imagem passa por 5 etapas determinísticas implementadas em `Fase4/src/preprocessamento.py`:
1. **Conversão de Formato (`RGBA -> RGB`):** composição sobre fundo branco puro `(255, 255, 255)` eliminando o canal alfa.
2. **Binarização Agnóstica à Cor (*Color-Invariant Masking*):** mede a distância máxima de qualquer canal RGB ao fundo estimado $d(x,y) = \max_c (bg_c - I_c(x,y))$, normaliza pelo percentil 95 da tinta e aplica binarização rigorosa com dilatação morfológica de 1 pixel — eliminando 100% da cor e da luminância específica de cada classe.
3. **Recorte de Região de Interesse (ROI):** recorta a janela `(52, 28, 388, 258)` para imagens padrão `432×288`, eliminando **37,9% de margens brancas vazias** sem distorcer a escala temporal do complexo QRS nem o intervalo R-R.
4. **Redimensionamento Padronizado:** `128×128` para a `CardioCNN` (do zero) e `224×224` em 3 canais replicados para Transfer Learning (`ResNet18`).
5. **Normalização de Intensidade:**
   - **CNN do zero:** `[0.0, 1.0]` com inversão de polaridade (traço do ECG = `1.0`, fundo = `0.0`), concentrando ativações convolucionais sobre o sinal elétrico;
   - **Transfer Learning (ResNet18):** padronização pelos momentos do ImageNet (`mean=[0.485, 0.456, 0.406]`, `std=[0.229, 0.224, 0.225]`).
            """
        ),
        code_cell(
            r"""
# Demonstração passo a passo do pipeline em 3 classes críticas (N, M, V)
fig, axes = plt.subplots(3, 5, figsize=(15, 7.8))
col_titles = [
    "1. Original RGBA\n(432x288 + ROI)",
    "2. Grayscale Ingênuo\n(Viés de Luminância!)",
    "3. Binarização\nColor-Invariant",
    f"4. Recorte ROI\n(-{summary['roi_area_reduction_pct']}% área)",
    "5. Tensor Normalizado\n128x128 [0, 1]",
]
for r, cls in enumerate(["N", "M", "V"]):
    fpath = df_manifest[(df_manifest["label"] == cls) & (df_manifest["split"] == "train")].iloc[0]["abs_path"]
    raw = Image.open(fpath)
    rgb = compor_sobre_branco(raw)
    gray = rgb.convert("L")
    mask = extrair_mascara_traco_invariante_cor(raw)
    roi = recortar_roi_ecg(mask, raw.size)
    tensor_vis = preprocessar_imagem_ecg(raw, target_size=(128, 128), modo="binarizado", para_transfer_learning=False)

    axes[r, 0].imshow(rgb)
    l, t, rx, b = STD_ROI_BOX
    axes[r, 0].add_patch(plt.Rectangle((l, t), rx - l, b - t, fill=False, edgecolor="#e11d48", lw=1.6, ls="--"))
    axes[r, 0].set_ylabel(f"Classe {cls}", fontsize=10, fontweight="bold")
    axes[r, 1].imshow(gray, cmap="gray", vmin=0, vmax=255)
    axes[r, 2].imshow(1.0 - mask, cmap="gray", vmin=0, vmax=1)
    axes[r, 3].imshow(1.0 - roi, cmap="gray", vmin=0, vmax=1)
    axes[r, 4].imshow(tensor_vis[:, :, 0], cmap="inferno", vmin=0, vmax=1)
    for c in range(5):
        if r == 0:
            axes[r, c].set_title(col_titles[c], fontsize=9.5, fontweight="bold")
        axes[r, c].set_xticks([]); axes[r, c].set_yticks([])

plt.suptitle("Etapas do Pipeline de Pré-processamento Médico — CardioIA Fase 4", fontsize=13, fontweight="bold")
plt.tight_layout()
plt.show()
            """
        ),
        md_cell(
            r"""
---
## 4. Divisão Estratificada (Treino, Validação e Teste) e Data Augmentation Clínico

* **Treino (`240` imagens — `40/classe`, `57,1%`):** 80% da pasta `train/` original.
* **Validação (`60` imagens — `10/classe`, `14,3%`):** 20% estratificado da pasta `train/` para seleção de hiperparâmetros e melhor checkpoint.
* **Teste Independente (`120` imagens — `20/classe`, `28,6%`):** pasta `test/` original mantida 100% isolada.

No treinamento, aplicamos **Data Augmentation clinicamente válido** (pequenos deslocamentos horizontais/verticais, leve variação de ganho/espessura e ruído gaussiano sutil de eletrodo), **evitando deliberadamente flips horizontais e verticais**, pois inverter um ECG alteraria a polaridade do segmento ST (confundindo supra com infra de ST) e a sequência fisiológica P-QRS-T.
            """
        ),
        code_cell(
            r"""
# Tabela de contingência Split x Classe
ct = pd.crosstab(df_manifest["split"], df_manifest["label"]).loc[["train", "val", "test"], CLASSES]
ct["Total"] = ct.sum(axis=1)
print("Distribuição Estratificada (Split x Classe):")
print(ct.to_string())

# Visualização de Data Augmentation clinicamente seguro em uma amostra de Infarto (M)
sample_m = df_manifest[(df_manifest["label"] == "M") & (df_manifest["split"] == "train")].iloc[0]["abs_path"]
base_arr = preprocessar_imagem_ecg(sample_m, target_size=(128, 128), modo="binarizado", para_transfer_learning=False)

fig, axes = plt.subplots(1, 5, figsize=(14, 2.8))
axes[0].imshow(base_arr[:, :, 0], cmap="gray_r", vmin=0, vmax=1)
axes[0].set_title("Pré-processada Base", fontsize=9.5, fontweight="bold")
axes[0].axis("off")

rng = np.random.default_rng(123)
for i in range(1, 5):
    aug = augmentar_ecg_clinico(base_arr, para_transfer=False, rng=rng)
    axes[i].imshow(aug[:, :, 0], cmap="gray_r", vmin=0, vmax=1)
    axes[i].set_title(f"Augmentation #{i}", fontsize=9.5)
    axes[i].axis("off")

plt.suptitle("Data Augmentation Clinicamente Seguro (Sem Flip Vertical/Horizontal) — Classe M", fontsize=12, fontweight="bold")
plt.tight_layout()
plt.show()
            """
        ),
        code_cell(
            r"""
# Verificação estatística dos tensores finais (média, desvio padrão e faixa de valores)
sample_paths = df_manifest[df_manifest["split"] == "train"]["abs_path"].tolist()[:30]
batch_cnn = np.stack([preprocessar_imagem_ecg(p, (128, 128), "binarizado", False) for p in sample_paths])
batch_tl = np.stack([preprocessar_imagem_ecg(p, (224, 224), "binarizado", True) for p in sample_paths])

print(f"Lote CardioCNN (Zero):      shape={batch_cnn.shape}, dtype={batch_cnn.dtype}, min={batch_cnn.min():.3f}, max={batch_cnn.max():.3f}, mean={batch_cnn.mean():.4f}")
print(f"Lote ResNet18 (Transfer):   shape={batch_tl.shape}, dtype={batch_tl.dtype}, min={batch_tl.min():.3f}, max={batch_tl.max():.3f}, mean={batch_tl.mean():.4f}")
print("Manifesto salvo em:", processed_dir / "manifest_dataset.csv")
print("Pipeline da Parte 1 validado com sucesso!")
            """
        ),
    ]


# ---------------------------------------------------------------------------
# NOTEBOOK 2 — PARTE 2: Classificação com CNN do Zero vs Transfer Learning
# ---------------------------------------------------------------------------
def build_notebook_2() -> List[Dict[str, Any]]:
    return [
        md_cell(
            r"""
# FIAP — Inteligência Artificial (PBL · 2º Ano)
## CardioIA: A Nova Era da Cardiologia Inteligente
### Fase 4 (Parte 2) — Classificação de Imagens Médicas de ECG com CNN do Zero e Transfer Learning (ResNet18)

* **Aluno:** Cauã Santos — **RM:** 566599
* **Abordagens Comparadas:**
  1. **CardioCNN (Treinada do Zero):** Rede Convolucional de 4 blocos (`Conv2d -> BatchNorm -> ReLU -> MaxPool`) + *Dual Global Pooling* (Avg + Max) sobre tensores `(1, 128, 128)` binarizados.
  2. **ResNet18 (Transfer Learning — ImageNet-1K):** Treinamento em dois estágios (*Feature Extraction* com backbone congelado + *Fine-Tuning* com learning rate diferencial) sobre tensores `(3, 224, 224)` binarizados.
* **Avaliação Clínica:** Acurácia, Precisão, Recall, F1-Score (Macro e por classe), Matriz de Confusão, Explicabilidade visual via **Grad-CAM** e **Protótipo Interativo de Classificação**.
            """
        ),
        code_cell(
            r"""
import os
import sys
import json
from pathlib import Path

if "google.colab" in sys.modules and not Path("/content/CardioIA").exists():
    os.system("git clone https://github.com/cauasantoslt/CardioIA.git /content/CardioIA")

candidates = [Path.cwd(), Path.cwd().parent, Path.cwd().parent.parent, Path("/content/CardioIA")]
PROJECT_ROOT = next((p for p in candidates if (p / "Fase1" / "assets" / "images" / "ECG_Image_data").exists()), None)
assert PROJECT_ROOT is not None, "Repositório CardioIA não encontrado."

SRC_DIR = PROJECT_ROOT / "Fase4" / "src"
MODELS_DIR = PROJECT_ROOT / "Fase4" / "models"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import torch
from sklearn.metrics import classification_report, confusion_matrix
from torch.utils.data import DataLoader

from preprocessamento import CLASSES, CLASS_INFO, auditar_e_organizar_dataset, preprocessar_imagem_ecg
from modelos import (
    CardioCNN,
    ResNet18ECG,
    ECGDataset,
    GradCAM,
    CardioPredictor,
    array_para_tensor,
    renderizar_gradcam_sobreposto,
)
from treinar_e_avaliar import avaliar_modelo, treinar_cnn_do_zero, treinar_resnet18_transfer

plt.style.use("seaborn-v0_8-whitegrid" if "seaborn-v0_8-whitegrid" in plt.style.available else "default")
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
print(f"PyTorch {torch.__version__} | Dispositivo: {device}")
            """
        ),
        md_cell(
            r"""
---
## 1. Carregamento do Dataset Organizado e Arquiteturas

Para reprodutibilidade rápida no notebook, a flag `RETREINAR_DO_ZERO = False` carrega os checkpoints já treinados e auditados em `Fase4/models/` (gerados por `Fase4/src/treinar_e_avaliar.py`). Altere para `True` caso deseje reexecutar todas as épocas do treinamento diretamente no Google Colab com GPU.
            """
        ),
        code_cell(
            r"""
df, prep_summary = auditar_e_organizar_dataset()
print("Splits carregados:", prep_summary["splits"])

RETREINAR_DO_ZERO = False  # Altere para True para retreinar no Colab (GPU/CPU)

cnn_ckpt = MODELS_DIR / "cnn_scratch_ecg.pt"
res_ckpt = MODELS_DIR / "resnet18_transfer_ecg.pt"
meta_path = MODELS_DIR / "metadata_modelos.json"

if RETREINAR_DO_ZERO or not (cnn_ckpt.exists() and res_ckpt.exists() and meta_path.exists()):
    print("Iniciando treinamento completo das duas abordagens...")
    cnn_model, cnn_res, _ = treinar_cnn_do_zero(df, device=device, epochs=45, batch_size=24)
    res_model, res_res, _ = treinar_resnet18_transfer(df, device=device, epochs_stage1=8, epochs_stage2=24, batch_size=20)
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    torch.save(cnn_model.state_dict(), cnn_ckpt)
    torch.save(res_model.state_dict(), res_ckpt)
    history_cnn = cnn_res["history"]
    history_res = res_res["history"]
    best_ep_cnn = cnn_res["best_epoch"]
    best_ep_res = res_res["best_epoch"]
    s1_epochs = res_res["epochs_stage1"]
else:
    print("Carregando pesos treinados salvos em Fase4/models/...")
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    cnn_model = CardioCNN(num_classes=len(CLASSES), in_channels=1).to(device)
    cnn_model.load_state_dict(torch.load(cnn_ckpt, map_location=device, weights_only=True))
    res_model = ResNet18ECG(num_classes=len(CLASSES), pretrained=False).to(device)
    res_model.load_state_dict(torch.load(res_ckpt, map_location=device, weights_only=True))
    history_cnn = meta["models"]["cnn_scratch"]["history"]
    history_res = meta["models"]["resnet18_transfer"]["history"]
    best_ep_cnn = meta["models"]["cnn_scratch"]["best_epoch"]
    best_ep_res = meta["models"]["resnet18_transfer"]["best_epoch"]
    s1_epochs = meta["models"]["resnet18_transfer"]["epochs_stage1"]

print(f"Parâmetros CardioCNN (Do Zero):         {sum(p.numel() for p in cnn_model.parameters()):,}")
print(f"Parâmetros ResNet18 (Transfer Learning): {sum(p.numel() for p in res_model.parameters()):,}")
            """
        ),
        md_cell(
            r"""
---
## 2. Curvas de Treinamento e Validação (Convergência das Duas Abordagens)
            """
        ),
        code_cell(
            r"""
fig, axes = plt.subplots(2, 2, figsize=(13.5, 8))
ep_c = np.arange(1, len(history_cnn["train_loss"]) + 1)
ep_r = np.arange(1, len(history_res["train_loss"]) + 1)

axes[0, 0].plot(ep_c, history_cnn["train_loss"], label="Treino", color="#2563eb", lw=2)
axes[0, 0].plot(ep_c, history_cnn["val_loss"], label="Validação", color="#dc2626", lw=2, ls="--")
axes[0, 0].axvline(best_ep_cnn, color="#059669", ls=":", label=f"Melhor época ({best_ep_cnn})")
axes[0, 0].set_title("CardioCNN (Do Zero) — Loss", fontweight="bold")
axes[0, 0].set_xlabel("Época"); axes[0, 0].set_ylabel("Loss"); axes[0, 0].legend()

axes[0, 1].plot(ep_c, history_cnn["train_acc"], label="Treino", color="#2563eb", lw=2)
axes[0, 1].plot(ep_c, history_cnn["val_acc"], label="Validação", color="#059669", lw=2, ls="--")
axes[0, 1].axvline(best_ep_cnn, color="#059669", ls=":", label=f"Melhor época ({best_ep_cnn})")
axes[0, 1].set_title("CardioCNN (Do Zero) — Acurácia", fontweight="bold")
axes[0, 1].set_xlabel("Época"); axes[0, 1].set_ylabel("Acurácia"); axes[0, 1].set_ylim(0, 1.05); axes[0, 1].legend()

axes[1, 0].plot(ep_r, history_res["train_loss"], label="Treino", color="#7c3aed", lw=2)
axes[1, 0].plot(ep_r, history_res["val_loss"], label="Validação", color="#dc2626", lw=2, ls="--")
axes[1, 0].axvline(s1_epochs + 0.5, color="#f59e0b", ls="-.", label="Início Fine-Tuning")
axes[1, 0].axvline(best_ep_res, color="#059669", ls=":", label=f"Melhor época ({best_ep_res})")
axes[1, 0].set_title("ResNet18 (Transfer Learning) — Loss", fontweight="bold")
axes[1, 0].set_xlabel("Época"); axes[1, 0].set_ylabel("Loss"); axes[1, 0].legend()

axes[1, 1].plot(ep_r, history_res["train_acc"], label="Treino", color="#7c3aed", lw=2)
axes[1, 1].plot(ep_r, history_res["val_acc"], label="Validação", color="#059669", lw=2, ls="--")
axes[1, 1].axvline(s1_epochs + 0.5, color="#f59e0b", ls="-.", label="Início Fine-Tuning")
axes[1, 1].axvline(best_ep_res, color="#059669", ls=":", label=f"Melhor época ({best_ep_res})")
axes[1, 1].set_title("ResNet18 (Transfer Learning) — Acurácia", fontweight="bold")
axes[1, 1].set_xlabel("Época"); axes[1, 1].set_ylabel("Acurácia"); axes[1, 1].set_ylim(0, 1.05); axes[1, 1].legend()

plt.suptitle("Evolução do Treinamento — CardioCNN (Zero) vs. ResNet18 (Transfer Learning)", fontsize=13, fontweight="bold")
plt.tight_layout()
plt.show()
            """
        ),
        md_cell(
            r"""
---
## 3. Avaliação no Conjunto de Teste Independente (n = 120 imagens)

Avaliamos ambas as abordagens sobre o mesmo conjunto de teste independente (20 exames por classe, **100% binarizados e livres de viés cromático**) com as métricas: **Acurácia, Precisão, Recall, F1-Score e Matriz de Confusão**.
            """
        ),
        code_cell(
            r"""
te_df = df[df["split"] == "test"].reset_index(drop=True)
dl_te_cnn = DataLoader(ECGDataset(te_df["abs_path"].tolist(), te_df["label_idx"].tolist(), (128, 128), "binarizado", False, False), batch_size=24)
dl_te_res = DataLoader(ECGDataset(te_df["abs_path"].tolist(), te_df["label_idx"].tolist(), (224, 224), "binarizado", True, False), batch_size=20)

eval_cnn = avaliar_modelo(cnn_model, dl_te_cnn, device)
eval_res = avaliar_modelo(res_model, dl_te_res, device)

comp_df = pd.DataFrame([
    {
        "Modelo": "CardioCNN (Treinada do Zero)",
        "Acurácia": f"{eval_cnn['accuracy']*100:.2f}%",
        "Precisão (Macro)": f"{eval_cnn['precision_macro']*100:.2f}%",
        "Recall (Macro)": f"{eval_cnn['recall_macro']*100:.2f}%",
        "F1-Score (Macro)": f"{eval_cnn['f1_macro']*100:.2f}%",
    },
    {
        "Modelo": "ResNet18 (Transfer Learning)",
        "Acurácia": f"{eval_res['accuracy']*100:.2f}%",
        "Precisão (Macro)": f"{eval_res['precision_macro']*100:.2f}%",
        "Recall (Macro)": f"{eval_res['recall_macro']*100:.2f}%",
        "F1-Score (Macro)": f"{eval_res['f1_macro']*100:.2f}%",
    },
])
print("=== QUADRO COMPARATIVO NO CONJUNTO DE TESTE (n=120) ===")
print(comp_df.to_string(index=False))

print("\n--- Classification Report: CardioCNN (Do Zero) ---")
print(classification_report(eval_cnn["y_true"], eval_cnn["y_pred"], target_names=CLASSES, digits=4))

print("--- Classification Report: ResNet18 (Transfer Learning) ---")
print(classification_report(eval_res["y_true"], eval_res["y_pred"], target_names=CLASSES, digits=4))
            """
        ),
        code_cell(
            r"""
# Matrizes de Confusão lado a lado
fig, axes = plt.subplots(1, 2, figsize=(13, 5.2))
sns.heatmap(np.array(eval_cnn["confusion_matrix"]), annot=True, fmt="d", cmap="Blues",
            xticklabels=CLASSES, yticklabels=CLASSES, ax=axes[0], cbar=False)
axes[0].set_title(f"CardioCNN (Zero) | Acc={eval_cnn['accuracy']*100:.2f}% | F1={eval_cnn['f1_macro']*100:.2f}%", fontweight="bold")
axes[0].set_xlabel("Predito"); axes[0].set_ylabel("Real (AAMI)")

sns.heatmap(np.array(eval_res["confusion_matrix"]), annot=True, fmt="d", cmap="Purples",
            xticklabels=CLASSES, yticklabels=CLASSES, ax=axes[1], cbar=False)
axes[1].set_title(f"ResNet18 (Transfer) | Acc={eval_res['accuracy']*100:.2f}% | F1={eval_res['f1_macro']*100:.2f}%", fontweight="bold")
axes[1].set_xlabel("Predito"); axes[1].set_ylabel("Real (AAMI)")

plt.suptitle("Matrizes de Confusão no Conjunto de Teste Independente (Sem Viés de Cor)", fontsize=13, fontweight="bold")
plt.tight_layout()
plt.show()
            """
        ),
        md_cell(
            r"""
---
## 4. Explicabilidade Clínica com Grad-CAM e Protótipo Interativo de Inferência

Aplicamos **Grad-CAM** na última camada convolucional da `ResNet18` (`layer4[-1].conv2`) para verificar visualmente se a rede concentra atenção nos picos **QRS**, ondas **P/T** e segmento **ST**, e demonstramos o motor de inferência `CardioPredictor` que também alimenta a interface web Flask (`Fase4/backend/app.py`) e o aplicativo mobile em React Native (`Fase4/mobile/App.js`).
            """
        ),
        code_cell(
            r"""
predictor = CardioPredictor(MODELS_DIR)

# Demonstração do Protótipo de Inferência Clínica em 6 exames do conjunto de teste (1 de cada classe)
fig, axes = plt.subplots(2, 6, figsize=(15.5, 5.4))
for i, cls in enumerate(CLASSES):
    sample_path = te_df[te_df["label"] == cls].iloc[0]["abs_path"]
    res = predictor.predict(sample_path, model_key="resnet18_transfer", include_gradcam=True)

    # Decodifica imagens retornadas pelo protótipo
    import base64, io
    from PIL import Image
    pre_img = Image.open(io.BytesIO(base64.b64decode(res["preprocessed_image_b64"].split(",", 1)[1])))
    cam_img = Image.open(io.BytesIO(base64.b64decode(res["gradcam_image_b64"].split(",", 1)[1])))

    axes[0, i].imshow(pre_img)
    axes[0, i].set_title(f"Real: {cls} ({CLASS_INFO[cls]['risk_level']})", fontsize=9.5, fontweight="bold")
    axes[0, i].axis("off")

    cor = "#059669" if res["predicted_class"] == cls else "#dc2626"
    axes[1, i].imshow(cam_img)
    axes[1, i].set_title(f"Pred: {res['predicted_class']} ({res['confidence_pct']:.1f}%)", fontsize=9.5, fontweight="bold", color=cor)
    axes[1, i].axis("off")

    print(
        f"[{Path(sample_path).name:12s}] Real={cls} -> Pred={res['predicted_class']} "
        f"({res['class_name_pt']:38s}) | Conf={res['confidence_pct']:5.1f}% | Risco={res['risk_level']:8s} | {res['inference_time_ms']} ms"
    )

plt.suptitle("Protótipo CardioIA — Entrada Binarizada e Explicabilidade Grad-CAM (ResNet18)", fontsize=13, fontweight="bold")
plt.tight_layout()
plt.show()
            """
        ),
    ]


# ---------------------------------------------------------------------------
# NOTEBOOK 3 — IR ALÉM 1: Ética, Governança e Fairness em Visão Computacional
# ---------------------------------------------------------------------------
def build_notebook_3() -> List[Dict[str, Any]]:
    return [
        md_cell(
            r"""
# FIAP — Inteligência Artificial (PBL · 2º Ano)
## CardioIA: A Nova Era da Cardiologia Inteligente
### Fase 4 (Ir Além 1) — Ética, Governança e Métricas de Fairness em Visão Computacional Médica

* **Aluno:** Cauã Santos — **RM:** 566599
* **Objetivos:**
  1. Identificar e provar experimentalmente limitações e vieses reais no dataset público de ECG (*Viés Cromático / Efeito Clever Hans*, tamanho amostral reduzido, balanceamento artificial distante da prevalência epidemiológica real e ausência de metadados demográficos).
  2. Aplicar métricas formais de **Fairness** (*Demographic Parity Difference*, *Disparate Impact Ratio*, *Equal Opportunity Difference*, *Equalized Odds Gap* e *FNR Parity*) comparando subgrupos de infraestrutura de aquisição (**Hospital de Referência** vs. **UBS / Wearable com Ruído**).
  3. Validar práticas concretas de mitigação: **Pré-processamento Color-Invariant** e **Calibração de Limiar Clínico ($\tau = 0{,}30$)** para reduzir Falsos Negativos em emergências cardiovasculares (`M`, `V`, `F`).
            """
        ),
        code_cell(
            r"""
import os
import sys
import json
from pathlib import Path

if "google.colab" in sys.modules and not Path("/content/CardioIA").exists():
    os.system("git clone https://github.com/cauasantoslt/CardioIA.git /content/CardioIA")

candidates = [Path.cwd(), Path.cwd().parent, Path.cwd().parent.parent, Path("/content/CardioIA")]
PROJECT_ROOT = next((p for p in candidates if (p / "Fase1" / "assets" / "images" / "ECG_Image_data").exists()), None)
assert PROJECT_ROOT is not None, "Repositório CardioIA não encontrado."

SRC_DIR = PROJECT_ROOT / "Fase4" / "src"
PROCESSED_DIR = PROJECT_ROOT / "Fase4" / "data" / "processed"
ASSETS_DIR = PROJECT_ROOT / "Fase4" / "assets"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from PIL import Image

from auditoria_fairness import executar_auditoria_completa

audit_json = PROCESSED_DIR / "fairness_audit.json"
REEXECUTAR_AUDITORIA = False  # Altere para True para reexecutar o experimento completo

if REEXECUTAR_AUDITORIA or not audit_json.exists():
    audit = executar_auditoria_completa()
else:
    audit = json.loads(audit_json.read_text(encoding="utf-8"))

print("Auditoria de Ética e Fairness carregada com sucesso!")
            """
        ),
        md_cell(
            r"""
---
## 1. Experimento 1 — Prova Experimental do Efeito *Clever Hans* (Viés Cromático)

Treinamos modelos ingênuos diretamente sobre as imagens RGB e Grayscale simples e submetemos todos os modelos a um **Teste Contrafactual de Troca de Cores (*Color Swap*)**, no qual traçados de **Infarto (`M`)** são pintados de **Ciano** (cor original da classe Normal `N`) e vice-versa.
            """
        ),
        code_cell(
            r"""
exp1 = audit["experimento_1_vies_cromatico_clever_hans"]
rows_exp1 = []
for nome, vals in exp1.items():
    rows_exp1.append({
        "Modelo / Pipeline": nome,
        "Acurácia Original": f"{vals['acc_original']*100:.2f}%",
        "Acurácia Color Swap (OOD)": f"{vals['acc_color_swap']*100:.2f}%",
        "Queda (p.p.)": f"{vals['queda_pp']:+.2f} pp",
    })
print("=== RESULTADO DO TESTE CONTRAFACTUAL DE TROCA DE CORES ===")
print(pd.DataFrame(rows_exp1).to_string(index=False))

fig, ax = plt.subplots(figsize=(13.5, 5.8))
ax.imshow(Image.open(ASSETS_DIR / "08_fairness_clever_hans_color_swap.png"))
ax.axis("off")
plt.tight_layout()
plt.show()
            """
        ),
        md_cell(
            r"""
---
## 2. Experimento 2 e 3 — Métricas Formais de Fairness por Subgrupo de Infraestrutura e Mitigação Sensível ao Risco

Avaliamos a equidade da `ResNet18` entre:
* **Grupo Privilegiado (`Hospital_Ref`):** exames de ECG com alta razão sinal-ruído.
* **Grupo Desfavorecido (`UBS_Ruido`):** exames com ruído de eletrodo, atenuação de contraste e leve deslocamento basal (simulando clínicas periféricas, UBSs e wearables de baixo custo).

Em seguida aplicamos **Calibração de Limiar Clínico ($\tau = 0{,}30$)** sobre a probabilidade acumulada das classes de alto risco (`M + V + F`), reduzindo drasticamente a Taxa de Falsos Negativos (FNR) e diminuindo o *Equal Opportunity Gap* no grupo desfavorecido.
            """
        ),
        code_cell(
            r"""
f_antes = audit["experimento_3_fairness_critico_antes_mitigacao"]
f_depois = audit["experimento_3_fairness_critico_depois_mitigacao_tau_030"]

comp_fair = pd.DataFrame([
    {
        "Cenário (Triagem Crítica M/V/F)": "Argmax Padrão (Antes)",
        "TPR Hospital": f"{f_antes['group_privileged']['Hospital_Ref']['tpr']*100:.1f}%",
        "TPR UBS (Ruído)": f"{f_antes['group_unprivileged']['UBS_Ruido']['tpr']*100:.1f}%",
        "FNR UBS ↓": f"{f_antes['group_unprivileged']['UBS_Ruido']['fnr']*100:.1f}%",
        "Equal Opp. Diff ↓": f"{f_antes['equal_opportunity_diff']:.4f}",
        "Demog. Parity Diff ↓": f"{f_antes['demographic_parity_diff']:.4f}",
        "Disparate Impact (≈1)": f"{f_antes['disparate_impact_ratio']:.4f}",
    },
    {
        "Cenário (Triagem Crítica M/V/F)": "Threshold Clínico τ=0,30 (Mitigado)",
        "TPR Hospital": f"{f_depois['group_privileged']['Hospital_Ref']['tpr']*100:.1f}%",
        "TPR UBS (Ruído)": f"{f_depois['group_unprivileged']['UBS_Ruido']['tpr']*100:.1f}%",
        "FNR UBS ↓": f"{f_depois['group_unprivileged']['UBS_Ruido']['fnr']*100:.1f}%",
        "Equal Opp. Diff ↓": f"{f_depois['equal_opportunity_diff']:.4f}",
        "Demog. Parity Diff ↓": f"{f_depois['demographic_parity_diff']:.4f}",
        "Disparate Impact (≈1)": f"{f_depois['disparate_impact_ratio']:.4f}",
    },
])
print("=== MÉTRICAS DE FAIRNESS — ANTES VS. DEPOIS DA MITIGAÇÃO ===")
print(comp_fair.to_string(index=False))

fig, ax = plt.subplots(figsize=(13.5, 5.2))
ax.imshow(Image.open(ASSETS_DIR / "09_fairness_subgrupos_e_mitigacao.png"))
ax.axis("off")
plt.tight_layout()
plt.show()
            """
        ),
    ]


def main() -> None:
    execute_and_save_notebook(build_notebook_1(), NOTEBOOKS_DIR / "01_preprocessamento_ecg.ipynb")
    execute_and_save_notebook(build_notebook_2(), NOTEBOOKS_DIR / "02_classificacao_cnn_transfer_learning.ipynb")
    execute_and_save_notebook(build_notebook_3(), NOTEBOOKS_DIR / "03_etica_governanca_fairness.ipynb")
    print("\nTodos os 3 notebooks foram gerados e executados com sucesso!")


if __name__ == "__main__":
    main()
