<script setup lang="ts">
withDefaults(defineProps<{
  modelValue?: string;
  type?: string;
  placeholder?: string;
  disabled?: boolean;
  invalid?: boolean;
}>(), { type: 'text' });

defineEmits<{ 'update:modelValue': [value: string] }>();
</script>

<template>
  <input
    class="ff-input"
    :class="{ 'ff-input--invalid': invalid }"
    :type="type"
    :value="modelValue"
    :placeholder="placeholder"
    :disabled="disabled"
    @input="$emit('update:modelValue', ($event.target as HTMLInputElement).value)"
  />
</template>

<style scoped>
.ff-input {
  width: 100%;
  height: 32px;
  padding: 0 12px;
  background: var(--surface-inset);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-sm);
  color: var(--text-primary);
  font-family: var(--font-sans);
  font-size: var(--text-body);
  outline: none;
  transition: border-color var(--mo-duration-fast) var(--mo-easing),
              background-color var(--mo-duration-fast) var(--mo-easing);
}
.ff-input:focus { border-color: var(--ac); background: var(--surface-raised); }
.ff-input:disabled { opacity: 0.5; cursor: not-allowed; }
.ff-input--invalid { border-color: var(--status-error); }
.ff-input--invalid:focus { border-color: var(--status-error); }
.ff-input::placeholder { color: var(--text-dim); }
</style>
