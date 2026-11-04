# FIAP - Faculdade de Informática e Administração Paulista

<p align="center">
  <a href="https://www.fiap.com.br/">
    <img src="./Fase1/assets/logo-fiap.png" alt="FIAP - Faculdade de Informática e Administração Paulista" border="0" width="40%">
  </a>
</p>

<br>

# CardioIA: A Nova Era da Cardiologia Inteligente

> **Fase 3 - Monitoramento Contínuo: IoT na Saúde (Edge, Fog & Cloud Computing)**  
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

## 📡 6. Fase 3 – Monitoramento Contínuo: IoT na Saúde (Edge, Fog & Cloud)

Na **Fase 3**, expandimos o ecossistema **CardioIA** com o **CardioIA Wear**, um protótipo de dispositivo vestível (*wearable*) em **ESP32 (Wokwi)** integrado via **MQTT (HiveMQ)** a um dashboard em tempo real no **Node-RED** e a um subsistema automatizado **REST + RPA em Python**:

### 6.1. Parte 1 – Armazenamento e Processamento Local (Edge Computing)
* **Link do Projeto no Wokwi:** [**https://wokwi.com/projects/479801389695851521**](https://wokwi.com/projects/479801389695851521)
* **Circuito e Firmware ESP32 (`Fase3/esp32_wearable/`):**
  * **Sensores:** **DHT22** obrigatório (temperatura corporal °C e umidade/sudorese %), **Botão de Pressão + Potenciômetro** (frequência cardíaca em BPM, com modo manual por interrupção e modo automático com variabilidade fisiológica) e **MPU6050 I2C** (acelerômetro 3 eixos a 20 Hz para nível de atividade, detecção de queda $> 2{,}5\,g$ e imobilidade prolongada).
  * **Conectividade e Atuadores:** chave deslizante `swWifi` controlando a variável booleana `wifiSimulado` (simulando quedas de rede), chave `swModo` (`AUTO`/`MANUAL`), 3 LEDs (`ONLINE`, `OFFLINE`, `ALERTA`) e buzzer de alarme local.
  * **Resiliência Offline Alinhada ao Negócio:** capacidade dimensionada para **6.600 amostras** (~8h20 de autonomia offline em produção a 1 leitura/5 s), dividida em **duas filas independentes**: **Fila Crítica Prioritária (`600` amostras)** e **Fila Normal (`6.000` amostras)**, impedindo que leituras normais sobrescrevam alertas médicos.
  * **Duplo Backend (`SPIFFS` + `RAM`):** gravação em arquivos CSV segmentados (`/n_*.csv` e `/c_*.csv`) na Flash **SPIFFS** em chips reais, com *fallback* automático para buffer circular em **RAM** no simulador Wokwi. Ao reconectar, sincroniza primeiro os alertas críticos em lotes não-bloqueantes (`Serial.println("[SYNC->CLOUD] ...")` + publicação MQTT em `/backlog`) e apaga o arquivo/registro local após confirmação.
* **Relatório Técnico Parte 1:** [`Fase3/relatorios/Relatorio_Parte1_Edge_Computing.md`](Fase3/relatorios/Relatorio_Parte1_Edge_Computing.md)

![Simulação de Resiliência Offline no Edge](Fase3/assets/simulacao_resiliencia_edge.png)

### 6.2. Parte 2 – Transmissão para Nuvem e Visualização (Fog/Cloud Computing)
* **Arquitetura MQTT (`broker.hivemq.com:1883` / `HiveMQ Cloud TLS 8883`):**
  * Tópicos estruturados em `cardioia/rm566599/wear01/`: `/telemetria` (QoS 0), `/backlog` (QoS 0), `/alerta` (QoS 1), `/status` (QoS 1 + *Retained* + *Last Will and Testament*) e `/cmd` (QoS 1, comandos remotos `silenciar` e `status`).
* **Dashboard Interativo no Node-RED (`Fase3/node-red/cardioia_dashboard_flow.json`):**
  * Camada **Fog** que valida os pacotes e reavalia os limites clínicos ($\text{FC} > 120$ ou $< 50\text{ bpm}$, $\text{Temp} > 38{,}0$ ou $< 35{,}0\,^\circ\text{C}$, queda e imobilidade);
  * **Gráficos em tempo real (`ui_chart`)** de Frequência Cardíaca e Temperatura Corporal com linhas tracejadas dos limites clínicos;
  * **Medidores (`ui_gauge`)** de Temperatura (°C), Umidade/Sudorese (%) e Movimento ($g$);
  * **Indicador visual de alerta (`ui_template` + `ui_toast`)** com LED virtual animado (verde/amarelo/vermelho pulsante), descrição dos riscos ativos, *watchdog* de fluxo de dados, painel de resiliência do ESP32 e tabela histórica de eventos e sincronizações.
* **Relatório Técnico Parte 2:** [`Fase3/relatorios/Relatorio_Parte2_MQTT_e_Dashboard.md`](Fase3/relatorios/Relatorio_Parte2_MQTT_e_Dashboard.md)

![Dashboard Node-RED CardioIA](Fase3/assets/dashboard_nodered_preview.png)

### 6.3. Ir Além 1 – Comunicação Automatizada com REST, Risco Clínico e E-mail (RPA)
* **Servidor e Cliente REST (`Fase3/ir_alem_1/api_server.py` e `cliente_rest.py`):** API em **Flask + SQLite** autenticada via `X-API-Key` para ingestão individual/em lote (`POST /api/v1/leituras`), consulta incremental (`GET /api/v1/leituras`), consolidação por paciente (`/ultima`, `/resumo`) e auditoria de alertas (`/alertas`).
* **Motor de Risco Clínico (`Fase3/ir_alem_1/risco.py`):** avalia regras instantâneas (`TAQUICARDIA`, `BRADICARDIA`, `SEM_PULSO`, `FEBRE`, `HIPOTERMIA`, `SUSPEITA_SEPSE` por critérios SIRS, `QUEDA`) e regras de janela deslizante (`TAQUICARDIA_SUSTENTADA`, `AUSENCIA_MOVIMENTO` e `IMOBILIDADE_COM_FC_BAIXA` para suspeita de síncope).
* **Automação RPA de E-mail (`Fase3/ir_alem_1/monitor_rpa.py` e `notificador_email.py`):** consome a API continuamente, aplica *cooldown* anti-spam por código de risco e dispara e-mails **MIME Multipart (HTML + texto)** via SMTP/STARTTLS ou gravação auditável `.eml` em `Fase3/ir_alem_1/outbox/`.
* **Relatório Técnico Ir Além 1:** [`Fase3/relatorios/Relatorio_Ir_Alem_1_REST_e_RPA.md`](Fase3/relatorios/Relatorio_Ir_Alem_1_REST_e_RPA.md)

---

## 🎥 Vídeos de Demonstração (YouTube - Não Listados)

| Fase / Entrega | Link do Vídeo | Descrição |
| :--- | :--- | :--- |
| **Fase 2: Diagnóstico Automatizado & Modelos** | [Link no YouTube (Vídeo Não Listado)](https://youtu.be/d6C0rwUkQXQ) | Apresentação em até 4 min dos scripts de extração, treino do modelo de triagem, notebook e discussão de governança. |
| **Ir Além 1: Portal Web CardioIA (React)** | [Link no YouTube (Vídeo Não Listado)](https://www.youtube.com/watch?v=SEU_LINK_AQUI) | Demonstração do portal: login, proteção de rotas, dashboard, triagem e agendamento com useReducer. |

---

## 📁 7. Estrutura de Pastas Atualizada

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
│   ├── cardioia-portal/                # Ir Além 1 (Fase 2): Portal Web (React + Vite)
│   ├── data/
│   │   ├── frases_sintomas.txt         # 10 relatos clínicos
│   │   ├── mapa_conhecimento.csv       # Ontologia clínica
│   │   └── triagem_risco.csv           # 32 frases rotuladas (alto/baixo risco)
│   ├── notebooks/
│   │   ├── classificador_risco.ipynb   # Notebook unificado (Partes 1 e 2)
│   │   └── mlp_ecg_diagnostico.ipynb   # Ir Além 2 (MLP em Keras para ECG)
│   └── src/
│       ├── extracao_diagnostico.py     # Script de extração ontológica
│       └── classificador_risco.py      # Script de treino e inferência TF-IDF
├── Fase3/                              # Fase 3: Monitoramento Contínuo - IoT na Saúde
│   ├── assets/                         # Figuras e evidências visuais (Edge e Dashboard)
│   ├── esp32_wearable/                 # Parte 1: Firmware ESP32 + Circuito Wokwi
│   │   ├── src/main.cpp                # Código C++ comentado (SPIFFS/RAM + MQTT)
│   │   ├── sketch.ino                  # Cópia .ino para Wokwi Web / Arduino IDE
│   │   ├── diagram.json                # Circuito Wokwi (ESP32, DHT22, MPU6050, botão, pot, LEDs)
│   │   ├── libraries.txt               # Bibliotecas do Wokwi Web
│   │   ├── platformio.ini              # Configuração de build PlatformIO
│   │   └── wokwi.toml                  # Integração VS Code Wokwi Simulator
│   ├── node-red/                       # Parte 2: Fog Computing & Visualização
│   │   ├── cardioia_dashboard_flow.json # Export completo do fluxo Node-RED (34 nós)
│   │   └── simulador_mqtt.py           # Publicador MQTT para testar o dashboard sem Wokwi
│   ├── ir_alem_1/                      # Ir Além 1: API REST, Risco Clínico e E-mail (RPA)
│   │   ├── api_server.py               # Servidor REST (Flask + SQLite)
│   │   ├── cliente_rest.py             # Cliente HTTP REST (requests)
│   │   ├── risco.py                    # Motor de risco (regras instantâneas e janela)
│   │   ├── notificador_email.py        # Disparo de e-mail MIME/SMTP ou outbox/*.eml
│   │   ├── monitor_rpa.py              # Robô RPA de polling e disparo com cooldown
│   │   ├── simulador_wearable.py       # Simulador de cenários + ponte MQTT -> REST
│   │   ├── demo_completa.py            # Execução e teste ponta a ponta automatizado
│   │   └── outbox/                     # E-mails .eml gerados automaticamente
│   └── relatorios/                     # Relatórios técnicos detalhados da Fase 3
│       ├── Relatorio_Parte1_Edge_Computing.md
│       ├── Relatorio_Parte2_MQTT_e_Dashboard.md
│       └── Relatorio_Ir_Alem_1_REST_e_RPA.md
├── requirements.txt
├── .gitignore
└── README.md
```

---

## ⚙️ Como Executar os Módulos da Fase 3

### 1. Parte 1 – Simulação do Wearable ESP32 no Wokwi
* **Link direto no Wokwi Web:** [**https://wokwi.com/projects/479801389695851521**](https://wokwi.com/projects/479801389695851521)
* **No VS Code (extensão Wokwi):** abra a pasta `Fase3/esp32_wearable/`, pressione `F1` $\rightarrow$ **`Wokwi: Start Simulator`**.
* **Controles durante a simulação:**
  * Chave esquerda (`swWifi`): desligue para simular queda de Wi-Fi (modo **OFFLINE**, LED amarelo acende e amostras vão para as filas locais) e religue para ver a sincronização em lote no Monitor Serial (`[SYNC->CLOUD]`) e via MQTT;
  * Chave direita (`swModo`): alterna entre pulso automático (controlado pelo potenciômetro de 30 a 200 bpm) e manual (botão vermelho / tecla `P`);
  * Clique no **DHT22** para elevar a temperatura acima de `38.0 °C` ou no **MPU6050** para simular queda/imobilidade.

### 2. Parte 2 – Dashboard no Node-RED + Broker MQTT
```bash
# 1. Importe Fase3/node-red/cardioia_dashboard_flow.json no Node-RED (http://127.0.0.1:1880)
# 2. Acesse o dashboard em http://127.0.0.1:1880/ui
# 3. (Opcional) Para alimentar o dashboard sem abrir o Wokwi:
python Fase3/node-red/simulador_mqtt.py
```

### 3. Ir Além 1 – API REST, Verificação de Risco e E-mail Automatizado (RPA)
```bash
# Execução ponta a ponta em um único comando (sobe a API, envia 16 leituras, roda o RPA e gera os .eml):
python Fase3/ir_alem_1/demo_completa.py
```
Ou em terminais separados:
```bash
python Fase3/ir_alem_1/api_server.py           # Terminal 1: API REST na porta 5000
python Fase3/ir_alem_1/monitor_rpa.py          # Terminal 2: Robô RPA monitorando a API
python Fase3/ir_alem_1/simulador_wearable.py   # Terminal 3: Envia cenário clínico (ou --mqtt-bridge)
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
cd Fase2/cardioia-portal
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
* **0.3.0 - 04/11/2026**
  * Entrega da **Fase 3 (Monitoramento Contínuo – IoT na Saúde)**.
  * Protótipo de wearable em ESP32 no Wokwi com DHT22, sensor de pulso cardíaco (botão + gerador automático), acelerômetro MPU6050, triagem clínica embarcada e resiliência offline priorizada em SPIFFS/RAM (Parte 1).
  * Telemetria em tempo real via MQTT (HiveMQ) e dashboard interativo no Node-RED com validação na camada Fog, gráficos, gauges, LED virtual de alerta e controle remoto (Parte 2).
  * API REST em Python/Flask, cliente HTTP, motor de verificação de risco (instantâneo e em janela deslizante) e automação RPA de envio de e-mail em caso de alerta (Ir Além 1).
* **0.4.0 - Em breve**
  * *Fase 4: Coração em Imagens - Visão Computacional com CNNs.*
* **0.5.0 - Em breve**
  * *Fase 5: Assistente Cardiológico Virtual com RAG & NLP.*

---

## 📋 Licença

<img style="height:22px!important;margin-left:3px;vertical-align:text-bottom;" src="https://mirrors.creativecommons.org/presskit/icons/cc.svg?ref=chooser-v1"><img style="height:22px!important;margin-left:3px;vertical-align:text-bottom;" src="https://mirrors.creativecommons.org/presskit/icons/by.svg?ref=chooser-v1"><p xmlns:cc="http://creativecommons.org/ns#" xmlns:dct="http://purl.org/dc/terms/"><a property="dct:title" rel="cc:attributionURL" href="https://github.com/agodoi/template">MODELO GIT FIAP</a> por <a rel="cc:attributionURL dct:creator" property="cc:attributionName" href="https://fiap.com.br">Fiap</a> está licenciado sobre <a href="http://creativecommons.org/licenses/by/4.0/?ref=chooser-v1" target="_blank" rel="license noopener noreferrer" style="display:inline-block;">Attribution 4.0 International</a>.</p>
