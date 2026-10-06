import { Link } from 'react-router-dom';
import { HeartCrack, ArrowLeft } from 'lucide-react';
import styles from '../styles/NotFound.module.css';

export default function NotFound() {
  return (
    <div className={styles.container}>
      <HeartCrack size={72} color="#dc2626" />
      <div className={styles.errorCode}>404</div>
      <h1 className={styles.title}>Página Hospitalar Não Encontrada</h1>
      <p className={styles.description}>
        O prontuário ou rota solicitada não existe ou foi arquivada no sistema central do CardioIA.
      </p>
      <Link to="/dashboard" className={styles.backBtn}>
        <ArrowLeft size={18} />
        <span>Retornar ao Painel Principal</span>
      </Link>
    </div>
  );
}
