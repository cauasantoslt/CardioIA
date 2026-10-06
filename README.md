# FIAP - Faculdade de Informática e Administração Paulista

<p align="center">
  <a href="https://www.fiap.com.br/">
    <img src="./Fase1/assets/logo-fiap.png" alt="FIAP - Faculdade de Informática e Administração Paulista" border="0" width="40%">
  </a>
</p>

<br>

# CardioIA: A Nova Era da Cardiologia Inteligente

> **Fase 1: Batimentos de Dados – Mapeando o Coração Moderno**  
> **Curso:** Inteligência Artificial (PBL - Project Based Learning)  
> **Instituição:** FIAP (Faculdade de Informática e Administração Paulista)

---

## 👥 Integrantes
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

## 🩺 5. Fase 2 – Diagnóstico Automatizado: IA no Estetoscópio Digital

Nesta fase, implementamos os módulos de automação diagnóstica e suporte à decisão médica, unindo **Processamento de Linguagem Natural (NLP)**, **Machine Learning Supervisionado**, **Visão Computacional com Redes Neurais** e um **Portal Web Interativo**:

### 5.1. Parte 1 – Extração de Sintomas e Mapeamento Ontológico de Doenças
* **Entrada Textual (`Fase2/data/frases_sintomas.txt`):** 10 relatos clínicos ricos descrevendo o que o paciente sente, quando os sintomas iniciaram e como afetam suas atividades diárias.
* **Mapa de Conhecimento (`Fase2/data/mapa_conhecimento.csv`):** Ontologia médica relacionando pares de sintomas (*Sintoma 1 | Sintoma 2*) às patologias correspondentes (*Síndrome Coronariana Aguda/IAM*, *Insuficiência Cardíaca*, *Fibrilação Atrial*, *Hipotensão/Pré-Síncope*, etc.).
* **Pipeline de Extração (`Fase2/src/extracao_diagnostico.py`):** Algoritmo de normalização Unicode (remoção de acentos e conversão para caixa baixa), busca léxica por entidades clínicas e inferência diagnóstica estruturada.

### 5.2. Parte 2 – Classificador de Triagem Textual (TF-IDF + Machine Learning)
* **Dataset de Triagem (`Fase2/data/triagem_risco.csv`):** 32 relatos médicos balanceados (16 de *alto risco* e 16 de *baixo risco*) simulando o Protocolo de Manchester para priorização de atendimento emergencial.
* **Vetorização Numérica:** Algoritmo **TF-IDF** (Term Frequency - Inverse Document Frequency) configurado com unigramas e bigramas (`ngram_range=(1, 2)`) e stop-words médicas em português.
* **Modelo Preditivo:** Regressão Logística com regularização L2, alcançando **100% de Acurácia** e **100% de Recall** para a classe crítica de alto risco no conjunto de teste.
* **Scripts e Notebook:**
  * Script standalone: `Fase2/src/classificador_risco.py`
  * Notebook unificado: `Fase2/notebooks/classificador_risco.ipynb` (com matriz de confusão gráfica, explicabilidade léxica e inferência em tempo real com probabilidades).

### 5.3. Ir Além 1 – Portal Web CardioIA (`cardioia-portal/`)
Aplicação web responsiva construída em **React 19 + Vite** com:
* **Autenticação Simulada (Context API):** Gerenciamento de sessão e persistência de token JWT falso em `localStorage`.
* **Proteção de Rotas:** Componente `ProtectedRoute` impedindo acesso a áreas restritas sem autenticação.
* **Dashboard Clínico:** Indicadores em tempo real (Total em Triagem, Consultas Hoje, Casos Críticos, Ocupação de Leitos) e banner de alertas emergenciais.
* **Triagem de Pacientes:** 10 pacientes clínicos com sinais vitais (P.A., Frequência Cardíaca, SpO2), queixa em texto livre, filtro por nível de risco e busca instantânea.
* **Agendamento de Consultas:** Gerenciamento complexo com `useReducer` (`ADD_APPOINTMENT`, `CANCEL_APPOINTMENT`, `FILTER_BY_DOCTOR`) e controle de inputs com `useState`.
* **Estilização Modular:** CSS Modules (`*.module.css`) com design system hospitalar moderno.

### 5.4. Ir Além 2 – Diagnóstico Visual de ECG com Rede Neural MLP em Keras (`Fase2/notebooks/mlp_ecg_diagnostico.ipynb`)
Pipeline de Deep Learning para classificação binária de exames de Eletrocardiograma (Normal vs. Anormal):
* **Dataset de ECG:** Imagens da pasta `Fase1/assets/images/ECG_Image_data/` (Normal: `N`; Anormal: `M`, `V`, `S`).
* **Pré-processamento:** Redimensionamento para $64 \times 64$ píxeis em escala de cinza, normalização $[0, 1]$ e achatamento (*flatten*) para vetor de 4096 features de entrada.
* **Arquitetura Keras:** Camada Dense (256, ReLU, He Normal), BatchNormalization, Dropout(0.3), Dense (64, ReLU), Dropout(0.2) e Saída Dense (1, Sigmoid).
* **Treinamento & Monitoramento:** `EarlyStopping(patience=5)` com Adam ($\alpha = 0.001$), curvas de perda/acurácia, Matriz de Confusão, Relatório de Classificação e Curva ROC/AUC.
* **Governança:** Discussão crítica sobre limitações do MLP frente a Redes Convolucionais (CNNs da Fase 4) e assimetria clínica dos Falsos Negativos.

---

## 🎥 Vídeos de Demonstração (YouTube - Não Listados)

| Fase / Entrega | Link do Vídeo | Descrição |
| :--- | :--- | :--- |
| **Fase 2: Diagnóstico Automatizado & Modelos** | [Link no YouTube (Vídeo Não Listado)](https://www.youtube.com/watch?v=SEU_LINK_AQUI) | Apresentação em até 4 min dos scripts de extração, treino do modelo de triagem, notebook e discussão de governança. |
| **Ir Além 1: Portal Web CardioIA (React)** | [Link no YouTube (Vídeo Não Listado)](https://www.youtube.com/watch?v=SEU_LINK_AQUI) | Demonstração do portal: login, proteção de rotas, dashboard, triagem e agendamento com useReducer. |

---

## 📁 6. Estrutura de Pastas Atualizada

```bash
CardioIA/
├── Fase1/
│   ├── assets/
│   │   ├── docs/
│   │   └── images/
│   │       └── ECG_Image_data/
│   │           ├── train/ (Classes: F, M, N, Q, S, V)
│   │           └── test/
│   └── data/
│       ├── processed/
│       └── raw/
├── Fase2/
│   ├── data/
│   │   ├── frases_sintomas.txt     # 10 relatos clínicos
│   │   ├── mapa_conhecimento.csv   # Ontologia clínica
│   │   └── triagem_risco.csv       # 32 frases rotuladas (alto/baixo risco)
│   ├── notebooks/
│   │   ├── classificador_risco.ipynb # Notebook unificado (Partes 1 e 2)
│   │   └── mlp_ecg_diagnostico.ipynb # Ir Além 2 (MLP em Keras para ECG)
│   └── src/
│       ├── extracao_diagnostico.py # Script de extração ontológica
│       └── classificador_risco.py  # Script de treino e inferência TF-IDF
├── cardioia-portal/                # Ir Além 1: Portal Web (React + Vite)
│   ├── src/
│   │   ├── components/             # Header, Sidebar, StatCard, PatientCard, etc.
│   │   ├── contexts/               # AuthContext.jsx (JWT simulado)
│   │   ├── pages/                  # Login, Dashboard, Patients, Appointments
│   │   ├── reducers/               # appointmentReducer.js
│   │   ├── services/               # api.js
│   │   └── styles/                 # *.module.css
│   ├── package.json
│   └── README.md
├── .gitignore
└── README.md
```

---

## ⚙️ Como Executar os Módulos da Fase 2

### 1. Extração Ontológica e Classificador de Triagem (CLI)
```bash
# Executar a extração baseada no mapa de conhecimento
python Fase2/src/extracao_diagnostico.py

# Treinar e testar o classificador TF-IDF de triagem
python Fase2/src/classificador_risco.py
```

### 2. Jupyter Notebooks
Abra o JupyterLab ou VS Code e execute:
* `Fase2/notebooks/classificador_risco.ipynb` (Partes 1 e 2 integradas com dados da pasta `data/`).
* `Fase2/notebooks/mlp_ecg_diagnostico.ipynb` (Ir Além 2 - Rede Neural MLP com Keras para imagens de ECG).

### 3. Portal Web CardioIA (React + Vite)
```bash
cd cardioia-portal
npm install
npm run dev
```
Acesse em: `http://localhost:5173` (Credenciais: `medico@cardioia.com` / `cardio123`).

---

## 🗃 Histórico de Lançamentos

* **0.1.0 - 01/09/2026**
  * Entrega da **Fase 1 (Batimentos de Dados)**.
* **0.2.0 - 05/10/2026**
  * Entrega da **Fase 2 (Diagnóstico Automatizado – IA no Estetoscópio Digital)**.
  * Módulo de extração ontológica e inferência diagnóstica a partir de queixas em texto livre.
  * Classificador estatístico supervisionado com TF-IDF e Regressão Logística para triagem de risco clínico.
  * Implementação da interface web interativa do portal hospitalar em React + Vite (Ir Além 1).
  * Implementação do modelo de rede neural profunda MLP em Keras para diagnóstico visual de ECG (Ir Além 2).
* **0.3.0 - Em breve**
  * *Fase 3: Monitoramento Contínuo - IoT e Sensores Médicos.*
* **0.4.0 - Em breve**
  * *Fase 4: Coração em Imagens - Visão Computacional com CNNs.*
* **0.5.0 - Em breve**
  * *Fase 5: Assistente Cardiológico Virtual com RAG & NLP.*

---

## 📋 Licença

<img style="height:22px!important;margin-left:3px;vertical-align:text-bottom;" src="https://mirrors.creativecommons.org/presskit/icons/cc.svg?ref=chooser-v1"><img style="height:22px!important;margin-left:3px;vertical-align:text-bottom;" src="https://mirrors.creativecommons.org/presskit/icons/by.svg?ref=chooser-v1"><p xmlns:cc="http://creativecommons.org/ns#" xmlns:dct="http://purl.org/dc/terms/"><a property="dct:title" rel="cc:attributionURL" href="https://github.com/agodoi/template">MODELO GIT FIAP</a> por <a rel="cc:attributionURL dct:creator" property="cc:attributionName" href="https://fiap.com.br">Fiap</a> está licenciado sobre <a href="http://creativecommons.org/licenses/by/4.0/?ref=chooser-v1" target="_blank" rel="license noopener noreferrer" style="display:inline-block;">Attribution 4.0 International</a>.</p>
