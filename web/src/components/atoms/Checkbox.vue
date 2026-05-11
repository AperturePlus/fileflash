<script setup lang="ts">
import { useId } from 'vue';
import Icon from './Icon.vue';

withDefaults(defineProps<{
  modelValue: boolean;
  disabled?: boolean;
  label?: string;
}>(), {});

defineEmits<{ 'update:modelValue': [value: boolean] }>();

// Vue 3.5+ provides a stable, SSR-safe id generator.
const id = useId();
</script>

<template>
  <label class="ff-checkbox" :class="{ 'ff-checkbox--checked': modelValue, 'ff-checkbox--disabled': disabled }" :for="id">
    <input
      :id="id"
      type="checkbox"
      class="ff-checkbox-native"
      :checked="modelValue"
      :disabled="disabled"
      @change="$emit('update:modelValue', ($event.target as HTMLInputElement).checked)"
    />
    <span class="ff-checkbox-box" aria-hidden="true">
      <Icon v-if="modelValue" name="check" :size="12" />
    </span>
    <span v-if="label" class="ff-checkbox-label">{{ label }}</span>
  </label>
</template>

<style scoped>
.ff-checkbox { display: inline-flex; align-items: center; gap: 8px; cursor: pointer; user-select: none; }
.ff-checkbox--disabled { opacity: 0.5; cursor: not-allowed; }
.ff-checkbox-native { position: absolute; opacity: 0; pointer-events: none; }
.ff-checkbox-box {
  display: inline-flex; align-items: center; justify-content: center;
  width: 16px; height: 16px;
  background: var(--surface-inset);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-sm);
  color: var(--ac-fg);
  transition: all var(--mo-duration-fast) var(--mo-easing);
}
.ff-checkbox--checked .ff-checkbox-box { background: var(--ac); border-color: var(--ac); }
.ff-checkbox-label { font-size: var(--text-body); color: var(--text-secondary); }
</style>
