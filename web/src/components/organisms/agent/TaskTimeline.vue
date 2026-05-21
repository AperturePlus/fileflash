<script setup lang="ts">
import { nextTick, ref, watch } from 'vue';
import TurnEntry from './TurnEntry.vue';
import type { AgentExecutionPolicy } from '../../../types/agent';
import type { AgentTurn } from '../../../composables/useAgentSession';

const props = defineProps<{
  turns: AgentTurn[];
  policy: AgentExecutionPolicy;
  focusedId?: string | null;
}>();

defineEmits<{
  execute: [id: string];
  cancel: [id: string];
  'focus-turn': [id: string];
  'hint-pick': [text: string];
}>();

const HINTS = [
  'Organize my screenshots into folders by date',
  'Find duplicates across my photo library',
  'Tag invoices and move them under /finance',
];

const scrollEl = ref<HTMLElement | null>(null);

watch(
  () => props.turns.length,
  async () => {
    await nextTick();
    if (scrollEl.value) scrollEl.value.scrollTop = scrollEl.value.scrollHeight;
  },
);
</script>

<template>
  <div ref="scrollEl" class="ff-tt">
    <header class="ff-tt__label">TIMELINE</header>
    <div v-if="!turns.length" class="ff-tt__welcome">
      <p class="ff-tt__hint">Type a task below to get started.</p>
      <div class="ff-tt__chips">
        <button
          v-for="h in HINTS"
          :key="h"
          type="button"
          class="ff-tt__chip"
          @click="$emit('hint-pick', h)"
        >
          {{ h }}
        </button>
      </div>
    </div>
    <TurnEntry
      v-for="t in turns"
      :key="t.agent.id"
      :turn="t"
      :policy="policy"
      :focused="t.agent.id === focusedId"
      @execute="$emit('execute', t.agent.id)"
      @cancel="$emit('cancel', t.agent.id)"
      @focus="$emit('focus-turn', t.agent.id)"
    />
  </div>
</template>

<style scoped>
.ff-tt {
  flex: 1 1 auto;
  overflow-y: auto;
  background: var(--surface-base);
}
.ff-tt__label {
  position: sticky; top: 0; z-index: 1;
  padding: var(--sp-sm) var(--sp-lg);
  background: var(--surface-base);
  border-bottom: 1px solid var(--border-default);
  font-family: var(--font-mono); font-size: var(--text-label);
  letter-spacing: var(--tracking-wide); text-transform: uppercase;
  color: var(--text-tertiary);
}
.ff-tt__welcome {
  padding: var(--sp-xl) var(--sp-lg);
  display: flex; flex-direction: column; gap: var(--sp-lg);
}
.ff-tt__hint {
  margin: 0;
  font-family: var(--font-mono);
  font-size: var(--text-label);
  letter-spacing: var(--tracking-wide);
  text-transform: uppercase;
  color: var(--text-tertiary);
}
.ff-tt__chips {
  display: flex; flex-direction: column; gap: var(--sp-sm);
}
.ff-tt__chip {
  text-align: left;
  padding: var(--sp-sm) var(--sp-md);
  background: var(--surface-raised);
  color: var(--text-secondary);
  border: 1px solid var(--border-default);
  border-radius: 0;
  cursor: pointer;
  font-family: var(--font-sans);
  font-size: var(--text-body);
  transition: border-color var(--mo-duration-fast) var(--mo-easing),
              color var(--mo-duration-fast) var(--mo-easing);
}
.ff-tt__chip:hover { border-color: var(--ac); color: var(--text-primary); }
</style>
