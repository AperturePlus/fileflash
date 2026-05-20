<script setup lang="ts">
import Button from '../../molecules/Button.vue';
import Select from '../../molecules/Select.vue';
import type { AgentExecutionPolicy } from '../../../types/agent';

defineProps<{
  modelValue: string;
  policy: AgentExecutionPolicy;
  disabled?: boolean;
}>();

const emit = defineEmits<{
  'update:modelValue': [value: string];
  'update:policy': [value: AgentExecutionPolicy];
  submit: [];
}>();

const POLICY_OPTIONS = [
  { value: 'planOnly', label: 'PLAN ONLY' },
  { value: 'confirm', label: 'CONFIRM' },
  { value: 'autopilot', label: 'AUTOPILOT' },
];

const onInput = (e: Event) => {
  emit('update:modelValue', (e.target as HTMLTextAreaElement).value);
};

const onKey = (e: KeyboardEvent) => {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault();
    emit('submit');
  }
};
</script>

<template>
  <footer class="ff-tid">
    <textarea
      class="ff-tid__ta"
      :value="modelValue"
      :disabled="disabled"
      placeholder="Describe a task. Shift+Enter for newline."
      rows="2"
      @input="onInput"
      @keydown="onKey"
    />
    <div class="ff-tid__row">
      <Select
        size="sm"
        :model-value="policy"
        :options="POLICY_OPTIONS"
        @update:model-value="(v) => $emit('update:policy', v as AgentExecutionPolicy)"
      />
      <Button
        variant="primary"
        :disabled="!modelValue.trim() || disabled"
        @click="$emit('submit')"
      >Send</Button>
    </div>
  </footer>
</template>

<style scoped>
.ff-tid {
  display: flex; flex-direction: column; gap: var(--sp-sm);
  padding: var(--sp-md) var(--sp-lg);
  border-top: 1px solid var(--border-default);
  background: var(--surface-base);
}
.ff-tid__ta {
  width: 100%;
  resize: vertical;
  min-height: 64px;
  padding: var(--sp-sm) var(--sp-md);
  background: var(--surface-raised);
  color: var(--text-primary);
  border: 1px solid var(--border-default);
  border-radius: 0;
  font-family: var(--font-sans);
  font-size: var(--text-body);
  outline: none;
  transition: border-color var(--mo-duration-fast) var(--mo-easing);
}
.ff-tid__ta:focus { border-color: var(--ac); }
.ff-tid__ta:disabled { opacity: 0.6; cursor: not-allowed; }

.ff-tid__row {
  display: flex; align-items: center; justify-content: space-between;
  gap: var(--sp-sm);
}
</style>
