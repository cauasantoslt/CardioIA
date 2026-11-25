import { Platform } from 'react-native';

function normalizeBaseUrl(url) {
  return (url || '').trim().replace(/\/+$/, '');
}

async function parseJsonResponse(response) {
  const text = await response.text();
  let data;
  try {
    data = JSON.parse(text);
  } catch {
    throw new Error(`Resposta inesperada da API (HTTP ${response.status}).`);
  }
  if (!response.ok) {
    throw new Error(data.erro || `Erro HTTP ${response.status} ao comunicar com o backend.`);
  }
  return data;
}

export async function checkHealth(baseUrl) {
  const res = await fetch(`${normalizeBaseUrl(baseUrl)}/api/v1/health`);
  return parseJsonResponse(res);
}

export async function fetchSamples(baseUrl) {
  const res = await fetch(`${normalizeBaseUrl(baseUrl)}/api/v1/samples`);
  return parseJsonResponse(res);
}

export async function fetchHistory(baseUrl, limit = 15) {
  const res = await fetch(`${normalizeBaseUrl(baseUrl)}/api/v1/history?limit=${limit}`);
  return parseJsonResponse(res);
}

/**
 * Aplica o filtro Color-Invariant ao vivo via backend Flask para pré-visualização imediata.
 */
export async function previewColorInvariantFilter(baseUrl, asset) {
  const endpoint = `${normalizeBaseUrl(baseUrl)}/api/v1/preview-filter`;
  if (asset.base64) {
    const res = await fetch(endpoint, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ image_base64: asset.base64 }),
    });
    return parseJsonResponse(res);
  }
  const formData = new FormData();
  formData.append('image', {
    uri: asset.uri,
    name: asset.fileName || 'preview_ecg.png',
    type: asset.mimeType || 'image/png',
  });
  const res = await fetch(endpoint, { method: 'POST', body: formData });
  return parseJsonResponse(res);
}

/**
 * Envia imagem escolhida da galeria/câmera para POST /api/v1/predict.
 */
export async function predictFromImageAsset(baseUrl, asset, modelKey, patientId) {
  const endpoint = `${normalizeBaseUrl(baseUrl)}/api/v1/predict`;
  const filename = asset.fileName || `ecg_${Date.now()}.png`;
  const mimeType = asset.mimeType || 'image/png';

  if (Platform.OS === 'web' && asset.base64) {
    const res = await fetch(endpoint, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        image_base64: asset.base64,
        filename,
        model: modelKey,
        patient_id: patientId || 'PAC-MOBILE',
        source: 'mobile_react_native_web',
        gradcam: true,
      }),
    });
    return parseJsonResponse(res);
  }

  const formData = new FormData();
  formData.append('image', {
    uri: asset.uri,
    name: filename,
    type: mimeType,
  });
  formData.append('model', modelKey);
  formData.append('patient_id', patientId || 'PAC-MOBILE');
  formData.append('source', 'mobile_react_native');
  formData.append('gradcam', 'true');

  const res = await fetch(endpoint, { method: 'POST', body: formData });
  return parseJsonResponse(res);
}

export async function predictFromSample(baseUrl, sampleId, modelKey, patientId) {
  const endpoint = `${normalizeBaseUrl(baseUrl)}/api/v1/predict`;
  const res = await fetch(endpoint, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      sample_id: sampleId,
      model: modelKey,
      patient_id: patientId || 'PAC-MOBILE',
      source: 'mobile_sample',
      gradcam: true,
    }),
  });
  return parseJsonResponse(res);
}
