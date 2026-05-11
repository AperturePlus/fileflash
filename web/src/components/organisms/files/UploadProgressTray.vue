<script setup lang="ts">
import { Bar, Text } from '../../atoms';
import { useLocaleStore } from '../../../store/locale';

export interface UploadTaskView {
  id: string | number;
  name: string;
  progress: { percentage: number };
}

defineProps<{ tasks: UploadTaskView[] }>();

const localeStore = useLocaleStore();
const t = localeStore.t;
</script>

<template>
  <section v-if="tasks.length > 0" class="tray">
    <header class="tray__head">
      <Text variant="label">{{ t('files.upload.queueTitle') }} — {{ tasks.length }}</Text>
    </header>
    <div class="tray__rows">
      <div v-for="task in tasks" :key="task.id" class="tray__row">
        <span class="tray__name">{{ task.name }}</span>
        <div class="tray__track">
          <Bar :value="task.progress.percentage / 100" />
        </div>
        <span class="tray__pct">{{ task.progress.percentage }}%</span>
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
  grid-template-columns: minmax(160px, 240px) 1fr 56px;
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
</style>
