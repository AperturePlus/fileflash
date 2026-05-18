<script setup lang="ts">
import { computed } from 'vue';
import Text from '../atoms/Text.vue';
import Bar from '../atoms/Bar.vue';

const props = withDefaults(defineProps<{
  value: number;
  tone?: 'accent' | 'success' | 'warning' | 'error' | 'info';
}>(), { tone: 'accent' });

const pct = computed(() => Math.round(Math.max(0, Math.min(1, props.value)) * 100));
</script>

<template>
  <div class="ff-progress">
    <div class="ff-progress-header">
      <slot name="label">
        <Text variant="label">PROGRESS</Text>
      </slot>
      <Text variant="data">{{ pct }}%</Text>
    </div>
    <div class="ff-progress-track">
      <Bar :value="value" :tone="tone" />
    </div>
  </div>
</template>

<style scoped>
.ff-progress { display: flex; flex-direction: column; gap: 6px; }
.ff-progress-header { display: flex; justify-content: space-between; align-items: baseline; }
.ff-progress-track { background: var(--surface-inset); }
</style>
