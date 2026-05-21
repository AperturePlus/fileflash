<script setup lang="ts">
import IconButton from '../../molecules/IconButton.vue';
import SessionItem from './SessionItem.vue';
import type { Session } from '../../../composables/useAgentSession';

defineProps<{ sessions: Session[]; activeId: string | null }>();
defineEmits<{
  select: [id: string];
  create: [];
  delete: [id: string];
}>();
</script>

<template>
  <aside class="ff-sl">
    <header class="ff-sl__head">
      <span class="ff-sl__label">SESSIONS</span>
      <IconButton icon="plus" label="New session" size="sm" @click="$emit('create')" />
    </header>
    <div v-if="sessions.length" class="ff-sl__list">
      <SessionItem
        v-for="s in sessions"
        :key="s.id"
        :session="s"
        :active="s.id === activeId"
        @select="$emit('select', s.id)"
        @delete="$emit('delete', s.id)"
      />
    </div>
    <div v-else class="ff-sl__empty">No sessions yet.</div>
  </aside>
</template>

<style scoped>
.ff-sl {
  display: flex; flex-direction: column;
  width: 240px;
  height: 100%;
  border-right: 1px solid var(--border-default);
  background: var(--surface-base);
}
.ff-sl__head {
  display: flex; align-items: center; justify-content: space-between;
  height: 40px;
  padding: 0 var(--sp-md);
  border-bottom: 1px solid var(--border-default);
}
.ff-sl__label {
  font-family: var(--font-mono);
  font-size: var(--text-label);
  letter-spacing: var(--tracking-wide);
  text-transform: uppercase;
  color: var(--text-tertiary);
}
.ff-sl__list { flex: 1; overflow-y: auto; }
.ff-sl__empty {
  padding: var(--sp-lg) var(--sp-md);
  color: var(--text-tertiary);
  font-family: var(--font-mono);
  font-size: var(--text-label);
  letter-spacing: var(--tracking-wide);
  text-transform: uppercase;
  text-align: center;
}
</style>
