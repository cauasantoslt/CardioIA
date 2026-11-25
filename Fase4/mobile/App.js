import React, { useCallback, useEffect, useState } from 'react';
import {
  ActivityIndicator,
  Alert,
  Image,
  SafeAreaView,
  ScrollView,
  StyleSheet,
  Switch,
  Text,
  TextInput,
  TouchableOpacity,
  View,
} from 'react-native';
import { StatusBar } from 'expo-status-bar';
import * as ImagePicker from 'expo-image-picker';

import { getDefaultApiUrl, MODEL_OPTIONS } from './src/config';
import { darkTheme, lightTheme } from './src/theme';
import {
  checkHealth,
  fetchHistory,
  fetchSamples,
  predictFromImageAsset,
  predictFromSample,
  previewColorInvariantFilter,
} from './src/services/api';
import RiskBadge from './src/components/RiskBadge';
import ProbabilityBar from './src/components/ProbabilityBar';
import InteractiveGradCamViewer from './src/components/InteractiveGradCamViewer';

export default function App() {
  const [isDark, setIsDark] = useState(false); // Padrão: Hospitalar Clean (Claro Clínico)
  const theme = isDark ? darkTheme : lightTheme;

  const [apiUrl, setApiUrl] = useState(getDefaultApiUrl());
  const [showConfig, setShowConfig] = useState(false);
  const [apiStatus, setApiStatus] = useState({ online: false, info: null, error: null });

  const [activeTab, setActiveTab] = useState('analyze'); // 'analyze' | 'samples' | 'history'
  const [selectedModel, setSelectedModel] = useState('resnet18_transfer');
  const [patientId, setPatientId] = useState('PAC-0001');
  const [selectedAsset, setSelectedAsset] = useState(null);

  // Filtro Color-Invariant ao vivo no Preview (antes mesmo da inferência)
  const [liveFilterOn, setLiveFilterOn] = useState(false);
  const [liveFilterPreview, setLiveFilterPreview] = useState(null);
  const [liveFilterLoading, setLiveFilterLoading] = useState(false);

  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [samples, setSamples] = useState([]);
  const [history, setHistory] = useState([]);

  const refreshConnection = useCallback(async (urlToTest) => {
    const target = urlToTest || apiUrl;
    try {
      const h = await checkHealth(target);
      setApiStatus({ online: true, info: h, error: null });
      const [sRes, hRes] = await Promise.all([
        fetchSamples(target),
        fetchHistory(target, 15),
      ]);
      setSamples(sRes.samples || []);
      setHistory(hRes.history || []);
    } catch (err) {
      setApiStatus({
        online: false,
        info: null,
        error: err.message || 'Falha ao conectar ao backend Flask.',
      });
    }
  }, [apiUrl]);

  useEffect(() => {
    refreshConnection();
  }, [refreshConnection]);

  async function applyLiveFilterIfNeeded(asset, shouldEnable) {
    if (!shouldEnable || !asset || !apiStatus.online) return;
    if (liveFilterPreview && liveFilterPreview.uri === asset.uri) return;
    setLiveFilterLoading(true);
    try {
      const resp = await previewColorInvariantFilter(apiUrl, asset);
      setLiveFilterPreview({ uri: asset.uri, data: resp });
    } catch {
      // Silencioso caso offline
    } finally {
      setLiveFilterLoading(false);
    }
  }

  async function toggleLiveFilter(val) {
    setLiveFilterOn(val);
    if (val && selectedAsset) {
      await applyLiveFilterIfNeeded(selectedAsset, true);
    }
  }

  async function pickImageFromGallery() {
    const perm = await ImagePicker.requestMediaLibraryPermissionsAsync();
    if (!perm.granted) {
      Alert.alert('Permissão necessária', 'Libere o acesso à galeria para selecionar uma imagem de ECG.');
      return;
    }
    const pickerRes = await ImagePicker.launchImageLibraryAsync({
      mediaTypes: ['images'],
      allowsEditing: false,
      quality: 1,
      base64: true,
    });
    if (!pickerRes.canceled && pickerRes.assets && pickerRes.assets.length > 0) {
      const asset = pickerRes.assets[0];
      setSelectedAsset(asset);
      setLiveFilterPreview(null);
      setResult(null);
      if (liveFilterOn) {
        await applyLiveFilterIfNeeded(asset, true);
      }
    }
  }

  async function captureImageFromCamera() {
    const perm = await ImagePicker.requestCameraPermissionsAsync();
    if (!perm.granted) {
      Alert.alert('Permissão necessária', 'Libere o acesso à câmera para fotografar o exame de ECG.');
      return;
    }
    const camRes = await ImagePicker.launchCameraAsync({
      allowsEditing: false,
      quality: 0.9,
      base64: true,
    });
    if (!camRes.canceled && camRes.assets && camRes.assets.length > 0) {
      const asset = camRes.assets[0];
      setSelectedAsset(asset);
      setLiveFilterPreview(null);
      setResult(null);
      if (liveFilterOn) {
        await applyLiveFilterIfNeeded(asset, true);
      }
    }
  }

  async function handleClassifyUploadedImage() {
    if (!selectedAsset) {
      Alert.alert('Nenhuma imagem', 'Selecione uma imagem de ECG da galeria ou câmera primeiro.');
      return;
    }
    setLoading(true);
    try {
      const pred = await predictFromImageAsset(apiUrl, selectedAsset, selectedModel, patientId);
      setResult(pred);
      const hRes = await fetchHistory(apiUrl, 15);
      setHistory(hRes.history || []);
    } catch (err) {
      Alert.alert('Erro na classificação', err.message || 'Não foi possível classificar a imagem.');
    } finally {
      setLoading(false);
    }
  }

  async function handleClassifySample(sample) {
    setActiveTab('analyze');
    setSelectedAsset({ uri: sample.thumbnail_b64, fileName: sample.filename });
    setLiveFilterPreview(null);
    setLiveFilterOn(false);
    setLoading(true);
    try {
      const pred = await predictFromSample(apiUrl, sample.sample_id, selectedModel, patientId);
      setResult(pred);
      const hRes = await fetchHistory(apiUrl, 15);
      setHistory(hRes.history || []);
    } catch (err) {
      Alert.alert('Erro na amostra', err.message || 'Falha ao classificar amostra.');
    } finally {
      setLoading(false);
    }
  }

  const previewUriToShow =
    liveFilterOn && liveFilterPreview?.data?.preprocessed_image_b64
      ? liveFilterPreview.data.preprocessed_image_b64
      : selectedAsset?.uri;

  const resnetSummary = apiStatus.info?.models_summary?.resnet18_transfer;

  return (
    <SafeAreaView style={[styles.safe, { backgroundColor: theme.bg }]}>
      <StatusBar style={theme.statusBarStyle} />

      {/* Header Hospitalar Clean / UTI */}
      <View style={[styles.header, { backgroundColor: theme.surface, borderBottomColor: theme.border }]}>
        <View style={styles.headerLeft}>
          <View style={[styles.logoBox, { backgroundColor: theme.primary }]}>
            <Text style={styles.logoPulse}>♥</Text>
          </View>
          <View>
            <Text style={[styles.title, { color: theme.text }]}>CardioIA Vision</Text>
            <Text style={[styles.subtitle, { color: theme.textMuted }]}>
              CNN &amp; ResNet18 · Grad-CAM
            </Text>
          </View>
        </View>

        <View style={styles.headerRight}>
          <TouchableOpacity
            style={[styles.pillBtn, { backgroundColor: theme.surfaceSoft, borderColor: theme.border }]}
            onPress={() => setIsDark(!isDark)}
          >
            <Text style={[styles.pillBtnText, { color: theme.textSecondary }]}>
              {isDark ? '☀ Claro' : '🌙 UTI'}
            </Text>
          </TouchableOpacity>
          <TouchableOpacity
            style={[
              styles.pillBtn,
              {
                backgroundColor: apiStatus.online ? theme.successSoft : theme.dangerSoft,
                borderColor: apiStatus.online ? theme.success : theme.danger,
              },
            ]}
            onPress={() => setShowConfig(!showConfig)}
          >
            <Text
              style={[
                styles.pillBtnText,
                { color: apiStatus.online ? theme.success : theme.danger },
              ]}
            >
              {apiStatus.online ? '● Online' : '● Offline'} ⚙
            </Text>
          </TouchableOpacity>
        </View>
      </View>

      {/* Configuração rápida da URL do Backend Flask */}
      {showConfig && (
        <View style={[styles.configBox, { backgroundColor: theme.surfaceSoft, borderBottomColor: theme.border }]}>
          <Text style={[styles.configLabel, { color: theme.textSecondary }]}>
            Endpoint do Backend Flask (ex.: http://192.168.0.10:5000)
          </Text>
          <View style={styles.configRow}>
            <TextInput
              style={[
                styles.configInput,
                { backgroundColor: theme.surface, color: theme.text, borderColor: theme.border },
              ]}
              value={apiUrl}
              onChangeText={setApiUrl}
              autoCapitalize="none"
              autoCorrect={false}
              placeholder="http://localhost:5000"
              placeholderTextColor={theme.textMuted}
            />
            <TouchableOpacity
              style={[styles.configBtn, { backgroundColor: theme.primary }]}
              onPress={() => refreshConnection(apiUrl)}
            >
              <Text style={styles.configBtnText}>Testar</Text>
            </TouchableOpacity>
          </View>
          {apiStatus.error ? <Text style={[styles.errorText, { color: theme.danger }]}>{apiStatus.error}</Text> : null}
        </View>
      )}

      {/* Navegação em Abas */}
      <View style={[styles.tabs, { backgroundColor: theme.surface, borderBottomColor: theme.border }]}>
        {[
          { id: 'analyze', label: 'Analisar ECG' },
          { id: 'samples', label: `Amostras (${samples.length})` },
          { id: 'history', label: `Histórico (${history.length})` },
        ].map((t) => {
          const active = activeTab === t.id;
          return (
            <TouchableOpacity
              key={t.id}
              style={[
                styles.tab,
                {
                  backgroundColor: active ? theme.primary : theme.surfaceSoft,
                  borderColor: active ? theme.primary : theme.border,
                },
              ]}
              onPress={() => setActiveTab(t.id)}
            >
              <Text style={[styles.tabText, { color: active ? '#ffffff' : theme.textSecondary }]}>
                {t.label}
              </Text>
            </TouchableOpacity>
          );
        })}
      </View>

      <ScrollView contentContainerStyle={styles.content}>
        {/* Faixa de KPIs Compacta */}
        {resnetSummary && (
          <View style={styles.kpiRow}>
            <View style={[styles.kpiMini, { backgroundColor: theme.surface, borderColor: theme.border }]}>
              <Text style={[styles.kpiLbl, { color: theme.textMuted }]}>RESNET18</Text>
              <Text style={[styles.kpiVal, { color: theme.primary }]}>
                {(resnetSummary.accuracy * 100).toFixed(1)}% Acc
              </Text>
            </View>
            <View style={[styles.kpiMini, { backgroundColor: theme.surface, borderColor: theme.border }]}>
              <Text style={[styles.kpiLbl, { color: theme.textMuted }]}>COLOR-INVARIANT</Text>
              <Text style={[styles.kpiVal, { color: theme.teal }]}>0,0 pp Viés</Text>
            </View>
            <View style={[styles.kpiMini, { backgroundColor: theme.surface, borderColor: theme.border }]}>
              <Text style={[styles.kpiLbl, { color: theme.textMuted }]}>FAIRNESS</Text>
              <Text style={[styles.kpiVal, { color: theme.text }]}>τ = 0,30</Text>
            </View>
          </View>
        )}

        {/* ABA 1: UPLOAD, FILTRO AO VIVO E RESULTADO COM GRAD-CAM INTERATIVO */}
        {activeTab === 'analyze' && (
          <>
            <View style={[styles.card, { backgroundColor: theme.surface, borderColor: theme.border }]}>
              <Text style={[styles.sectionTitle, { color: theme.text }]}>1. Aquisição de Exame de ECG</Text>

              <View style={styles.actionRow}>
                <TouchableOpacity
                  style={[styles.pickBtn, { backgroundColor: theme.primary }]}
                  onPress={pickImageFromGallery}
                >
                  <Text style={styles.pickBtnText}>📁 Galeria</Text>
                </TouchableOpacity>
                <TouchableOpacity
                  style={[styles.pickBtn, { backgroundColor: theme.teal }]}
                  onPress={captureImageFromCamera}
                >
                  <Text style={styles.pickBtnText}>📷 Câmera</Text>
                </TouchableOpacity>
              </View>

              {selectedAsset ? (
                <View style={[styles.previewCard, { backgroundColor: theme.surfaceSoft, borderColor: theme.border }]}>
                  <View style={styles.liveToggleRow}>
                    <Text style={[styles.liveToggleLabel, { color: theme.textSecondary }]}>
                      🛡 Filtro Color-Invariant ao vivo
                    </Text>
                    <Switch
                      value={liveFilterOn}
                      onValueChange={toggleLiveFilter}
                      trackColor={{ false: theme.borderStrong, true: theme.teal }}
                      thumbColor="#ffffff"
                    />
                  </View>
                  <View style={styles.previewImgBox}>
                    {liveFilterLoading ? (
                      <ActivityIndicator color={theme.primary} />
                    ) : (
                      <Image source={{ uri: previewUriToShow }} style={styles.previewImg} resizeMode="contain" />
                    )}
                  </View>
                  <Text style={[styles.previewCaption, { color: theme.textMuted }]}>
                    {selectedAsset.fileName || 'Exame pronto para classificação'}
                    {liveFilterOn && liveFilterPreview?.data?.chromatic_audit
                      ? ` · Cor ${liveFilterPreview.data.chromatic_audit.hex_color} neutralizada`
                      : ''}
                  </Text>
                </View>
              ) : (
                <View style={[styles.placeholderBox, { backgroundColor: theme.surfaceSoft, borderColor: theme.borderStrong }]}>
                  <Text style={[styles.placeholderText, { color: theme.textMuted }]}>
                    Selecione um traçado de ECG da galeria/câmera ou escolha uma amostra real na aba "Amostras".
                  </Text>
                </View>
              )}

              {/* Seletor de Modelo CNN */}
              <Text style={[styles.fieldLabel, { color: theme.textSecondary }]}>Arquitetura de Deep Learning</Text>
              <View style={[styles.modelRow, { backgroundColor: theme.surfaceSoft, borderColor: theme.border }]}>
                {MODEL_OPTIONS.map((m) => {
                  const active = selectedModel === m.key;
                  return (
                    <TouchableOpacity
                      key={m.key}
                      style={[
                        styles.modelChip,
                        active && { backgroundColor: theme.surface, borderColor: theme.primary, borderWidth: 1 },
                      ]}
                      onPress={() => setSelectedModel(m.key)}
                    >
                      <Text
                        style={[
                          styles.modelChipText,
                          { color: active ? theme.primary : theme.textMuted },
                        ]}
                      >
                        {m.label}
                      </Text>
                    </TouchableOpacity>
                  );
                })}
              </View>

              {/* ID do Paciente */}
              <Text style={[styles.fieldLabel, { color: theme.textSecondary }]}>ID Simulado do Paciente</Text>
              <TextInput
                style={[
                  styles.input,
                  { backgroundColor: theme.surfaceSoft, color: theme.text, borderColor: theme.border },
                ]}
                value={patientId}
                onChangeText={setPatientId}
                placeholder="PAC-0001"
                placeholderTextColor={theme.textMuted}
              />

              <TouchableOpacity
                style={[
                  styles.primaryBtn,
                  { backgroundColor: theme.primary },
                  (!selectedAsset || loading) && styles.btnDisabled,
                ]}
                disabled={!selectedAsset || loading}
                onPress={handleClassifyUploadedImage}
              >
                {loading ? (
                  <ActivityIndicator color="#ffffff" />
                ) : (
                  <Text style={styles.primaryBtnText}>Classificar ECG com IA</Text>
                )}
              </TouchableOpacity>
            </View>

            {/* Cartão de Resultado + Inspetor Grad-CAM Interativo */}
            {result && (
              <View style={[styles.card, { backgroundColor: theme.surface, borderColor: theme.border }]}>
                <View style={styles.resultHeader}>
                  <View style={{ flex: 1 }}>
                    <RiskBadge level={result.risk_level} color={result.risk_color} />
                    <Text style={[styles.predTitle, { color: theme.text }]}>
                      Classe {result.predicted_class} — {result.class_name_pt}
                    </Text>
                    <Text style={[styles.predSub, { color: theme.textMuted }]}>
                      {result.class_name_en} · {result.model_label} ({result.inference_time_ms} ms)
                    </Text>
                  </View>
                  <View style={[styles.confBox, { backgroundColor: theme.primarySoft, borderColor: theme.primary }]}>
                    <Text style={[styles.confLabel, { color: theme.primary }]}>CONFIANÇA</Text>
                    <Text style={[styles.confValue, { color: theme.primary }]}>
                      {Number(result.confidence_pct).toFixed(1)}%
                    </Text>
                  </View>
                </View>

                {result.ground_truth_class ? (
                  <Text
                    style={[
                      styles.gtNote,
                      { color: result.match_ground_truth ? theme.success : theme.danger },
                    ]}
                  >
                    Referência do conjunto de teste: Classe {result.ground_truth_class}{' '}
                    {result.match_ground_truth ? '✓ Correto' : '✗ Divergente'}
                  </Text>
                ) : null}

                {/* Banner Fairness (Ir Além 1: tau = 0.30) */}
                {result.fairness_triage && (
                  <View
                    style={[
                      styles.fairnessBox,
                      {
                        backgroundColor: result.fairness_triage.critical_alert_triggered
                          ? theme.dangerSoft
                          : theme.successSoft,
                        borderColor: result.fairness_triage.critical_alert_triggered
                          ? theme.danger
                          : theme.success,
                      },
                    ]}
                  >
                    <Text
                      style={{
                        fontSize: 12,
                        fontWeight: '700',
                        color: result.fairness_triage.critical_alert_triggered
                          ? theme.danger
                          : theme.success,
                      }}
                    >
                      {result.fairness_triage.critical_alert_triggered
                        ? `⚠ Triagem Fairness (τ=0,30): P(M+V+F) = ${result.fairness_triage.critical_prob_pct.toFixed(1)}% — Priorizar revisão`
                        : `✓ Triagem Fairness (τ=0,30): P(M+V+F) = ${result.fairness_triage.critical_prob_pct.toFixed(1)}% (baixo risco crítico)`}
                    </Text>
                  </View>
                )}

                {/* PAINEL INTERATIVO DE GRAD-CAM (Opacidade + Zoom + Color-Invariant) */}
                <InteractiveGradCamViewer result={result} theme={theme} />

                {/* Distribuição de Probabilidades */}
                <Text style={[styles.sectionTitle, { color: theme.text, marginTop: 16 }]}>
                  Probabilidades por Categoria (AAMI)
                </Text>
                {(result.probabilities || []).map((p) => (
                  <ProbabilityBar
                    key={p.code}
                    item={p}
                    isTop={p.code === result.predicted_class}
                    theme={theme}
                  />
                ))}

                {/* Morfologia & Conduta Simulada */}
                <View
                  style={[
                    styles.clinicalBox,
                    { backgroundColor: theme.surfaceSoft, borderLeftColor: theme.primary, borderColor: theme.border },
                  ]}
                >
                  <Text style={[styles.clinicalTitle, { color: theme.primary }]}>
                    Morfologia &amp; Conduta Simulada
                  </Text>
                  <Text style={[styles.clinicalBody, { color: theme.textSecondary }]}>{result.morphology}</Text>
                  <Text style={[styles.clinicalBody, { color: theme.text, marginTop: 6, fontWeight: '500' }]}>
                    {result.recommendation}
                  </Text>
                </View>

                <View
                  style={[
                    styles.disclaimerBox,
                    { backgroundColor: theme.warnBg, borderColor: theme.warnBorder },
                  ]}
                >
                  <Text style={[styles.disclaimerText, { color: theme.warnText }]}>
                    {result.clinical_disclaimer}
                  </Text>
                </View>
              </View>
            )}
          </>
        )}

        {/* ABA 2: AMOSTRAS REAIS DO CONJUNTO DE TESTE */}
        {activeTab === 'samples' && (
          <View style={[styles.card, { backgroundColor: theme.surface, borderColor: theme.border }]}>
            <Text style={[styles.sectionTitle, { color: theme.text }]}>
              Exames Reais do Conjunto de Teste (MIT-BIH)
            </Text>
            <Text style={[styles.helperText, { color: theme.textMuted }]}>
              Toque em qualquer exame abaixo para executar a classificação via Flask e abrir o Inspetor Grad-CAM interativo.
            </Text>
            {samples.length === 0 ? (
              <Text style={[styles.placeholderText, { color: theme.textMuted }]}>
                Conecte-se ao backend Flask para listar as amostras de teste.
              </Text>
            ) : (
              samples.map((s) => (
                <TouchableOpacity
                  key={s.sample_id}
                  style={[
                    styles.sampleCard,
                    { backgroundColor: theme.surfaceSoft, borderColor: theme.border },
                  ]}
                  onPress={() => handleClassifySample(s)}
                >
                  <Image source={{ uri: s.thumbnail_b64 }} style={styles.sampleThumb} resizeMode="contain" />
                  <View style={{ flex: 1 }}>
                    <RiskBadge level={s.risk_level} color={s.risk_color} />
                    <Text style={[styles.sampleTitle, { color: theme.text }]}>{s.label_display}</Text>
                    <Text style={[styles.sampleSub, { color: theme.textMuted }]}>
                      {s.filename} · Cor original: {s.cor_original || '—'}
                    </Text>
                  </View>
                </TouchableOpacity>
              ))
            )}
          </View>
        )}

        {/* ABA 3: HISTÓRICO PERSISTIDO EM SQLITE */}
        {activeTab === 'history' && (
          <View style={[styles.card, { backgroundColor: theme.surface, borderColor: theme.border }]}>
            <View style={styles.historyHeader}>
              <Text style={[styles.sectionTitle, { color: theme.text }]}>Histórico de Análises (SQLite)</Text>
              <TouchableOpacity onPress={() => refreshConnection(apiUrl)}>
                <Text style={[styles.refreshLink, { color: theme.primary }]}>↻ Atualizar</Text>
              </TouchableOpacity>
            </View>
            {history.length === 0 ? (
              <Text style={[styles.placeholderText, { color: theme.textMuted }]}>
                Nenhuma classificação registrada ainda.
              </Text>
            ) : (
              history.map((h) => (
                <View key={h.id} style={[styles.historyItem, { borderBottomColor: theme.border }]}>
                  <View style={{ flex: 1 }}>
                    <Text style={[styles.historyTitle, { color: theme.text }]}>
                      #{h.id} · Classe {h.classe_predita} ({h.nome_classe})
                    </Text>
                    <Text style={[styles.historySub, { color: theme.textMuted }]}>
                      {h.paciente_id} · {h.modelo === 'resnet18_transfer' ? 'ResNet18' : 'CardioCNN'} · {h.risco}
                    </Text>
                  </View>
                  <Text style={[styles.historyPct, { color: theme.primary }]}>
                    {Number(h.confianca_pct).toFixed(1)}%
                  </Text>
                </View>
              ))
            )}
          </View>
        )}
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1 },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingHorizontal: 14,
    paddingVertical: 12,
    borderBottomWidth: 1,
    gap: 8,
  },
  headerLeft: { flexDirection: 'row', alignItems: 'center', gap: 10 },
  logoBox: {
    width: 38,
    height: 38,
    borderRadius: 11,
    alignItems: 'center',
    justifyContent: 'center',
  },
  logoPulse: { color: '#fff', fontSize: 20, fontWeight: '800' },
  title: { fontSize: 16.5, fontWeight: '800' },
  subtitle: { fontSize: 11 },
  headerRight: { flexDirection: 'row', alignItems: 'center', gap: 6 },
  pillBtn: {
    paddingHorizontal: 10,
    paddingVertical: 6,
    borderRadius: 999,
    borderWidth: 1,
  },
  pillBtnText: { fontSize: 11.5, fontWeight: '700' },

  configBox: { padding: 12, borderBottomWidth: 1 },
  configLabel: { fontSize: 12, marginBottom: 6, fontWeight: '600' },
  configRow: { flexDirection: 'row', gap: 8 },
  configInput: {
    flex: 1,
    borderRadius: 9,
    borderWidth: 1,
    paddingHorizontal: 10,
    paddingVertical: 8,
    fontSize: 13,
  },
  configBtn: { borderRadius: 9, paddingHorizontal: 14, justifyContent: 'center' },
  configBtnText: { color: '#fff', fontWeight: '700', fontSize: 13 },
  errorText: { fontSize: 11.5, marginTop: 6 },

  tabs: {
    flexDirection: 'row',
    paddingHorizontal: 12,
    paddingVertical: 10,
    gap: 8,
    borderBottomWidth: 1,
  },
  tab: {
    flex: 1,
    paddingVertical: 9,
    borderRadius: 10,
    borderWidth: 1,
    alignItems: 'center',
  },
  tabText: { fontSize: 12.5, fontWeight: '700' },

  content: { padding: 14, paddingBottom: 38, gap: 14 },
  kpiRow: { flexDirection: 'row', gap: 8 },
  kpiMini: {
    flex: 1,
    borderRadius: 12,
    borderWidth: 1,
    paddingVertical: 9,
    paddingHorizontal: 10,
  },
  kpiLbl: { fontSize: 9.5, fontWeight: '800', letterSpacing: 0.4 },
  kpiVal: { fontSize: 13.5, fontWeight: '800', marginTop: 2 },

  card: {
    borderRadius: 16,
    padding: 16,
    borderWidth: 1,
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.06,
    shadowRadius: 12,
    elevation: 2,
  },
  sectionTitle: { fontSize: 15, fontWeight: '800', marginBottom: 10 },
  helperText: { fontSize: 12.5, marginBottom: 12 },

  actionRow: { flexDirection: 'row', gap: 10, marginBottom: 12 },
  pickBtn: { flex: 1, paddingVertical: 12, borderRadius: 11, alignItems: 'center' },
  pickBtnText: { color: '#fff', fontWeight: '700', fontSize: 14 },

  previewCard: {
    borderRadius: 12,
    borderWidth: 1,
    padding: 10,
    marginBottom: 12,
  },
  liveToggleRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginBottom: 8,
  },
  liveToggleLabel: { fontSize: 12, fontWeight: '700' },
  previewImgBox: {
    height: 150,
    backgroundColor: '#ffffff',
    borderRadius: 8,
    alignItems: 'center',
    justifyContent: 'center',
    borderWidth: 1,
    borderColor: '#e2e8f0',
  },
  previewImg: { width: '100%', height: '100%' },
  previewCaption: { fontSize: 11, marginTop: 6, textAlign: 'center' },

  placeholderBox: {
    borderRadius: 12,
    padding: 18,
    borderWidth: 1,
    borderStyle: 'dashed',
    marginBottom: 12,
  },
  placeholderText: { fontSize: 12.5, textAlign: 'center' },

  fieldLabel: { fontSize: 12, fontWeight: '700', marginBottom: 6, marginTop: 4 },
  modelRow: {
    flexDirection: 'row',
    gap: 6,
    padding: 4,
    borderRadius: 11,
    borderWidth: 1,
    marginBottom: 10,
  },
  modelChip: { flex: 1, paddingVertical: 9, borderRadius: 8, alignItems: 'center' },
  modelChipText: { fontSize: 12.5, fontWeight: '700' },

  input: {
    borderRadius: 10,
    borderWidth: 1,
    paddingHorizontal: 12,
    paddingVertical: 10,
    fontSize: 14,
    marginBottom: 12,
  },
  primaryBtn: { paddingVertical: 14, borderRadius: 12, alignItems: 'center' },
  btnDisabled: { opacity: 0.45 },
  primaryBtnText: { color: '#ffffff', fontSize: 15, fontWeight: '800' },

  resultHeader: { flexDirection: 'row', alignItems: 'flex-start', gap: 10 },
  predTitle: { fontSize: 16.5, fontWeight: '800', marginTop: 6 },
  predSub: { fontSize: 12, marginTop: 2 },
  confBox: {
    paddingHorizontal: 11,
    paddingVertical: 8,
    borderRadius: 12,
    borderWidth: 1,
    alignItems: 'center',
  },
  confLabel: { fontSize: 9.5, fontWeight: '800' },
  confValue: { fontSize: 20, fontWeight: '800' },
  gtNote: { fontSize: 12, fontWeight: '700', marginTop: 8 },

  fairnessBox: {
    marginTop: 10,
    padding: 10,
    borderRadius: 10,
    borderWidth: 1,
  },

  clinicalBox: {
    marginTop: 12,
    borderLeftWidth: 4,
    borderWidth: 1,
    borderRadius: 11,
    padding: 12,
  },
  clinicalTitle: { fontSize: 13, fontWeight: '800', marginBottom: 4 },
  clinicalBody: { fontSize: 12.5, lineHeight: 18 },

  disclaimerBox: {
    marginTop: 12,
    borderWidth: 1,
    borderRadius: 10,
    padding: 10,
  },
  disclaimerText: { fontSize: 11.5, lineHeight: 16 },

  sampleCard: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
    borderRadius: 12,
    padding: 10,
    marginBottom: 10,
    borderWidth: 1,
  },
  sampleThumb: {
    width: 90,
    height: 62,
    backgroundColor: '#ffffff',
    borderRadius: 8,
    borderWidth: 1,
    borderColor: '#e2e8f0',
  },
  sampleTitle: { fontSize: 13, fontWeight: '700', marginTop: 4 },
  sampleSub: { fontSize: 11.5, marginTop: 2 },

  historyHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
  refreshLink: { fontSize: 13, fontWeight: '700' },
  historyItem: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingVertical: 10,
    borderBottomWidth: 1,
  },
  historyTitle: { fontSize: 13.5, fontWeight: '700' },
  historySub: { fontSize: 11.5, marginTop: 2 },
  historyPct: { fontSize: 14, fontWeight: '800', marginLeft: 8 },
});
