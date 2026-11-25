import React, { useState } from 'react';
import {
  Image,
  Modal,
  ScrollView,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from 'react-native';

const VIEW_MODES = [
  { id: 'gradcam', label: '🔥 Grad-CAM' },
  { id: 'binarizado', label: '🛡 Color-Inv.' },
  { id: 'original', label: '🎨 Original' },
];

const OPACITY_STEPS = [0, 0.25, 0.5, 0.75, 1.0];

/**
 * Painel Interativo de Grad-CAM e Filtro Color-Invariant ao Vivo para React Native.
 * Suporta:
 *  - Alternância instantânea entre Grad-CAM, Color-Invariant (sem cor) e Original RGB
 *  - Slider tátil de opacidade do heatmap (0% a 100%)
 *  - Zoom interativo (1.0x até 3.0x) com rolagem panorâmica e Modal Fullscreen
 *  - Exibição da cor original detectada e neutralizada pelo pipeline
 */
export default function InteractiveGradCamViewer({ result, theme }) {
  const [viewMode, setViewMode] = useState('gradcam');
  const [opacity, setOpacity] = useState(0.75);
  const [zoom, setZoom] = useState(1.0);
  const [sliderWidth, setSliderWidth] = useState(240);
  const [modalOpen, setModalOpen] = useState(false);

  if (!result) return null;

  const baseUri =
    viewMode === 'original'
      ? result.original_roi_image_b64 || result.preprocessed_image_b64
      : result.preprocessed_image_b64;

  const showHeat = viewMode === 'gradcam' && !!result.gradcam_heatmap_b64;
  const imgSize = Math.round(250 * zoom);

  function updateOpacityFromTouch(evt) {
    const x = evt.nativeEvent.locationX;
    const ratio = Math.max(0, Math.min(1, x / Math.max(sliderWidth, 1)));
    setOpacity(Math.round(ratio * 20) / 20);
  }

  return (
    <View style={[styles.wrap, { backgroundColor: theme.surfaceSoft, borderColor: theme.border }]}>
      {/* Barra de modos (Grad-CAM / Color-Invariant / Original) */}
      <View style={[styles.toolbar, { backgroundColor: theme.surface, borderBottomColor: theme.border }]}>
        <View style={styles.modeRow}>
          {VIEW_MODES.map((m) => {
            const active = viewMode === m.id;
            return (
              <TouchableOpacity
                key={m.id}
                style={[
                  styles.modePill,
                  {
                    backgroundColor: active ? theme.primary : theme.surfaceSoft,
                    borderColor: active ? theme.primary : theme.border,
                  },
                ]}
                onPress={() => setViewMode(m.id)}
              >
                <Text style={[styles.modeText, { color: active ? '#ffffff' : theme.textSecondary }]}>
                  {m.label}
                </Text>
              </TouchableOpacity>
            );
          })}
        </View>

        {/* Controles de Zoom + Tela Cheia */}
        <View style={styles.zoomRow}>
          <TouchableOpacity
            style={[styles.zoomBtn, { backgroundColor: theme.surfaceSoft, borderColor: theme.border }]}
            onPress={() => setZoom((z) => Math.max(1.0, +(z - 0.5).toFixed(1)))}
          >
            <Text style={[styles.zoomBtnText, { color: theme.text }]}>−</Text>
          </TouchableOpacity>
          <Text style={[styles.zoomLabel, { color: theme.textSecondary }]}>{Math.round(zoom * 100)}%</Text>
          <TouchableOpacity
            style={[styles.zoomBtn, { backgroundColor: theme.surfaceSoft, borderColor: theme.border }]}
            onPress={() => setZoom((z) => Math.min(3.0, +(z + 0.5).toFixed(1)))}
          >
            <Text style={[styles.zoomBtnText, { color: theme.text }]}>+</Text>
          </TouchableOpacity>
          {zoom > 1.0 && (
            <TouchableOpacity
              style={[styles.zoomBtn, { backgroundColor: theme.surfaceSoft, borderColor: theme.border, paddingHorizontal: 8 }]}
              onPress={() => setZoom(1.0)}
            >
              <Text style={[styles.zoomBtnText, { color: theme.primary, fontSize: 11 }]}>Reset</Text>
            </TouchableOpacity>
          )}
          <TouchableOpacity
            style={[styles.zoomBtn, { backgroundColor: theme.primarySoft, borderColor: theme.primary, paddingHorizontal: 9 }]}
            onPress={() => setModalOpen(true)}
          >
            <Text style={[styles.zoomBtnText, { color: theme.primary, fontSize: 12 }]}>⛶</Text>
          </TouchableOpacity>
        </View>
      </View>

      {/* Palco com Zoom e Pan */}
      <View style={styles.stageContainer}>
        <ScrollView horizontal contentContainerStyle={styles.scrollCenter} showsHorizontalScrollIndicator={zoom > 1}>
          <ScrollView contentContainerStyle={styles.scrollCenter} nestedScrollEnabled showsVerticalScrollIndicator={zoom > 1}>
            <View style={{ width: imgSize, height: imgSize, position: 'relative', backgroundColor: '#ffffff' }}>
              <Image
                source={{ uri: baseUri }}
                style={{ width: imgSize, height: imgSize }}
                resizeMode="contain"
              />
              {showHeat && (
                <Image
                  source={{ uri: result.gradcam_heatmap_b64 }}
                  style={{
                    position: 'absolute',
                    top: 0,
                    left: 0,
                    width: imgSize,
                    height: imgSize,
                    opacity,
                  }}
                  resizeMode="contain"
                />
              )}
            </View>
          </ScrollView>
        </ScrollView>
      </View>

      {/* Slider Interativo de Opacidade do Grad-CAM */}
      <View style={[styles.footer, { backgroundColor: theme.surface, borderTopColor: theme.border }]}>
        <View style={styles.sliderHeader}>
          <Text style={[styles.sliderTitle, { color: theme.textSecondary }]}>
            Opacidade do Grad-CAM
          </Text>
          <Text style={[styles.sliderPct, { color: theme.primary }]}>
            {showHeat ? `${Math.round(opacity * 100)}%` : 'Oculto'}
          </Text>
        </View>

        <View
          style={[styles.sliderTrackWrap, { opacity: showHeat ? 1 : 0.4 }]}
          onLayout={(e) => setSliderWidth(e.nativeEvent.layout.width)}
          onStartShouldSetResponder={() => showHeat}
          onResponderGrant={updateOpacityFromTouch}
          onResponderMove={updateOpacityFromTouch}
        >
          <View style={[styles.sliderTrack, { backgroundColor: theme.trackBg }]}>
            <View
              style={[
                styles.sliderFill,
                { width: `${Math.round(opacity * 100)}%`, backgroundColor: theme.primary },
              ]}
            />
          </View>
          <View
            style={[
              styles.sliderThumb,
              {
                left: `${Math.round(opacity * 100)}%`,
                backgroundColor: theme.primary,
                borderColor: theme.surface,
              },
            ]}
          />
        </View>

        {/* Presets rápidos de opacidade */}
        <View style={styles.presetRow}>
          {OPACITY_STEPS.map((val) => {
            const selected = showHeat && Math.abs(opacity - val) < 0.06;
            return (
              <TouchableOpacity
                key={val}
                disabled={!showHeat}
                onPress={() => setOpacity(val)}
                style={[
                  styles.presetChip,
                  {
                    backgroundColor: selected ? theme.primarySoft : theme.surfaceSoft,
                    borderColor: selected ? theme.primary : theme.border,
                  },
                ]}
              >
                <Text style={[styles.presetText, { color: selected ? theme.primary : theme.textMuted }]}>
                  {Math.round(val * 100)}%
                </Text>
              </TouchableOpacity>
            );
          })}
        </View>

        {/* Selo de Auditoria Cromática Color-Invariant */}
        {result.chromatic_audit && (
          <View style={[styles.auditRow, { backgroundColor: theme.surfaceSoft, borderColor: theme.border }]}>
            <View
              style={[
                styles.swatch,
                { backgroundColor: result.chromatic_audit.hex_color || '#000' },
              ]}
            />
            <Text style={[styles.auditText, { color: theme.textSecondary }]} numberOfLines={2}>
              <Text style={{ fontWeight: '800', color: theme.teal }}>Viés Cromático Neutralizado: </Text>
              Cor original {result.chromatic_audit.hex_color} (Lum {result.chromatic_audit.median_luminance}) → Binarizado
            </Text>
          </View>
        )}
      </View>

      {/* Modal Fullscreen */}
      <Modal visible={modalOpen} transparent animationType="fade" onRequestClose={() => setModalOpen(false)}>
        <View style={styles.modalBackdrop}>
          <View style={[styles.modalCard, { backgroundColor: theme.surface, borderColor: theme.border }]}>
            <View style={[styles.modalHeader, { borderBottomColor: theme.border }]}>
              <Text style={[styles.modalTitle, { color: theme.text }]}>
                Inspeção Ampliada — Classe {result.predicted_class}
              </Text>
              <TouchableOpacity onPress={() => setModalOpen(false)}>
                <Text style={[styles.modalClose, { color: theme.primary }]}>Fechar ✕</Text>
              </TouchableOpacity>
            </View>
            <View style={styles.modalStage}>
              <Image source={{ uri: baseUri }} style={styles.modalImg} resizeMode="contain" />
              {showHeat && (
                <Image
                  source={{ uri: result.gradcam_heatmap_b64 }}
                  style={[styles.modalImg, { position: 'absolute', opacity }]}
                  resizeMode="contain"
                />
              )}
            </View>
          </View>
        </View>
      </Modal>
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: {
    marginTop: 14,
    borderRadius: 14,
    borderWidth: 1,
    overflow: 'hidden',
  },
  toolbar: {
    padding: 10,
    borderBottomWidth: 1,
    gap: 8,
  },
  modeRow: {
    flexDirection: 'row',
    gap: 6,
  },
  modePill: {
    flex: 1,
    paddingVertical: 7,
    paddingHorizontal: 6,
    borderRadius: 9,
    borderWidth: 1,
    alignItems: 'center',
  },
  modeText: {
    fontSize: 11.5,
    fontWeight: '700',
  },
  zoomRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'flex-end',
    gap: 6,
  },
  zoomBtn: {
    height: 28,
    minWidth: 28,
    borderRadius: 8,
    borderWidth: 1,
    alignItems: 'center',
    justifyContent: 'center',
  },
  zoomBtnText: {
    fontSize: 15,
    fontWeight: '800',
  },
  zoomLabel: {
    fontSize: 11.5,
    fontWeight: '700',
    minWidth: 40,
    textAlign: 'center',
  },
  stageContainer: {
    height: 264,
    backgroundColor: '#ffffff',
    alignItems: 'center',
    justifyContent: 'center',
  },
  scrollCenter: {
    alignItems: 'center',
    justifyContent: 'center',
    minWidth: '100%',
    minHeight: 260,
  },
  footer: {
    padding: 12,
    borderTopWidth: 1,
  },
  sliderHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 8,
  },
  sliderTitle: {
    fontSize: 12,
    fontWeight: '700',
  },
  sliderPct: {
    fontSize: 12.5,
    fontWeight: '800',
  },
  sliderTrackWrap: {
    height: 28,
    justifyContent: 'center',
    position: 'relative',
  },
  sliderTrack: {
    height: 8,
    borderRadius: 999,
    overflow: 'hidden',
  },
  sliderFill: {
    height: '100%',
    borderRadius: 999,
  },
  sliderThumb: {
    position: 'absolute',
    width: 20,
    height: 20,
    borderRadius: 10,
    marginLeft: -10,
    borderWidth: 3,
    top: 4,
  },
  presetRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    gap: 6,
    marginTop: 6,
  },
  presetChip: {
    flex: 1,
    paddingVertical: 5,
    borderRadius: 8,
    borderWidth: 1,
    alignItems: 'center',
  },
  presetText: {
    fontSize: 11,
    fontWeight: '700',
  },
  auditRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    marginTop: 10,
    padding: 9,
    borderRadius: 10,
    borderWidth: 1,
  },
  swatch: {
    width: 14,
    height: 14,
    borderRadius: 4,
    borderWidth: 1,
    borderColor: 'rgba(0,0,0,0.2)',
  },
  auditText: {
    flex: 1,
    fontSize: 11,
    lineHeight: 15,
  },
  modalBackdrop: {
    flex: 1,
    backgroundColor: 'rgba(15, 23, 42, 0.82)',
    justifyContent: 'center',
    padding: 16,
  },
  modalCard: {
    borderRadius: 16,
    borderWidth: 1,
    overflow: 'hidden',
  },
  modalHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: 14,
    borderBottomWidth: 1,
  },
  modalTitle: { fontSize: 14, fontWeight: '800' },
  modalClose: { fontSize: 13.5, fontWeight: '700' },
  modalStage: {
    height: 360,
    backgroundColor: '#ffffff',
    alignItems: 'center',
    justifyContent: 'center',
  },
  modalImg: { width: '92%', height: '92%' },
});
