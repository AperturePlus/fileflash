<script setup lang="ts">
import { ref, computed } from 'vue';

const props = defineProps<{
  currentBytes: number;
  storageUsed: number;
}>();
const emit = defineEmits<{ (e: 'submit', newBytes: number): void }>();

const gb = ref((props.currentBytes / 1024 / 1024 / 1024).toFixed(1));
const errorMessage = ref('');
const usedGb = computed(() => (props.storageUsed / 1024 / 1024 / 1024).toFixed(2));

function submit() {
  const parsed = Number(gb.value);
  if (!Number.isFinite(parsed) || parsed < 0) {
    errorMessage.value = 'Enter a positive number';
    return;
  }
  const bytes = Math.round(parsed * 1024 * 1024 * 1024);
  if (bytes < props.storageUsed) {
    errorMessage.value = `Cannot be below current usage (${usedGb.value} GB)`;
    return;
  }
  errorMessage.value = '';
  emit('submit', bytes);
}
</script>

<template>
  <div class="quota-editor">
    <input v-model="gb" type="number" step="0.1" min="0" />
    <small>GB · used {{ usedGb }} GB</small>
    <button class="quota-editor__submit" @click="submit">Save</button>
    <p v-if="errorMessage" class="quota-editor__error">{{ errorMessage }}</p>
  </div>
</template>

<style scoped>
.quota-editor {
  display: flex;
  align-items: center;
  gap: var(--sp-sm);
  flex-wrap: wrap;
}
.quota-editor input {
  width: 100px;
  height: 28px;
  padding: 0 var(--sp-sm);
  background: var(--surface-base);
  color: var(--text-primary);
  border: 1px solid var(--border-default);
  font-family: var(--font-mono);
  font-size: var(--text-body);
}
.quota-editor input:focus {
  outline: none;
  border-color: var(--ac);
}
.quota-editor small {
  color: var(--text-tertiary);
  font-family: var(--font-mono);
  font-size: var(--text-small);
}
.quota-editor__submit {
  height: 28px;
  padding: 0 var(--sp-md);
  background: var(--ac);
  border: none;
  color: var(--ac-fg);
  font-family: var(--font-mono);
  font-size: var(--text-label);
  text-transform: uppercase;
  letter-spacing: var(--tracking-wide);
  cursor: pointer;
}
.quota-editor__error {
  width: 100%;
  margin: var(--sp-xs) 0 0;
  color: var(--status-error);
  font-family: var(--font-mono);
  font-size: var(--text-small);
}
</style>
