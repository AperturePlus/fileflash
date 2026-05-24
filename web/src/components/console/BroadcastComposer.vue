<script setup lang="ts">
import { ref } from 'vue';

const emit = defineEmits<{ (e: 'submit', message: string, title?: string): void }>();

const title = ref('');
const message = ref('');

function submit() {
  const trimmed = message.value.trim();
  if (!trimmed) return;
  emit('submit', trimmed, title.value.trim() || undefined);
  title.value = '';
  message.value = '';
}
</script>

<template>
  <div class="broadcast">
    <input v-model="title" type="text" placeholder="Title (optional)" />
    <textarea v-model="message" rows="3" placeholder="Broadcast message..." />
    <button class="broadcast__submit" :disabled="!message.trim()" @click="submit">Send</button>
  </div>
</template>

<style scoped>
.broadcast {
  display: flex;
  flex-direction: column;
  gap: var(--sp-sm);
  padding: var(--sp-md);
  background: var(--surface-raised);
  border: 1px solid var(--border-default);
}
.broadcast input,
.broadcast textarea {
  background: var(--surface-base);
  color: var(--text-primary);
  border: 1px solid var(--border-default);
  padding: var(--sp-sm);
  font-family: var(--font-mono);
  font-size: var(--text-body);
}
.broadcast input:focus,
.broadcast textarea:focus {
  outline: none;
  border-color: var(--ac);
}
.broadcast__submit {
  align-self: flex-end;
  height: 32px;
  padding: 0 var(--sp-lg);
  background: var(--ac);
  border: none;
  color: var(--ac-fg);
  font-family: var(--font-mono);
  font-size: var(--text-label);
  text-transform: uppercase;
  letter-spacing: var(--tracking-wide);
  cursor: pointer;
}
.broadcast__submit:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}
</style>
