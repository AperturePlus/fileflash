<script setup lang="ts">
defineProps<{
  title: string;
  value: string | number;
  unit?: string;
  accent?: 'primary' | 'warning' | 'danger';
}>();
</script>

<template>
  <article class="kpi-card" :class="accent ? `is-${accent}` : ''">
    <h3 class="kpi-card__title">{{ title }}</h3>
    <div class="kpi-card__value">
      <strong>{{ value }}</strong>
      <small v-if="unit">{{ unit }}</small>
    </div>
  </article>
</template>

<style scoped>
.kpi-card {
  background: var(--surface-raised);
  border: 1px solid var(--border-default);
  padding: var(--sp-lg);
  display: flex;
  flex-direction: column;
  gap: var(--sp-sm);
}
.kpi-card__title {
  margin: 0;
  font-family: var(--font-mono);
  font-size: var(--text-label);
  color: var(--text-tertiary);
  letter-spacing: var(--tracking-wide);
  text-transform: uppercase;
}
.kpi-card__value {
  display: flex;
  align-items: baseline;
  gap: var(--sp-xs);
}
.kpi-card__value strong {
  font-family: var(--font-mono);
  font-size: var(--text-display);
  font-variant-numeric: tabular-nums;
  color: var(--text-primary);
  font-weight: var(--weight-medium);
}
.kpi-card__value small {
  font-family: var(--font-mono);
  font-size: var(--text-small);
  color: var(--text-tertiary);
}
.kpi-card.is-warning .kpi-card__value strong { color: var(--status-warning); }
.kpi-card.is-danger .kpi-card__value strong { color: var(--status-error); }
.kpi-card.is-primary .kpi-card__value strong { color: var(--ac); }
</style>
