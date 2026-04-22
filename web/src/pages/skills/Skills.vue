<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue';
import { useDebounceFn } from '@vueuse/core';
import { createCustomSkill, deleteCustomSkill, importGlobalSkills, listAgentSkills, updateCustomSkill } from '../../api/skill';
import { useLocaleStore } from '../../store/locale';
import { useUserStore } from '../../store/user';
import type { AgentSkillItem, ImportAgentSkillMode, ImportAgentSkillResult, ImportAgentSkillItem } from '../../types/skill';
import type { PaginatedData } from '../../types/base';

const localeStore = useLocaleStore();
const userStore = useUserStore();
const t = localeStore.t;

type TabId = 'marketplace' | 'my-skills';

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

// ---- My Skills editor ----
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
  } catch (err) {
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
    alert('Name and description are required.');
    return;
  }

  editorLoading.value = true;
  try {
    const planTemplate = parseJsonOrThrow(formPlanTemplate.value, 'planTemplate');
    const inputsSchema = parseJsonOrThrow(formInputsSchema.value, 'inputsSchema');
    const outputsSchema = parseJsonOrThrow(formOutputsSchema.value, 'outputsSchema');

    const payload = {
      name: formName.value.trim(),
      description: formDescription.value.trim(),
      triggersText: formTriggers.value.trim() ? formTriggers.value.trim() : null,
      toolWhitelist: buildToolWhitelist(),
      planTemplate,
      inputsSchema,
      outputsSchema,
    };

    if (editingKey.value) {
      await updateCustomSkill(editingKey.value, payload);
    } else {
      await createCustomSkill(payload);
    }

    closeEditor();
    await loadMySkills();
  } catch (error) {
    console.error('Failed to save skill:', error);
    alert(String((error as Error).message || 'Failed to save skill.'));
  } finally {
    editorLoading.value = false;
  }
};

const removeSkill = async (skillKey: string) => {
  if (!confirm(`Delete skill ${skillKey}?`)) return;
  await deleteCustomSkill(skillKey);
  await loadMySkills();
};

// ---- Admin import ----
const importMode = ref<ImportAgentSkillMode>('upsert');
const importJson = ref('');
const importResults = ref<ImportAgentSkillResult[]>([]);
const importLoading = ref(false);

const handleImportFile = (event: Event) => {
  const file = (event.target as HTMLInputElement).files?.[0];
  if (!file) return;

  const reader = new FileReader();
  reader.onload = (e) => {
    importJson.value = String(e.target?.result || '');
  };
  reader.readAsText(file);
};

const submitImport = async () => {
  importResults.value = [];
  if (!importJson.value.trim()) {
    alert('Paste JSON first.');
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
      throw new Error('Import JSON must be an array or an object with { items: [] }');
    }

    const response = await importGlobalSkills({
      mode: importMode.value,
      items,
    });

    importResults.value = response.results || [];
    await loadMarketplace();
  } catch (error) {
    console.error('Import failed:', error);
    alert(String((error as Error).message || 'Import failed.'));
  } finally {
    importLoading.value = false;
  }
};

const hasMarketplaceNext = computed(() => Boolean(marketplace.value?.pagination?.hasNext));
const hasMarketplacePrev = computed(() => Boolean(marketplace.value?.pagination?.hasPrev));
const hasMySkillsNext = computed(() => Boolean(mySkills.value?.pagination?.hasNext));
const hasMySkillsPrev = computed(() => Boolean(mySkills.value?.pagination?.hasPrev));

const gotoMarketplacePrev = async () => {
  if (!hasMarketplacePrev.value) return;
  marketplacePage.value -= 1;
  await loadMarketplace();
};
const gotoMarketplaceNext = async () => {
  if (!hasMarketplaceNext.value) return;
  marketplacePage.value += 1;
  await loadMarketplace();
};
const gotoMySkillsPrev = async () => {
  if (!hasMySkillsPrev.value) return;
  mySkillsPage.value -= 1;
  await loadMySkills();
};
const gotoMySkillsNext = async () => {
  if (!hasMySkillsNext.value) return;
  mySkillsPage.value += 1;
  await loadMySkills();
};
</script>

<template>
  <div class="skills-page">
    <header class="page-header">
      <h1>{{ t('skills.pageTitle') }}</h1>
      <p>{{ t('skills.pageDescription') }}</p>
    </header>

    <div class="toolbar">
      <div class="search-box">
        <input v-model="queryText" type="text" :placeholder="t('skills.searchPlaceholder')" />
      </div>

      <div class="tabs">
        <button class="tab" :class="{ active: activeTab === 'marketplace' }" @click="activeTab = 'marketplace'">
          {{ t('skills.tab.marketplace') }}
        </button>
        <button class="tab" :class="{ active: activeTab === 'my-skills' }" @click="activeTab = 'my-skills'">
          {{ t('skills.tab.mySkills') }}
        </button>
      </div>

      <div class="actions">
        <button class="btn secondary" @click="refreshActiveTab">{{ t('skills.actions.refresh') }}</button>
        <button v-if="activeTab === 'my-skills'" class="btn primary" @click="openNewSkill">
          {{ t('skills.actions.newSkill') }}
        </button>
      </div>
    </div>

    <section v-if="activeTab === 'marketplace'" class="panel">
      <div class="panel-head">
        <h2>{{ t('skills.tab.marketplace') }}</h2>
        <div class="pager">
          <button class="btn small" :disabled="!hasMarketplacePrev || isMarketplaceLoading" @click="gotoMarketplacePrev">Prev</button>
          <button class="btn small" :disabled="!hasMarketplaceNext || isMarketplaceLoading" @click="gotoMarketplaceNext">Next</button>
        </div>
      </div>

      <div v-if="isMarketplaceLoading" class="loading">Loading...</div>
      <div v-else-if="!marketplace?.items?.length" class="empty">{{ t('skills.marketplace.empty') }}</div>
      <div v-else class="grid">
        <article v-for="skill in marketplace.items" :key="skill.skillKey" class="skill-card">
          <header>
            <strong>{{ skill.name }}</strong>
            <span class="pill">global</span>
          </header>
          <p class="desc">{{ skill.description }}</p>
          <div class="meta">
            <code class="key">{{ skill.skillKey }}</code>
            <span v-if="skill.triggersText" class="triggers">{{ skill.triggersText }}</span>
          </div>
        </article>
      </div>

      <div v-if="isAdmin" class="admin-import">
        <h3>{{ t('skills.admin.importTitle') }}</h3>
        <div class="import-row">
          <label class="label">
            {{ t('skills.admin.mode') }}
            <select v-model="importMode" class="select">
              <option value="upsert">{{ t('skills.admin.mode.upsert') }}</option>
              <option value="insertOnly">{{ t('skills.admin.mode.insertOnly') }}</option>
            </select>
          </label>
          <label class="label">
            File
            <input type="file" accept=".json,application/json" @change="handleImportFile" />
          </label>
          <button class="btn primary" :disabled="importLoading" @click="submitImport">
            {{ importLoading ? 'Importing...' : t('skills.admin.import') }}
          </button>
        </div>
        <textarea v-model="importJson" class="import-textarea" rows="10" :placeholder="t('skills.admin.jsonPlaceholder')" />

        <div v-if="importResults.length" class="import-results">
          <h4>{{ t('skills.admin.results') }}</h4>
          <ul>
            <li v-for="item in importResults" :key="item.skillKey">
              <code>{{ item.skillKey }}</code> — <span class="action">{{ item.action }}</span>
            </li>
          </ul>
        </div>
      </div>
    </section>

    <section v-else class="panel">
      <div class="panel-head">
        <h2>{{ t('skills.tab.mySkills') }}</h2>
        <div class="pager">
          <button class="btn small" :disabled="!hasMySkillsPrev || isMySkillsLoading" @click="gotoMySkillsPrev">Prev</button>
          <button class="btn small" :disabled="!hasMySkillsNext || isMySkillsLoading" @click="gotoMySkillsNext">Next</button>
        </div>
      </div>

      <div v-if="isMySkillsLoading" class="loading">Loading...</div>
      <div v-else-if="!mySkills?.items?.length" class="empty">{{ t('skills.mySkills.empty') }}</div>
      <div v-else class="grid">
        <article v-for="skill in mySkills.items" :key="skill.skillKey" class="skill-card">
          <header>
            <strong>{{ skill.name }}</strong>
            <span class="pill private">private</span>
          </header>
          <p class="desc">{{ skill.description }}</p>
          <div class="meta">
            <code class="key">{{ skill.skillKey }}</code>
            <span v-if="skill.triggersText" class="triggers">{{ skill.triggersText }}</span>
          </div>
          <div class="card-actions">
            <button class="btn small" @click="openEditSkill(skill)">{{ t('skills.actions.edit') }}</button>
            <button class="btn small danger" @click="removeSkill(skill.skillKey)">{{ t('skills.actions.delete') }}</button>
          </div>
        </article>
      </div>

      <div v-if="editorOpen" class="editor-overlay" @click.self="closeEditor">
        <div class="editor">
          <div class="editor-head">
            <h3>{{ editingKey ? t('skills.actions.edit') : t('skills.actions.newSkill') }}</h3>
            <button class="icon" @click="closeEditor">×</button>
          </div>

          <div class="form">
            <label class="field">
              <span>{{ t('skills.form.name') }}</span>
              <input v-model="formName" type="text" />
            </label>
            <label class="field">
              <span>{{ t('skills.form.description') }}</span>
              <textarea v-model="formDescription" rows="3" />
            </label>
            <label class="field">
              <span>{{ t('skills.form.triggers') }}</span>
              <input v-model="formTriggers" type="text" placeholder="e.g. organize, classify" />
            </label>
            <label class="field">
              <span>{{ t('skills.form.tools') }}</span>
              <input v-model="formTools" type="text" placeholder="tool.a, tool.b" />
            </label>

            <details class="advanced">
              <summary>Advanced JSON</summary>
              <label class="field">
                <span>{{ t('skills.form.planTemplate') }}</span>
                <textarea v-model="formPlanTemplate" rows="5" />
              </label>
              <label class="field">
                <span>{{ t('skills.form.inputsSchema') }}</span>
                <textarea v-model="formInputsSchema" rows="5" />
              </label>
              <label class="field">
                <span>{{ t('skills.form.outputsSchema') }}</span>
                <textarea v-model="formOutputsSchema" rows="5" />
              </label>
            </details>
          </div>

          <div class="editor-actions">
            <button class="btn secondary" :disabled="editorLoading" @click="closeEditor">{{ t('skills.actions.cancel') }}</button>
            <button class="btn primary" :disabled="editorLoading" @click="saveSkill">
              {{ editorLoading ? 'Saving...' : t('skills.actions.save') }}
            </button>
          </div>
        </div>
      </div>
    </section>
  </div>
</template>

<style scoped>
.skills-page {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-lg);
}

.page-header h1 {
  margin: 0;
  font-size: 28px;
  color: var(--color-text-primary);
}

.page-header p {
  margin: 6px 0 0;
  color: var(--color-text-tertiary);
}

.toolbar {
  display: grid;
  grid-template-columns: 1fr auto auto;
  gap: var(--spacing-md);
  align-items: center;
}

.search-box input {
  width: 100%;
  height: 42px;
  border-radius: var(--border-radius-md);
  border: 1px solid var(--color-border);
  background-color: var(--color-bg-secondary);
  padding: 0 14px;
  color: var(--color-text-primary);
}

.tabs {
  display: inline-flex;
  background-color: var(--color-bg-tertiary);
  border: 1px solid var(--color-border);
  border-radius: 999px;
  padding: 4px;
  gap: 4px;
}

.tab {
  height: 34px;
  padding: 0 14px;
  border-radius: 999px;
  border: none;
  background: transparent;
  color: var(--color-text-secondary);
  cursor: pointer;
}

.tab.active {
  background-color: var(--color-bg-primary);
  border: 1px solid var(--color-border);
  color: var(--color-text-primary);
}

.actions {
  display: inline-flex;
  gap: 10px;
  justify-content: flex-end;
}

.panel {
  background-color: var(--color-bg-secondary);
  border: 1px solid var(--color-border);
  border-radius: var(--border-radius-lg);
  padding: var(--spacing-lg);
}

.panel-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--spacing-md);
}

.panel-head h2 {
  margin: 0;
  font-size: 18px;
}

.pager {
  display: inline-flex;
  gap: 8px;
}

.grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
  gap: var(--spacing-md);
}

.skill-card {
  border: 1px solid var(--color-border);
  border-radius: var(--border-radius-lg);
  background: linear-gradient(180deg, var(--color-bg-primary), var(--color-bg-tertiary));
  padding: var(--spacing-md);
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.skill-card header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.pill {
  font-size: 12px;
  padding: 2px 10px;
  border-radius: 999px;
  border: 1px solid var(--color-border);
  color: var(--color-text-tertiary);
}

.pill.private {
  color: var(--color-text-secondary);
}

.desc {
  margin: 0;
  color: var(--color-text-secondary);
  line-height: 1.4;
}

.meta {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.key {
  font-size: 12px;
  color: var(--color-text-tertiary);
  word-break: break-all;
}

.triggers {
  font-size: 12px;
  color: var(--color-text-tertiary);
}

.card-actions {
  display: flex;
  gap: 8px;
}

.btn {
  border: 1px solid var(--color-border);
  background-color: var(--color-bg-primary);
  color: var(--color-text-primary);
  border-radius: var(--border-radius-md);
  padding: 8px 12px;
  cursor: pointer;
}

.btn.small {
  padding: 6px 10px;
  font-size: 12px;
}

.btn.primary {
  border-color: rgba(var(--color-primary-rgb), 0.55);
  background-color: rgba(var(--color-primary-rgb), 0.12);
}

.btn.secondary {
  background-color: transparent;
}

.btn.danger {
  border-color: rgba(255, 77, 79, 0.4);
  color: rgba(255, 77, 79, 0.95);
}

.btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.loading,
.empty {
  color: var(--color-text-tertiary);
  padding: var(--spacing-md) 0;
}

.admin-import {
  margin-top: var(--spacing-lg);
  padding-top: var(--spacing-lg);
  border-top: 1px solid var(--color-border);
  display: flex;
  flex-direction: column;
  gap: var(--spacing-md);
}

.import-row {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  align-items: flex-end;
}

.label {
  display: flex;
  flex-direction: column;
  gap: 6px;
  font-size: 12px;
  color: var(--color-text-tertiary);
}

.select {
  height: 36px;
  border-radius: var(--border-radius-md);
  border: 1px solid var(--color-border);
  background-color: var(--color-bg-primary);
  color: var(--color-text-primary);
  padding: 0 10px;
}

.import-textarea {
  width: 100%;
  border-radius: var(--border-radius-lg);
  border: 1px solid var(--color-border);
  background-color: var(--color-bg-primary);
  color: var(--color-text-primary);
  padding: 12px;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace;
}

.import-results ul {
  margin: 8px 0 0;
  padding-left: 18px;
  color: var(--color-text-secondary);
}

.editor-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.4);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 60;
  padding: var(--spacing-lg);
}

.editor {
  width: min(860px, 100%);
  max-height: 88vh;
  overflow: auto;
  background-color: var(--color-bg-secondary);
  border: 1px solid var(--color-border);
  border-radius: var(--border-radius-lg);
  padding: var(--spacing-lg);
  display: flex;
  flex-direction: column;
  gap: var(--spacing-md);
}

.editor-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.icon {
  border: none;
  background: transparent;
  font-size: 22px;
  color: var(--color-text-tertiary);
  cursor: pointer;
}

.form {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--spacing-md);
}

.field {
  display: flex;
  flex-direction: column;
  gap: 6px;
  font-size: 12px;
  color: var(--color-text-tertiary);
}

.field input,
.field textarea {
  border-radius: var(--border-radius-md);
  border: 1px solid var(--color-border);
  background-color: var(--color-bg-primary);
  color: var(--color-text-primary);
  padding: 10px 12px;
}

.field textarea {
  resize: vertical;
  min-height: 90px;
}

.advanced {
  grid-column: 1 / -1;
  border: 1px dashed var(--color-border);
  border-radius: var(--border-radius-lg);
  padding: var(--spacing-md);
  background-color: rgba(var(--color-primary-rgb), 0.04);
}

.advanced summary {
  cursor: pointer;
  color: var(--color-text-secondary);
  margin-bottom: 10px;
}

.editor-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}

@media (max-width: 960px) {
  .toolbar {
    grid-template-columns: 1fr;
  }

  .actions {
    justify-content: flex-start;
  }

  .form {
    grid-template-columns: 1fr;
  }
}
</style>

