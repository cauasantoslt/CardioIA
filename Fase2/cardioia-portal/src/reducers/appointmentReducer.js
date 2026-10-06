export const INITIAL_APPOINTMENTS = [
  {
    id: 'apt_101',
    patientName: 'Carlos Alberto Ferreira',
    doctor: 'Dr. Cauã Santos (Cardiologia Intervencionista - RM 566599)',
    date: '2026-10-06',
    time: '08:30',
    procedureType: 'Triagem de Alto Risco',
    notes: 'Avaliação pós-trombólise / Cateterismo emergencial programado.',
    status: 'Confirmado',
    createdAt: '2026-10-05 19:20'
  },
  {
    id: 'apt_102',
    patientName: 'Roberto Mendonça de Lima',
    doctor: 'Dra. Beatriz Mendes (Eletrofisiologia & Arritmias)',
    date: '2026-10-06',
    time: '10:00',
    procedureType: 'Exame de ECG com IA',
    notes: 'Mapeamento de arritmia paroxística e ajuste de betabloqueador.',
    status: 'Confirmado',
    createdAt: '2026-10-05 19:40'
  },
  {
    id: 'apt_103',
    patientName: 'Maria Madalena de Sousa',
    doctor: 'Dr. Ricardo Ramos (Insuficiência Cardíaca & Transplante)',
    date: '2026-10-06',
    time: '11:15',
    procedureType: 'Ecocardiograma Transtorácico',
    notes: 'Avaliação da fração de ejeção do ventrículo esquerdo (FEVE).',
    status: 'Confirmado',
    createdAt: '2026-10-05 20:00'
  },
  {
    id: 'apt_104',
    patientName: 'Juliana Pires Martins',
    doctor: 'Dra. Mariana Takahashi (Ergometria & Reabilitação)',
    date: '2026-10-06',
    time: '14:00',
    procedureType: 'Consulta Cardiológica de Rotina',
    notes: 'Check-up de rotina cardiovascular e orientação preventiva.',
    status: 'Confirmado',
    createdAt: '2026-10-05 20:15'
  }
];

export const initialAppointmentState = {
  appointments: INITIAL_APPOINTMENTS,
  filterDoctor: 'ALL',
  lastAction: null,
  successMessage: null
};

export const APPOINTMENT_ACTIONS = {
  ADD_APPOINTMENT: 'ADD_APPOINTMENT',
  CANCEL_APPOINTMENT: 'CANCEL_APPOINTMENT',
  FILTER_BY_DOCTOR: 'FILTER_BY_DOCTOR',
  CLEAR_MESSAGE: 'CLEAR_MESSAGE',
  RESET_DEFAULT: 'RESET_DEFAULT'
};

export function appointmentReducer(state, action) {
  switch (action.type) {
    case APPOINTMENT_ACTIONS.ADD_APPOINTMENT: {
      const newAppointment = {
        ...action.payload,
        id: `apt_${Date.now()}`,
        status: 'Confirmado',
        createdAt: new Date().toLocaleString('pt-BR')
      };

      return {
        ...state,
        appointments: [newAppointment, ...state.appointments],
        lastAction: APPOINTMENT_ACTIONS.ADD_APPOINTMENT,
        successMessage: `Consulta para "${newAppointment.patientName}" agendada com sucesso!`
      };
    }

    case APPOINTMENT_ACTIONS.CANCEL_APPOINTMENT: {
      const appointmentId = action.payload;
      const updatedList = state.appointments.map((apt) => {
        if (apt.id === appointmentId) {
          return { ...apt, status: 'Cancelado' };
        }
        return apt;
      });

      return {
        ...state,
        appointments: updatedList,
        lastAction: APPOINTMENT_ACTIONS.CANCEL_APPOINTMENT,
        successMessage: 'Agendamento cancelado com sucesso no prontuário.'
      };
    }

    case APPOINTMENT_ACTIONS.FILTER_BY_DOCTOR: {
      return {
        ...state,
        filterDoctor: action.payload,
        lastAction: APPOINTMENT_ACTIONS.FILTER_BY_DOCTOR
      };
    }

    case APPOINTMENT_ACTIONS.CLEAR_MESSAGE: {
      return {
        ...state,
        successMessage: null
      };
    }

    case APPOINTMENT_ACTIONS.RESET_DEFAULT: {
      return initialAppointmentState;
    }

    default:
      return state;
  }
}
