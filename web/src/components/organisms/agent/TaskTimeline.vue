<script setup lang="ts">
import { computed, nextTick, ref, watch } from 'vue';
import TurnEntry from './TurnEntry.vue';
import { useLocaleStore } from '../../../store/locale';
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
  reply: [id: string, value: unknown];
  pause: [id: string];
  resume: [id: string];
  skip: [id: string];
  approve: [id: string];
  deny: [id: string];
  'focus-turn': [id: string];
  'hint-pick': [text: string];
}>();

const localeStore = useLocaleStore();
const t = localeStore.t;

const hints = computed(() => [
  t('agent.v2.timeline.hint.organize'),
  t('agent.v2.timeline.hint.duplicates'),
  t('agent.v2.timeline.hint.tagInvoices'),
]);

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
    <header class="ff-tt__label">{{ t('agent.v2.timeline.label') }}</header>
    <div v-if="!turns.length" class="ff-tt__welcome">
      <p class="ff-tt__hint">{{ t('agent.v2.timeline.welcomeHint') }}</p>
      <div class="ff-tt__chips">
        <button
          v-for="h in hints"
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
      v-for="turn in turns"
      :key="turn.agent.id"
      :turn="turn"
      :policy="policy"
      :focused="turn.agent.id === focusedId"
      @execute="$emit('execute', turn.agent.id)"
      @cancel="$emit('cancel', turn.agent.id)"
      @reply="(value) => $emit('reply', turn.agent.id, value)"
      @pause="$emit('pause', turn.agent.id)"
      @resume="$emit('resume', turn.agent.id)"
      @skip="$emit('skip', turn.agent.id)"
      @approve="$emit('approve', turn.agent.id)"
      @deny="$emit('deny', turn.agent.id)"
      @focus="$emit('focus-turn', turn.agent.id)"
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
  font-family: var(--font-mono); font-size: var(--text-small);
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
  font-size: var(--text-small);
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
