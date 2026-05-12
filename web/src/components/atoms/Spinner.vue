<script setup lang="ts">
withDefaults(defineProps<{ label?: string }>(), { label: 'Loading' });
</script>

<template>
  <div class="ff-spinner" role="status">
    <span class="ff-spinner-bar" />
    <span class="ff-spinner-bar" />
    <span class="ff-spinner-bar" />
    <span class="ff-visually-hidden">{{ label }}</span>
  </div>
</template>

<style scoped>
.ff-spinner { display: inline-flex; gap: 3px; align-items: center; height: 12px; }
.ff-spinner-bar {
  display: block; width: 2px; height: 100%;
  background: var(--ac);
  animation: ff-scan 0.9s linear infinite;
}
.ff-spinner-bar:nth-child(2) { animation-delay: 0.15s; }
.ff-spinner-bar:nth-child(3) { animation-delay: 0.3s; }
@keyframes ff-scan {
  0%, 100% { transform: scaleY(0.3); opacity: 0.4; }
  50%      { transform: scaleY(1); opacity: 1; }
}
.ff-visually-hidden {
  position: absolute; width: 1px; height: 1px; padding: 0; margin: -1px;
  overflow: hidden; clip: rect(0,0,0,0); white-space: nowrap; border: 0;
}
[data-motion="reduced"] .ff-spinner-bar { animation: none; opacity: 0.7; }
</style>
