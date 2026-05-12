<script setup lang="ts">
import Icon from '../atoms/Icon.vue';
import Spinner from '../atoms/Spinner.vue';
import type { IconName } from '../atoms/icons';

withDefaults(defineProps<{
  variant?: 'primary' | 'ghost' | 'danger';
  size?: 'sm' | 'md';
  icon?: IconName;
  loading?: boolean;
  disabled?: boolean;
  type?: 'button' | 'submit' | 'reset';
}>(), { variant: 'primary', size: 'md', type: 'button' });

defineEmits<{ click: [event: MouseEvent] }>();
</script>

<template>
  <button
    :type="type"
    class="ff-btn"
    :class="[`ff-btn--${variant}`, `ff-btn--${size}`, { 'ff-btn--loading': loading }]"
    :disabled="disabled || loading"
    @click="$emit('click', $event)"
  >
    <Spinner v-if="loading" label="Loading" />
    <Icon v-else-if="icon" :name="icon" :size="size === 'sm' ? 14 : 16" />
    <span class="ff-btn-label"><slot /></span>
  </button>
</template>

<style scoped>
.ff-btn {
  display: inline-flex; align-items: center; gap: 8px;
  padding: 0 14px;
  border: 1px solid transparent;
  border-radius: var(--radius-sm);
  font-family: var(--font-mono);
  font-size: var(--text-label);
  font-weight: var(--weight-bold);
  letter-spacing: var(--tracking-wide);
  text-transform: uppercase;
  cursor: pointer;
  transition: transform var(--mo-duration-fast) var(--mo-easing),
              filter var(--mo-duration-fast) var(--mo-easing),
              background-color var(--mo-duration-fast) var(--mo-easing),
              border-color var(--mo-duration-fast) var(--mo-easing);
}
.ff-btn:active:not(:disabled) { transform: scale(var(--mo-press-scale)); }
.ff-btn:disabled { opacity: 0.5; cursor: not-allowed; }

.ff-btn--md { height: 32px; }
.ff-btn--sm { height: 24px; padding: 0 10px; font-size: 9px; }

.ff-btn--primary { background: var(--ac); color: var(--ac-fg); }
.ff-btn--primary:hover:not(:disabled) { filter: brightness(1.1); box-shadow: var(--mo-hover-bloom); }

.ff-btn--ghost { background: transparent; color: var(--text-secondary); border-color: var(--border-default); }
.ff-btn--ghost:hover:not(:disabled) { background: var(--surface-inset); color: var(--text-primary); }

.ff-btn--danger { background: var(--status-error); color: #fff; }
.ff-btn--danger:hover:not(:disabled) { filter: brightness(1.1); }
</style>
