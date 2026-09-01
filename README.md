# FIAP - Faculdade de Informática e Administração Paulista

<p align="center">
  <a href="https://www.fiap.com.br/">
    <img src="./Fase1/assets/logo-fiap.png" alt="FIAP - Faculdade de Informática e Administração Paulista" border="0" width="40%">
  </a>
</p>

<br>

# 🫀 CardioIA: A Nova Era da Cardiologia Inteligente

> **Fase 1: Batimentos de Dados – Mapeando o Coração Moderno**  
> **Curso:** Inteligência Artificial (PBL - Project Based Learning)  
> **Instituição:** FIAP (Faculdade de Informática e Administração Paulista)

---

## 👥 Integrantes
* **Grupo:** 82
* **Aluno:** [Cauã Santos](https://www.linkedin.com/in/cauasantoslt) — **RM:** 566599

### 👩‍🏫 Professores
* **Tutor(a):** [Leonardo Ruiz Orabona](https://www.linkedin.com/in/leonardoorabona/)
* **Coordenador(a):** [André Godoi](https://www.linkedin.com/in/andregodoichiovato/)

---

## 🔗 Acesso aos Dados (Armazenamento em Nuvem)

Todos os dados coletados e preparados para esta fase (tabelas numéricas, corpus textual para NLP e banco de imagens de ECG) estão disponíveis no link público abaixo:

<div align="center">

[![Google Drive](https://img.shields.io/badge/Google%20Drive-Acesso%20aos%20Dados%20Completos%20(CardioIA)-4285F4?style=for-the-badge&logo=googledrive&logoColor=white)](https://drive.google.com/drive/folders/1zWeh3gKtj51HhFHUD_G8GjBWjF0ZIVlX?usp=sharing)

**Link direto:** [https://drive.google.com/drive/folders/1zWeh3gKtj51HhFHUD_G8GjBWjF0ZIVlX?usp=sharing](https://drive.google.com/drive/folders/1zWeh3gKtj51HhFHUD_G8GjBWjF0ZIVlX?usp=sharing)

</div>

---

## 📜 1. Descrição do Projeto

O **CardioIA** é uma plataforma digital concebida para simular o ecossistema de uma cardiologia moderna e inteligente, integrando **Ciência de Dados**, **Machine Learning**, **Processamento de Linguagem Natural (NLP)**, **Visão Computacional** e **IoT**. 

Na **Fase 1 (Batimentos de Dados)**, atuamos na base do ecossistema hospitalar: levantamento, organização, curadoria clínica e governança dos dados que alimentarão os futuros modelos diagnósticos, preditivos e assistentes virtuais da plataforma.

---

## 📊 2. Parte 1 – Dados Numéricos (IoT / Clínico)

### 2.1. Origem e Composição da Base
* **Dados Reais (`heart_disease_original.csv`):** 303 registros clínicos provenientes do *UCI Machine Learning Repository / Cleveland Clinic Foundation*, padrão de referência em pesquisas cardiovasculares.
* **Dados Processados e Aumentados (`cardioia_dataset_processado.csv`):** Base expandida para **504 registros**, combinando os dados reais higienizados com dados sintéticos supervisionados (preservando correlações fisiológicas). A coluna `data_origin` identifica a procedência de cada registro (`real` ou `synthetic`).
* **Formatos:** `.csv` e `.xlsx`.

### 2.2. Dicionário de Variáveis Clínicas

| Variável | Nome Padronizado | Tipo | Domínio / Unidade | Relevância Clínica & Importância para IA |
| :--- | :--- | :--- | :--- | :--- |
| `age` | `age` | Contínuo | Anos | Fator de risco não modificável primário para aterosclerose e rigidez arterial. |
| `sex` | `sex` | Binário | 1 = Masc; 0 = Fem | Epidemiologia e apresentação clínica (mulheres frequentemente manifestam sintomas atípicos). |
| `cp` | `chest_pain_type` | Categórico | 1: Típica, 2: Atípica, 3: Não-anginosa, 4: Assintomático | Variável central na triagem de emergência para estratificação de risco de isquemia miocárdica. |
| `trestbps` | `resting_bp` | Contínuo | mmHg | Pressão arterial sistólica em repouso. Hipertensão crônica gera sobrecarga e hipertrofia ventricular. |
| `chol` | `cholesterol` | Contínuo | mg/dl | Colesterol sérico total. Marcador de formação e instabilização de placas ateromatosas coronárias. |
| `fbs` | `fasting_blood_sugar` | Binário | 1 = >120 mg/dl; 0 = Normal | Glicemia de jejum elevada. Indicativo de diabetes, comorbidade de alto risco cardiovascular. |
| `restecg` | `rest_ecg` | Categórico | 0: Normal, 1: ST-T anormal, 2: Hipertrofia VE | Eletrocardiograma basal. Detecta alterações elétricas de sobrecarga e repolarização. |
| `thalach` | `max_heart_rate` | Contínuo | bpm | Frequência cardíaca máxima atingida em esforço. Reflete a reserva cronotrópica funcional. |
| `exang` | `exercise_angina` | Binário | 1 = Sim; 0 = Não | Angina induzida por esforço. Indicador direto de insuficiência de fluxo coronário. |
| `oldpeak` | `st_depression` | Contínuo | mm | Depressão do segmento ST induzida pelo esforço. Forte marcador de isquemia subendocárdica. |
| `slope` | `st_slope` | Categórico | 1: Ascendente, 2: Plano, 3: Descendente | Morfologia do ST no pico do esforço. Declives planos e descendentes indicam alto risco isquêmico. |
| `ca` | `num_major_vessels` | Discreto | 0 a 3 | Número de grandes vasos coronários com obstrução visualizados por fluoroscopia/angiografia. |
| `thal` | `thalassemia` | Categórico | 3: Normal, 6: Defeito Fixo, 7: Defeito Reversível | Cintilografia miocárdica. Diferencia miocárdio infartado fibrótico de tecido isquêmico viável. |
| `target` | `target` | Binário | 0: Ausente, 1: Presente | Desfecho clínico (presença de estenose coronariana significativa > 50%). |
| `data_origin` | `data_origin` | Texto | `real` / `synthetic` | Rastreabilidade da proveniência da linha para conformidade e governança. |

### 2.3. Governança, LGPD e Mitigação de Viés
* **Privacidade:** A base é integralmente anonimizada, sem identificadores diretos (PII), respeitando os preceitos da LGPD (Lei 13.709/2018).
* **Viés Amostral:** Identificamos as distribuições por sexo e faixa etária para aplicar técnicas de balanceamento (ex: pesos balanceados de classes) nas fases de treinamento supervisionado, prevenindo subdiagnósticos em populações sub-representadas.
* **Integração com IoT:** Variáveis como pressão, frequência cardíaca e ECG de repouso simulam dados coletados por sensores em tempo real (como microcontroladores ESP32 em fases futuras).

---

## 📝 3. Parte 2 – Dados Textuais (NLP)

### 3.1. Corpus Médico na Pasta `Fase1/assets/docs/`
1. **`01_diretriz_insuficiencia_cardiaca_sus.txt`** (Fonte: Ministério da Saúde / CONITEC / SBC): Critérios diagnósticos de Framingham, estadiamento funcional NYHA e protocolo terapêutico no SUS.
2. **`02_protocolo_sindrome_coronariana_aguda_scielo.txt`** (Fonte: SciELO / SBC): Manejo de emergência no Infarto Agudo do Miocárdio (IAMCSST e IAMSSST), tempo porta-ECG e troponina.
3. **`03_manejo_arritmias_fibrilacao_atrial_bvs.txt`** (Fonte: BVS / OPAS / SOBRAC): Diagnóstico de Fibrilação Atrial, identificação de ondas *f* e estratificação de risco de AVC pelo escore $CHA_2DS_2\text{-VASc}$.
4. **`04_hipertensao_arterial_saude_populacional_sus.txt`** (Fonte: Fiocruz / MS): Epidemiologia da HAS, lesões em órgãos-alvo e estratégias de adesão terapêutica na atenção primária.

### 3.2. Exploração por Processamento de Linguagem Natural (NLP)
* **Named Entity Recognition (NER Clínico):** Treinamento de modelos para identificar automaticamente sintomas (*"dispneia paroxística"*, *"dor precordial"*), medicações (*"Enalapril"*, *"Metoprolol"*) e escores de gravidade em prontuários e relatos livres.
* **Classificação de Tópicos e Triagem de Urgência:** Classificação automática de queixas de pacientes para priorizar emergências (SCA/IAM) frente a quadros crônicos ambulatoriais.
* **Análise de Sentimento e Adesão:** Análise do nível de ansiedade e adesão medicamentosa do paciente para o futuro assistente virtual (Fase 5).
* **RAG (Retrieval-Augmented Generation):** Uso das diretrizes oficiais como base vetorial de conhecimento confiável para alimentar chatbots médicos sem alucinações.

---

## 🖼️ 4. Parte 3 – Dados Visuais (Visão Computacional)

### 4.1. Conjunto de Imagens de ECG
Reunimos mais de 100 imagens de exames de Eletrocardiograma (ECG) organizadas na pasta `Fase1/assets/images/ECG_Image_data/`, estruturadas nos padrões internacionais da **AAMI / MIT-BIH**:

* **`N` (Normal Beat):** Batimentos sinusais normais (ritmo fisiológico de referência).
* **`S` (Supraventricular Ectopic Beat):** Extrassístoles supraventriculares (gatilhos para taquiarritmias e Fibrilação Atrial).
* **`V` (Ventricular Ectopic Beat):** Extrassístoles ventriculares (alerta para taquicardia/fibrilação ventricular).
* **`F` (Fusion Beat):** Batimentos de fusão ventricular (focos elétricos simultâneos).
* **`Q` (Unknown / Paced Beat):** Batimentos inclassificáveis ou originados por marca-passo.
* **`M` (Myocardial Infarction / Pathological):** Traçados com elevação de segmento ST e padrões isquêmicos agudos.

### 4.2. Exploração por Visão Computacional (VC)
* **Detecção de Padrões e Morfologia:** Algoritmos de filtragem e detecção de bordas para segmentar complexos **QRS**, medir intervalos **PR**, **QT** e desníveis do segmento **ST**.
* **Classificação com Redes Convolucionais (CNNs):** Treinamento de redes neurais (ex: ResNet, EfficientNet) para diagnóstico automatizado das classes de arritmia a partir da imagem do traçado.
* **Explicabilidade (Grad-CAM):** Geração de mapas de calor visuais destacando no traçado exatamente qual onda levou o modelo à predição diagnóstica, garantindo transparência e confiabilidade clínica.

---

## 📁 5. Estrutura de Pastas

```bash
CardioIA/
├── Fase1/
│   ├── assets/
│   │   ├── docs/
│   │   ├── images/
│   │   │   └── ECG_Image_data/
│   │   └── logo-fiap.png
│   └── data/
│       ├── processed/
│       └── raw/
├── notebooks/
├── .gitignore
└── README.md
```

---

## 🗃 Histórico de Lançamentos

* **0.1.0 - 01/09/2026**
  * Entrega da **Fase 1 (Batimentos de Dados)**.
  * Estruturação e curadoria dos datasets clínicos numéricos (real e sintético).
  * Coleta e contextualização do corpus textual médico para NLP.
  * Organização do acervo de imagens de exames de ECG por classes diagnósticas AAMI para Visão Computacional.
  * Documentação completa de governança, viés e dicionário clínico.
* **0.2.0 - XX/XX/2026**
  * *Fase 2: Diagnóstico Automatizado - Modelos Supervisionados de IA.*
* **0.3.0 - XX/XX/2026**
  * *Fase 3: Monitoramento Contínuo - IoT e Sensores Médicos.*
* **0.4.0 - XX/XX/2026**
  * *Fase 4: Coração em Imagens - Visão Computacional em Exames.*
* **0.5.0 - XX/XX/2026**
  * *Fase 5: Assistente Cardiológico Virtual com NLP.*

---

## 📋 Licença

<img style="height:22px!important;margin-left:3px;vertical-align:text-bottom;" src="https://mirrors.creativecommons.org/presskit/icons/cc.svg?ref=chooser-v1"><img style="height:22px!important;margin-left:3px;vertical-align:text-bottom;" src="https://mirrors.creativecommons.org/presskit/icons/by.svg?ref=chooser-v1"><p xmlns:cc="http://creativecommons.org/ns#" xmlns:dct="http://purl.org/dc/terms/"><a property="dct:title" rel="cc:attributionURL" href="https://github.com/agodoi/template">MODELO GIT FIAP</a> por <a rel="cc:attributionURL dct:creator" property="cc:attributionName" href="https://fiap.com.br">Fiap</a> está licenciado sobre <a href="http://creativecommons.org/licenses/by/4.0/?ref=chooser-v1" target="_blank" rel="license noopener noreferrer" style="display:inline-block;">Attribution 4.0 International</a>.</p>
# CardioIA
