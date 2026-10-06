import { useState, useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { HeartPulse, Mail, Lock, ArrowRight, AlertCircle, ShieldCheck } from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';
import styles from '../styles/Login.module.css';

export default function Login() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [errorMessage, setErrorMessage] = useState('');
  const { login, loading, isAuthenticated } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const from = location.state?.from?.pathname || '/dashboard';

  useEffect(() => {
    if (isAuthenticated) {
      navigate('/dashboard', { replace: true });
    }
  }, [isAuthenticated, navigate]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setErrorMessage('');

    if (!email || !password) {
      setErrorMessage('Por favor, preencha o e-mail e a senha de acesso.');
      return;
    }

    try {
      await login(email, password);
      navigate(from, { replace: true });
    } catch (err) {
      setErrorMessage(err.message || 'Falha ao autenticar.');
    }
  };

  const handleAutoFill = () => {
    setEmail('medico@cardioia.com');
    setPassword('cardio123');
    setErrorMessage('');
  };

  return (
    <div className={styles.loginContainer}>
      <div className={styles.glowBackground}></div>
      <div className={styles.glowBackgroundSecondary}></div>

      <div className={styles.loginCard}>
        <div className={styles.brandHeader}>
          <div className={styles.logoIcon}>
            <HeartPulse className={styles.heartPulseIcon} size={32} />
          </div>
          <h1 className={styles.portalTitle}>
            Cardio<span className={styles.titleBlue}>IA</span> Portal
          </h1>
          <p className={styles.portalSubtitle}>
            Acesso Restrito ao Módulo Clínico de Suporte à Decisão
          </p>
        </div>

        {errorMessage && (
          <div className={styles.errorBanner}>
            <AlertCircle size={16} />
            <span>{errorMessage}</span>
          </div>
        )}

        <form onSubmit={handleSubmit} className={styles.form}>
          <div className={styles.inputGroup}>
            <label htmlFor="email" className={styles.label}>
              E-mail Institucional
            </label>
            <div className={styles.inputWrapper}>
              <Mail className={styles.inputIcon} size={18} />
              <input
                id="email"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="medico@cardioia.com"
                className={styles.input}
                autoComplete="email"
                required
              />
            </div>
          </div>

          <div className={styles.inputGroup}>
            <label htmlFor="password" className={styles.label}>
              Senha de Segurança
            </label>
            <div className={styles.inputWrapper}>
              <Lock className={styles.inputIcon} size={18} />
              <input
                id="password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                className={styles.input}
                autoComplete="current-password"
                required
              />
            </div>
          </div>

          <button
            type="submit"
            className={styles.submitBtn}
            disabled={loading}
          >
            {loading ? (
              <>
                <div className={styles.spinner}></div>
                <span>Validando Credenciais...</span>
              </>
            ) : (
              <>
                <span>Acessar Prontuário Digital</span>
                <ArrowRight size={18} />
              </>
            )}
          </button>
        </form>

        <div className={styles.demoBox}>
          <div className={styles.demoTitle}>
            <span>Credenciais de Simulação (FIAP)</span>
            <ShieldCheck size={14} color="#3b82f6" />
          </div>
          <p className={styles.demoCredentials}>
            Usuário: <strong>medico@cardioia.com</strong><br />
            Senha: <strong>cardio123</strong>
          </p>
          <button
            type="button"
            onClick={handleAutoFill}
            className={styles.autoFillBtn}
          >
            Preencher dados de teste
          </button>
        </div>

        <div className={styles.academicFooter}>
          FIAP • Inteligência Artificial 2026<br />
          <strong>Cauã Santos — RM: 566599</strong>
        </div>
      </div>
    </div>
  );
}
