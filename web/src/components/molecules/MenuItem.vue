<script setup lang="ts">
import Icon from '../atoms/Icon.vue';
import KeyHint from '../atoms/KeyHint.vue';
import type { IconName } from '../atoms/icons';

withDefaults(defineProps<{
  icon?: IconName;
  variant?: 'default' | 'danger';
  keyHint?: string[];
  disabled?: boolean;
}>(), { variant: 'default' });

defineEmits<{ click: [event: MouseEvent] }>();
</script>

<template>
  <button
    type="button"
    class="ff-menuitem"
    :class="[`ff-menuitem--${variant}`, { 'ff-menuitem--disabled': disabled }]"
    :disabled="disabled"
    @click="$emit('click', $event)"
  >
    <Icon v-if="icon" :name="icon" :size="14" />
    <span class="ff-menuitem-label"><slot /></span>
    <KeyHint v-if="keyHint" :keys="keyHint" class="ff-menuitem-hint" />
  </button>
</template>

<style scoped>
.ff-menuitem {
  display: flex; align-items: center; gap: 10px;
  width: 100%; padding: 6px 10px;
  background: transparent; border: 0;
  color: var(--text-secondary);
  font-family: var(--font-sans); font-size: var(--text-body);
  text-align: left; cursor: pointer;
  transition: background-color var(--mo-duration-fast) var(--mo-easing), color var(--mo-duration-fast) var(--mo-easing);
}
.ff-menuitem:hover:not(:disabled) { background: var(--surface-inset); color: var(--text-primary); }
.ff-menuitem--disabled { opacity: 0.5; cursor: not-allowed; }
.ff-menuitem--danger { color: var(--status-error); }
.ff-menuitem-label { flex: 1; }
.ff-menuitem-hint { margin-left: auto; }
</style>
