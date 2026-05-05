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
    <NGridItem :span="24" :md="9" :lg="8">
      <NCard class="control-card" :title="t('agent.workspace.controls')">
        <NForm label-placement="top" :show-feedback="false">
          <NFormItem :label="t('agent.fields.task')">
            <NInput
              v-model:value="taskInput"
              type="textarea"
              :autosize="{ minRows: 4, maxRows: 8 }"
              :placeholder="t('agent.fields.taskPlaceholder')"
            />
          </NFormItem>

          <NFormItem :label="t('agent.fields.executionPolicy')">
            <NRadioGroup v-model:value="executionPolicy">
              <NRadioButton value="planOnly">Plan Only</NRadioButton>
              <NRadioButton value="confirm">Confirm</NRadioButton>
              <NRadioButton value="autopilot">Autopilot</NRadioButton>
            </NRadioGroup>
          </NFormItem>

          <NDivider />

          <NFormItem :label="t('agent.fields.allowFileContent')">
            <NSwitch v-model:value="allowFileContent" />
          </NFormItem>

          <NFormItem :label="t('agent.fields.maxReadBytes')">
            <NInputNumber v-model:value="maxReadBytes" :min="1024" :step="1024" />
          </NFormItem>

          <NFormItem :label="t('agent.fields.allowedMimeTypes')">
            <NInput v-model:value="allowedMimeTypesInput" placeholder="image/*,application/pdf" />
          </NFormItem>

          <NDivider />

          <NFormItem :label="t('agent.fields.maxSteps')">
            <NInputNumber v-model:value="maxSteps" :min="1" :max="100" />
          </NFormItem>

          <NFormItem :label="t('agent.fields.budgetTokens')">
            <NInputNumber v-model:value="budgetTokens" :min="1000" :max="100000" :step="1000" />
          </NFormItem>
        </NForm>

        <NSpace>
          <NButton type="primary" :loading="isPlanning" @click="submitPlan">
            {{ t('agent.actions.plan') }}
          </NButton>
          <NButton quaternary @click="resetResultState">{{ t('agent.actions.reset') }}</NButton>
        </NSpace>
      </NCard>
    </NGridItem>

    <NGridItem :span="24" :md="15" :lg="16">
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
.control-card {
  height: 100%;
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
