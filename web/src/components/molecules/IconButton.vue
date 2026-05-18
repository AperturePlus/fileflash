<script setup lang="ts">
import Icon from '../atoms/Icon.vue';
import type { IconName } from '../atoms/icons';

withDefaults(defineProps<{
  icon: IconName;
  label: string;
  variant?: 'primary' | 'ghost';
  size?: 'sm' | 'md';
  disabled?: boolean;
}>(), { variant: 'ghost', size: 'md' });

defineEmits<{ click: [event: MouseEvent] }>();
</script>

<template>
  <button
    type="button"
    class="ff-iconbtn"
    :class="[`ff-iconbtn--${variant}`, `ff-iconbtn--${size}`]"
    :aria-label="label"
    :disabled="disabled"
    @click="$emit('click', $event)"
  >
    <Icon :name="icon" :size="size === 'sm' ? 14 : 18" />
  </button>
</template>

<style scoped>
.ff-iconbtn {
  display: inline-flex; align-items: center; justify-content: center;
  border: 1px solid transparent;
  border-radius: var(--radius-sm);
  background: transparent;
  color: var(--text-secondary);
  cursor: pointer;
  transition: all var(--mo-duration-fast) var(--mo-easing);
}
.ff-iconbtn:disabled { opacity: 0.5; cursor: not-allowed; }
.ff-iconbtn:active:not(:disabled) { transform: scale(var(--mo-press-scale)); }
.ff-iconbtn--md { width: 32px; height: 32px; }
.ff-iconbtn--sm { width: 24px; height: 24px; }
.ff-iconbtn--ghost:hover:not(:disabled) { background: var(--surface-inset); color: var(--text-primary); }
.ff-iconbtn--primary { background: var(--ac); color: var(--ac-fg); }
.ff-iconbtn--primary:hover:not(:disabled) { filter: brightness(1.1); }
</style>
