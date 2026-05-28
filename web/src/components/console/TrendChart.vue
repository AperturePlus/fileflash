<script setup lang="ts">
import { computed } from 'vue';

const props = defineProps<{
  points: Array<{ date: string; used: number }>;
}>();

const maxValue = computed(() => Math.max(1, ...props.points.map((p) => p.used)));
</script>

<template>
  <div class="trend-chart">
    <div v-for="p in points" :key="p.date" class="trend-chart__bar">
      <div
        class="trend-chart__fill"
        :style="{ height: `${Math.max(4, (p.used / maxValue) * 100)}%` }"
      />
      <small class="trend-chart__label">{{ p.date.slice(5) }}</small>
    </div>
  </div>
</template>

<style scoped>
.trend-chart {
  display: flex;
  align-items: flex-end;
  gap: var(--sp-sm);
  height: 160px;
  padding: var(--sp-lg);
  background: var(--surface-raised);
  border: 1px solid var(--border-default);
}
.trend-chart__bar {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--sp-xs);
  height: 100%;
  min-width: 0;
}
.trend-chart__fill {
  width: 100%;
  max-width: 24px;
  background: var(--ac);
  margin-top: auto;
}
.trend-chart__label {
  font-family: var(--font-mono);
  font-size: var(--text-label);
  color: var(--text-tertiary);
  letter-spacing: var(--tracking-wide);
}
</style>
