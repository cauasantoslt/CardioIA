const MOCK_PATIENTS = [
  {
    id: 1,
    name: 'Carlos Alberto Ferreira',
    age: 64,
    gender: 'Masculino',
    bloodPressure: '165/100 mmHg',
    heartRate: '118 bpm',
    spo2: '93%',
    complaint: 'Dor retroesternal em aperto opressivo há mais de 25 minutos com irradiação para mandíbula e sudorese fria profusa.',
    riskLevel: 'Alto Risco',
    ecgStatus: 'Supradesnivelamento de ST (V1-V4)',
    triageCategory: 'Emergência (Vermelho)',
    room: 'Leito UTI 02',
    admissionTime: 'Há 12 min'
  },
  {
    id: 2,
    name: 'Maria Madalena de Sousa',
    age: 71,
    gender: 'Feminino',
    bloodPressure: '150/90 mmHg',
    heartRate: '104 bpm',
    spo2: '91%',
    complaint: 'Falta de ar aguda ao deitar (ortopneia), tosse seca e edema bilateral importante em membros inferiores há 3 dias.',
    riskLevel: 'Alto Risco',
    ecgStatus: 'Sobrecarga Atrial Esquerda + BAV 1º',
    triageCategory: 'Muito Urgente (Laranja)',
    room: 'Leito Semi-Intensivo 04',
    admissionTime: 'Há 25 min'
  },
  {
    id: 3,
    name: 'Juliana Pires Martins',
    age: 38,
    gender: 'Feminino',
    bloodPressure: '120/78 mmHg',
    heartRate: '76 bpm',
    spo2: '99%',
    complaint: 'Leve desconforto muscular interescapular após carregar compras de supermercado; nega precordialgia.',
    riskLevel: 'Baixo Risco',
    ecgStatus: 'Ritmo Sinusal Fisiológico Normal',
    triageCategory: 'Pouco Urgente (Verde)',
    room: 'Consultório Ambulatorial 01',
    admissionTime: 'Há 45 min'
  },
  {
    id: 4,
    name: 'Roberto Mendonça de Lima',
    age: 58,
    gender: 'Masculino',
    bloodPressure: '175/105 mmHg',
    heartRate: '142 bpm',
    spo2: '95%',
    complaint: 'Palpitações taquicárdicas irregulares em repouso iniciadas subitamente, associadas a tontura e escurecimento visual.',
    riskLevel: 'Alto Risco',
    ecgStatus: 'Fibrilação Atrial com Alta Resposta Ventricular',
    triageCategory: 'Emergência (Vermelho)',
    room: 'Box de Emergência 01',
    admissionTime: 'Há 50 min'
  },
  {
    id: 5,
    name: 'Ana Lúcia Barbosa',
    age: 49,
    gender: 'Feminino',
    bloodPressure: '135/85 mmHg',
    heartRate: '82 bpm',
    spo2: '98%',
    complaint: 'Sensação de queimação retroesternal e azia pós-prandial após refeição copiosa, sem piora ao esforço físico.',
    riskLevel: 'Baixo Risco',
    ecgStatus: 'Repolarização Ventricular Normal',
    triageCategory: 'Não Urgente (Azul)',
    room: 'Consultório Ambulatorial 03',
    admissionTime: 'Há 1h 10min'
  },
  {
    id: 6,
    name: 'Antônio Vicente de Paula',
    age: 79,
    gender: 'Masculino',
    bloodPressure: '88/54 mmHg',
    heartRate: '42 bpm',
    spo2: '92%',
    complaint: 'Episódio sincopal com perda transitória de consciência ao caminhar, fraqueza extrema e palidez cutânea.',
    riskLevel: 'Alto Risco',
    ecgStatus: 'Bradicardia Sinusal Severa / Pausa Sinusal',
    triageCategory: 'Emergência (Vermelho)',
    room: 'Sala de Estabilização',
    admissionTime: 'Há 1h 30min'
  },
  {
    id: 7,
    name: 'Camila Fernandes Costa',
    age: 29,
    gender: 'Feminino',
    bloodPressure: '115/72 mmHg',
    heartRate: '70 bpm',
    spo2: '99%',
    complaint: 'Tensão muscular leve na região cervical devido à postura prolongada no computador em regime home-office.',
    riskLevel: 'Baixo Risco',
    ecgStatus: 'Ritmo Sinusal Regular',
    triageCategory: 'Não Urgente (Azul)',
    room: 'Consultório Ambulatorial 02',
    admissionTime: 'Há 1h 55min'
  },
  {
    id: 8,
    name: 'Fernando Guimarães Borges',
    age: 62,
    gender: 'Masculino',
    bloodPressure: '158/98 mmHg',
    heartRate: '98 bpm',
    spo2: '94%',
    complaint: 'Sensação de aperto torácico aos pequenos esforços acompanhado de fadiga intensa e náuseas matinais.',
    riskLevel: 'Alto Risco',
    ecgStatus: 'Inversão Simétrica de Onda T (V4-V6)',
    triageCategory: 'Muito Urgente (Laranja)',
    room: 'Leito Observação Cardíaca 03',
    admissionTime: 'Há 2h 10min'
  },
  {
    id: 9,
    name: 'Patrícia Duarte Ribeiro',
    age: 42,
    gender: 'Feminino',
    bloodPressure: '122/80 mmHg',
    heartRate: '68 bpm',
    spo2: '98%',
    complaint: 'Pigarro na garganta pela manhã e coriza hialina sem febre ou dispneia; consulta eletiva de retorno.',
    riskLevel: 'Baixo Risco',
    ecgStatus: 'Normalidade Eletrocardiográfica',
    triageCategory: 'Não Urgente (Azul)',
    room: 'Consultório Ambulatorial 01',
    admissionTime: 'Há 2h 40min'
  },
  {
    id: 10,
    name: 'Jorge Henrique Silveira',
    age: 55,
    gender: 'Masculino',
    bloodPressure: '185/115 mmHg',
    heartRate: '108 bpm',
    spo2: '93%',
    complaint: 'Crise hipertensiva com cefaleia occipital pulsátil severa, escotomas cintilantes e dor precordial atípica.',
    riskLevel: 'Alto Risco',
    ecgStatus: 'Critérios de Sokolow-Lyon Positivos (HVE)',
    triageCategory: 'Emergência (Vermelho)',
    room: 'Box de Emergência 02',
    admissionTime: 'Há 3h 05min'
  }
];

export const DOCTORS = [
  'Dr. Cauã Santos (Cardiologia Intervencionista - RM 566599)',
  'Dra. Beatriz Mendes (Eletrofisiologia & Arritmias)',
  'Dr. Ricardo Ramos (Insuficiência Cardíaca & Transplante)',
  'Dra. Mariana Takahashi (Ergometria & Reabilitação)'
];

export const PROCEDURE_TYPES = [
  'Exame de ECG com IA',
  'Triagem de Alto Risco',
  'Consulta Cardiológica de Rotina',
  'Ecocardiograma Transtorácico',
  'Mapeamento Holter 24h',
  'Avaliação Pré-Operatória'
];

export async function getPatients() {
  await new Promise((resolve) => setTimeout(resolve, 200));
  return [...MOCK_PATIENTS];
}

export async function getDashboardStats() {
  await new Promise((resolve) => setTimeout(resolve, 150));
  const highRiskCount = MOCK_PATIENTS.filter((p) => p.riskLevel === 'Alto Risco').length;
  const lowRiskCount = MOCK_PATIENTS.filter((p) => p.riskLevel === 'Baixo Risco').length;

  return {
    totalTriaged: MOCK_PATIENTS.length + 38,
    scheduledToday: 14,
    criticalCases: highRiskCount + 2,
    lowRiskCases: lowRiskCount + 36,
    occupancyRate: '87.5%',
    avgTriageTime: '3.4 min',
    criticalAlerts: [
      {
        id: 'alt_1',
        title: 'Alerta de SCA / IAM Agudo Detectado',
        patient: 'Carlos Alberto Ferreira (Leito 02)',
        time: 'Há 12 min',
        type: 'danger'
      },
      {
        id: 'alt_2',
        title: 'Fibrilação Atrial de Alta Resposta',
        patient: 'Roberto Mendonça de Lima (Box 01)',
        time: 'Há 50 min',
        type: 'warning'
      },
      {
        id: 'alt_3',
        title: 'Crise Hipertensiva Grave (185/115)',
        patient: 'Jorge Henrique Silveira (Box 02)',
        time: 'Há 3h',
        type: 'warning'
      }
    ]
  };
}
