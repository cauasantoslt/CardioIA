import styles from '../styles/StatCard.module.css';

export default function StatCard({
  title,
  value,
  subtitle,
  badgeText,
  badgeType = 'neutral',
  colorTheme = 'blue',
  icon: Icon
}) {
  const getIconClass = () => {
    switch (colorTheme) {
      case 'red': return styles.iconRed;
      case 'emerald': return styles.iconEmerald;
      case 'amber': return styles.iconAmber;
      default: return styles.iconBlue;
    }
  };

  const getBadgeClass = () => {
    switch (badgeType) {
      case 'positive': return styles.badgePositive;
      case 'alert': return styles.badgeAlert;
      default: return styles.badgeNeutral;
    }
  };

  return (
    <div className={styles.card}>
      <div className={styles.topRow}>
        <span className={styles.title}>{title}</span>
        {Icon && (
          <div className={`${styles.iconWrapper} ${getIconClass()}`}>
            <Icon size={22} />
          </div>
        )}
      </div>

      <div className={styles.value}>{value}</div>

      <div className={styles.bottomRow}>
        {badgeText && (
          <span className={`${styles.badge} ${getBadgeClass()}`}>
            {badgeText}
          </span>
        )}
        {subtitle && <span className={styles.subtitle}>{subtitle}</span>}
      </div>
    </div>
  );
}
