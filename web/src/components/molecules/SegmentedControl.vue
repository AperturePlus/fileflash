<script setup lang="ts">
export interface SegmentedOption {
  value: string | number;
  label: string;
}

defineProps<{
  modelValue: string | number;
  options: SegmentedOption[];
  disabled?: boolean;
}>();

defineEmits<{ 'update:modelValue': [value: string | number] }>();
</script>

<template>
  <div class="ff-segmented" role="group">
    <button
      v-for="opt in options"
      :key="opt.value"
      type="button"
      class="ff-segmented-option"
      :class="{ 'ff-segmented-option--active': opt.value === modelValue }"
      :aria-pressed="opt.value === modelValue ? 'true' : 'false'"
      :disabled="disabled"
      @click="$emit('update:modelValue', opt.value)"
    >
      {{ opt.label }}
    </button>
  </div>
</template>

<style scoped>
.ff-segmented {
  display: inline-flex;
  background: var(--surface-inset);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-sm);
  padding: 2px;
  gap: 2px;
}
.ff-segmented-option {
  padding: 4px 12px;
  background: transparent; border: 0;
  color: var(--text-secondary);
  font-family: var(--font-mono); font-size: var(--text-label); letter-spacing: var(--tracking-wide);
  text-transform: uppercase; cursor: pointer;
  transition: all var(--mo-duration-fast) var(--mo-easing);
}
.ff-segmented-option:hover:not(:disabled) { color: var(--text-primary); }
.ff-segmented-option--active { background: var(--ac); color: var(--ac-fg); }
.ff-segmented-option:disabled { opacity: 0.5; cursor: not-allowed; }
</style>
