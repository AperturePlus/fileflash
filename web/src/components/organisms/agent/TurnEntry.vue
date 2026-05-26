<script setup lang="ts">
import { computed } from 'vue';
import Button from '../../molecules/Button.vue';
import MonoNumber from '../../atoms/MonoNumber.vue';
import PlanActionRow from './PlanActionRow.vue';
import { useLocaleStore } from '../../../store/locale';
import type { LocaleKey } from '../../../i18n/messages';
import type { AgentExecutionPolicy } from '../../../types/agent';
import type { AgentTurn } from '../../../composables/useAgentSession';

const props = defineProps<{
  turn: AgentTurn;
  policy: AgentExecutionPolicy;
  focused: boolean;
}>();

defineEmits<{ execute: []; cancel: []; focus: [] }>();

const localeStore = useLocaleStore();
const t = localeStore.t;

const canExecute = computed(
  () =>
    Boolean(props.turn.agent.planHash) &&
    props.turn.agent.status === 'succeeded' &&
    props.policy !== 'planOnly' &&
    !props.turn.agent.executeJobId,
);

const isActive = computed(
  () => props.turn.agent.status === 'pending' || props.turn.agent.status === 'running',
);

const resultText = computed(
  () => props.turn.agent.executeResult?.answer || props.turn.agent.executeResult?.summary || '',
);

const activityEvents = computed(() =>
  (props.turn.agent.events || [])
    .filter((event) => event.message && !event.type.startsWith('job.succeeded'))
    .slice(-4),
);

const statusLabel = computed(() => {
  const key = `agent.v2.turn.status.${props.turn.agent.status}` as LocaleKey;
  return t(key);
});

const formatTime = (iso: string) => {
  try {
    return new Date(iso).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  } catch {
    return '';
  }
};
</script>

<template>
  <Transition name="ff-te" appear>
    <div class="ff-te" @click="$emit('focus')">
      <!-- user row -->
      <div class="ff-te__user">
        <div class="ff-te__user-card">
          <span class="ff-te__user-content">{{ turn.user.content }}</span>
          <span class="ff-te__user-time">{{ formatTime(turn.user.timestamp) }}</span>
        </div>
      </div>

      <!-- agent row -->
      <div class="ff-te__agent" :class="{ 'is-focused': focused, 'is-active': isActive }">
        <header class="ff-te__agent-head">
          <span class="ff-te__role">{{ t('agent.v2.turn.role') }}</span>
          <span class="ff-te__status" :class="`ff-te__status--${turn.agent.status}`">{{
            statusLabel
          }}</span>
        </header>

        <div v-if="isActive" class="ff-te__progress" />

        <ol v-if="activityEvents.length" class="ff-te__events">
          <li v-for="event in activityEvents" :key="event.id" class="ff-te__event">
            <span class="ff-te__event-dot" />
            <span>{{ event.message }}</span>
          </li>
        </ol>

        <p v-if="resultText" class="ff-te__sum ff-te__answer">
          {{ resultText }}
        </p>

        <p v-else-if="turn.agent.planResult?.summary" class="ff-te__sum">
          {{ turn.agent.planResult.summary }}
        </p>

        <section v-if="!resultText && turn.agent.planResult?.proposedActions?.length" class="ff-te__actions">
          <PlanActionRow
            v-for="a in turn.agent.planResult.proposedActions"
            :key="a.step"
            :action="a"
          />
        </section>

        <div v-if="turn.agent.planResult?.costEstimate" class="ff-te__cost">
          <span class="ff-te__cost-label">{{ t('agent.v2.turn.cost.label') }}</span>
          <span class="ff-te__cost-item">
            {{ t('agent.v2.turn.cost.tokens') }} <MonoNumber :value="turn.agent.planResult.costEstimate.tokens" />
          </span>
          <span class="ff-te__cost-item">
            {{ t('agent.v2.turn.cost.calls') }} <MonoNumber :value="turn.agent.planResult.costEstimate.toolCalls" />
          </span>
          <span class="ff-te__cost-item">
            {{ t('agent.v2.turn.cost.est') }} <MonoNumber :value="`${turn.agent.planResult.costEstimate.durationSecEstimate}s`" />
          </span>
        </div>

        <div v-if="turn.agent.executeResult?.warnings?.length" class="ff-te__warn">
          <span class="ff-te__warn-label">{{ t('agent.v2.turn.warn.label') }}</span>
          <ul>
            <li v-for="(w, i) in turn.agent.executeResult.warnings" :key="i">{{ w }}</li>
          </ul>
        </div>

        <div v-if="turn.agent.errorMessage" class="ff-te__err">{{ turn.agent.errorMessage }}</div>

        <div v-if="canExecute || isActive" class="ff-te__row">
          <Button
            v-if="canExecute"
            variant="primary"
            size="sm"
            @click.stop="$emit('execute')"
          >{{ t('agent.v2.turn.execute') }}</Button>
          <Button
            v-if="isActive"
            variant="ghost"
            size="sm"
            @click.stop="$emit('cancel')"
          >{{ t('agent.v2.turn.cancel') }}</Button>
        </div>
      </div>
    </div>
  </Transition>
</template>

<style scoped>
.ff-te {
  display: flex; flex-direction: column; gap: var(--sp-md);
  padding: var(--sp-md) var(--sp-lg);
  border-bottom: 1px solid var(--border-default);
  cursor: pointer;
}

.ff-te__user { display: flex; justify-content: flex-end; }
.ff-te__user-card {
  display: flex; flex-direction: column; gap: 4px;
  max-width: 75%;
  padding: var(--sp-sm) var(--sp-md);
  background: var(--surface-raised);
  border: 1px solid var(--border-default);
  border-radius: 0;
}
.ff-te__user-content { white-space: pre-wrap; color: var(--text-primary); }
.ff-te__user-time {
  align-self: flex-end;
  font-family: var(--font-mono); font-size: var(--text-small);
  color: var(--text-tertiary); letter-spacing: var(--tracking-wide);
}

.ff-te__agent {
  display: flex; flex-direction: column; gap: var(--sp-sm);
  padding: var(--sp-md);
  background: var(--surface-raised);
  border: 1px solid var(--border-default);
  border-radius: 0;
  transition: outline var(--mo-duration-fast) var(--mo-easing);
}
.ff-te__agent.is-focused { outline: 1px solid var(--ac); outline-offset: -1px; }

.ff-te__agent-head { display: flex; align-items: center; justify-content: space-between; }
.ff-te__role {
  font-family: var(--font-mono); font-size: var(--text-small);
  text-transform: uppercase; letter-spacing: var(--tracking-wide);
  color: var(--text-tertiary);
}
.ff-te__status {
  font-family: var(--font-mono); font-size: var(--text-small);
  text-transform: uppercase; letter-spacing: var(--tracking-wide);
}
.ff-te__status--pending, .ff-te__status--running { color: var(--ac); }
.ff-te__status--succeeded { color: var(--status-success); }
.ff-te__status--failed { color: var(--status-error); }
.ff-te__status--canceled { color: var(--text-tertiary); }

.ff-te__progress {
  height: 2px;
  background: linear-gradient(90deg, transparent, var(--ac), transparent);
  background-size: 200% 100%;
  animation: ff-te-progress 1.2s linear infinite;
}
@keyframes ff-te-progress {
  0% { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}

.ff-te__sum { margin: 0; color: var(--text-primary); }
.ff-te__answer { white-space: pre-wrap; }

.ff-te__events {
  display: flex;
  flex-direction: column;
  gap: 4px;
  margin: 0;
  padding: 0;
  list-style: none;
}
.ff-te__event {
  display: flex;
  align-items: center;
  gap: 8px;
  min-height: 18px;
  font-family: var(--font-mono);
  font-size: var(--text-small);
  color: var(--text-tertiary);
}
.ff-te__event-dot {
  width: 5px;
  height: 5px;
  background: var(--ac);
  flex: 0 0 auto;
}

.ff-te__actions {
  border: 1px solid var(--border-subtle);
  border-bottom: 0;
}

.ff-te__cost {
  display: flex; gap: var(--sp-md); align-items: baseline;
  font-family: var(--font-mono); font-size: var(--text-small);
  letter-spacing: var(--tracking-wide); text-transform: uppercase;
  color: var(--text-tertiary);
}
.ff-te__cost-label { color: var(--text-tertiary); }
.ff-te__cost-item { display: inline-flex; gap: 6px; align-items: baseline; color: var(--text-secondary); }

.ff-te__warn, .ff-te__err {
  padding: var(--sp-sm) var(--sp-md);
  border: 1px solid;
}
.ff-te__warn { border-color: var(--status-warning); color: var(--status-warning); }
.ff-te__warn-label {
  font-family: var(--font-mono); font-size: var(--text-small);
  letter-spacing: var(--tracking-wide); text-transform: uppercase;
}
.ff-te__warn ul { margin: 4px 0 0; padding-left: 16px; }
.ff-te__err { border-color: var(--status-error); color: var(--status-error); }

.ff-te__row { display: flex; gap: var(--sp-sm); justify-content: flex-end; }

.ff-te-enter-active { transition: opacity 220ms var(--mo-easing), transform 220ms var(--mo-easing); }
.ff-te-enter-from { opacity: 0; transform: translateY(4px); }

@media (prefers-reduced-motion: reduce) {
  .ff-te__progress { animation: none; background: var(--ac); }
  .ff-te-enter-active { transition: none; }
}
</style>
