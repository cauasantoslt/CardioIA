import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Search, UserX } from 'lucide-react';
import PatientCard from '../components/PatientCard';
import { getPatients } from '../services/api';
import styles from '../styles/Patients.module.css';

export default function Patients() {
  const [patients, setPatients] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [riskFilter, setRiskFilter] = useState('ALL');
  const navigate = useNavigate();

  useEffect(() => {
    async function fetchPatientsData() {
      try {
        const data = await getPatients();
        setPatients(data);
      } finally {
        setLoading(false);
      }
    }
    fetchPatientsData();
  }, []);

  const filteredPatients = patients.filter((patient) => {
    const matchesSearch =
      patient.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      patient.complaint.toLowerCase().includes(searchQuery.toLowerCase()) ||
      patient.ecgStatus.toLowerCase().includes(searchQuery.toLowerCase());

    const matchesRisk =
      riskFilter === 'ALL' || patient.riskLevel === riskFilter;

    return matchesSearch && matchesRisk;
  });

  const handleSelectPatientForAppointment = (patient) => {
    navigate('/appointments', { state: { prefilledPatient: patient.name } });
  };

  const highRiskCount = patients.filter((p) => p.riskLevel === 'Alto Risco').length;
  const lowRiskCount = patients.filter((p) => p.riskLevel === 'Baixo Risco').length;

  return (
    <div className={styles.patientsContainer}>
      <div className={styles.headerSection}>
        <h1 className={styles.pageTitle}>Triagem Clínica de Pacientes</h1>
        <p className={styles.pageSubtitle}>
          Lista de prontuários com estratificação de risco cardiovascular em tempo real (TF-IDF +
          Ontologia Clínica).
        </p>
      </div>

      <div className={styles.controlsBar}>
        <div className={styles.searchWrapper}>
          <Search className={styles.searchIcon} size={18} />
          <input
            type="text"
            placeholder="Buscar por nome do paciente, sintoma ou traçado ECG..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className={styles.searchInput}
          />
        </div>

        <div className={styles.filterTabs}>
          <button
            type="button"
            className={`${styles.filterTab} ${
              riskFilter === 'ALL' ? styles.filterTabActive : ''
            }`}
            onClick={() => setRiskFilter('ALL')}
          >
            Todos ({patients.length})
          </button>
          <button
            type="button"
            className={`${styles.filterTab} ${styles.filterTabHighRisk} ${
              riskFilter === 'Alto Risco' ? styles.filterTabActive : ''
            }`}
            onClick={() => setRiskFilter('Alto Risco')}
          >
            Alto Risco ({highRiskCount})
          </button>
          <button
            type="button"
            className={`${styles.filterTab} ${styles.filterTabLowRisk} ${
              riskFilter === 'Baixo Risco' ? styles.filterTabActive : ''
            }`}
            onClick={() => setRiskFilter('Baixo Risco')}
          >
            Baixo Risco ({lowRiskCount})
          </button>
        </div>
      </div>

      <div className={styles.summaryRow}>
        <span>
          Exibindo <span className={styles.countHighlight}>{filteredPatients.length}</span> pacientes
          na visualização atual
        </span>
        {searchQuery && (
          <span>
            Filtro ativo por termo: "<strong>{searchQuery}</strong>"
          </span>
        )}
      </div>

      {loading ? (
        <div style={{ textAlign: 'center', padding: '3rem', color: '#64748b' }}>
          Carregando base de triagem cardiovascular...
        </div>
      ) : filteredPatients.length > 0 ? (
        <div className={styles.cardsGrid}>
          {filteredPatients.map((patient) => (
            <PatientCard
              key={patient.id}
              patient={patient}
              onSelectPatient={handleSelectPatientForAppointment}
            />
          ))}
        </div>
      ) : (
        <div className={styles.emptyState}>
          <UserX size={44} className={styles.emptyIcon} />
          <h3 className={styles.emptyTitle}>Nenhum paciente localizado</h3>
          <p className={styles.emptySubtitle}>
            Não encontramos registros compatíveis com os critérios de busca especificados.
          </p>
          <button
            type="button"
            onClick={() => {
              setSearchQuery('');
              setRiskFilter('ALL');
            }}
            className={styles.clearSearchBtn}
          >
            Limpar Filtros de Busca
          </button>
        </div>
      )}
    </div>
  );
}
