import React from 'react';
import { StyleSheet, Text, View } from 'react-native';

export default function RiskBadge({ level, color }) {
  const bg = color || '#38bdf8';
  return (
    <View style={[styles.badge, { backgroundColor: bg }]}>
      <Text style={styles.text}>RISCO {level || 'INFO'}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  badge: {
    alignSelf: 'flex-start',
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: 999,
  },
  text: {
    color: '#ffffff',
    fontSize: 11,
    fontWeight: '800',
    letterSpacing: 0.6,
  },
});
