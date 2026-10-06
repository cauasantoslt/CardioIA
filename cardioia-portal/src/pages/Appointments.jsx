import { useState, useReducer, useEffect } from 'react';
import { useLocation } from 'react-router-dom';
import {
  CalendarClock,
  PlusCircle,
  Filter,
  Calendar,
  Clock,
  CheckCircle2,
  AlertCircle
} from 'lucide-react';
import {
  appointmentReducer,
  initialAppointmentState,
  APPOINTMENT_ACTIONS
} from '../reducers/appointmentReducer';
import { DOCTORS, PROCEDURE_TYPES } from '../services/api';
import styles from '../styles/Appointments.module.css';

export default function Appointments() {
  const location = useLocation();

  const [state, dispatch] = useReducer(appointmentReducer, initialAppointmentState);

  const [patientName, setPatientName] = useState(
    location.state?.prefilledPatient || ''
  );
  const [doctor, setDoctor] = useState(DOCTORS[0]);
  const [date, setDate] = useState(() => {
    const today = new Date();
    today.setDate(today.getDate() + 1);
    return today.toISOString().split('T')[0];
  });
  const [time, setTime] = useState('09:00');
  const [procedureType, setProcedureType] = useState(PROCEDURE_TYPES[0]);
  const [notes, setNotes] = useState('');
  const [formError, setFormError] = useState('');

  useEffect(() => {
    if (state.successMessage) {
      const timer = setTimeout(() => {
        dispatch({ type: APPOINTMENT_ACTIONS.CLEAR_MESSAGE });
      }, 4000);
      return () => clearTimeout(timer);
    }
  }, [state.successMessage]);

  const handleFormSubmit = (e) => {
    e.preventDefault();
    setFormError('');

    if (!patientName.trim()) {
      setFormError('Informe o nome completo do paciente.');
      return;
    }
    if (!date) {
      setFormError('Selecione uma data para o agendamento.');
      return;
    }
    if (!time) {
      setFormError('Selecione o horário da consulta.');
      return;
    }

    dispatch({
      type: APPOINTMENT_ACTIONS.ADD_APPOINTMENT,
      payload: {
        patientName: patientName.trim(),
        doctor,
        date,
        time,
        procedureType,
        notes: notes.trim() || 'Consulta cardiológica agendada sem observações adicionais.'
      }
    });

    setPatientName('');
    setNotes('');
  };

  const handleCancelAppointment = (id) => {
    if (window.confirm('Deseja realmente cancelar este agendamento cardiológico?')) {
      dispatch({
        type: APPOINTMENT_ACTIONS.CANCEL_APPOINTMENT,
        payload: id
      });
    }
  };

  const handleFilterDoctorChange = (e) => {
    dispatch({
      type: APPOINTMENT_ACTIONS.FILTER_BY_DOCTOR,
      payload: e.target.value
    });
  };

  const displayedAppointments = state.appointments.filter((apt) => {
    if (state.filterDoctor === 'ALL') return true;
    return apt.doctor === state.filterDoctor;
  });

  return (
    <div className={styles.container}>
      <div className={styles.headerSection}>
        <h1 className={styles.pageTitle}>Agendamento e Agenda Cardiológica</h1>
        <p className={styles.pageSubtitle}>
          Gestão centralizada de consultas, exames de ECG assistidos por IA e telemetria (gerenciado
          via <code>useReducer</code> + <code>useState</code>).
        </p>
      </div>

      {state.successMessage && (
        <div className={styles.successBanner}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
            <CheckCircle2 size={20} />
            <span>{state.successMessage}</span>
          </div>
          <button
            onClick={() => dispatch({ type: APPOINTMENT_ACTIONS.CLEAR_MESSAGE })}
            className={styles.bannerCloseBtn}
            type="button"
          >
            ×
          </button>
        </div>
      )}

      <div className={styles.layoutGrid}>
        <section className={styles.formCard}>
          <div className={styles.cardHeader}>
            <PlusCircle size={22} color="#2563eb" />
            <h2 className={styles.cardTitle}>Marcar Nova Consulta</h2>
          </div>

          {formError && (
            <div className={styles.validationError}>
              <AlertCircle size={15} style={{ display: 'inline', marginRight: 6, verticalAlign: -2 }} />
              {formError}
            </div>
          )}

          <form onSubmit={handleFormSubmit} className={styles.form}>
            <div className={styles.inputGroup}>
              <label htmlFor="patientName" className={styles.label}>
                Nome do Paciente <span className={styles.requiredStar}>*</span>
              </label>
              <input
                id="patientName"
                type="text"
                placeholder="Ex: Carlos Alberto Ferreira"
                value={patientName}
                onChange={(e) => setPatientName(e.target.value)}
                className={styles.input}
                required
              />
            </div>

            <div className={styles.inputGroup}>
              <label htmlFor="doctor" className={styles.label}>
                Médico Responsável <span className={styles.requiredStar}>*</span>
              </label>
              <select
                id="doctor"
                value={doctor}
                onChange={(e) => setDoctor(e.target.value)}
                className={styles.select}
              >
                {DOCTORS.map((doc, idx) => (
                  <option key={idx} value={doc}>
                    {doc}
                  </option>
                ))}
              </select>
            </div>

            <div className={styles.twoCols}>
              <div className={styles.inputGroup}>
                <label htmlFor="date" className={styles.label}>
                  Data <span className={styles.requiredStar}>*</span>
                </label>
                <input
                  id="date"
                  type="date"
                  value={date}
                  onChange={(e) => setDate(e.target.value)}
                  className={styles.input}
                  required
                />
              </div>

              <div className={styles.inputGroup}>
                <label htmlFor="time" className={styles.label}>
                  Horário <span className={styles.requiredStar}>*</span>
                </label>
                <input
                  id="time"
                  type="time"
                  value={time}
                  onChange={(e) => setTime(e.target.value)}
                  className={styles.input}
                  required
                />
              </div>
            </div>

            <div className={styles.inputGroup}>
              <label htmlFor="procedureType" className={styles.label}>
                Tipo de Procedimento <span className={styles.requiredStar}>*</span>
              </label>
              <select
                id="procedureType"
                value={procedureType}
                onChange={(e) => setProcedureType(e.target.value)}
                className={styles.select}
              >
                {PROCEDURE_TYPES.map((proc, idx) => (
                  <option key={idx} value={proc}>
                    {proc}
                  </option>
                ))}
              </select>
            </div>

            <div className={styles.inputGroup}>
              <label htmlFor="notes" className={styles.label}>
                Observações Clínicas e Histórico
              </label>
              <textarea
                id="notes"
                placeholder="Ex: Histórico prévio de SCA, controle pós-operatório ou queixa de palpitação..."
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                className={styles.textarea}
              />
            </div>

            <button type="submit" className={styles.submitBtn}>
              <CalendarClock size={18} />
              <span>Confirmar Agendamento</span>
            </button>
          </form>
        </section>

        <section className={styles.listCard}>
          <div className={styles.filterBar}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <CalendarClock size={20} color="#0f172a" />
              <h2 className={styles.cardTitle}>
                Consultas Marcadas ({displayedAppointments.length})
              </h2>
            </div>

            <div className={styles.filterSelectWrapper}>
              <Filter size={16} color="#64748b" />
              <span className={styles.filterLabel}>Filtrar Médico:</span>
              <select
                value={state.filterDoctor}
                onChange={handleFilterDoctorChange}
                className={styles.filterSelect}
              >
                <option value="ALL">Todos os Especialistas</option>
                {DOCTORS.map((doc, idx) => (
                  <option key={idx} value={doc}>
                    {doc.split('(')[0]}
                  </option>
                ))}
              </select>
            </div>
          </div>

          <div className={styles.appointmentsList}>
            {displayedAppointments.length === 0 ? (
              <p style={{ color: '#64748b', textAlign: 'center', padding: '2rem' }}>
                Nenhum agendamento encontrado para este filtro.
              </p>
            ) : (
              displayedAppointments.map((apt) => {
                const isCancelled = apt.status === 'Cancelado';
                return (
                  <div
                    key={apt.id}
                    className={`${styles.appointmentItem} ${
                      isCancelled ? styles.aptCancelled : ''
                    }`}
                  >
                    <div className={styles.aptTopRow}>
                      <div>
                        <h3 className={styles.patientName}>{apt.patientName}</h3>
                        <p className={styles.doctorName}>{apt.doctor}</p>
                      </div>
                      <span
                        className={`${styles.statusPill} ${
                          isCancelled ? styles.statusCancelled : styles.statusConfirmed
                        }`}
                      >
                        {apt.status}
                      </span>
                    </div>

                    <div className={styles.aptDetailsRow}>
                      <span className={styles.detailBadge}>
                        <Calendar size={14} color="#2563eb" />
                        {apt.date}
                      </span>
                      <span className={styles.detailBadge}>
                        <Clock size={14} color="#2563eb" />
                        {apt.time}
                      </span>
                      <span className={styles.procedureTag}>{apt.procedureType}</span>
                    </div>

                    {apt.notes && (
                      <div className={styles.notesBlock}>
                        <strong>Obs:</strong> {apt.notes}
                      </div>
                    )}

                    {!isCancelled && (
                      <div className={styles.aptActionsRow}>
                        <button
                          type="button"
                          onClick={() => handleCancelAppointment(apt.id)}
                          className={styles.cancelBtn}
                        >
                          Cancelar Agendamento
                        </button>
                      </div>
                    )}
                  </div>
                );
              })
            )}
          </div>
        </section>
      </div>
    </div>
  );
}
