<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue';
import { useDebounceFn } from '@vueuse/core';
import {
  createCustomSkill,
  deleteCustomSkill,
  importGlobalSkills,
  listAgentSkills,
  updateCustomSkill,
} from '../../../api/skill';
import { useLocaleStore } from '../../../store/locale';
import { useUserStore } from '../../../store/user';
import type {
  AgentSkillItem,
  ImportAgentSkillItem,
  ImportAgentSkillMode,
  ImportAgentSkillResult,
} from '../../../types/skill';
import type { PaginatedData } from '../../../types/base';
import type { UploadFileInfo } from 'naive-ui';
import {
  NButton,
  NCard,
  NCollapse,
  NCollapseItem,
  NDivider,
  NEmpty,
  NForm,
  NFormItem,
  NInput,
  NModal,
  NPagination,
  NRadioButton,
  NRadioGroup,
  NSpace,
  NSpin,
  NTag,
  NUpload,
  useDialog,
  useMessage,
} from 'naive-ui';

type TabId = 'marketplace' | 'my-skills';

const localeStore = useLocaleStore();
const userStore = useUserStore();
const t = localeStore.t;
const dialog = useDialog();
const message = useMessage();

const activeTab = ref<TabId>('marketplace');
const queryText = ref('');

const perPage = 20;
const marketplacePage = ref(1);
const mySkillsPage = ref(1);

const isMarketplaceLoading = ref(false);
const isMySkillsLoading = ref(false);

const marketplace = ref<PaginatedData<AgentSkillItem> | null>(null);
const mySkills = ref<PaginatedData<AgentSkillItem> | null>(null);

const isAdmin = computed(() => userStore.user?.role === 'admin');

const loadMarketplace = async () => {
  isMarketplaceLoading.value = true;
  try {
    marketplace.value = await listAgentSkills({
      page: marketplacePage.value,
      perPage,
      visibility: 'global',
      queryText: queryText.value.trim() || undefined,
    });
  } finally {
    isMarketplaceLoading.value = false;
  }
};

const loadMySkills = async () => {
  isMySkillsLoading.value = true;
  try {
    mySkills.value = await listAgentSkills({
      page: mySkillsPage.value,
      perPage,
      visibility: 'private',
      queryText: queryText.value.trim() || undefined,
    });
  } finally {
    isMySkillsLoading.value = false;
  }
};

const refreshActiveTab = async () => {
  if (activeTab.value === 'marketplace') {
    await loadMarketplace();
  } else {
    await loadMySkills();
  }
};

const debouncedSearch = useDebounceFn(() => {
  marketplacePage.value = 1;
  mySkillsPage.value = 1;
  loadMarketplace();
  loadMySkills();
}, 250);

watch(queryText, () => debouncedSearch());

onMounted(async () => {
  await Promise.all([loadMarketplace(), loadMySkills()]);
});

const editorOpen = ref(false);
const editorLoading = ref(false);
const editingKey = ref<string | null>(null);

const formName = ref('');
const formDescription = ref('');
const formTriggers = ref('');
const formTools = ref('');
const formPlanTemplate = ref('{}');
const formInputsSchema = ref('{}');
const formOutputsSchema = ref('{}');

const openNewSkill = () => {
  editingKey.value = null;
  formName.value = '';
  formDescription.value = '';
  formTriggers.value = '';
  formTools.value = '';
  formPlanTemplate.value = '{}';
  formInputsSchema.value = '{}';
  formOutputsSchema.value = '{}';
  editorOpen.value = true;
};

const openEditSkill = (skill: AgentSkillItem) => {
  editingKey.value = skill.skillKey;
  formName.value = skill.name;
  formDescription.value = skill.description;
  formTriggers.value = skill.triggersText || '';
  formTools.value = (skill.toolWhitelist || []).join(', ');
  formPlanTemplate.value = JSON.stringify(skill.planTemplate || {}, null, 2);
  formInputsSchema.value = JSON.stringify(skill.inputsSchema || {}, null, 2);
  formOutputsSchema.value = JSON.stringify(skill.outputsSchema || {}, null, 2);
  editorOpen.value = true;
};

const closeEditor = () => {
  editorOpen.value = false;
  editorLoading.value = false;
};

const parseJsonOrThrow = (raw: string, label: string) => {
  try {
    return raw.trim() ? JSON.parse(raw) : {};
  } catch {
    throw new Error(`${label} JSON invalid`);
  }
};

const buildToolWhitelist = () => {
  return formTools.value
    .split(',')
    .map((item) => item.trim())
    .filter(Boolean);
};

const saveSkill = async () => {
  if (!formName.value.trim() || !formDescription.value.trim()) {
    message.warning(t('skills.validation.required'));
    return;
  }

  editorLoading.value = true;
  try {
    const payload = {
      name: formName.value.trim(),
      description: formDescription.value.trim(),
      triggersText: formTriggers.value.trim() || null,
      toolWhitelist: buildToolWhitelist(),
      planTemplate: parseJsonOrThrow(formPlanTemplate.value, 'planTemplate'),
      inputsSchema: parseJsonOrThrow(formInputsSchema.value, 'inputsSchema'),
      outputsSchema: parseJsonOrThrow(formOutputsSchema.value, 'outputsSchema'),
    };

    if (editingKey.value) {
      await updateCustomSkill(editingKey.value, payload);
    } else {
      await createCustomSkill(payload);
    }

    closeEditor();
    await loadMySkills();
    message.success(t('skills.feedback.saved'));
  } catch (error) {
    console.error('Failed to save skill:', error);
    message.error(String((error as Error).message || t('skills.feedback.saveFailed')));
  } finally {
    editorLoading.value = false;
  }
};

const removeSkill = (skillKey: string) => {
  dialog.warning({
    title: t('skills.dialog.deleteTitle'),
    content: `${t('skills.dialog.deleteContentPrefix')} ${skillKey}?`,
    positiveText: t('skills.actions.delete'),
    negativeText: t('skills.actions.cancel'),
    onPositiveClick: async () => {
      await deleteCustomSkill(skillKey);
      await loadMySkills();
      message.success(t('skills.feedback.deleted'));
    },
  });
};

const importMode = ref<ImportAgentSkillMode>('upsert');
const importJson = ref('');
const importResults = ref<ImportAgentSkillResult[]>([]);
const importLoading = ref(false);

const handleImportUploadChange = (options: { file: UploadFileInfo }) => {
  const raw = options.file.file;
  if (!raw) return;
  const reader = new FileReader();
  reader.onload = (e) => {
    importJson.value = String(e.target?.result || '');
  };
  reader.readAsText(raw);
};

const submitImport = async () => {
  importResults.value = [];
  if (!importJson.value.trim()) {
    message.warning(t('skills.feedback.emptyImport'));
    return;
  }

  importLoading.value = true;
  try {
    const parsed = JSON.parse(importJson.value);
    let items: ImportAgentSkillItem[] = [];
    if (Array.isArray(parsed)) {
      items = parsed as ImportAgentSkillItem[];
    } else if (parsed && typeof parsed === 'object' && Array.isArray((parsed as any).items)) {
      items = (parsed as any).items as ImportAgentSkillItem[];
    } else {
      throw new Error(t('skills.feedback.invalidImport'));
    }

    const response = await importGlobalSkills({ mode: importMode.value, items });
    importResults.value = response.results || [];
    await loadMarketplace();
    message.success(t('skills.feedback.imported'));
  } catch (error) {
    console.error('Import failed:', error);
    message.error(String((error as Error).message || t('skills.feedback.importFailed')));
  } finally {
    importLoading.value = false;
  }
};

const marketplaceTotal = computed(() => marketplace.value?.pagination.totalItems || 0);
const mySkillsTotal = computed(() => mySkills.value?.pagination.totalItems || 0);
</script>

<template>
  <div class="agent-skills-page">
    <NCard>
      <div class="toolbar">
        <NInput v-model:value="queryText" clearable :placeholder="t('skills.searchPlaceholder')" />
        <NSpace>
          <NButton @click="refreshActiveTab">{{ t('skills.actions.refresh') }}</NButton>
          <NButton v-if="activeTab === 'my-skills'" type="primary" @click="openNewSkill">
            {{ t('skills.actions.newSkill') }}
          </NButton>
        </NSpace>
      </div>
    </NCard>

    <NCard>
      <NRadioGroup v-model:value="activeTab">
        <NRadioButton value="marketplace">{{ t('skills.tab.marketplace') }}</NRadioButton>
        <NRadioButton value="my-skills">{{ t('skills.tab.mySkills') }}</NRadioButton>
      </NRadioGroup>
    </NCard>

    <NCard v-if="activeTab === 'marketplace'" :title="t('skills.tab.marketplace')">
      <NSpin :show="isMarketplaceLoading">
        <template v-if="marketplace?.items?.length">
          <div class="skill-grid">
            <NCard v-for="skill in marketplace.items" :key="skill.skillKey" size="small" class="skill-card">
              <template #header>
                <div class="card-header">
                  <strong>{{ skill.name }}</strong>
                  <NTag type="info" size="small">global</NTag>
                </div>
              </template>
              <p class="desc">{{ skill.description }}</p>
              <code class="skill-key">{{ skill.skillKey }}</code>
              <p v-if="skill.triggersText" class="meta">{{ skill.triggersText }}</p>
            </NCard>
          </div>
          <div class="pager">
            <NPagination
              v-model:page="marketplacePage"
              :page-size="perPage"
              :item-count="marketplaceTotal"
              @update:page="loadMarketplace"
            />
          </div>
        </template>
        <NEmpty v-else :description="t('skills.marketplace.empty')" />
      </NSpin>

      <template v-if="isAdmin">
        <NDivider />
        <NCard size="small" :title="t('skills.admin.importTitle')">
          <NForm label-placement="top">
            <NFormItem :label="t('skills.admin.mode')">
              <NRadioGroup v-model:value="importMode">
                <NRadioButton value="upsert">{{ t('skills.admin.mode.upsert') }}</NRadioButton>
                <NRadioButton value="insertOnly">{{ t('skills.admin.mode.insertOnly') }}</NRadioButton>
              </NRadioGroup>
            </NFormItem>
            <NSpace>
              <NUpload
                :show-file-list="false"
                :default-upload="false"
                accept=".json,application/json"
                @change="handleImportUploadChange"
              >
                <NButton>{{ t('skills.actions.pickFile') }}</NButton>
              </NUpload>
              <NButton type="primary" :loading="importLoading" @click="submitImport">
                {{ t('skills.admin.import') }}
              </NButton>
            </NSpace>
            <NFormItem>
              <NInput
                v-model:value="importJson"
                type="textarea"
                :autosize="{ minRows: 8, maxRows: 14 }"
                :placeholder="t('skills.admin.jsonPlaceholder')"
              />
            </NFormItem>
          </NForm>

          <template v-if="importResults.length">
            <NDivider />
            <NSpace vertical>
              <strong>{{ t('skills.admin.results') }}</strong>
              <div v-for="result in importResults" :key="result.skillKey" class="result-row">
                <code>{{ result.skillKey }}</code>
                <NTag size="small">{{ result.action }}</NTag>
              </div>
            </NSpace>
          </template>
        </NCard>
      </template>
    </NCard>

    <NCard v-else :title="t('skills.tab.mySkills')">
      <NSpin :show="isMySkillsLoading">
        <template v-if="mySkills?.items?.length">
          <div class="skill-grid">
            <NCard v-for="skill in mySkills.items" :key="skill.skillKey" size="small" class="skill-card">
              <template #header>
                <div class="card-header">
                  <strong>{{ skill.name }}</strong>
                  <NTag type="warning" size="small">private</NTag>
                </div>
              </template>
              <p class="desc">{{ skill.description }}</p>
              <code class="skill-key">{{ skill.skillKey }}</code>
              <p v-if="skill.triggersText" class="meta">{{ skill.triggersText }}</p>
              <NSpace>
                <NButton size="small" @click="openEditSkill(skill)">{{ t('skills.actions.edit') }}</NButton>
                <NButton size="small" type="error" ghost @click="removeSkill(skill.skillKey)">
                  {{ t('skills.actions.delete') }}
                </NButton>
              </NSpace>
            </NCard>
          </div>
          <div class="pager">
            <NPagination
              v-model:page="mySkillsPage"
              :page-size="perPage"
              :item-count="mySkillsTotal"
              @update:page="loadMySkills"
            />
          </div>
        </template>
        <NEmpty v-else :description="t('skills.mySkills.empty')" />
      </NSpin>
    </NCard>

    <NModal v-model:show="editorOpen" preset="card" style="width: min(920px, 96vw)" :title="editingKey ? t('skills.actions.edit') : t('skills.actions.newSkill')">
      <NForm label-placement="top">
        <div class="editor-grid">
          <NFormItem :label="t('skills.form.name')">
            <NInput v-model:value="formName" />
          </NFormItem>
          <NFormItem :label="t('skills.form.description')">
            <NInput v-model:value="formDescription" type="textarea" :autosize="{ minRows: 3, maxRows: 6 }" />
          </NFormItem>
          <NFormItem :label="t('skills.form.triggers')">
            <NInput v-model:value="formTriggers" placeholder="organize, classify" />
          </NFormItem>
          <NFormItem :label="t('skills.form.tools')">
            <NInput v-model:value="formTools" placeholder="tool.a, tool.b" />
          </NFormItem>
        </div>

        <NCollapse>
          <NCollapseItem title="Advanced JSON" name="advanced">
            <NFormItem :label="t('skills.form.planTemplate')">
              <NInput v-model:value="formPlanTemplate" type="textarea" :autosize="{ minRows: 4, maxRows: 8 }" />
            </NFormItem>
            <NFormItem :label="t('skills.form.inputsSchema')">
              <NInput v-model:value="formInputsSchema" type="textarea" :autosize="{ minRows: 4, maxRows: 8 }" />
            </NFormItem>
            <NFormItem :label="t('skills.form.outputsSchema')">
              <NInput v-model:value="formOutputsSchema" type="textarea" :autosize="{ minRows: 4, maxRows: 8 }" />
            </NFormItem>
          </NCollapseItem>
        </NCollapse>
      </NForm>

      <template #footer>
        <NSpace justify="end">
          <NButton @click="closeEditor">{{ t('skills.actions.cancel') }}</NButton>
          <NButton type="primary" :loading="editorLoading" @click="saveSkill">
            {{ t('skills.actions.save') }}
          </NButton>
        </NSpace>
      </template>
    </NModal>
  </div>
</template>

<style scoped>
.agent-skills-page {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-md);
}

.toolbar {
  display: grid;
  grid-template-columns: 1fr auto;
  gap: var(--spacing-md);
}

.skill-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
  gap: var(--spacing-md);
}

.skill-card {
  height: 100%;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: var(--spacing-sm);
}

.desc {
  margin: 0 0 var(--spacing-sm);
  color: var(--color-text-secondary);
}

.meta,
.skill-key {
  margin: 0 0 var(--spacing-sm);
  color: var(--color-text-tertiary);
  font-size: 12px;
}

.pager {
  margin-top: var(--spacing-md);
  display: flex;
  justify-content: flex-end;
}

.result-row {
  display: flex;
  align-items: center;
  gap: 8px;
}

.editor-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--spacing-md);
}

@media (max-width: 960px) {
  .toolbar {
    grid-template-columns: 1fr;
  }

  .editor-grid {
    grid-template-columns: 1fr;
  }
}
</style>
