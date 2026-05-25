<script setup lang="ts">
import { computed, ref } from 'vue';
import useAgentSession, {
  type AgentTurn,
  type ChatMessage,
} from '../../../composables/useAgentSession';
import SessionList from '../../../components/organisms/agent/SessionList.vue';
import TaskTimeline from '../../../components/organisms/agent/TaskTimeline.vue';
import TaskInputDock from '../../../components/organisms/agent/TaskInputDock.vue';
import PlanInspector from '../../../components/organisms/agent/PlanInspector.vue';

const {
  sessions, activeSessionId, activeTurns, policy, taskInput, isSending,
  createSession, switchSession, deleteSession,
  sendMessage, runExecute, cancel,
} = useAgentSession();

const focusedTurnId = ref<string | null>(null);

const focusedTurn = computed<AgentTurn | null>(() =>
  activeTurns.value.find((t) => t.agent.id === focusedTurnId.value) ?? null,
);

const turnOf = (id: string): ChatMessage | null =>
  activeTurns.value.find((t) => t.agent.id === id)?.agent ?? null;

const onExecute = (id: string) => { const m = turnOf(id); if (m) runExecute(m); };
const onCancel  = (id: string) => { const m = turnOf(id); if (m) cancel(m); };
const onHint = (text: string) => { taskInput.value = text; sendMessage(); };
</script>

<template>
  <div class="aw">
    <SessionList
      class="aw__left"
      :sessions="sessions"
      :active-id="activeSessionId"
      @select="switchSession"
      @create="createSession"
      @delete="deleteSession"
    />
    <div class="aw__center">
      <TaskTimeline
        :turns="activeTurns"
        :policy="policy"
        :focused-id="focusedTurnId"
        @execute="onExecute"
        @cancel="onCancel"
        @focus-turn="focusedTurnId = $event"
        @hint-pick="onHint"
      />
      <TaskInputDock
        v-model="taskInput"
        :policy="policy"
        :disabled="isSending"
        @update:policy="policy = $event"
        @submit="sendMessage"
      />
    </div>
    <PlanInspector class="aw__right" :turn="focusedTurn" />
  </div>
</template>

<style scoped>
.aw {
  display: grid;
  grid-template-columns: 240px 1fr 320px;
  width: 100%;
  height: 100%;
  min-height: 0;
  min-width: 0;
  overflow: hidden;
  background: var(--surface-base);
  position: relative;
}
.aw__left { min-height: 0; min-width: 0; }
.aw__center {
  display: flex; flex-direction: column;
  min-height: 0;
  min-width: 0;
  overflow: hidden;
  border-right: 1px solid var(--border-default);
}
.aw__right { min-height: 0; min-width: 0; }

@media (max-width: 1280px) {
  .aw { grid-template-columns: 240px 1fr; }
  .aw__right {
    position: absolute; right: 0; top: 0; bottom: 0;
    width: 320px;
    z-index: 50;
    transform: translateX(100%);
    transition: transform var(--mo-duration-mid) var(--mo-easing);
    background: var(--surface-base);
    border-left: 1px solid var(--border-default);
  }
  .aw:has(.is-focused) .aw__right { transform: translateX(0); }
}

@media (prefers-reduced-motion: reduce) {
  .aw__right { transition: none; }
}
</style>
