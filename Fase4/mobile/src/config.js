import { Platform } from 'react-native';

/**
 * URL padrão do backend Flask (Fase4/backend/app.py):
 * - Web / iOS Simulator: http://localhost:5000
 * - Emulador Android:    http://10.0.2.2:5000 (atalho para localhost do host)
 * - Celular físico (Expo Go): altere na própria tela do app para http://<IP_DA_SUA_MAQUINA>:5000
 */
export function getDefaultApiUrl() {
  if (Platform.OS === 'android') {
    return 'http://10.0.2.2:5000';
  }
  return 'http://localhost:5000';
}

export const MODEL_OPTIONS = [
  { key: 'resnet18_transfer', label: 'ResNet18 (Transfer)' },
  { key: 'cnn_scratch', label: 'CardioCNN (Zero)' },
];
