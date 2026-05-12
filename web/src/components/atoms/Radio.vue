<script setup lang="ts">
import { computed, useId } from 'vue';

const props = defineProps<{
  modelValue: string | number;
  value: string | number;
  name: string;
  disabled?: boolean;
  label?: string;
}>();

defineEmits<{ 'update:modelValue': [value: string | number] }>();

const id = useId();
const checked = computed(() => props.modelValue === props.value);
</script>

<template>
  <label class="ff-radio" :class="{ 'ff-radio--checked': checked, 'ff-radio--disabled': disabled }" :for="id">
    <input
      :id="id"
      type="radio"
      class="ff-radio-native"
      :name="name"
      :value="value"
      :checked="checked"
      :disabled="disabled"
      @change="$emit('update:modelValue', value)"
    />
    <span class="ff-radio-dot" aria-hidden="true" />
    <span v-if="label" class="ff-radio-label">{{ label }}</span>
  </label>
</template>

<style scoped>
.ff-radio { display: inline-flex; align-items: center; gap: 8px; cursor: pointer; user-select: none; }
.ff-radio--disabled { opacity: 0.5; cursor: not-allowed; }
.ff-radio-native { position: absolute; opacity: 0; pointer-events: none; }
.ff-radio-dot {
  position: relative;
  width: 16px; height: 16px;
  background: var(--surface-inset);
  border: 1px solid var(--border-default);
  border-radius: 50%;
  transition: all var(--mo-duration-fast) var(--mo-easing);
}
.ff-radio-dot::after {
  content: ''; position: absolute; inset: 3px;
  background: var(--ac); border-radius: 50%;
  transform: scale(0);
  transition: transform var(--mo-duration-fast) var(--mo-easing);
}
.ff-radio--checked .ff-radio-dot { border-color: var(--ac); }
.ff-radio--checked .ff-radio-dot::after { transform: scale(1); }
.ff-radio-label { font-size: var(--text-body); color: var(--text-secondary); }
</style>
