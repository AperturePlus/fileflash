<script setup lang="ts">
import { computed } from 'vue';
import Text from '../atoms/Text.vue';
import MonoNumber from '../atoms/MonoNumber.vue';

const props = defineProps<{
  label: string;
  value: string | number;
  delta?: number;
}>();

const deltaTone = computed(() => {
  if (!props.delta) return 'neutral';
  return props.delta > 0 ? 'up' : 'down';
});
</script>

<template>
  <div class="ff-statblock">
    <Text variant="label">{{ label }}</Text>
    <MonoNumber :value="value" accent class="ff-statblock-value" />
    <span v-if="delta != null" class="ff-statblock-delta" :class="`ff-statblock-delta--${deltaTone}`">
      <span v-if="delta > 0">↑</span><span v-else>↓</span> {{ Math.abs(delta) }}
    </span>
  </div>
</template>

<style scoped>
.ff-statblock { display: flex; flex-direction: column; gap: 4px; }
.ff-statblock-value { font-size: var(--text-data-big) !important; }
.ff-statblock-delta {
  font-family: var(--font-mono); font-size: var(--text-small);
}
.ff-statblock-delta--up   { color: var(--status-success); }
.ff-statblock-delta--down { color: var(--status-error); }
</style>
