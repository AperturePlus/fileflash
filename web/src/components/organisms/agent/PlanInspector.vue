<script setup lang="ts">
import { computed, ref } from 'vue';
import StatBlock from '../../molecules/StatBlock.vue';
import { useLocaleStore } from '../../../store/locale';
import { useUserStore } from '../../../store/user';
import type { AgentTurn } from '../../../composables/useAgentSession';

const props = defineProps<{ turn?: AgentTurn | null }>();

const localeStore = useLocaleStore();
const t = localeStore.t;
const userStore = useUserStore();
const isAdmin = computed(() => userStore.isAdmin);

const plan = computed(() => props.turn?.agent.planResult ?? null);
const skillName = computed(() => plan.value?.chosenSkill?.name ?? '—');
const planHash = computed(() => plan.value?.planHash ?? '');
const actions = computed(() => plan.value?.proposedActions.length ?? 0);
const warnings = computed(() => props.turn?.agent.executeResult?.warnings.length ?? 0);
const cost = computed(() => plan.value?.costEstimate ?? null);

const copied = ref(false);
const copyHash = async () => {
  if (!planHash.value) return;
  try {
    await navigator.clipboard?.writeText(planHash.value);
    copied.value = true;
    setTimeout(() => (copied.value = false), 1200);
  } catch {
    // ignore
  }
};
</script>

<template>
  <aside class="ff-pi">
    <header class="ff-pi__label">{{ t('agent.v2.inspector.label') }}</header>
    <div v-if="!turn" class="ff-pi__empty">{{ t('agent.v2.inspector.empty') }}</div>
    <div v-else class="ff-pi__body">
      <section class="ff-pi__sect">
        <span class="ff-pi__key">{{ t('agent.v2.inspector.skill') }}</span>
        <span class="ff-pi__val">{{ skillName }}</span>
      </section>
      <section v-if="isAdmin" class="ff-pi__sect">
        <span class="ff-pi__key">{{ t('agent.v2.inspector.planHash') }}</span>
        <button
          type="button"
          class="ff-pi__hash"
          :title="planHash || ''"
          :disabled="!planHash"
          @click="copyHash"
        >
          {{ planHash || '—' }}
          <span v-if="copied" class="ff-pi__copied">{{ t('agent.v2.inspector.copied') }}</span>
        </button>
      </section>

      <section v-if="cost" class="ff-pi__cost">
        <StatBlock :label="t('agent.v2.inspector.tokens')" :value="cost.tokens" />
        <StatBlock :label="t('agent.v2.inspector.calls')" :value="cost.toolCalls" />
        <StatBlock :label="t('agent.v2.inspector.estSec')" :value="cost.durationSecEstimate" />
      </section>

      <section class="ff-pi__sect">
        <span class="ff-pi__key">{{ t('agent.v2.inspector.actions') }}</span>
        <span class="ff-pi__val">{{ actions }}</span>
      </section>
      <section class="ff-pi__sect">
        <span class="ff-pi__key">{{ t('agent.v2.inspector.warnings') }}</span>
        <span class="ff-pi__val">{{ warnings }}</span>
      </section>
    </div>
  </aside>
</template>

<style scoped>
.ff-pi {
  display: flex; flex-direction: column;
  width: 320px;
  height: 100%;
  border-left: 1px solid var(--border-default);
  background: var(--surface-base);
  overflow-y: auto;
}
.ff-pi__label {
  padding: var(--sp-sm) var(--sp-lg);
  border-bottom: 1px solid var(--border-default);
  font-family: var(--font-mono); font-size: var(--text-small);
  letter-spacing: var(--tracking-wide); text-transform: uppercase;
  color: var(--text-tertiary);
}
.ff-pi__empty {
  padding: var(--sp-xl) var(--sp-lg);
  color: var(--text-tertiary);
  font-family: var(--font-mono); font-size: var(--text-small);
  letter-spacing: var(--tracking-wide); text-transform: uppercase;
  text-align: center;
}
.ff-pi__body { padding: var(--sp-lg); display: flex; flex-direction: column; gap: var(--sp-md); }
.ff-pi__sect { display: flex; flex-direction: column; gap: 2px; }
.ff-pi__key {
  font-family: var(--font-mono); font-size: var(--text-small);
  letter-spacing: var(--tracking-wide); text-transform: uppercase;
  color: var(--text-tertiary);
}
.ff-pi__val {
  font-family: var(--font-mono); font-size: var(--text-body);
  color: var(--text-primary);
}
.ff-pi__hash {
  text-align: left;
  background: var(--surface-inset);
  border: 1px solid var(--border-default);
  border-radius: 0;
  padding: var(--sp-xs) var(--sp-sm);
  color: var(--text-primary);
  font-family: var(--font-mono); font-size: var(--text-small);
  cursor: pointer;
  overflow: hidden; text-overflow: ellipsis;
  display: flex; justify-content: space-between; align-items: center; gap: var(--sp-sm);
}
.ff-pi__hash:disabled { opacity: 0.5; cursor: not-allowed; }
.ff-pi__hash:hover:not(:disabled) { border-color: var(--ac); }
.ff-pi__copied {
  font-size: var(--text-small); color: var(--ac);
  letter-spacing: var(--tracking-wide);
}
.ff-pi__cost {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: var(--sp-sm);
  padding-block: var(--sp-sm);
  border-block: 1px solid var(--border-subtle);
}
</style>
