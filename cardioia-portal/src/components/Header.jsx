import { Link, useNavigate } from 'react-router-dom';
import { HeartPulse, LogOut } from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';
import styles from '../styles/Header.module.css';

export default function Header() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  return (
    <header className={styles.header}>
      <div className={styles.leftSection}>
        <Link to="/dashboard" className={styles.brand}>
          <div className={styles.logoIconWrapper}>
            <HeartPulse className={styles.heartIcon} size={24} />
          </div>
          <div className={styles.brandText}>
            <span className={styles.title}>
              Cardio<span className={styles.titleHighlight}>IA</span>
            </span>
            <span className={styles.subtitle}>Estetoscópio Digital</span>
          </div>
        </Link>

        <div className={styles.statusBadge}>
          <span className={styles.statusDot}></span>
          <span>Centro Clínico Ativo</span>
        </div>
      </div>

      <div className={styles.rightSection}>
        {user && (
          <div className={styles.userCard}>
            <img
              src={user.avatar || 'https://images.unsplash.com/photo-1622253692010-333f2da6031d?w=150&auto=format&fit=crop&q=80'}
              alt={user.name}
              className={styles.userAvatar}
            />
            <div className={styles.userMeta}>
              <span className={styles.userName}>{user.name}</span>
              <span className={styles.userRole}>
                {user.crm} • RM {user.rm}
              </span>
            </div>
          </div>
        )}

        <button
          onClick={handleLogout}
          className={styles.logoutBtn}
          title="Encerrar sessão no portal"
        >
          <LogOut size={16} />
          <span>Sair</span>
        </button>
      </div>
    </header>
  );
}
