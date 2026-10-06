import { NavLink } from 'react-router-dom';
import { LayoutDashboard, Users, CalendarClock } from 'lucide-react';
import styles from '../styles/Sidebar.module.css';

export default function Sidebar() {
  const navItems = [
    { to: '/dashboard', label: 'Dashboard Clínico', icon: LayoutDashboard },
    { to: '/patients', label: 'Triagem de Pacientes', icon: Users },
    { to: '/appointments', label: 'Agendamentos', icon: CalendarClock }
  ];

  return (
    <aside className={styles.sidebar}>
      <nav className={styles.navGroup}>
        <span className={styles.navLabel}>Menu Principal</span>
        {navItems.map((item) => {
          const Icon = item.icon;
          return (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) =>
                `${styles.navLink} ${isActive ? styles.navLinkActive : ''}`
              }
            >
              <Icon size={20} className={styles.linkIcon} />
              <span>{item.label}</span>
            </NavLink>
          );
        })}
      </nav>

      <div className={styles.sidebarFooter}>
        <div className={styles.studentCard}>
          <span className={styles.fiapBadge}>FIAP • PBL 2026</span>
          <span className={styles.studentName}>Cauã Santos</span>
          <span className={styles.studentRm}>RM: 566599</span>
        </div>
      </div>
    </aside>
  );
}
