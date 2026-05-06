<script setup lang="ts">
import { computed, onBeforeUnmount, ref } from 'vue';
import {
  NAlert,
  NButton,
  NCard,
  NDivider,
  NEmpty,
  NForm,
  NFormItem,
  NGrid,
  NGridItem,
  NInput,
  NInputNumber,
  NRadioButton,
  NRadioGroup,
  NSpace,
  NSpin,
  NStatistic,
  NSwitch,
  NTag,
  NTimeline,
  NTimelineItem,
  NPopover,
  useMessage,
} from 'naive-ui';
import { cancelAgentJob, executeAgentPlan, getAgentJob, planAgentTask } from '../../../api/agent';
import { useLocaleStore } from '../../../store/locale';
import { useUserStore } from '../../../store/user';
import type {
  AgentBackgroundJob,
  AgentExecutionPolicy,
  AgentExecutionResult,
  AgentPlanResult,
  PlanAgentRequest,
} from '../../../types/agent';

const localeStore = useLocaleStore();
const userStore = useUserStore();
const t = localeStore.t;
const message = useMessage();

const taskInput = ref('');
const executionPolicy = ref<AgentExecutionPolicy>('confirm');
const allowFileContent = ref(false);
const maxReadBytes = ref(1048576);
const allowedMimeTypesInput = ref('image/*');
const maxSteps = ref(20);
const budgetTokens = ref(20000);

const planJob = ref<AgentBackgroundJob<AgentPlanResult> | null>(null);
const executeJob = ref<AgentBackgroundJob<AgentExecutionResult> | null>(null);
const planResult = ref<AgentPlanResult | null>(null);
const executeResult = ref<AgentExecutionResult | null>(null);
const agentError = ref('');

const isPlanning = ref(false);
const isExecuting = ref(false);
const isPromptFocused = ref(false);

let planPollTimer: ReturnType<typeof setInterval> | null = null;
let executePollTimer: ReturnType<typeof setInterval> | null = null;

const planStatus = computed(() => planJob.value?.status || 'idle');
const executeStatus = computed(() => executeJob.value?.status || 'idle');

const canExecute = computed(
  () =>
    Boolean(planResult.value?.planHash) &&
    planJob.value?.status === 'succeeded' &&
    !isExecuting.value,
);

const hasRunningExecute = computed(() => {
  const status = executeJob.value?.status || '';
  return status === 'pending' || status === 'running';
});

const sideEffectTagType = (sideEffect: string) => {
  if (sideEffect === 'write') return 'warning';
  return 'info';
};

const stopPolling = (kind: 'plan' | 'execute') => {
  if (kind === 'plan' && planPollTimer) {
    clearInterval(planPollTimer);
    planPollTimer = null;
  }
  if (kind === 'execute' && executePollTimer) {
    clearInterval(executePollTimer);
    executePollTimer = null;
  }
};

const isTerminalStatus = (status?: string | null) => {
  return status === 'succeeded' || status === 'failed' || status === 'canceled';
};

const refreshPlanJob = async (jobId: string) => {
  const latest = await getAgentJob<AgentPlanResult>(jobId);
  planJob.value = latest;
  if (latest.status === 'succeeded') {
    planResult.value = latest.result;
  }
  if (latest.status === 'failed' || latest.status === 'canceled') {
    agentError.value = latest.errorMessage || t('agent.errors.planFailed');
  }
  if (isTerminalStatus(latest.status)) {
    isPlanning.value = false;
    stopPolling('plan');
  }
};

const refreshExecuteJob = async (jobId: string) => {
  const latest = await getAgentJob<AgentExecutionResult>(jobId);
  executeJob.value = latest;
  if (latest.status === 'succeeded') {
    executeResult.value = latest.result;
  }
  if (latest.status === 'failed' || latest.status === 'canceled') {
    agentError.value = latest.errorMessage || t('agent.errors.executeFailed');
  }
  if (isTerminalStatus(latest.status)) {
    isExecuting.value = false;
    stopPolling('execute');
  }
};

const startPollingPlan = async (jobId: string) => {
  stopPolling('plan');
  await refreshPlanJob(jobId);
  if (isTerminalStatus(planJob.value?.status)) return;
  planPollTimer = setInterval(() => {
    refreshPlanJob(jobId).catch((error) => {
      console.error('Failed to refresh plan job:', error);
    });
  }, 1200);
};

const startPollingExecute = async (jobId: string) => {
  stopPolling('execute');
  await refreshExecuteJob(jobId);
  if (isTerminalStatus(executeJob.value?.status)) return;
  executePollTimer = setInterval(() => {
    refreshExecuteJob(jobId).catch((error) => {
      console.error('Failed to refresh execute job:', error);
    });
  }, 1200);
};

const buildPlanPayload = (): PlanAgentRequest => {
  const mimeTypes = allowedMimeTypesInput.value
    .split(',')
    .map((item) => item.trim())
    .filter(Boolean);
  return {
    input: taskInput.value.trim(),
    context: {
      rootFolderId: 'root',
      selectedFileIds: [],
      selectedFolderIds: [],
      currentPath: '/My Files',
    },
    executionPolicy: executionPolicy.value,
    dataPolicy: {
      allowFileContent: allowFileContent.value,
      maxReadBytes: maxReadBytes.value,
      allowedMimeTypes: mimeTypes.length ? mimeTypes : ['*/*'],
    },
    hints: {
      preferSkillId: null,
      maxSteps: maxSteps.value,
      budgetTokens: budgetTokens.value,
    },
  };
};

const resetResultState = () => {
  planJob.value = null;
  executeJob.value = null;
  planResult.value = null;
  executeResult.value = null;
  agentError.value = '';
  isPlanning.value = false;
  isExecuting.value = false;
  stopPolling('plan');
  stopPolling('execute');
};

const submitPlan = async () => {
  if (!taskInput.value.trim()) {
    message.warning(t('agent.errors.taskRequired'));
    return;
  }
  resetResultState();
  isPlanning.value = true;
  try {
    const response = await planAgentTask(buildPlanPayload());
    planJob.value = {
      jobId: response.jobId,
      status: response.status,
      taskType: response.taskType,
      priority: 100,
      payload: {},
      result: {} as AgentPlanResult,
      attempt: 0,
      maxAttempts: 0,
      scheduledAt: new Date().toISOString(),
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
    };
    await startPollingPlan(response.jobId);
  } catch (error) {
    console.error('Failed to create plan:', error);
    isPlanning.value = false;
    agentError.value = t('agent.errors.planFailed');
    message.error(t('agent.errors.planFailed'));
  }
};

const runExecute = async () => {
  if (!planResult.value) return;
  isExecuting.value = true;
  agentError.value = '';
  executeResult.value = null;
  try {
    const response = await executeAgentPlan({
      planJobId: planResult.value.planJobId,
      planHash: planResult.value.planHash,
      approval: {
        confirmedBy: userStore.user?.userId || 'current-user',
        confirmedAt: new Date().toISOString(),
      },
    });
    await startPollingExecute(response.jobId);
  } catch (error) {
    console.error('Failed to execute plan:', error);
    isExecuting.value = false;
    agentError.value = t('agent.errors.executeFailed');
    message.error(t('agent.errors.executeFailed'));
  }
};

const cancelRunningJob = async () => {
  const jobId = executeJob.value?.jobId;
  if (!jobId) return;
  try {
    await cancelAgentJob(jobId);
    await refreshExecuteJob(jobId);
    message.success(t('agent.actions.cancelled'));
  } catch (error) {
    console.error('Failed to cancel job:', error);
    message.error(t('agent.errors.cancelFailed'));
  }
};

onBeforeUnmount(() => {
  stopPolling('plan');
  stopPolling('execute');
});
</script>

<template>
  <NGrid :x-gap="16" :y-gap="16" :cols="24" responsive="screen">
    <NGridItem :span="24" :md="10" :lg="10">
      <div class="rich-prompt-box" :class="{ 'is-focused': isPromptFocused }">
        <NInput
          v-model:value="taskInput"
          type="textarea"
          class="borderless-input"
          :autosize="{ minRows: 4, maxRows: 12 }"
          :placeholder="t('agent.fields.taskPlaceholder')"
          @focus="isPromptFocused = true"
          @blur="isPromptFocused = false"
        />

        <div class="prompt-bottom-bar">
          <div class="bar-left">
            <NPopover trigger="click" placement="bottom-start" :style="{ width: '320px' }">
              <template #trigger>
                <NButton size="small" quaternary class="settings-btn">
                  <template #icon>
                    <svg viewBox="0 0 24 24" width="16" height="16"><path fill="currentColor" d="M12 15.5A3.5 3.5 0 0 1 8.5 12A3.5 3.5 0 0 1 12 8.5a3.5 3.5 0 0 1 3.5 3.5a3.5 3.5 0 0 1-3.5 3.5m7.43-2.53c.04-.32.07-.64.07-.97c0-.33-.03-.66-.07-1l2.11-1.63c.19-.15.24-.42.12-.64l-2-3.46c-.12-.22-.39-.31-.61-.22l-2.49 1c-.52-.39-1.06-.73-1.69-.98l-.37-2.65A.506.506 0 0 0 14 2h-4c-.25 0-.46.18-.5.42l-.37 2.65c-.63.25-1.17.59-1.69.98l-2.49-1c-.22-.09-.49 0-.61.22l-2 3.46c-.13.22-.07.49.12.64L4.57 11.5c-.04.34-.07.67-.07 1c0 .33.03.65.07.97l-2.11 1.66c-.19.15-.25.42-.12.64l2 3.46c.12.22.39.3.61.22l2.49-1.01c.52.4 1.06.74 1.69.99l.37 2.65c.04.24.25.42.5.42h4c.25 0 .46-.18.5-.42l.37-2.65c.63-.26 1.17-.59 1.69-.99l2.49 1.01c.22.08.49 0 .61-.22l2-3.46c.12-.22.07-.49-.12-.64l-2.11-1.66Z"/></svg>
                  </template>
                  {{ executionPolicy }}
                </NButton>
              </template>
              
              <div class="popover-settings">
                <div class="popover-header">{{ t('agent.workspace.advancedSettings') }}</div>
                <NForm label-placement="left" :label-width="140" :show-feedback="false" size="small">
                  <NFormItem :label="t('agent.fields.executionPolicy')">
                    <NRadioGroup v-model:value="executionPolicy">
                      <NSpace vertical>
                        <NRadioButton value="planOnly">Plan Only</NRadioButton>
                        <NRadioButton value="confirm">Confirm</NRadioButton>
                        <NRadioButton value="autopilot">Autopilot</NRadioButton>
                      </NSpace>
                    </NRadioGroup>
                  </NFormItem>
                  <NFormItem :label="t('agent.fields.allowFileContent')">
                    <NSwitch v-model:value="allowFileContent" />
                  </NFormItem>
                  <NFormItem :label="t('agent.fields.maxReadBytes')">
                    <NInputNumber v-model:value="maxReadBytes" :min="1024" :step="1024" />
                  </NFormItem>
                  <NFormItem :label="t('agent.fields.allowedMimeTypes')">
                    <NInput v-model:value="allowedMimeTypesInput" placeholder="image/*,application/pdf" />
                  </NFormItem>
                  <NFormItem :label="t('agent.fields.maxSteps')">
                    <NInputNumber v-model:value="maxSteps" :min="1" :max="100" />
                  </NFormItem>
                  <NFormItem :label="t('agent.fields.budgetTokens')">
                    <NInputNumber v-model:value="budgetTokens" :min="1000" :max="100000" :step="1000" />
                  </NFormItem>
                </NForm>
              </div>
            </NPopover>
          </div>
          <div class="bar-right">
            <NButton v-if="planResult || isExecuting" size="small" quaternary @click="resetResultState">
              {{ t('agent.actions.reset') }}
            </NButton>
            <NButton circle type="primary" size="small" :loading="isPlanning" @click="submitPlan" class="submit-btn">
              <template #icon>
                <svg viewBox="0 0 24 24" width="16" height="16"><path fill="currentColor" d="M3 20V4l19 8l-19 8zm2-3l11.85-5L5 7v3.5l6 1.5l-6 1.5V17z"/></svg>
              </template>
            </NButton>
          </div>
        </div>
      </div>
    </NGridItem>

    <NGridItem :span="24" :md="14" :lg="14">
      <NSpace vertical :size="16">
        <NGrid :cols="3" :x-gap="12">
          <NGridItem>
            <NCard size="small">
              <NStatistic :label="t('agent.metrics.planStatus')" :value="planStatus" />
            </NCard>
          </NGridItem>
          <NGridItem>
            <NCard size="small">
              <NStatistic :label="t('agent.metrics.executeStatus')" :value="executeStatus" />
            </NCard>
          </NGridItem>
          <NGridItem>
            <NCard size="small">
              <NStatistic
                :label="t('agent.metrics.actions')"
                :value="planResult?.proposedActions?.length || 0"
              />
            </NCard>
          </NGridItem>
        </NGrid>

        <NAlert v-if="agentError" type="error" :title="t('agent.errors.title')">
          {{ agentError }}
        </NAlert>

        <NCard :title="t('agent.workspace.planPreview')" class="plan-card">
          <NSpin :show="isPlanning">
            <template v-if="planResult">
              <NSpace vertical size="small">
                <p class="plan-summary">{{ planResult.summary }}</p>
                <NSpace align="center">
                  <span class="muted">{{ t('agent.fields.planHash') }}</span>
                  <code class="hash">{{ planResult.planHash }}</code>
                </NSpace>
                <NSpace align="center">
                  <span class="muted">{{ t('agent.fields.chosenSkill') }}</span>
                  <NTag type="success" size="small">{{ planResult.chosenSkill?.name || '-' }}</NTag>
                </NSpace>
              </NSpace>

              <NDivider />

              <NGrid :cols="3" :x-gap="12">
                <NGridItem>
                  <NStatistic :label="t('agent.metrics.tokens')" :value="planResult.costEstimate.tokens" />
                </NGridItem>
                <NGridItem>
                  <NStatistic :label="t('agent.metrics.toolCalls')" :value="planResult.costEstimate.toolCalls" />
                </NGridItem>
                <NGridItem>
                  <NStatistic
                    :label="t('agent.metrics.durationSec')"
                    :value="planResult.costEstimate.durationSecEstimate"
                  />
                </NGridItem>
              </NGrid>

              <NDivider />

              <NTimeline>
                <NTimelineItem
                  v-for="action in planResult.proposedActions"
                  :key="`${action.step}-${action.tool}`"
                  :title="`#${action.step} ${action.tool}`"
                  :type="sideEffectTagType(action.sideEffect)"
                >
                  <template #default>
                    <NSpace align="center" :wrap-item="false">
                      <NTag size="small" :type="sideEffectTagType(action.sideEffect)">
                        {{ action.sideEffect }}
                      </NTag>
                      <code class="input-json">{{ JSON.stringify(action.input) }}</code>
                    </NSpace>
                  </template>
                </NTimelineItem>
              </NTimeline>

              <NDivider />

              <NSpace>
                <NButton type="primary" :disabled="!canExecute" :loading="isExecuting" @click="runExecute">
                  {{ t('agent.actions.execute') }}
                </NButton>
                <NButton v-if="hasRunningExecute" type="warning" ghost @click="cancelRunningJob">
                  {{ t('agent.actions.cancel') }}
                </NButton>
              </NSpace>
            </template>
            <NEmpty v-else :description="t('agent.workspace.emptyPlan')" />
          </NSpin>
        </NCard>

        <NCard :title="t('agent.workspace.executionResult')">
          <template v-if="executeResult">
            <NSpace vertical size="small">
              <p class="plan-summary">{{ executeResult.summary }}</p>
              <NGrid :cols="3" :x-gap="12">
                <NGridItem>
                  <NStatistic :label="t('agent.metrics.appliedActions')" :value="executeResult.appliedActions" />
                </NGridItem>
                <NGridItem>
                  <NStatistic :label="t('agent.metrics.skippedActions')" :value="executeResult.skippedActions" />
                </NGridItem>
                <NGridItem>
                  <NStatistic :label="t('agent.metrics.warnings')" :value="executeResult.warnings.length" />
                </NGridItem>
              </NGrid>
            </NSpace>
          </template>
          <NAlert v-else-if="hasRunningExecute" type="info" :title="t('agent.workspace.executing')" />
          <NEmpty v-else :description="t('agent.workspace.emptyExecution')" />
        </NCard>
      </NSpace>
    </NGridItem>
  </NGrid>
</template>

<style scoped>
.rich-prompt-box {
  display: flex;
  flex-direction: column;
  background: var(--color-bg-primary);
  border: 1px solid var(--color-border);
  border-radius: 12px;
  overflow: hidden;
  transition: box-shadow 0.2s ease, border-color 0.2s ease;
  box-shadow: var(--shadow-sm);
}

.rich-prompt-box.is-focused {
  border-color: var(--color-primary);
  box-shadow: 0 0 0 3px rgba(var(--color-primary-rgb), 0.15);
}

.borderless-input {
  --n-border: none !important;
  --n-border-hover: none !important;
  --n-border-focus: none !important;
  --n-box-shadow-focus: none !important;
  background-color: transparent;
  padding: 12px 16px;
  font-size: 15px;
}

.borderless-input :deep(.n-input__textarea-el) {
  background-color: transparent;
}

.prompt-bottom-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 12px;
  background-color: var(--color-bg-primary);
  border-top: 1px solid transparent; /* visually grouping with the prompt */
}

.bar-left, .bar-right {
  display: flex;
  align-items: center;
  gap: 8px;
}

.settings-btn {
  text-transform: capitalize;
  font-size: 12px;
  color: var(--color-text-secondary);
}

.submit-btn {
  width: 28px;
  height: 28px;
}

.popover-settings {
  padding: 8px;
}

.popover-header {
  font-weight: 600;
  margin-bottom: 12px;
  color: var(--color-text-primary);
  border-bottom: 1px solid var(--color-border);
  padding-bottom: 8px;
}

.plan-card :deep(.n-timeline) {
  margin-top: var(--spacing-xs);
}

.plan-summary {
  margin: 0;
  color: var(--color-text-secondary);
}

.muted {
  color: var(--color-text-tertiary);
  font-size: 12px;
}

.hash {
  padding: 2px 8px;
  border-radius: 999px;
  border: 1px solid var(--color-border);
  background-color: var(--color-bg-tertiary);
  color: var(--color-text-secondary);
}

.input-json {
  color: var(--color-text-tertiary);
  font-size: 12px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 100%;
}
</style>
