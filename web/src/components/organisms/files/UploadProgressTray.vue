<script setup lang="ts">
import { Bar, Text } from '../../atoms';
import { useLocaleStore } from '../../../store/locale';

type UploadTaskStatus = 'hashing' | 'uploading' | 'succeeded' | 'failed' | 'canceled';

export interface UploadTaskView {
  id: string | number;
  name: string;
  progress: { percentage: number };
  status?: UploadTaskStatus;
  isCanceling?: boolean;
}

const props = defineProps<{ tasks: UploadTaskView[] }>();
const emit = defineEmits<{
  (event: 'cancel', taskId: string | number): void;
}>();

const localeStore = useLocaleStore();
const t = localeStore.t;

const isTerminalStatus = (status: UploadTaskStatus | undefined) =>
  status === 'succeeded' || status === 'failed' || status === 'canceled';

const getStatusLabel = (task: UploadTaskView) => {
  if (task.isCanceling) return t('files.upload.state.canceling');
  switch (task.status) {
    case 'hashing':
      return t('files.upload.state.hashing');
    case 'failed':
      return t('files.upload.state.failed');
    case 'canceled':
      return t('files.upload.state.canceled');
    case 'succeeded':
      return t('files.upload.state.succeeded');
    default:
      return t('files.upload.state.uploading');
  }
};
</script>

<template>
  <section v-if="props.tasks.length > 0" class="tray">
    <header class="tray__head">
      <Text variant="label">{{ t('files.upload.queueTitle') }} — {{ props.tasks.length }}</Text>
    </header>
    <div class="tray__rows">
      <div v-for="task in props.tasks" :key="task.id" class="tray__row">
        <span class="tray__name">{{ task.name }}</span>
        <div class="tray__track">
          <Bar :value="task.progress.percentage / 100" />
        </div>
        <span class="tray__pct">{{ task.progress.percentage }}%</span>
        <button
          v-if="!isTerminalStatus(task.status)"
          class="tray__cancel"
          :disabled="task.isCanceling"
          @click="emit('cancel', task.id)"
        >
          {{ task.isCanceling ? t('files.upload.state.canceling') : t('files.upload.action.cancel') }}
        </button>
        <span v-else class="tray__state">{{ getStatusLabel(task) }}</span>
      </div>
    </div>
  </section>
</template>

<style scoped>
.tray {
  border: 1px solid var(--border-default);
  background: var(--surface-raised);
  padding: 12px 16px;
}
.tray__head { margin-bottom: 8px; }
.tray__rows { display: flex; flex-direction: column; gap: 6px; }
.tray__row {
  display: grid;
  grid-template-columns: minmax(160px, 240px) 1fr 56px 96px;
  align-items: center;
  gap: 12px;
}
.tray__name {
  font-family: var(--font-mono);
  font-size: 12px;
  color: var(--text-secondary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.tray__track {
  height: 4px;
  background: var(--surface-inset);
  position: relative;
}
.tray__pct {
  font-family: var(--font-mono);
  font-feature-settings: "tnum";
  font-size: 12px;
  color: var(--text-secondary);
  text-align: right;
}
.tray__cancel {
  border: 1px solid var(--border-default);
  background: transparent;
  color: var(--text-secondary);
  border-radius: var(--radius-sm);
  height: 24px;
  padding: 0 8px;
  cursor: pointer;
  font-size: 11px;
}
.tray__cancel:hover:not(:disabled) {
  color: var(--text-primary);
  border-color: var(--text-secondary);
}
.tray__cancel:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}
.tray__state {
  font-size: 11px;
  color: var(--text-dim);
  text-align: right;
}
</style>
