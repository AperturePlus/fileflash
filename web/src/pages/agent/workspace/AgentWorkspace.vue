<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, ref } from 'vue';
import {
  NAlert,
  NButton,
  NDivider,
  NInput,
  NPopconfirm,
  NSelect,
  NSpin,
  NTag,
  useMessage,
} from 'naive-ui';
import { cancelAgentJob, executeAgentPlan, getAgentJob, planAgentTask } from '../../../api/agent';
import { useLocaleStore } from '../../../store/locale';
import { useUserStore } from '../../../store/user';
import type {
  AgentExecutionPolicy,
  AgentExecutionResult,
  AgentPlanResult,
  PlanAgentRequest,
} from '../../../types/agent';

const localeStore = useLocaleStore();
const userStore = useUserStore();
const t = localeStore.t;
const message = useMessage();

// —— conversation model ——
type MsgStatus = 'pending' | 'running' | 'succeeded' | 'failed' | 'canceled';

interface ChatMessage {
  id: string;
  role: 'user' | 'agent';
  content: string;
  status: MsgStatus;
  planJobId?: string;
  planHash?: string;
  planResult?: AgentPlanResult;
  executeJobId?: string;
  executeResult?: AgentExecutionResult;
  errorMessage?: string;
  timestamp: string;
}

interface Conversation {
  id: string;
  title: string;
  messages: ChatMessage[];
  createdAt: string;
  updatedAt: string;
}

const conversations = ref<Conversation[]>([]);
const activeConversationId = ref<string | null>(null);
const taskInput = ref('');
const isSending = ref(false);
const isPromptFocused = ref(false);

// —— settings ——
const executionPolicy = ref<AgentExecutionPolicy>('confirm');

const executionPolicyOptions = [
  { label: '仅规划', value: 'planOnly' as const },
  { label: '确认后执行', value: 'confirm' as const },
  { label: '自动执行', value: 'autopilot' as const },
];

// —— polling timers ——
const pollTimers = new Map<string, ReturnType<typeof setInterval>>();

// —— refs ——
const chatMessagesEl = ref<HTMLElement | null>(null);

// —— helpers ——
let msgCounter = 0;
const nextMsgId = () => `msg-${Date.now()}-${++msgCounter}`;

const isTerminalStatus = (s?: string | null) =>
  s === 'succeeded' || s === 'failed' || s === 'canceled';

const sideEffectTagType = (se: string) => (se === 'write' ? 'warning' : 'info');

// —— active conversation ——
const activeConversation = computed(() => {
  if (!activeConversationId.value) return null;
  return conversations.value.find((c) => c.id === activeConversationId.value) || null;
});

const activeMessages = computed(() => activeConversation.value?.messages || []);

// —— conversation management ——
const createConversation = () => {
  const id = `conv-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
  const conv: Conversation = {
    id,
    title: '新对话',
    messages: [],
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString(),
  };
  conversations.value.unshift(conv);
  activeConversationId.value = id;
  taskInput.value = '';
  stopAllPolling();
};

const deleteConversation = (id: string) => {
  const idx = conversations.value.findIndex((c) => c.id === id);
  if (idx === -1) return;
  conversations.value.splice(idx, 1);
  if (activeConversationId.value === id) {
    stopAllPolling();
    if (conversations.value.length > 0) {
      activeConversationId.value = conversations.value[Math.min(idx, conversations.value.length - 1)].id;
    } else {
      activeConversationId.value = null;
    }
  }
};

const switchConversation = (id: string) => {
  if (activeConversationId.value === id) return;
  stopAllPolling();
  activeConversationId.value = id;
  taskInput.value = '';
};

const ensureConversation = () => {
  if (!activeConversation.value) {
    createConversation();
  }
};

// —— auto-scroll ——
const scrollToBottom = async () => {
  await nextTick();
  const el = chatMessagesEl.value;
  if (el) el.scrollTop = el.scrollHeight;
};

// —— poll a job & update the agent message ——
const pollJob = async (
  msg: ChatMessage,
  jobId: string,
  kind: 'plan' | 'execute',
) => {
  const timerKey = `${msg.id}:${kind}`;
  stopPolling(timerKey);

  const tick = async () => {
    try {
      const job = kind === 'plan'
        ? await getAgentJob<AgentPlanResult>(jobId)
        : await getAgentJob<AgentExecutionResult>(jobId);

      msg.status = (job.status as MsgStatus) || 'running';

      if (job.status === 'succeeded') {
        if (kind === 'plan') {
          msg.planResult = job.result;
          msg.planHash = job.result?.planHash;
        } else {
          msg.executeResult = job.result;
        }
      }
      if (job.status === 'failed' || job.status === 'canceled') {
        msg.errorMessage = job.errorMessage || t('agent.errors.planFailed');
      }
      if (isTerminalStatus(job.status)) {
        stopPolling(timerKey);
        if (kind === 'plan' && msg.planResult && executionPolicy.value === 'autopilot') {
          autoExecute(msg);
        }
      }
    } catch {
      // ignore polling errors
    }
  };

  await tick();
  if (!isTerminalStatus(msg.status)) {
    pollTimers.set(timerKey, setInterval(tick, 1200));
  }
  await scrollToBottom();
};

const stopPolling = (key: string) => {
  const t = pollTimers.get(key);
  if (t) { clearInterval(t); pollTimers.delete(key); }
};

const stopAllPolling = () => {
  pollTimers.forEach((t) => clearInterval(t));
  pollTimers.clear();
};

onBeforeUnmount(() => stopAllPolling());

// —— send: POST /agent/plan ——
const sendMessage = async () => {
  const input = taskInput.value.trim();
  if (!input || isSending.value) return;
  ensureConversation();
  const conv = activeConversation.value!;
  isSending.value = true;

  const userMsg: ChatMessage = {
    id: nextMsgId(),
    role: 'user',
    content: input,
    status: 'succeeded',
    timestamp: new Date().toISOString(),
  };

  const agentMsg: ChatMessage = {
    id: nextMsgId(),
    role: 'agent',
    content: '',
    status: 'pending',
    timestamp: new Date().toISOString(),
  };

  conv.messages.push(userMsg, agentMsg);
  conv.updatedAt = new Date().toISOString();
  // Set title from first user message
  if (conv.title === '新对话') {
    conv.title = input.slice(0, 30) + (input.length > 30 ? '…' : '');
  }
  taskInput.value = '';
  await scrollToBottom();

  // Get reactive proxies from the array (Vue wraps plain objects)
  const reactiveUserMsg = conv.messages[conv.messages.length - 2];
  const reactiveAgentMsg = conv.messages[conv.messages.length - 1];

  // POST /agent/plan
  try {
    const payload = buildPlanPayload(input);
    const res = await planAgentTask(payload);
    reactiveAgentMsg.planJobId = res.jobId;
    reactiveAgentMsg.status = 'pending';
    await pollJob(reactiveAgentMsg, res.jobId, 'plan');
  } catch {
    reactiveAgentMsg.status = 'failed';
    reactiveAgentMsg.errorMessage = t('agent.errors.planFailed');
    message.error(t('agent.errors.planFailed'));
  } finally {
    isSending.value = false;
  }
};

// —— auto-execute (autopilot) ——
const autoExecute = async (msg: ChatMessage) => {
  if (!msg.planResult) return;
  await runExecute(msg);
};

// —— execute: POST /agent/execute ——
const runExecute = async (msg: ChatMessage) => {
  if (!msg.planResult || !msg.planHash) return;
  msg.status = 'running';
  msg.errorMessage = '';
  msg.executeResult = undefined;

  try {
    const res = await executeAgentPlan({
      planJobId: msg.planResult.planJobId,
      planHash: msg.planHash,
      approval: {
        confirmedBy: userStore.user?.userId || 'current-user',
        confirmedAt: new Date().toISOString(),
      },
    });
    msg.executeJobId = res.jobId;
    await pollJob(msg, res.jobId, 'execute');
  } catch {
    msg.status = 'failed';
    msg.errorMessage = t('agent.errors.executeFailed');
    message.error(t('agent.errors.executeFailed'));
  }
  await scrollToBottom();
};

// —— cancel ——
const cancelRunningJob = async (msg: ChatMessage) => {
  const jobId = msg.executeJobId || msg.planJobId;
  if (!jobId) return;
  try {
    await cancelAgentJob(jobId);
    msg.status = 'canceled';
    stopAllPolling();
    message.success(t('agent.actions.cancelled'));
  } catch {
    message.error(t('agent.errors.cancelFailed'));
  }
};

// —— reset current conversation ——
const resetConversation = () => {
  if (!activeConversation.value) return;
  stopAllPolling();
  activeConversation.value.messages = [];
  activeConversation.value.title = '新对话';
  isSending.value = false;
};

// —— build payload ——
const buildPlanPayload = (input: string): PlanAgentRequest => {
  return {
    input,
    context: {
      rootFolderId: 'root',
      selectedFileIds: [],
      selectedFolderIds: [],
      currentPath: '/My Files',
    },
    executionPolicy: executionPolicy.value,
    dataPolicy: {
      allowFileContent: false,
      maxReadBytes: 1048576,
      allowedMimeTypes: ['*/*'],
    },
    hints: {
      preferSkillId: null,
      maxSteps: 12,
      budgetTokens: 8000,
    },
  };
};

// —— keyboard ——
const onKeydown = (e: KeyboardEvent) => {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault();
    sendMessage();
  }
};

// —— msg display helpers ——
const formatTime = (iso: string) => {
  const d = new Date(iso);
  return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
};

const relativeTime = (iso: string) => {
  const diff = Date.now() - new Date(iso).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return '刚刚';
  if (mins < 60) return `${mins} 分钟前`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours} 小时前`;
  const days = Math.floor(hours / 24);
  return `${days} 天前`;
};

const canExecute = (msg: ChatMessage) =>
  Boolean(msg.planHash) && msg.status === 'succeeded' && executionPolicy.value !== 'planOnly';

const isActive = (msg: ChatMessage) =>
  msg.status === 'pending' || msg.status === 'running';
</script>

<template>
  <div class="cursor-chat">
    <!-- sidebar -->
    <aside class="chat-sidebar">
      <div class="sidebar-header">
        <NButton block size="small" type="primary" @click="createConversation">
          <template #icon>
            <svg viewBox="0 0 24 24" width="14" height="14"><path fill="currentColor" d="M19 13h-6v6h-2v-6H5v-2h6V5h2v6h6v2z"/></svg>
          </template>
          新对话
        </NButton>
      </div>
      <div class="sidebar-list">
        <div
          v-for="conv in conversations"
          :key="conv.id"
          class="sidebar-item"
          :class="{ active: conv.id === activeConversationId }"
          @click="switchConversation(conv.id)"
        >
          <div class="sidebar-item-content">
            <span class="sidebar-item-title">{{ conv.title }}</span>
            <span class="sidebar-item-time">{{ relativeTime(conv.updatedAt) }}</span>
          </div>
          <NPopconfirm @positive-click.stop="deleteConversation(conv.id)">
            <template #trigger>
              <button class="sidebar-item-delete" @click.stop aria-label="Delete conversation">
                <svg viewBox="0 0 24 24" width="14" height="14"><path fill="currentColor" d="M6 19c0 1.1.9 2 2 2h8c1.1 0 2-.9 2-2V7H6v12zM19 4h-3.5l-1-1h-5l-1 1H5v2h14V4z"/></svg>
              </button>
            </template>
            删除此对话？
          </NPopconfirm>
        </div>
        <div v-if="!conversations.length" class="sidebar-empty">
          暂无对话记录
        </div>
      </div>
    </aside>

    <!-- main chat -->
    <div class="chat-main">
      <!-- header bar -->
      <div class="chat-topbar">
        <div class="topbar-left">
          <span class="topbar-title">Cloud Agent</span>
          <NTag :type="executionPolicy === 'autopilot' ? 'success' : executionPolicy === 'planOnly' ? 'default' : 'info'" size="small">
            {{ executionPolicyOptions.find(o => o.value === executionPolicy)?.label || executionPolicy }}
          </NTag>
        </div>
        <div class="topbar-right">
          <NButton v-if="activeMessages.length" size="tiny" quaternary @click="resetConversation">
            {{ t('agent.actions.reset') }}
          </NButton>
        </div>
      </div>

      <!-- messages -->
      <div ref="chatMessagesEl" class="chat-messages">
        <!-- empty -->
        <div v-if="!activeConversationId || !activeMessages.length" class="chat-welcome">
          <div class="welcome-icon">
            <svg viewBox="0 0 48 48" width="48" height="48" fill="none">
              <rect x="4" y="8" width="40" height="32" rx="4" stroke="currentColor" stroke-width="2.5"/>
              <circle cx="16" cy="24" r="4" fill="currentColor" opacity="0.5"/>
              <circle cx="32" cy="24" r="4" fill="currentColor" opacity="0.5"/>
              <line x1="20" y1="30" x2="28" y2="30" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
            </svg>
          </div>
          <h2>{{ t('agent.pageTitle') }}</h2>
          <p>{{ t('agent.pageDescription') }}</p>
          <div class="welcome-hints">
            <button
              v-for="hint in ['帮我看看根目录有哪些文件', '按类型整理 Downloads 文件夹', '列出最近修改的图片']"
              :key="hint"
              class="hint-chip"
              @click="taskInput = hint; sendMessage()"
            >{{ hint }}</button>
          </div>
        </div>

        <!-- messages -->
        <div v-for="msg in activeMessages" :key="msg.id" class="chat-turn" :class="{ 'is-active': isActive(msg) }">
          <!-- user message -->
          <div v-if="msg.role === 'user'" class="msg-row msg-row--user">
            <div class="msg-bubble msg-bubble--user">
              <p class="msg-text">{{ msg.content }}</p>
              <span class="msg-time">{{ formatTime(msg.timestamp) }}</span>
            </div>
          </div>

          <!-- agent message -->
          <div v-else class="msg-row msg-row--agent">
            <div class="msg-avatar">
              <svg viewBox="0 0 24 24" width="20" height="20"><path fill="currentColor" d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z"/></svg>
            </div>
            <div class="msg-bubble msg-bubble--agent">
              <!-- thinking -->
              <div v-if="msg.status === 'pending'" class="agent-thinking">
                <NSpin size="small" /> <span>Agent is planning…</span>
              </div>

              <!-- plan result -->
              <template v-if="msg.planResult">
                <p class="plan-summary-text">{{ msg.planResult.summary }}</p>

                <div class="plan-meta">
                  <div class="meta-item">
                    <span class="meta-label">{{ t('agent.fields.chosenSkill') }}</span>
                    <NTag type="success" size="tiny">{{ msg.planResult.chosenSkill?.name || '-' }}</NTag>
                  </div>
                  <div class="meta-item">
                    <span class="meta-label">{{ t('agent.fields.planHash') }}</span>
                    <code class="hash-code">{{ msg.planResult.planHash?.slice(0, 18) }}…</code>
                  </div>
                </div>

                <div class="plan-cost">
                  <span><strong>{{ msg.planResult.costEstimate.tokens }}</strong> tokens</span>
                  <span class="cost-sep">·</span>
                  <span><strong>{{ msg.planResult.costEstimate.toolCalls }}</strong> tool calls</span>
                  <span class="cost-sep">·</span>
                  <span>~<strong>{{ msg.planResult.costEstimate.durationSecEstimate }}</strong>s</span>
                </div>

                <NDivider />

                <!-- actions list -->
                <div class="action-steps">
                  <div
                    v-for="action in msg.planResult.proposedActions"
                    :key="`${msg.id}-${action.step}`"
                    class="action-step"
                  >
                    <div class="step-head">
                      <span class="step-num">{{ action.step }}</span>
                      <code class="step-tool">{{ action.tool }}</code>
                      <NTag :type="sideEffectTagType(action.sideEffect)" size="tiny" :bordered="false">
                        {{ action.sideEffect }}
                      </NTag>
                    </div>
                    <code class="step-input">{{ JSON.stringify(action.input) }}</code>
                  </div>
                </div>

                <!-- execute button -->
                <div v-if="!msg.executeResult && executionPolicy !== 'planOnly'" class="execute-row">
                  <NButton
                    type="primary"
                    :loading="msg.status === 'running'"
                    :disabled="!canExecute(msg) && msg.status !== 'running'"
                    @click="runExecute(msg)"
                  >
                    {{ msg.status === 'running' ? 'Executing…' : t('agent.actions.execute') }}
                  </NButton>
                  <NButton
                    v-if="msg.status === 'running'"
                    type="warning"
                    ghost
                    size="small"
                    @click="cancelRunningJob(msg)"
                  >
                    {{ t('agent.actions.cancel') }}
                  </NButton>
                </div>
              </template>

              <!-- executing spinner (before plan result) -->
              <div v-else-if="msg.status === 'running'" class="agent-thinking">
                <NSpin size="small" /> <span>Agent is executing…</span>
              </div>

              <!-- execution result -->
              <template v-if="msg.executeResult">
                <NDivider />
                <div class="exec-result">
                  <p class="exec-summary">{{ msg.executeResult.summary }}</p>
                  <div class="exec-stats">
                    <div class="exec-stat">
                      <span class="exec-stat-num">{{ msg.executeResult.appliedActions }}</span>
                      <span class="exec-stat-label">applied</span>
                    </div>
                    <div class="exec-stat">
                      <span class="exec-stat-num">{{ msg.executeResult.skippedActions }}</span>
                      <span class="exec-stat-label">skipped</span>
                    </div>
                    <div class="exec-stat">
                      <span class="exec-stat-num">{{ msg.executeResult.warnings?.length || 0 }}</span>
                      <span class="exec-stat-label">warnings</span>
                    </div>
                  </div>
                  <div v-if="msg.executeResult.warnings?.length" class="exec-warnings">
                    <NAlert v-for="(w, wi) in msg.executeResult.warnings" :key="wi" type="warning" size="small">
                      {{ w }}
                    </NAlert>
                  </div>
                </div>
              </template>

              <!-- error -->
              <NAlert v-if="msg.status === 'failed'" type="error" size="small" class="msg-error">
                {{ msg.errorMessage || t('agent.errors.planFailed') }}
              </NAlert>

              <!-- canceled -->
              <NAlert v-if="msg.status === 'canceled'" type="warning" size="small" class="msg-error">
                Task was cancelled.
              </NAlert>

              <span class="msg-time">{{ formatTime(msg.timestamp) }}</span>
            </div>
          </div>
        </div>
      </div>

      <!-- input area -->
      <div class="chat-input-area">
        <div class="input-container" :class="{ 'is-focused': isPromptFocused }">
          <NInput
            v-model:value="taskInput"
            type="textarea"
            class="chat-input"
            :autosize="{ minRows: 1, maxRows: 6 }"
            :placeholder="t('agent.fields.taskPlaceholder')"
            @focus="isPromptFocused = true"
            @blur="isPromptFocused = false"
            @keydown="onKeydown"
          />

          <button
            class="send-btn"
            :disabled="!taskInput.trim() || isSending"
            :class="{ 'is-loading': isSending }"
            @click="sendMessage"
            aria-label="Send"
          >
            <svg v-if="!isSending" viewBox="0 0 24 24" width="18" height="18"><path fill="currentColor" d="M3 20V4l19 8l-19 8zm2-3l11.85-5L5 7v3.5l6 1.5l-6 1.5V17z"/></svg>
            <NSpin v-else size="small" />
          </button>
        </div>

        <!-- execution policy dropdown -->
        <div class="policy-row">
          <span class="policy-label">执行策略</span>
          <NSelect
            v-model:value="executionPolicy"
            :options="executionPolicyOptions"
            size="tiny"
            class="policy-select"
            :consistent-menu-width="false"
          />
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
/* ===== layout ===== */
.cursor-chat {
  display: flex;
  height: calc(100vh - 180px);
  min-height: 520px;
  background: var(--color-bg-primary);
  border: 1px solid var(--color-border);
  border-radius: var(--border-radius-lg);
  overflow: hidden;
}

/* ===== sidebar ===== */
.chat-sidebar {
  width: 260px;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  background: var(--color-bg-secondary);
  border-right: 1px solid var(--color-border);
}
.sidebar-header {
  padding: 12px;
  border-bottom: 1px solid var(--color-border);
}
.sidebar-list {
  flex: 1;
  overflow-y: auto;
  padding: 8px;
}
.sidebar-empty {
  padding: 24px 12px;
  text-align: center;
  color: var(--color-text-tertiary);
  font-size: 13px;
}
.sidebar-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 12px;
  border-radius: 8px;
  cursor: pointer;
  transition: background 0.15s;
  margin-bottom: 2px;
  position: relative;
  border-left: 3px solid transparent;
}
.sidebar-item:hover {
  background: var(--color-bg-tertiary);
}
.sidebar-item.active {
  background: rgba(var(--color-primary-rgb), 0.08);
  border-left-color: var(--color-primary);
}
.sidebar-item-content {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
  flex: 1;
}
.sidebar-item-title {
  font-size: 13px;
  font-weight: 500;
  color: var(--color-text-primary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.sidebar-item-time {
  font-size: 11px;
  color: var(--color-text-tertiary);
}
.sidebar-item-delete {
  display: none;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  border: none;
  border-radius: 6px;
  background: transparent;
  color: var(--color-text-tertiary);
  cursor: pointer;
  flex-shrink: 0;
  transition: background 0.15s, color 0.15s;
}
.sidebar-item:hover .sidebar-item-delete {
  display: flex;
}
.sidebar-item-delete:hover {
  background: rgba(220, 38, 38, 0.1);
  color: rgb(220, 38, 38);
}

/* ===== main ===== */
.chat-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
}

/* ===== top bar ===== */
.chat-topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 16px;
  border-bottom: 1px solid var(--color-border);
  background: var(--color-bg-secondary);
  flex-shrink: 0;
}
.topbar-left {
  display: flex;
  align-items: center;
  gap: 8px;
}
.topbar-title {
  font-weight: 600;
  font-size: 14px;
  color: var(--color-text-primary);
}

/* ===== messages area ===== */
.chat-messages {
  flex: 1;
  overflow-y: auto;
  padding: 20px 16px;
  display: flex;
  flex-direction: column;
  gap: 24px;
  scroll-behavior: smooth;
}

/* ===== welcome ===== */
.chat-welcome {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
  padding: 60px 20px;
  gap: 12px;
  color: var(--color-text-secondary);
}
.chat-welcome h2 {
  margin: 0;
  font-size: 22px;
  color: var(--color-text-primary);
}
.chat-welcome p {
  margin: 0;
  font-size: 14px;
  max-width: 400px;
}
.welcome-icon {
  color: var(--color-primary);
  margin-bottom: 8px;
}
.welcome-hints {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  justify-content: center;
  margin-top: 12px;
}
.hint-chip {
  padding: 6px 14px;
  border: 1px solid var(--color-border);
  border-radius: 999px;
  background: var(--color-bg-secondary);
  color: var(--color-text-secondary);
  font-size: 13px;
  cursor: pointer;
  transition: border-color 0.15s, background 0.15s;
}
.hint-chip:hover {
  border-color: var(--color-primary);
  background: rgba(var(--color-primary-rgb), 0.06);
  color: var(--color-primary);
}

/* ===== message rows ===== */
.chat-turn {
  display: flex;
  flex-direction: column;
}
.msg-row {
  display: flex;
  gap: 10px;
  max-width: 85%;
}
.msg-row--user {
  align-self: flex-end;
  flex-direction: row-reverse;
}
.msg-row--agent {
  align-self: flex-start;
}

/* ===== avatar ===== */
.msg-avatar {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  background: rgba(var(--color-primary-rgb), 0.12);
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--color-primary);
  flex-shrink: 0;
  align-self: flex-start;
  margin-top: 2px;
}

/* ===== bubbles ===== */
.msg-bubble {
  padding: 12px 16px;
  border-radius: 14px;
  font-size: 14px;
  line-height: 1.6;
  position: relative;
  min-width: 0;
}
.msg-bubble--user {
  background: rgba(var(--color-primary-rgb), 0.1);
  border: 1px solid rgba(var(--color-primary-rgb), 0.2);
  border-bottom-right-radius: 4px;
}
.msg-bubble--agent {
  background: var(--color-bg-secondary);
  border: 1px solid var(--color-border);
  border-bottom-left-radius: 4px;
}
.msg-text {
  margin: 0;
  white-space: pre-wrap;
  word-break: break-word;
}
.msg-time {
  display: block;
  font-size: 11px;
  color: var(--color-text-tertiary);
  margin-top: 4px;
  text-align: right;
}

/* ===== agent thinking ===== */
.agent-thinking {
  display: flex;
  align-items: center;
  gap: 8px;
  color: var(--color-text-tertiary);
  font-size: 13px;
}
.agent-thinking :deep(.n-spin) {
  --n-size: 14px;
}

/* ===== plan inside agent bubble ===== */
.plan-summary-text {
  margin: 0 0 10px;
  color: var(--color-text-primary);
  font-size: 14px;
}
.plan-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  margin-bottom: 8px;
}
.meta-item {
  display: flex;
  align-items: center;
  gap: 4px;
}
.meta-label {
  font-size: 11px;
  color: var(--color-text-tertiary);
  text-transform: uppercase;
  letter-spacing: 0.04em;
}
.hash-code {
  font-size: 11px;
  padding: 1px 6px;
  border-radius: 4px;
  background: var(--color-bg-tertiary);
  border: 1px solid var(--color-border);
  color: var(--color-text-secondary);
}
.plan-cost {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  color: var(--color-text-tertiary);
}
.plan-cost strong {
  color: var(--color-text-secondary);
}
.cost-sep {
  margin: 0 2px;
}

/* ===== action steps ===== */
.action-steps {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.action-step {
  padding: 8px 10px;
  border-radius: 8px;
  background: var(--color-bg-tertiary);
  border: 1px solid var(--color-border);
}
.step-head {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 4px;
}
.step-num {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 18px;
  height: 18px;
  border-radius: 50%;
  background: var(--color-primary);
  color: #fff;
  font-size: 11px;
  font-weight: 600;
  flex-shrink: 0;
}
.step-tool {
  font-size: 12px;
  font-weight: 600;
  color: var(--color-text-primary);
}
.step-input {
  display: block;
  font-size: 11px;
  color: var(--color-text-tertiary);
  padding-left: 24px;
  word-break: break-all;
}

/* ===== execute row ===== */
.execute-row {
  margin-top: 12px;
  display: flex;
  align-items: center;
  gap: 8px;
}

/* ===== execution result ===== */
.exec-result {
  margin-top: 4px;
}
.exec-summary {
  margin: 0 0 10px;
  font-size: 14px;
  color: var(--color-text-primary);
}
.exec-stats {
  display: flex;
  gap: 20px;
  margin-bottom: 8px;
}
.exec-stat {
  display: flex;
  flex-direction: column;
  align-items: center;
}
.exec-stat-num {
  font-size: 18px;
  font-weight: 700;
  color: var(--color-primary);
}
.exec-stat-label {
  font-size: 11px;
  color: var(--color-text-tertiary);
  text-transform: uppercase;
}
.exec-warnings {
  margin-top: 8px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

/* ===== errors ===== */
.msg-error {
  margin-top: 8px;
}

/* ===== input area ===== */
.chat-input-area {
  padding: 12px 16px;
  border-top: 1px solid var(--color-border);
  background: var(--color-bg-secondary);
  flex-shrink: 0;
}
.input-container {
  display: flex;
  align-items: flex-end;
  gap: 8px;
  background: var(--color-bg-primary);
  border: 1px solid var(--color-border);
  border-radius: 12px;
  padding: 6px 10px;
  transition: border-color 0.2s, box-shadow 0.2s;
}
.input-container.is-focused {
  border-color: var(--color-primary);
  box-shadow: 0 0 0 3px rgba(var(--color-primary-rgb), 0.12);
}
.chat-input {
  flex: 1;
}
.chat-input :deep(.n-input__border),
.chat-input :deep(.n-input__state-border) {
  border: none !important;
  box-shadow: none !important;
}
.chat-input :deep(.n-input__textarea-el) {
  background: transparent;
  font-size: 14px;
}
.send-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  border: none;
  border-radius: 8px;
  background: var(--color-primary);
  color: #fff;
  cursor: pointer;
  flex-shrink: 0;
  transition: opacity 0.15s, transform 0.15s;
}
.send-btn:disabled {
  opacity: 0.35;
  cursor: not-allowed;
}
.send-btn:not(:disabled):hover {
  transform: scale(1.06);
}
.send-btn:not(:disabled):active {
  transform: scale(0.96);
}

/* ===== execution policy row ===== */
.policy-row {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 8px;
}
.policy-label {
  font-size: 12px;
  color: var(--color-text-tertiary);
  flex-shrink: 0;
}
.policy-select {
  width: 160px;
}
.policy-select :deep(.n-base-selection) {
  --n-border: none;
  --n-border-active: none;
  --n-border-focus: none;
  --n-box-shadow-active: none;
  --n-box-shadow-focus: none;
  background: var(--color-bg-primary);
  border-radius: 6px;
  font-size: 12px;
}
.policy-select :deep(.n-base-selection:hover) {
  background: var(--color-bg-tertiary);
}

/* ===== n-divider in bubble ===== */
.msg-bubble--agent :deep(.n-divider) {
  margin: 10px 0;
}

/* ===== responsive ===== */
@media (max-width: 720px) {
  .cursor-chat {
    height: calc(100vh - 140px);
    min-height: 400px;
    border-radius: 0;
    border: none;
  }
  .chat-sidebar {
    display: none;
  }
  .msg-row {
    max-width: 92%;
  }
  .chat-messages {
    padding: 12px 8px;
    gap: 16px;
  }
}
</style>
