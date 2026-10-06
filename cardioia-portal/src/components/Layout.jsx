import { Outlet } from 'react-router-dom';
import Header from './Header';
import Sidebar from './Sidebar';
import styles from '../styles/Layout.module.css';

export default function Layout() {
  return (
    <div className={styles.layoutWrapper}>
      <Header />
      <div className={styles.bodyContainer}>
        <Sidebar />
        <main className={styles.mainContent}>
          <Outlet />
        </main>
      </div>
    </div>
  );
}
