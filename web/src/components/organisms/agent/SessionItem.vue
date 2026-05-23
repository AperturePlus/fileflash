<script setup lang="ts">
import IconButton from '../../molecules/IconButton.vue';
import { useLocaleStore } from '../../../store/locale';
import type { Session } from '../../../composables/useAgentSession';

defineProps<{ session: Session; active: boolean }>();
defineEmits<{ select: []; delete: [] }>();

const localeStore = useLocaleStore();
const t = localeStore.t;

const formatRelativeUnit = (key:
  | 'agent.v2.sessions.relative.minutes'
  | 'agent.v2.sessions.relative.hours'
  | 'agent.v2.sessions.relative.days', value: number) =>
  t(key).replace('{value}', String(value));

const relativeTime = (iso: string): string => {
  const diff = Date.now() - new Date(iso).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return t('agent.v2.sessions.relative.justNow');
  if (mins < 60) return formatRelativeUnit('agent.v2.sessions.relative.minutes', mins);
  const hours = Math.floor(mins / 60);
  if (hours < 24) return formatRelativeUnit('agent.v2.sessions.relative.hours', hours);
  const days = Math.floor(hours / 24);
  return formatRelativeUnit('agent.v2.sessions.relative.days', days);
};
</script>

<template>
  <div class="ff-si" :class="{ 'is-active': active }" @click="$emit('select')">
    <div class="ff-si__main">
      <span class="ff-si__title">{{ session.title }}</span>
      <span class="ff-si__time">{{ relativeTime(session.updatedAt) }}</span>
    </div>
    <IconButton
      icon="trash"
      :label="t('agent.v2.sessions.delete')"
      size="sm"
      class="ff-si__del"
      @click.stop="$emit('delete')"
    />
  </div>
</template>

<style scoped>
.ff-si {
  display: flex; align-items: center; justify-content: space-between;
  gap: var(--sp-sm);
  padding: var(--sp-sm) var(--sp-md);
  border-bottom: 1px solid var(--border-default);
  cursor: pointer;
  color: var(--text-secondary);
  border-left: 2px solid transparent;
  transition: background var(--mo-duration-fast) var(--mo-easing),
              color var(--mo-duration-fast) var(--mo-easing);
}
.ff-si:hover { background: var(--surface-inset); color: var(--text-primary); }
.ff-si.is-active { border-left-color: var(--ac); color: var(--text-primary); background: var(--surface-inset); }

.ff-si__main {
  display: flex; flex-direction: column; gap: 2px;
  flex: 1 1 auto; min-width: 0;
}
.ff-si__title {
  font-size: var(--text-body);
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
.ff-si__time {
  font-family: var(--font-mono); font-size: var(--text-label);
  color: var(--text-tertiary);
  letter-spacing: var(--tracking-wide);
}
.ff-si__del { opacity: 0; transition: opacity var(--mo-duration-fast) var(--mo-easing); }
.ff-si:hover .ff-si__del { opacity: 1; }
.ff-si.is-active .ff-si__del { opacity: 0.6; }
</style>
