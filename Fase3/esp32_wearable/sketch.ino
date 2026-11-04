/*
 * ============================================================================
 *  CardioIA - Fase 3: Monitoramento Contínuo (IoT na Saúde)
 *  Firmware do wearable cardíaco "CardioIA Wear" - ESP32 (Wokwi / chip real)
 * ============================================================================
 *
 *  Fluxo de dados implementado:
 *      captura -> processamento local (Edge) -> armazenamento offline
 *      -> transmissão MQTT (Fog/Cloud) -> visualização (Node-RED) -> alerta
 *
 *  Sensores (mínimo exigido: 2 sensores distintos - usamos 3 + 1 entrada):
 *    1. DHT22 ............ temperatura corporal (°C) + umidade/sudorese (%)  [obrigatório]
 *    2. Botão de pressão . pulso cardíaco: cada toque = 1 batimento -> BPM
 *       (+ potenciômetro: gerador automático de batimentos para facilitar a demo)
 *    3. MPU6050 .......... acelerômetro: nível de movimento, queda e imobilidade
 *
 *  Atuadores / interface local:
 *    - LED verde ...... online (fixo) / sincronizando backlog (piscando)
 *    - LED amarelo .... offline: armazenando leituras localmente (Edge)
 *    - LED vermelho ... ATENÇÃO (fixo) / CRÍTICO (piscando + buzzer)
 *    - Chave "Wi-Fi" .. simula a conectividade (variável booleana wifiSimulado)
 *    - Chave "Modo" ... AUTO (potenciômetro gera o pulso) / MANUAL (botão)
 *
 *  Resiliência offline (Edge Computing):
 *    - Backend preferencial: SPIFFS (arquivos CSV segmentados, persistente em
 *      chip real). Se o SPIFFS não montar, usa buffer circular em RAM.
 *    - Duas filas com prioridade clínica: CRÍTICA (alertas) e NORMAL.
 *    - Capacidade: 6.000 amostras normais + 600 críticas (~8h20 offline a
 *      1 amostra/5 s em produção). Ao encher, descarta-se a amostra NORMAL mais
 *      antiga (FIFO); alertas ficam em fila separada e nunca são expulsos por
 *      leituras normais.
 *    - Ao reconectar: sincroniza primeiro os alertas, depois o restante, em
 *      lotes não-bloqueantes, imprimindo cada registro via Serial.println
 *      (o "envio para a nuvem" pedido no enunciado) e publicando via MQTT.
 *      Cada registro só é apagado do armazenamento local após envio OK.
 *
 *  Autor: Cauã Santos (RM 566599) - FIAP Inteligência Artificial
 * ============================================================================
 */

#include <Arduino.h>
#include <WiFi.h>
#include <WiFiClientSecure.h>
#include <PubSubClient.h>
#include <Wire.h>
#include <DHT.h>
#include <SPIFFS.h>
#include <time.h>

// ============================================================================
// 1. CONFIGURAÇÕES GERAIS
// ============================================================================

// ---- Identificação (pseudonimizada - LGPD: nenhum dado pessoal trafega) ----
#define DEVICE_ID   "wear01"
#define PATIENT_ID  "PAC-0001"          // código do paciente, não o nome

// ---- Wi-Fi (no Wokwi a rede "Wokwi-GUEST" dá acesso à internet) ----
const char* WIFI_SSID = "Wokwi-GUEST";
const char* WIFI_PASS = "";

// ---- Broker MQTT ----
// MQTT_USE_TLS = 0 -> broker público HiveMQ (porta 1883), funciona sem cadastro.
// MQTT_USE_TLS = 1 -> HiveMQ Cloud (cluster privado, TLS na porta 8883 + login).
#define MQTT_USE_TLS 0

#if MQTT_USE_TLS
const char*    MQTT_HOST = "SEU-CLUSTER.s1.eu.hivemq.cloud";
const uint16_t MQTT_PORT = 8883;
const char*    MQTT_USER = "SEU_USUARIO";
const char*    MQTT_PASS = "SUA_SENHA";
#else
const char*    MQTT_HOST = "broker.hivemq.com";
const uint16_t MQTT_PORT = 1883;
const char*    MQTT_USER = nullptr;
const char*    MQTT_PASS = nullptr;
#endif

// ---- Tópicos MQTT (hierarquia: projeto / grupo / dispositivo / canal) ----
#define TOPIC_BASE "cardioia/rm566599/" DEVICE_ID
const char* T_TELEMETRIA = TOPIC_BASE "/telemetria";  // leituras ao vivo (QoS 0)
const char* T_BACKLOG    = TOPIC_BASE "/backlog";     // leituras sincronizadas do buffer
const char* T_ALERTA     = TOPIC_BASE "/alerta";      // eventos clínicos (início/fim)
const char* T_STATUS     = TOPIC_BASE "/status";      // estado do device (retained + LWT)
const char* T_CMD        = TOPIC_BASE "/cmd";         // comandos vindos do dashboard

// ---- Pinagem ----
#define PIN_DHT        15   // DHT22 (dados)
#define PIN_BEAT_BTN    4   // botão de pulso (INPUT_PULLUP, ativo em LOW)
#define PIN_POT_BPM    34   // potenciômetro - BPM no modo automático (ADC1)
#define PIN_SW_WIFI    27   // chave deslizante: HIGH = Wi-Fi "conectado"
#define PIN_SW_MODE    26   // chave deslizante: HIGH = modo AUTO, LOW = MANUAL
#define PIN_LED_ONLINE 18   // LED verde
#define PIN_LED_OFFLINE 5   // LED amarelo
#define PIN_LED_ALERT  19   // LED vermelho
#define PIN_BUZZER     23   // buzzer
#define PIN_SDA        21   // I2C MPU6050
#define PIN_SCL        22
#define MPU_ADDR     0x68

// ---- Temporização ----
const uint32_t SAMPLE_INTERVAL_MS   = 2000;   // período de amostragem (demo). Produção: 5000
const uint32_t MOTION_INTERVAL_MS   = 50;     // leitura rápida do acelerômetro (detecção de queda)
const uint32_t BEAT_DEBOUNCE_MS     = 200;    // limite físico: 300 bpm
const uint32_t NO_PULSE_TIMEOUT_MS  = 6000;   // sem batimento por 6 s => SEM_PULSO
const uint32_t PULSE_GRACE_MS       = 8000;   // carência após boot / troca de modo
const uint32_t IMMOBILITY_MS        = 60000;  // sem movimento por 60 s => IMOBILIDADE (demo)
const uint32_t WIFI_RETRY_MS        = 10000;
const uint32_t MQTT_RETRY_MS        = 5000;
const uint32_t STATUS_INTERVAL_MS   = 30000;  // heartbeat do dispositivo
const uint32_t ALERT_REPEAT_MS      = 60000;  // relembra alerta persistente a cada 60 s
const uint32_t MUTE_DURATION_MS     = 60000;  // silenciar buzzer por 60 s
const uint16_t SYNC_BATCH           = 20;     // registros sincronizados por iteração do loop

// ---- Limiares clínicos definidos pelo grupo ----
const uint8_t BPM_TAQUICARDIA = 120;   // > 120 bpm em repouso
const uint8_t BPM_BRADICARDIA = 50;    // < 50 bpm
const float   TEMP_FEBRE      = 38.0;  // > 38,0 °C
const float   TEMP_HIPOTERMIA = 35.0;  // < 35,0 °C
const float   MOV_LIMIAR_G    = 0.08;  // desvio de 1 g que caracteriza "movimento"
const float   QUEDA_LIMIAR_G  = 2.5;   // pico de aceleração típico de queda

// ---- Estratégia de armazenamento offline (modelo de negócio) ----
// Paciente pós-alta usa o wearable 24h; o gateway (celular/Wi-Fi de casa) pode
// ficar indisponível por até ~8 h (noite, deslocamentos, viagens).
// Em produção: 1 amostra/5 s -> 8 h = 5.760 amostras. Dimensionamos 6.000.
#define USE_SPIFFS          1      // 1 = tenta SPIFFS (chip real); 0 = força RAM
const uint32_t CAP_NORMAL   = 6000;  // amostras normais/atenção
const uint32_t CAP_CRITICO  = 600;   // amostras com alerta crítico (fila prioritária)
const uint16_t SEG_LINHAS_N = 500;   // SPIFFS: 12 segmentos x 500 = 6.000
const uint16_t SEG_LINHAS_C = 100;   // SPIFFS:  6 segmentos x 100 =   600

// ============================================================================
// 2. MODELO DE DADOS
// ============================================================================

// Flags de risco calculadas no Edge (bitmask de 8 bits)
enum FlagRisco : uint8_t {
  F_TAQUICARDIA  = 1 << 0,
  F_BRADICARDIA  = 1 << 1,
  F_SEM_PULSO    = 1 << 2,
  F_FEBRE        = 1 << 3,
  F_HIPOTERMIA   = 1 << 4,
  F_QUEDA        = 1 << 5,
  F_IMOBILIDADE  = 1 << 6,
  F_FALHA_SENSOR = 1 << 7
};
const uint8_t MASK_CRITICO = F_TAQUICARDIA | F_BRADICARDIA | F_SEM_PULSO |
                             F_FEBRE | F_HIPOTERMIA | F_QUEDA;
const char* FLAG_NOMES[8] = {"TAQUICARDIA", "BRADICARDIA", "SEM_PULSO", "FEBRE",
                             "HIPOTERMIA", "QUEDA", "IMOBILIDADE", "FALHA_SENSOR"};

enum Severidade : uint8_t { SEV_NORMAL = 0, SEV_ATENCAO = 1, SEV_CRITICO = 2 };
const char* SEV_NOMES[3] = {"NORMAL", "ATENCAO", "CRITICO"};

// Amostra compacta: 12 bytes -> 6.600 amostras ocupam ~79 KB de RAM.
const int16_t TEMP_INVALIDA = INT16_MIN;
struct __attribute__((packed)) Amostra {
  uint32_t uptime_s;   // segundos desde o boot (convertido em epoch no envio)
  int16_t  temp_x10;   // temperatura x10 (365 = 36,5 °C) ou TEMP_INVALIDA
  uint16_t umid_x10;   // umidade x10
  uint8_t  bpm;        // frequência cardíaca (0 = sem pulso detectado)
  uint8_t  mov_cg;     // movimento médio em centi-g (0..255 = 0..2,55 g)
  uint8_t  flags;      // FlagRisco
  uint8_t  sev;        // Severidade
};

// ============================================================================
// 3. CAMADA DE ARMAZENAMENTO LOCAL (EDGE) - interface comum + 2 backends
// ============================================================================

class BufferAmostras {
 public:
  virtual ~BufferAmostras() {}
  virtual bool begin() = 0;
  virtual bool push(const Amostra& a) = 0;   // false => houve descarte por falta de espaço
  virtual bool peek(Amostra& a) = 0;         // lê a mais antiga sem remover
  virtual void pop() = 0;                    // remove a mais antiga (após envio OK)
  virtual uint32_t size() const = 0;
  virtual uint32_t capacity() const = 0;
  virtual uint32_t dropped() const = 0;
  virtual const char* backend() const = 0;
};

// ---------------------------------------------------------------------------
// 3.1 Backend RAM: buffer circular (ring buffer) que sobrescreve o mais antigo.
//     Funciona em qualquer simulador. É volátil (perde-se no reset).
// ---------------------------------------------------------------------------
class RamRingBuffer : public BufferAmostras {
 public:
  explicit RamRingBuffer(uint32_t cap) : cap_(cap) {}

  bool begin() override {
    // Alocação dinâmica com degradação: se faltar heap, reduz pela metade.
    while (cap_ >= 50) {
      buf_ = static_cast<Amostra*>(malloc(cap_ * sizeof(Amostra)));
      if (buf_) return true;
      cap_ /= 2;
    }
    return false;
  }

  bool push(const Amostra& a) override {
    if (!buf_) return false;
    bool semDescarte = true;
    if (count_ == cap_) {            // cheio: descarta a mais antiga (FIFO)
      head_ = (head_ + 1) % cap_;
      count_--;
      drop_++;
      semDescarte = false;
    }
    buf_[(head_ + count_) % cap_] = a;
    count_++;
    return semDescarte;
  }

  bool peek(Amostra& a) override {
    if (count_ == 0) return false;
    a = buf_[head_];
    return true;
  }

  void pop() override {
    if (count_ == 0) return;
    head_ = (head_ + 1) % cap_;
    count_--;
  }

  uint32_t size() const override { return count_; }
  uint32_t capacity() const override { return cap_; }
  uint32_t dropped() const override { return drop_; }
  const char* backend() const override { return "RAM"; }

 private:
  Amostra* buf_ = nullptr;
  uint32_t cap_, head_ = 0, count_ = 0, drop_ = 0;
};

// ---------------------------------------------------------------------------
// 3.2 Backend SPIFFS: fila persistente em arquivos CSV segmentados.
//     /n_000000.csv, /n_000001.csv, ... (cada um com até `segLinhas_` linhas)
//     - push: acrescenta no segmento mais novo; ao exceder `maxSegs_`,
//       apaga o segmento mais antigo inteiro (rotação de log).
//     - pop : avança o cursor de leitura; quando um segmento é totalmente
//       enviado, o ARQUIVO LOCAL É APAGADO (requisito do enunciado).
//     - begin: reconstrói a fila a partir dos arquivos existentes (resiste a
//       queda de energia/reset em chip real). Entrega "at-least-once".
// ---------------------------------------------------------------------------
class SpiffsSegmentBuffer : public BufferAmostras {
 public:
  SpiffsSegmentBuffer(const char* prefixo, uint16_t segLinhas, uint16_t maxSegs)
      : pref_(prefixo), segLinhas_(segLinhas), maxSegs_(maxSegs < 2 ? 2 : maxSegs) {}

  bool begin() override {
    // Varre o sistema de arquivos procurando segmentos deste prefixo.
    bool achou = false;
    uint32_t minS = UINT32_MAX, maxS = 0;
    File root = SPIFFS.open("/");
    if (!root) return false;
    File f = root.openNextFile();
    while (f) {
      uint32_t seg;
      if (parseNome(f.name(), seg)) {
        achou = true;
        if (seg < minS) minS = seg;
        if (seg > maxS) maxS = seg;
      }
      f = root.openNextFile();
    }
    if (achou) {
      head_ = minS;
      tail_ = maxS;
      total_ = 0;
      for (uint32_t s = head_; s <= tail_; s++) {
        uint32_t n = contarLinhas(caminho(s));
        total_ += n;
        if (s == tail_) tailLinhas_ = n;
      }
    }
    return true;
  }

  bool push(const Amostra& a) override {
    bool semDescarte = true;
    if (tailLinhas_ >= segLinhas_) {          // segmento atual cheio -> novo
      tail_++;
      tailLinhas_ = 0;
    }
    if (tail_ - head_ + 1 > maxSegs_) {        // excedeu capacidade -> rotação
      uint32_t restantes = linhasNoSeg(head_) - headConsumidas_;
      SPIFFS.remove(caminho(head_));
      total_ = (total_ >= restantes) ? total_ - restantes : 0;
      drop_ += restantes;
      head_++;
      readOffset_ = 0;
      headConsumidas_ = 0;
      semDescarte = false;
    }
    File f = SPIFFS.open(caminho(tail_), FILE_APPEND);
    if (!f) return false;
    char linha[64];
    snprintf(linha, sizeof(linha), "%lu,%d,%u,%u,%u,%u,%u\n",
             (unsigned long)a.uptime_s, a.temp_x10, a.umid_x10,
             a.bpm, a.mov_cg, a.flags, a.sev);
    f.print(linha);
    f.close();
    tailLinhas_++;
    total_++;
    return semDescarte;
  }

  bool peek(Amostra& a) override {
    while (total_ > 0) {
      File f = SPIFFS.open(caminho(head_), FILE_READ);
      if (!f) {                                 // segmento ausente: pula
        if (head_ < tail_) { avancaHead(false); continue; }
        total_ = 0;
        return false;
      }
      if (readOffset_ >= f.size()) {            // segmento esgotado
        f.close();
        if (head_ < tail_) { avancaHead(true); continue; }
        return false;
      }
      f.seek(readOffset_);
      String linha = f.readStringUntil('\n');
      f.close();
      pendLen_ = linha.length() + 1;            // +1 do '\n'
      if (parseLinha(linha, a)) return true;
      // linha corrompida (ex.: queda de energia no meio da escrita): descarta
      readOffset_ += pendLen_;
      headConsumidas_++;
      total_--;
      drop_++;
    }
    return false;
  }

  void pop() override {
    if (total_ == 0) return;
    readOffset_ += pendLen_;
    headConsumidas_++;
    total_--;
    if (headConsumidas_ >= linhasNoSeg(head_)) {
      if (head_ < tail_) {
        avancaHead(true);                       // apaga o arquivo já enviado
      } else {                                  // era o segmento corrente
        SPIFFS.remove(caminho(head_));
        tailLinhas_ = 0;
        readOffset_ = 0;
        headConsumidas_ = 0;
      }
    }
  }

  uint32_t size() const override { return total_; }
  uint32_t capacity() const override { return (uint32_t)segLinhas_ * maxSegs_; }
  uint32_t dropped() const override { return drop_; }
  const char* backend() const override { return "SPIFFS"; }

 private:
  const char* pref_;
  uint16_t segLinhas_, maxSegs_;
  uint32_t head_ = 0, tail_ = 0, total_ = 0, drop_ = 0;
  uint32_t tailLinhas_ = 0, headConsumidas_ = 0, readOffset_ = 0, pendLen_ = 0;

  String caminho(uint32_t seg) const {
    char b[24];
    snprintf(b, sizeof(b), "/%s_%06lu.csv", pref_, (unsigned long)seg);
    return String(b);
  }

  // Aceita "n_000001.csv" ou "/n_000001.csv" (varia conforme versão do core).
  bool parseNome(const char* nome, uint32_t& seg) const {
    if (nome[0] == '/') nome++;
    size_t lp = strlen(pref_);
    if (strncmp(nome, pref_, lp) != 0 || nome[lp] != '_') return false;
    unsigned long v;
    if (sscanf(nome + lp + 1, "%lu.csv", &v) != 1) return false;
    seg = (uint32_t)v;
    return true;
  }

  uint32_t linhasNoSeg(uint32_t seg) const {
    return (seg == tail_) ? tailLinhas_ : segLinhas_;
  }

  void avancaHead(bool apagar) {
    if (apagar) SPIFFS.remove(caminho(head_));
    head_++;
    readOffset_ = 0;
    headConsumidas_ = 0;
  }

  static uint32_t contarLinhas(const String& path) {
    File f = SPIFFS.open(path, FILE_READ);
    if (!f) return 0;
    uint32_t n = 0;
    while (f.available()) if (f.read() == '\n') n++;
    f.close();
    return n;
  }

  static bool parseLinha(String linha, Amostra& a) {
    linha.trim();
    unsigned long up;
    int t;
    unsigned int u, b, m, fl, sv;
    if (sscanf(linha.c_str(), "%lu,%d,%u,%u,%u,%u,%u",
               &up, &t, &u, &b, &m, &fl, &sv) != 7) return false;
    a.uptime_s = up;
    a.temp_x10 = (int16_t)t;
    a.umid_x10 = (uint16_t)u;
    a.bpm = (uint8_t)b;
    a.mov_cg = (uint8_t)m;
    a.flags = (uint8_t)fl;
    a.sev = (uint8_t)sv;
    return true;
  }
};

// ============================================================================
// 4. ESTADO GLOBAL
// ============================================================================

DHT dht(PIN_DHT, DHT22);

#if MQTT_USE_TLS
WiFiClientSecure netClient;
#else
WiFiClient netClient;
#endif
PubSubClient mqtt(netClient);

BufferAmostras* bufNormal  = nullptr;
BufferAmostras* bufCritico = nullptr;

// ---- Conectividade ----
bool wifiSimulado = true;     // <- variável booleana exigida (espelha a chave "Wi-Fi")
bool online = false;          // wifiSimulado && Wi-Fi real && broker MQTT conectados
bool wifiIniciado = false;
bool sincronizando = false;
bool timeSincronizado = false;
uint32_t ultimaTentativaWifi = 0, ultimaTentativaMqtt = 0, ultimoStatus = 0;
uint32_t sincronizadasSessao = 0, criticasSincronizadas = 0;

// ---- Pulso cardíaco (compartilhado com a ISR) ----
portMUX_TYPE beatMux = portMUX_INITIALIZER_UNLOCKED;
volatile uint32_t beatTimes[8] = {0};
volatile uint8_t  beatIdx = 0;
volatile uint32_t beatCount = 0;
volatile uint32_t lastBeatMs = 0;
bool     modoAuto = true;
uint32_t proximoBeatAuto = 0;
uint32_t carenciaPulsoAte = 0;

// ---- Movimento ----
bool     mpuOk = false;
float    movSoma = 0, movPico = 0;
uint16_t movN = 0;
uint32_t ultimoMovimentoMs = 0, ultimaLeituraMov = 0;

// ---- Amostragem / alertas ----
uint32_t ultimaAmostra = 0, seqAmostra = 0;
uint8_t  ultimasFlagsCriticas = 0;
uint32_t ultimoAlertaMs = 0;
uint8_t  sevAtual = SEV_NORMAL;
uint32_t silenciadoAte = 0;
float    ultimaTempValida = NAN;

// ============================================================================
// 5. SENSORES
// ============================================================================

// ---- 5.1 Pulso: ISR do botão (cada toque = 1 batimento) ----
void IRAM_ATTR isrBatimento() {
  uint32_t agora = millis();
  portENTER_CRITICAL_ISR(&beatMux);
  if (agora - lastBeatMs >= BEAT_DEBOUNCE_MS) {   // debounce + limite fisiológico
    beatTimes[beatIdx] = agora;
    beatIdx = (beatIdx + 1) % 8;
    beatCount++;
    lastBeatMs = agora;
  }
  portEXIT_CRITICAL_ISR(&beatMux);
}

// Mesmo registro de batimento, chamado pelo gerador automático (fora da ISR).
void registrarBatimento(uint32_t agora) {
  portENTER_CRITICAL(&beatMux);
  beatTimes[beatIdx] = agora;
  beatIdx = (beatIdx + 1) % 8;
  beatCount++;
  lastBeatMs = agora;
  portEXIT_CRITICAL(&beatMux);
}

void resetarPulso() {
  portENTER_CRITICAL(&beatMux);
  beatCount = 0;
  beatIdx = 0;
  lastBeatMs = 0;
  portEXIT_CRITICAL(&beatMux);
  carenciaPulsoAte = millis() + PULSE_GRACE_MS;
}

// BPM do potenciômetro (modo AUTO): 30..200 bpm.
uint8_t bpmAlvoPotenciometro() {
  return (uint8_t)map(analogRead(PIN_POT_BPM), 0, 4095, 30, 200);
}

// Modo AUTO: gera batimentos no ritmo do potenciômetro com pequena
// variabilidade (HRV ±3%) para tornar o sinal mais realista.
void processarPulsoAutomatico() {
  if (!modoAuto) return;
  uint32_t agora = millis();
  if ((int32_t)(agora - proximoBeatAuto) < 0) return;
  registrarBatimento(agora);
  uint32_t intervalo = 60000UL / bpmAlvoPotenciometro();
  intervalo = intervalo * (100 + random(-3, 4)) / 100;
  proximoBeatAuto = agora + intervalo;
}

// Calcula o BPM pela média dos últimos (até 7) intervalos entre batimentos.
uint8_t calcularBpm() {
  uint32_t tempos[8], cnt, ultimo;
  uint8_t idx;
  portENTER_CRITICAL(&beatMux);
  for (int i = 0; i < 8; i++) tempos[i] = beatTimes[i];
  idx = beatIdx;
  cnt = beatCount;
  ultimo = lastBeatMs;
  portEXIT_CRITICAL(&beatMux);

  uint32_t agora = millis();
  if (cnt < 2 || agora - ultimo > NO_PULSE_TIMEOUT_MS) return 0;

  uint8_t n = (cnt - 1 < 7) ? (uint8_t)(cnt - 1) : 7;
  uint32_t soma = 0;
  for (uint8_t k = 0; k < n; k++) {
    uint32_t novo  = tempos[(idx + 8 - 1 - k) % 8];
    uint32_t velho = tempos[(idx + 8 - 2 - k) % 8];
    soma += novo - velho;
  }
  uint32_t media = soma / n;
  uint32_t desdeUltimo = agora - ultimo;
  // Se o coração "desacelerou" (pausa maior que 1,5x a média), usa a pausa
  // atual -> detecção de bradicardia mais rápida.
  if (desdeUltimo > media * 3 / 2) media = desdeUltimo;
  if (media == 0) return 0;
  uint32_t bpm = 60000UL / media;
  return (uint8_t)(bpm > 255 ? 255 : bpm);
}

// ---- 5.2 MPU6050 via registradores (sem dependência de biblioteca) ----
bool iniciarMpu() {
  Wire.beginTransmission(MPU_ADDR);
  Wire.write(0x6B);   // PWR_MGMT_1
  Wire.write(0x00);   // acorda o sensor
  if (Wire.endTransmission() != 0) return false;
  Wire.beginTransmission(MPU_ADDR);
  Wire.write(0x1C);   // ACCEL_CONFIG
  Wire.write(0x08);   // fundo de escala ±4 g (necessário para ver picos de queda)
  return Wire.endTransmission() == 0;
}

bool lerAceleracaoG(float& ax, float& ay, float& az) {
  Wire.beginTransmission(MPU_ADDR);
  Wire.write(0x3B);   // ACCEL_XOUT_H
  if (Wire.endTransmission(false) != 0) return false;
  if (Wire.requestFrom((uint8_t)MPU_ADDR, (uint8_t)6) != 6) return false;
  int16_t rx = (Wire.read() << 8) | Wire.read();
  int16_t ry = (Wire.read() << 8) | Wire.read();
  int16_t rz = (Wire.read() << 8) | Wire.read();
  const float LSB_POR_G = 8192.0;  // ±4 g
  ax = rx / LSB_POR_G;
  ay = ry / LSB_POR_G;
  az = rz / LSB_POR_G;
  return true;
}

// Amostragem rápida (20 Hz) acumulando média e pico entre duas amostras.
void processarMovimento() {
  uint32_t agora = millis();
  if (!mpuOk || agora - ultimaLeituraMov < MOTION_INTERVAL_MS) return;
  ultimaLeituraMov = agora;
  float ax, ay, az;
  if (!lerAceleracaoG(ax, ay, az)) return;
  float mag = sqrtf(ax * ax + ay * ay + az * az);
  float desvio = fabsf(mag - 1.0f);         // 0 g = parado (só gravidade)
  movSoma += desvio;
  movN++;
  if (mag > movPico) movPico = mag;
  if (desvio > MOV_LIMIAR_G) ultimoMovimentoMs = agora;
}

// ============================================================================
// 6. PROCESSAMENTO NO EDGE: coleta + classificação de risco
// ============================================================================

Amostra coletarAmostra() {
  Amostra a;
  a.uptime_s = millis() / 1000;
  a.flags = 0;

  // --- DHT22 ---
  float t = dht.readTemperature();
  float u = dht.readHumidity();
  if (isnan(t) || isnan(u)) {
    a.flags |= F_FALHA_SENSOR;
    a.temp_x10 = TEMP_INVALIDA;
    a.umid_x10 = 0;
  } else {
    a.temp_x10 = (int16_t)lroundf(t * 10);
    a.umid_x10 = (uint16_t)lroundf(u * 10);
    ultimaTempValida = t;
  }

  // --- Pulso ---
  a.bpm = calcularBpm();

  // --- Movimento (média desde a última amostra) ---
  float movMedio = movN ? movSoma / movN : 0;
  float pico = movPico;
  movSoma = 0; movN = 0; movPico = 0;
  uint32_t cg = (uint32_t)lroundf(movMedio * 100);
  a.mov_cg = (uint8_t)(cg > 255 ? 255 : cg);
  if (!mpuOk) a.flags |= F_FALHA_SENSOR;

  // --- Regras clínicas (executadas localmente: funcionam mesmo offline) ---
  uint32_t agora = millis();
  bool emCarencia = (int32_t)(carenciaPulsoAte - agora) > 0;
  if (a.bpm > BPM_TAQUICARDIA) a.flags |= F_TAQUICARDIA;
  if (a.bpm > 0 && a.bpm < BPM_BRADICARDIA) a.flags |= F_BRADICARDIA;
  if (a.bpm == 0 && !emCarencia) a.flags |= F_SEM_PULSO;
  if (a.temp_x10 != TEMP_INVALIDA) {
    if (t > TEMP_FEBRE) a.flags |= F_FEBRE;
    if (t < TEMP_HIPOTERMIA) a.flags |= F_HIPOTERMIA;
  }
  if (mpuOk && pico > QUEDA_LIMIAR_G) a.flags |= F_QUEDA;
  if (mpuOk && agora - ultimoMovimentoMs > IMMOBILITY_MS) a.flags |= F_IMOBILIDADE;

  if (a.flags & MASK_CRITICO)  a.sev = SEV_CRITICO;
  else if (a.flags)            a.sev = SEV_ATENCAO;
  else                         a.sev = SEV_NORMAL;
  return a;
}

// ============================================================================
// 7. SERIALIZAÇÃO (JSON montado com snprintf - sem bibliotecas extras)
// ============================================================================

// Converte uptime da amostra em epoch UTC (se o relógio NTP já sincronizou).
uint32_t epochDaAmostra(const Amostra& a) {
  if (!timeSincronizado) return 0;
  uint32_t agoraUp = millis() / 1000;
  return (uint32_t)time(nullptr) - (agoraUp - a.uptime_s);
}

void flagsParaJson(uint8_t flags, char* out, size_t len) {
  size_t p = snprintf(out, len, "[");
  bool primeiro = true;
  for (int i = 0; i < 8 && p < len; i++) {
    if (flags & (1 << i)) {
      p += snprintf(out + p, len - p, "%s\"%s\"", primeiro ? "" : ",", FLAG_NOMES[i]);
      primeiro = false;
    }
  }
  if (p < len) snprintf(out + p, len - p, "]");
}

size_t amostraParaJson(const Amostra& a, const char* origem, char* out, size_t len) {
  char alertas[160];
  flagsParaJson(a.flags, alertas, sizeof(alertas));
  char temp[12], umid[12];
  if (a.temp_x10 == TEMP_INVALIDA) {
    strcpy(temp, "null");
    strcpy(umid, "null");
  } else {
    snprintf(temp, sizeof(temp), "%.1f", a.temp_x10 / 10.0);
    snprintf(umid, sizeof(umid), "%.1f", a.umid_x10 / 10.0);
  }
  return snprintf(out, len,
      "{\"device\":\"%s\",\"paciente\":\"%s\",\"origem\":\"%s\","
      "\"ts\":%lu,\"uptime_s\":%lu,\"bpm\":%u,\"temp\":%s,\"umid\":%s,"
      "\"mov\":%.2f,\"sev\":%u,\"nivel\":\"%s\",\"alertas\":%s,\"flags\":%u}",
      DEVICE_ID, PATIENT_ID, origem,
      (unsigned long)epochDaAmostra(a), (unsigned long)a.uptime_s,
      a.bpm, temp, umid, a.mov_cg / 100.0, a.sev, SEV_NOMES[a.sev], alertas, a.flags);
}

// ============================================================================
// 8. MQTT - publicação, status, alertas e comandos
// ============================================================================

bool publicarAmostra(const Amostra& a, const char* topico, const char* origem) {
  if (!mqtt.connected()) return false;
  char json[400];
  amostraParaJson(a, origem, json, sizeof(json));
  return mqtt.publish(topico, json);
}

void publicarStatus(const char* estado) {
  if (!mqtt.connected()) return;
  char json[320];
  snprintf(json, sizeof(json),
      "{\"device\":\"%s\",\"estado\":\"%s\",\"backend\":\"%s\","
      "\"buffer_normal\":%lu,\"buffer_critico\":%lu,\"capacidade\":%lu,"
      "\"descartadas\":%lu,\"sincronizadas\":%lu,\"modo\":\"%s\",\"rssi\":%d,\"uptime_s\":%lu}",
      DEVICE_ID, estado, bufNormal->backend(),
      (unsigned long)bufNormal->size(), (unsigned long)bufCritico->size(),
      (unsigned long)(bufNormal->capacity() + bufCritico->capacity()),
      (unsigned long)(bufNormal->dropped() + bufCritico->dropped()),
      (unsigned long)sincronizadasSessao, modoAuto ? "AUTO" : "MANUAL",
      (int)WiFi.RSSI(), (unsigned long)(millis() / 1000));
  mqtt.publish(T_STATUS, json, true);   // retained: dashboard recebe ao abrir
}

// Evento de alerta: publicado apenas quando surge um novo risco crítico,
// quando o risco persiste (lembrete a cada 60 s) ou quando normaliza.
// Evita "inundar" o broker/e-mail com um alerta a cada 2 s.
void avaliarEventoAlerta(const Amostra& a) {
  uint8_t crit = a.flags & MASK_CRITICO;
  uint32_t agora = millis();
  const char* evento = nullptr;
  if (crit & ~ultimasFlagsCriticas)                          evento = "ALERTA";
  else if (crit && agora - ultimoAlertaMs > ALERT_REPEAT_MS) evento = "ALERTA_PERSISTENTE";
  else if (!crit && ultimasFlagsCriticas)                    evento = "NORMALIZADO";
  ultimasFlagsCriticas = crit;
  if (!evento) return;
  ultimoAlertaMs = agora;

  Serial.printf("[ALERTA] %s -> flags=0x%02X\n", evento, crit);
  if (!online) return;   // offline: a amostra crítica já vai para a fila prioritária
  char dados[400], json[480];
  amostraParaJson(a, "live", dados, sizeof(dados));
  snprintf(json, sizeof(json), "{\"evento\":\"%s\",\"atrasado\":false,\"amostra\":%s}", evento, dados);
  mqtt.publish(T_ALERTA, json);
}

void onMqttMensagem(char* topico, byte* payload, unsigned int len) {
  String cmd;
  for (unsigned int i = 0; i < len; i++) cmd += (char)payload[i];
  cmd.trim();
  cmd.toLowerCase();
  Serial.printf("[CMD] Recebido do dashboard: '%s'\n", cmd.c_str());
  if (cmd == "silenciar") {
    silenciadoAte = millis() + MUTE_DURATION_MS;
    Serial.println("[CMD] Buzzer silenciado por 60 s.");
  } else if (cmd == "status") {
    publicarStatus("online");
  }
}

// ============================================================================
// 9. CONECTIVIDADE (Wi-Fi simulado por chave + Wi-Fi/MQTT reais)
// ============================================================================

String clientIdMqtt() {
  char id[40];
  snprintf(id, sizeof(id), "cardioia-%s-%04X", DEVICE_ID, (unsigned)(ESP.getEfuseMac() & 0xFFFF));
  return String(id);
}

void conectarMqtt() {
  uint32_t agora = millis();
  if (agora - ultimaTentativaMqtt < MQTT_RETRY_MS) return;
  ultimaTentativaMqtt = agora;
  Serial.printf("[MQTT] Conectando a %s:%u ...\n", MQTT_HOST, MQTT_PORT);
  char lwt[96];
  snprintf(lwt, sizeof(lwt), "{\"device\":\"%s\",\"estado\":\"offline\",\"motivo\":\"lwt\"}", DEVICE_ID);
  // Last Will: se o device cair sem avisar, o broker publica "offline".
  bool ok = mqtt.connect(clientIdMqtt().c_str(), MQTT_USER, MQTT_PASS, T_STATUS, 1, true, lwt);
  if (ok) {
    Serial.println("[MQTT] Conectado ao broker.");
    mqtt.subscribe(T_CMD);
    publicarStatus("online");
    ultimoStatus = agora;
  } else {
    Serial.printf("[MQTT] Falha (rc=%d). Nova tentativa em %lus.\n", mqtt.state(), MQTT_RETRY_MS / 1000);
  }
}

void atualizarConectividade() {
  uint32_t agora = millis();
  bool chave = digitalRead(PIN_SW_WIFI) == HIGH;

  if (chave != wifiSimulado) {
    wifiSimulado = chave;
    Serial.printf("\n[REDE] Chave Wi-Fi -> %s\n", wifiSimulado ? "CONECTADO" : "DESCONECTADO (simulação de queda)");
    if (!wifiSimulado) {
      // Queda simulada: avisa o broker (status retained) e derruba o link.
      publicarStatus("offline");
      mqtt.disconnect();
      WiFi.disconnect();
      wifiIniciado = false;
    }
  }

  if (wifiSimulado) {
    if (WiFi.status() != WL_CONNECTED) {
      if (!wifiIniciado || agora - ultimaTentativaWifi > WIFI_RETRY_MS) {
        Serial.printf("[REDE] Conectando ao Wi-Fi '%s'...\n", WIFI_SSID);
        WiFi.begin(WIFI_SSID, WIFI_PASS);
        wifiIniciado = true;
        ultimaTentativaWifi = agora;
      }
    } else {
      if (!timeSincronizado) {
        static bool ntpPedido = false;
        if (!ntpPedido) { configTime(0, 0, "pool.ntp.org", "time.google.com"); ntpPedido = true; }
        if (time(nullptr) > 1700000000) {
          timeSincronizado = true;
          Serial.println("[REDE] Relógio sincronizado via NTP.");
        }
      }
      if (!mqtt.connected()) conectarMqtt();
    }
  }

  bool estavaOnline = online;
  online = wifiSimulado && WiFi.status() == WL_CONNECTED && mqtt.connected();

  if (online && !estavaOnline) {
    uint32_t pend = bufNormal->size() + bufCritico->size();
    Serial.printf("[EDGE] Conexão restabelecida. %lu amostra(s) pendente(s) para sincronizar.\n", (unsigned long)pend);
    if (pend) { sincronizando = true; criticasSincronizadas = 0; }
  } else if (!online && estavaOnline) {
    Serial.println("[EDGE] Sem conexão -> modo OFFLINE: leituras serão armazenadas localmente.");
  }

  if (online && agora - ultimoStatus > STATUS_INTERVAL_MS) {
    publicarStatus(sincronizando ? "sincronizando" : "online");
    ultimoStatus = agora;
  }
}

// ============================================================================
// 10. RESILIÊNCIA: armazenamento offline e sincronização
// ============================================================================

void armazenarLocal(const Amostra& a) {
  BufferAmostras* fila = (a.sev == SEV_CRITICO) ? bufCritico : bufNormal;
  bool ok = fila->push(a);
  Serial.printf("         [EDGE] OFFLINE -> armazenada na fila %s (%s): %lu/%lu%s\n",
                a.sev == SEV_CRITICO ? "CRITICA" : "NORMAL", fila->backend(),
                (unsigned long)fila->size(), (unsigned long)fila->capacity(),
                ok ? "" : "  [cheia: amostra mais antiga descartada]");
}

// Envia um lote por iteração do loop (não bloqueia a coleta de sinais).
// Ordem: fila CRÍTICA primeiro (triagem), depois a NORMAL.
void sincronizarBacklog() {
  if (!online || !sincronizando) return;
  char json[400];
  uint16_t enviados = 0;
  Amostra a;
  while (enviados < SYNC_BATCH) {
    BufferAmostras* fila = bufCritico->size() ? bufCritico : bufNormal;
    if (!fila->peek(a)) break;
    amostraParaJson(a, "buffer", json, sizeof(json));
    if (!mqtt.publish(T_BACKLOG, json)) {
      Serial.println("[SYNC] Falha ao publicar; registro mantido para nova tentativa.");
      return;
    }
    // "Envio para a nuvem" via Serial (alternativa ao SPIFFS no simulador)
    Serial.print("[SYNC->CLOUD] ");
    Serial.println(json);
    fila->pop();                    // só apaga do armazenamento local após envio OK
    if (a.sev == SEV_CRITICO) criticasSincronizadas++;
    sincronizadasSessao++;
    enviados++;
    mqtt.loop();
  }

  if (bufNormal->size() == 0 && bufCritico->size() == 0) {
    sincronizando = false;
    Serial.printf("[SYNC] Concluída. Total sincronizado nesta sessão: %lu. Armazenamento local limpo.\n",
                  (unsigned long)sincronizadasSessao);
    if (criticasSincronizadas) {
      // Um único alerta retroativo resumindo os eventos ocorridos offline.
      char msg[200];
      snprintf(msg, sizeof(msg),
               "{\"evento\":\"ALERTA_RETROATIVO\",\"atrasado\":true,\"device\":\"%s\","
               "\"paciente\":\"%s\",\"amostras_criticas\":%lu}",
               DEVICE_ID, PATIENT_ID, (unsigned long)criticasSincronizadas);
      mqtt.publish(T_ALERTA, msg);
    }
    publicarStatus("online");
  }
}

// ============================================================================
// 11. ATUADORES LOCAIS (LEDs + buzzer) - alarme funciona mesmo sem rede
// ============================================================================

void atualizarIndicadores() {
  uint32_t agora = millis();
  bool pisca = (agora / 250) % 2;
  digitalWrite(PIN_LED_ONLINE, online && (!sincronizando || pisca));
  digitalWrite(PIN_LED_OFFLINE, !online);

  bool mudo = (int32_t)(silenciadoAte - agora) > 0;
  if (sevAtual == SEV_CRITICO) {
    digitalWrite(PIN_LED_ALERT, pisca);
    if (!mudo && pisca) tone(PIN_BUZZER, 2000);
    else noTone(PIN_BUZZER);
  } else {
    digitalWrite(PIN_LED_ALERT, sevAtual == SEV_ATENCAO);
    noTone(PIN_BUZZER);
  }
}

// ============================================================================
// 12. LOG NO MONITOR SERIAL + COMANDOS
// ============================================================================

void imprimirAmostra(const Amostra& a) {
  char temp[10];
  if (a.temp_x10 == TEMP_INVALIDA) strcpy(temp, " --.-");
  else snprintf(temp, sizeof(temp), "%5.1f", a.temp_x10 / 10.0);
  char alertas[160];
  flagsParaJson(a.flags, alertas, sizeof(alertas));
  Serial.printf("[#%05lu] t=%5lus | FC=%3u bpm | Temp=%sC | Umid=%5.1f%% | Mov=%.2fg | %-7s %s | %s\n",
                (unsigned long)seqAmostra, (unsigned long)a.uptime_s, a.bpm, temp,
                a.umid_x10 / 10.0, a.mov_cg / 100.0, SEV_NOMES[a.sev], alertas,
                online ? "ONLINE" : "OFFLINE");
}

void imprimirStatus() {
  Serial.println("\n------------------- STATUS CardioIA Wear -------------------");
  Serial.printf(" Wi-Fi simulado: %s | Wi-Fi real: %s | MQTT: %s\n",
                wifiSimulado ? "ON" : "OFF", WiFi.status() == WL_CONNECTED ? "OK" : "--",
                mqtt.connected() ? "OK" : "--");
  Serial.printf(" Modo pulso: %s (alvo pot.: %u bpm)\n", modoAuto ? "AUTO" : "MANUAL", bpmAlvoPotenciometro());
  Serial.printf(" Backend: %s | Fila normal: %lu/%lu | Fila critica: %lu/%lu | Descartadas: %lu\n",
                bufNormal->backend(),
                (unsigned long)bufNormal->size(), (unsigned long)bufNormal->capacity(),
                (unsigned long)bufCritico->size(), (unsigned long)bufCritico->capacity(),
                (unsigned long)(bufNormal->dropped() + bufCritico->dropped()));
  Serial.printf(" Heap livre: %lu bytes | Uptime: %lus\n", (unsigned long)ESP.getFreeHeap(), (unsigned long)(millis() / 1000));
  Serial.println("------------------------------------------------------------\n");
}

void processarComandosSerial() {
  while (Serial.available()) {
    char c = (char)Serial.read();
    if (c == 's') imprimirStatus();
    else if (c == 'm') { silenciadoAte = millis() + MUTE_DURATION_MS; Serial.println("[CMD] Buzzer silenciado por 60 s."); }
    else if (c == 'h') Serial.println("[AJUDA] s = status | m = silenciar buzzer 60 s | h = ajuda");
  }
}

// ============================================================================
// 13. SETUP E LOOP
// ============================================================================

void iniciarArmazenamento() {
#if USE_SPIFFS
  if (SPIFFS.begin(true)) {   // true = formata na primeira execução
    bufNormal  = new SpiffsSegmentBuffer("n", SEG_LINHAS_N, CAP_NORMAL / SEG_LINHAS_N);
    bufCritico = new SpiffsSegmentBuffer("c", SEG_LINHAS_C, CAP_CRITICO / SEG_LINHAS_C);
    if (bufNormal->begin() && bufCritico->begin()) {
      Serial.printf("[EDGE] SPIFFS montado (%u/%u bytes usados). Pendentes recuperados: %lu normal, %lu critico.\n",
                    (unsigned)SPIFFS.usedBytes(), (unsigned)SPIFFS.totalBytes(),
                    (unsigned long)bufNormal->size(), (unsigned long)bufCritico->size());
      return;
    }
    delete bufNormal;
    delete bufCritico;
  }
  Serial.println("[EDGE] SPIFFS indisponivel -> usando buffer circular em RAM.");
#endif
  bufNormal  = new RamRingBuffer(CAP_NORMAL);
  bufCritico = new RamRingBuffer(CAP_CRITICO);
  bufNormal->begin();
  bufCritico->begin();
  Serial.printf("[EDGE] Buffer RAM alocado: %lu + %lu amostras (%u bytes cada).\n",
                (unsigned long)bufNormal->capacity(), (unsigned long)bufCritico->capacity(),
                (unsigned)sizeof(Amostra));
}

void setup() {
  Serial.begin(115200);
  delay(200);
  Serial.println("\n==============================================================");
  Serial.println("  CardioIA Wear - Fase 3: Monitoramento Continuo (IoT/Edge)");
  Serial.println("==============================================================");

  pinMode(PIN_BEAT_BTN, INPUT_PULLUP);
  pinMode(PIN_SW_WIFI, INPUT);
  pinMode(PIN_SW_MODE, INPUT);
  pinMode(PIN_LED_ONLINE, OUTPUT);
  pinMode(PIN_LED_OFFLINE, OUTPUT);
  pinMode(PIN_LED_ALERT, OUTPUT);
  pinMode(PIN_BUZZER, OUTPUT);
  attachInterrupt(digitalPinToInterrupt(PIN_BEAT_BTN), isrBatimento, FALLING);
  randomSeed(esp_random());

  dht.begin();
  Wire.begin(PIN_SDA, PIN_SCL);
  mpuOk = iniciarMpu();
  Serial.printf("[SENSOR] DHT22 no GPIO %d | MPU6050: %s\n", PIN_DHT, mpuOk ? "OK" : "NAO ENCONTRADO");

  // Buffers alocados antes do Wi-Fi para garantir bloco contíguo de heap.
  iniciarArmazenamento();

  WiFi.mode(WIFI_STA);
#if MQTT_USE_TLS
  netClient.setInsecure();   // demo: em produção, carregar o certificado CA do broker
#endif
  mqtt.setServer(MQTT_HOST, MQTT_PORT);
  mqtt.setBufferSize(768);
  mqtt.setKeepAlive(30);
  mqtt.setSocketTimeout(3);
  mqtt.setCallback(onMqttMensagem);

  modoAuto = digitalRead(PIN_SW_MODE) == HIGH;
  wifiSimulado = !(digitalRead(PIN_SW_WIFI) == HIGH);   // força log/ação na 1ª leitura
  ultimoMovimentoMs = millis();
  resetarPulso();
  Serial.printf("[PULSO] Modo %s. Comandos seriais: s=status, m=silenciar, h=ajuda\n\n",
                modoAuto ? "AUTO (potenciometro)" : "MANUAL (botao)");
}

void loop() {
  uint32_t agora = millis();

  processarComandosSerial();
  atualizarConectividade();

  // Troca de modo do pulso (AUTO <-> MANUAL)
  bool modo = digitalRead(PIN_SW_MODE) == HIGH;
  if (modo != modoAuto) {
    modoAuto = modo;
    resetarPulso();
    Serial.printf("[PULSO] Modo alterado para %s\n", modoAuto ? "AUTO (potenciometro)" : "MANUAL (botao)");
  }

  processarPulsoAutomatico();
  processarMovimento();

  // ---- Ciclo de amostragem ----
  if (agora - ultimaAmostra >= SAMPLE_INTERVAL_MS) {
    ultimaAmostra = agora;
    seqAmostra++;
    Amostra a = coletarAmostra();
    sevAtual = a.sev;
    imprimirAmostra(a);
    avaliarEventoAlerta(a);

    // Online: publica ao vivo. Offline (ou falha no envio): guarda no Edge.
    if (!(online && publicarAmostra(a, T_TELEMETRIA, "live"))) {
      armazenarLocal(a);
      if (online && !sincronizando) sincronizando = true;
    }
  }

  sincronizarBacklog();
  atualizarIndicadores();
  mqtt.loop();
  delay(5);
}

