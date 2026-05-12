<script setup lang="ts">
import { MonoNumber } from '../../atoms';
import { Button } from '../../molecules';
import { useLocaleStore } from '../../../store/locale';

defineProps<{ count: number }>();
defineEmits<{
  (e: 'accept'): void;
  (e: 'clear'): void;
}>();

const localeStore = useLocaleStore();
const t = localeStore.t;
</script>

<template>
  <div v-if="count > 0" class="shared-batch">
    <div class="shared-batch__count">
      <MonoNumber :value="count" accent />
      <span class="shared-batch__label">{{ t('sharing.batch.selected') }}</span>
    </div>
    <div class="shared-batch__actions">
      <Button variant="primary" @click="$emit('accept')">{{ t('sharing.batch.acceptSelected') }}</Button>
      <Button variant="ghost" @click="$emit('clear')">{{ t('sharing.batch.clear') }}</Button>
    </div>
  </div>
</template>

<style scoped>
.shared-batch {
  display: flex; align-items: center; justify-content: space-between;
  gap: 16px;
  padding: 8px 12px;
  background: rgb(var(--ac-rgb) / 0.10);
  border: 1px solid var(--ac);
  color: var(--text-primary);
}
.shared-batch__count {
  display: inline-flex; align-items: baseline; gap: 8px;
}
.shared-batch__label {
  color: var(--text-dim);
  font-family: var(--font-mono);
  font-size: 11px;
  letter-spacing: 0.18em;
}
.shared-batch__actions {
  display: inline-flex; align-items: center; gap: 6px;
}
</style>
