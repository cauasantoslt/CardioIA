# CardioIA Vision — Aplicativo Mobile em React Native (Fase 4 · Ir Além 2)

Aplicativo móvel desenvolvido em **React Native (Expo)** integrado à API REST em **Flask** (`Fase4/backend/app.py`) para classificação de exames de ECG com os modelos treinados na Fase 4 (**ResNet18 Transfer Learning** e **CardioCNN do zero**).

## Funcionalidades

- **Identidade Hospitalar Clean & Modo Escuro UTI:** tema claro clínico por padrão com alternância instantânea (`🌙 UTI` / `☀ Claro`) no cabeçalho.
- **Upload de Imagem + Filtro Color-Invariant ao Vivo:** seleção pela **Galeria** ou captura pela **Câmera** (`expo-image-picker`) com switch para visualizar a remoção de viés cromático antes mesmo de classificar.
- **Painel Interativo de Grad-CAM (`InteractiveGradCamViewer.js`):** alternância entre `Grad-CAM`, `Color-Invariant` e `Original RGB`, slider tátil de opacidade (`0%–100%`), zoom `100%–300%` com rolagem 2D, modal em tela cheia e selo da cor original neutralizada.
- **Exibição Clara das Categorias AAMI:** classe detectada (`F`, `M`, `N`, `Q`, `S`, `V`), nível de risco, confiança (%), indicador do protocolo de Fairness ($\tau = 0{,}30$), barras de probabilidade das 6 classes e recomendação clínica simulada.
- **Amostras Reais & Histórico SQLite:** acesso direto às amostras de teste (`/api/v1/samples`) e histórico persistido (`/api/v1/history`).

## Como Executar

### 1. Subir o Backend Flask (Terminal 1)
Na raiz do repositório `CardioIA/`:
```bash
python Fase4/backend/app.py
```
O servidor ficará disponível em `http://127.0.0.1:5000` (e na rede local em `0.0.0.0:5000`).

### 2. Executar o App React Native (Terminal 2)
```bash
cd Fase4/mobile
npm install
npm start
```
- **Celular físico (Expo Go):** escaneie o QR Code e, no botão `⚙` no canto superior direito do app, informe `http://<IP_LOCAL_DO_PC>:5000` (ex.: `http://192.168.0.15:5000`).
- **Emulador Android:** pressione `a` (usa `http://10.0.2.2:5000` automaticamente).
- **Simulador iOS / Navegador Web:** pressione `i` ou `w` (usa `http://localhost:5000` automaticamente).
