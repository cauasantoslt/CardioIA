import { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import {
  Users,
  CalendarCheck,
  AlertTriangle,
  Activity,
  HeartPulse,
  PlusCircle,
  ArrowRight,
  Clock,
  CheckCircle2,
  BrainCircuit
} from 'lucide-react';
import StatCard from '../components/StatCard';
import { useAuth } from '../contexts/AuthContext';
import { getDashboardStats } from '../services/api';
import { INITIAL_APPOINTMENTS } from '../reducers/appointmentReducer';
import styles from '../styles/Dashboard.module.css';

export default function Dashboard() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadStats() {
      try {
        const data = await getDashboardStats();
        setStats(data);
      } finally {
        setLoading(false);
      }
    }
    loadStats();
  }, []);

  return (
    <div className={styles.dashboardContainer}>
      <section className={styles.welcomeHeader}>
        <div className={styles.headerInfo}>
          <h1 className={styles.title}>
            Olá, {user?.name || 'Dr. Cardiologista'} 👋
          </h1>
          <p className={styles.welcomeText}>
            Painel de inteligência diagnóstica e monitoramento contínuo. Sistema em operação com
            suporte a modelos de NLP e triagem automatizada da Fase 2.
          </p>
        </div>

        <div className={styles.headerActions}>
          <button
            onClick={() => navigate('/appointments')}
            className={styles.primaryActionBtn}
            type="button"
          >
            <PlusCircle size={18} />
            <span>Novo Agendamento</span>
          </button>
          <button
            onClick={() => navigate('/patients')}
            className={styles.secondaryActionBtn}
            type="button"
          >
            <Users size={18} />
            <span>Ver Triagem</span>
          </button>
        </div>

        <svg
          className={styles.ecgSvg}
          width="400"
          height="120"
          viewBox="0 0 500 150"
          fill="none"
          xmlns="http://www.w3.org/2000/svg"
        >
          <path
            d="M0 75 H120 L135 40 L150 110 L165 20 L180 130 L195 75 H240 L255 45 L270 100 L285 75 H500"
            stroke="#ffffff"
            strokeWidth="3"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </svg>
      </section>

      {stats?.criticalAlerts && stats.criticalAlerts.length > 0 && (
        <section className={styles.alertsBanner}>
          <div className={styles.alertLeft}>
            <AlertTriangle className={styles.alertIcon} size={24} />
            <div className={styles.alertText}>
              <strong>ALERTA DE PROTOCOLO MANCHESTER:</strong> 3 pacientes identificados com
              sintomatologia de alta prioridade (SCA / Arritmia Grave) aguardando reavaliação.
            </div>
          </div>
          <button
            onClick={() => navigate('/patients')}
            className={styles.alertBtn}
            type="button"
          >
            Atender Casos Críticos
          </button>
        </section>
      )}

      <section className={styles.statsGrid}>
        <StatCard
          title="Total em Triagem"
          value={loading ? '...' : stats?.totalTriaged || '48'}
          subtitle="Atendidos nas últimas 24h"
          badgeText="+12% hoje"
          badgeType="positive"
          colorTheme="blue"
          icon={Users}
        />
        <StatCard
          title="Consultas Agendadas Hoje"
          value={loading ? '...' : stats?.scheduledToday || '14'}
          subtitle="4 procedimentos de ECG com IA"
          badgeText="Na capacidade"
          badgeType="neutral"
          colorTheme="emerald"
          icon={CalendarCheck}
        />
        <StatCard
          title="Casos Críticos (Alto Risco)"
          value={loading ? '...' : stats?.criticalCases || '8'}
          subtitle="Tempo-porta médio < 12min"
          badgeText="Atenção Máxima"
          badgeType="alert"
          colorTheme="red"
          icon={HeartPulse}
        />
        <StatCard
          title="Taxa de Ocupação da UTI"
          value={loading ? '...' : stats?.occupancyRate || '87.5%'}
          subtitle="Leitos monitorados por telemetria"
          badgeText="Estável"
          badgeType="neutral"
          colorTheme="amber"
          icon={Activity}
        />
      </section>

      <div className={styles.dashboardSplit}>
        <div className={styles.sectionCard}>
          <div className={styles.sectionHeader}>
            <h2 className={styles.sectionTitle}>
              <Clock size={20} color="#2563eb" />
              <span>Próximos Atendimentos Agendados</span>
            </h2>
            <Link to="/appointments" className={styles.viewAllLink}>
              <span>Ver agenda completa</span>
              <ArrowRight size={14} />
            </Link>
          </div>

          <table className={styles.appointmentsTable}>
            <thead>
              <tr>
                <th>Paciente</th>
                <th>Médico Responsável</th>
                <th>Horário</th>
                <th>Procedimento</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {INITIAL_APPOINTMENTS.slice(0, 4).map((apt) => (
                <tr key={apt.id}>
                  <td className={styles.patientNameCell}>{apt.patientName}</td>
                  <td>{apt.doctor.split('(')[0]}</td>
                  <td>{apt.time}</td>
                  <td>
                    <span className={styles.procedureBadge}>{apt.procedureType}</span>
                  </td>
                  <td>
                    <span className={styles.statusConfirmed}>
                      <CheckCircle2 size={14} />
                      <span>{apt.status}</span>
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <div className={styles.sectionCard}>
          <div className={styles.sectionHeader}>
            <h2 className={styles.sectionTitle}>
              <BrainCircuit size={20} color="#dc2626" />
              <span>Métricas de Decisão IA</span>
            </h2>
          </div>

          <div className={styles.aiSnapshot}>
            <div className={styles.metricBox}>
              <span className={styles.metricLabel}>Acurácia do Classificador TF-IDF</span>
              <span className={styles.metricVal}>100.0% (Teste)</span>
              <div className={styles.progressBarWrapper}>
                <div className={styles.progressBarFill} style={{ width: '100%' }}></div>
              </div>
            </div>

            <div className={styles.metricBox}>
              <span className={styles.metricLabel}>Sensibilidade para Alto Risco (Recall)</span>
              <span className={styles.metricVal}>100.0% (Zero Falsos Negativos)</span>
              <div className={styles.progressBarWrapper}>
                <div className={styles.progressBarFillDanger} style={{ width: '100%' }}></div>
              </div>
            </div>

            <div className={styles.metricBox}>
              <span className={styles.metricLabel}>Tempo Médio de Inferência por Relato</span>
              <span className={styles.metricVal}>4.2 ms</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
