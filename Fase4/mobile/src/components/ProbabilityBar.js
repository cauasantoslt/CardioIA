import React from 'react';
import { StyleSheet, Text, View } from 'react-native';

export default function ProbabilityBar({ item, isTop, theme }) {
  const pct = Math.max(0, Math.min(100, Number(item.probability_pct || 0)));
  return (
    <View style={styles.row}>
      <View style={styles.labelRow}>
        <View
          style={[
            styles.codeBox,
            {
              backgroundColor: isTop ? theme.primarySoft : theme.surfaceSoft,
              borderColor: isTop ? theme.primary : theme.border,
            },
          ]}
        >
          <Text style={[styles.code, { color: isTop ? theme.primary : theme.text }]}>
            {item.code}
          </Text>
        </View>
        <Text
          style={[
            styles.name,
            { color: isTop ? theme.text : theme.textSecondary, fontWeight: isTop ? '700' : '500' },
          ]}
          numberOfLines={1}
        >
          {item.name_pt}
        </Text>
        <Text style={[styles.pct, { color: isTop ? theme.primary : theme.text }]}>
          {pct.toFixed(1)}%
        </Text>
      </View>
      <View style={[styles.track, { backgroundColor: theme.trackBg }]}>
        <View
          style={[
            styles.fill,
            {
              width: `${pct}%`,
              backgroundColor: item.risk_color || theme.primary,
            },
          ]}
        />
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  row: { marginBottom: 10 },
  labelRow: { flexDirection: 'row', alignItems: 'center', marginBottom: 5, gap: 7 },
  codeBox: {
    width: 24,
    height: 22,
    borderRadius: 6,
    borderWidth: 1,
    alignItems: 'center',
    justifyContent: 'center',
  },
  code: { fontWeight: '800', fontSize: 12 },
  name: { flex: 1, fontSize: 12.5 },
  pct: { width: 50, textAlign: 'right', fontWeight: '700', fontSize: 12.5 },
  track: { height: 8, borderRadius: 999, overflow: 'hidden' },
  fill: { height: '100%', borderRadius: 999 },
});
