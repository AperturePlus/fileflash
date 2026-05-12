<script setup lang="ts">
defineProps<{
  value: string | number;
  accent?: boolean;
}>();
</script>

<template>
  <span class="ff-num" :class="{ 'ff-num--accent': accent }">{{ value }}</span>
</template>

<style scoped>
.ff-num {
  font-family: var(--font-mono);
  font-feature-settings: "tnum";
  font-size: var(--text-data);
  color: var(--text-secondary);
}
.ff-num--accent { color: var(--ac); }
</style>
