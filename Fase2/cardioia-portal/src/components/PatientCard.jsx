import { Activity, Clock, ChevronRight } from 'lucide-react';
import styles from '../styles/PatientCard.module.css';

export default function PatientCard({ patient, onSelectPatient }) {
  const isHighRisk = patient.riskLevel === 'Alto Risco';

  return (
    <article className={styles.card}>
      <div className={styles.header}>
        <div className={styles.patientMeta}>
          <h3 className={styles.name}>{patient.name}</h3>
          <span className={styles.demographics}>
            {patient.age} anos • {patient.gender} • {patient.room}
          </span>
        </div>

        <div
          className={`${styles.riskBadge} ${
            isHighRisk ? styles.highRisk : styles.lowRisk
          }`}
        >
          <span className={isHighRisk ? styles.pulsingDot : styles.calmDot}></span>
          <span>{patient.riskLevel}</span>
        </div>
      </div>

      <div className={styles.vitalsRow}>
        <div className={styles.vitalItem}>
          <span className={styles.vitalLabel}>P.A. Basal</span>
          <span className={styles.vitalValue}>{patient.bloodPressure}</span>
        </div>
        <div className={styles.vitalItem}>
          <span className={styles.vitalLabel}>Freq. Cardíaca</span>
          <span className={styles.vitalValue}>{patient.heartRate}</span>
        </div>
        <div className={styles.vitalItem}>
          <span className={styles.vitalLabel}>SpO2</span>
          <span className={styles.vitalValue}>{patient.spo2}</span>
        </div>
      </div>

      <div className={styles.complaintSection}>
        <p className={styles.complaintText}>"{patient.complaint}"</p>
      </div>

      <div className={styles.ecgBanner}>
        <Activity size={15} color={isHighRisk ? '#dc2626' : '#2563eb'} />
        <span>
          ECG AI: <strong className={styles.ecgHighlight}>{patient.ecgStatus}</strong>
        </span>
      </div>

      <div className={styles.footerRow}>
        <span className={styles.locationBadge}>
          <Clock size={13} style={{ display: 'inline', marginRight: 4, verticalAlign: -1 }} />
          Chegada: {patient.admissionTime}
        </span>

        {onSelectPatient && (
          <button
            onClick={() => onSelectPatient(patient)}
            className={styles.actionBtn}
            type="button"
          >
            <span>Agendar Consulta</span>
            <ChevronRight size={14} />
          </button>
        )}
      </div>
    </article>
  );
}
