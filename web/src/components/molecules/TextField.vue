<script setup lang="ts">
import { useId } from 'vue';
import Input from '../atoms/Input.vue';
import Text from '../atoms/Text.vue';

defineProps<{
  modelValue: string;
  label: string;
  type?: string;
  placeholder?: string;
  hint?: string;
  error?: string;
  disabled?: boolean;
}>();

defineEmits<{ 'update:modelValue': [value: string] }>();

const id = useId();
</script>

<template>
  <label class="ff-textfield" :for="id">
    <Text variant="label">{{ label }}</Text>
    <Input
      :id="id"
      :model-value="modelValue"
      :type="type"
      :placeholder="placeholder"
      :disabled="disabled"
      :invalid="!!error"
      @update:model-value="$emit('update:modelValue', $event)"
    />
    <Text v-if="error" variant="small" class="ff-textfield-error">{{ error }}</Text>
    <Text v-else-if="hint" variant="small" class="ff-textfield-hint">{{ hint }}</Text>
  </label>
</template>

<style scoped>
.ff-textfield { display: flex; flex-direction: column; gap: 6px; }
.ff-textfield-error { color: var(--status-error) !important; }
.ff-textfield-hint  { color: var(--text-dim) !important; }
</style>
