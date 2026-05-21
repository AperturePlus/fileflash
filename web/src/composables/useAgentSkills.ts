import { reactive, ref, watch, type Ref } from 'vue';
import { useDebounceFn } from '@vueuse/core';
import {
  createCustomSkill,
  deleteCustomSkill,
  importGlobalSkills,
  listAgentSkills,
  updateCustomSkill,
} from '../api/skill';
import type {
  AgentSkillItem,
  ImportAgentSkillItem,
  ImportAgentSkillMode,
  ImportAgentSkillResult,
} from '../types/skill';
import type { PaginatedData } from '../types/base';

export interface SkillForm {
  name: string;
  description: string;
  triggersText: string | null;
  toolWhitelist: string[];
  planTemplate: Record<string, any>;
  inputsSchema: Record<string, any>;
  outputsSchema: Record<string, any>;
}

interface SkillsState {
  marketplace: Ref<PaginatedData<AgentSkillItem> | null>;
  mySkills: Ref<PaginatedData<AgentSkillItem> | null>;
  marketplacePage: Ref<number>;
  mySkillsPage: Ref<number>;
  isMarketplaceLoading: Ref<boolean>;
  isMySkillsLoading: Ref<boolean>;
  queryText: Ref<string>;
  editingKey: Ref<string | null>;
  editorOpen: Ref<boolean>;
  editorLoading: Ref<boolean>;
  form: SkillForm;
  importResults: Ref<ImportAgentSkillResult[]>;
  importLoading: Ref<boolean>;
  watcherStopper: (() => void) | null;
}

const PER_PAGE = 20;

const blankForm = (): SkillForm => ({
  name: '',
  description: '',
  triggersText: null,
  toolWhitelist: [],
  planTemplate: {},
  inputsSchema: {},
  outputsSchema: {},
});

let _state: SkillsState | null = null;

const getState = (): SkillsState => {
  if (_state) return _state;
  _state = {
    marketplace: ref<PaginatedData<AgentSkillItem> | null>(null),
    mySkills: ref<PaginatedData<AgentSkillItem> | null>(null),
    marketplacePage: ref(1),
    mySkillsPage: ref(1),
    isMarketplaceLoading: ref(false),
    isMySkillsLoading: ref(false),
    queryText: ref(''),
    editingKey: ref<string | null>(null),
    editorOpen: ref(false),
    editorLoading: ref(false),
    form: reactive(blankForm()),
    importResults: ref<ImportAgentSkillResult[]>([]),
    importLoading: ref(false),
    watcherStopper: null,
  };
  return _state;
};

export const __resetForTests = () => {
  if (_state?.watcherStopper) _state.watcherStopper();
  _state = null;
};

export default function useAgentSkills() {
  const s = getState();

  const loadMarketplace = async (): Promise<void> => {
    s.isMarketplaceLoading.value = true;
    try {
      s.marketplace.value = await listAgentSkills({
        page: s.marketplacePage.value,
        perPage: PER_PAGE,
        visibility: 'global',
        queryText: s.queryText.value.trim() || undefined,
      });
    } finally {
      s.isMarketplaceLoading.value = false;
    }
  };

  const loadMySkills = async (): Promise<void> => {
    s.isMySkillsLoading.value = true;
    try {
      s.mySkills.value = await listAgentSkills({
        page: s.mySkillsPage.value,
        perPage: PER_PAGE,
        visibility: 'private',
        queryText: s.queryText.value.trim() || undefined,
      });
    } finally {
      s.isMySkillsLoading.value = false;
    }
  };

  const debouncedSearch = useDebounceFn(async () => {
    s.marketplacePage.value = 1;
    s.mySkillsPage.value = 1;
    await Promise.all([loadMarketplace(), loadMySkills()]);
  }, 250);

  if (!s.watcherStopper) {
    s.watcherStopper = watch(s.queryText, () => {
      void debouncedSearch();
    });
  }

  const openNewSkill = (): void => {
    s.editingKey.value = null;
    Object.assign(s.form, blankForm());
    s.editorOpen.value = true;
  };

  const openEditSkill = (skill: AgentSkillItem): void => {
    s.editingKey.value = skill.skillKey;
    s.form.name = skill.name;
    s.form.description = skill.description;
    s.form.triggersText = skill.triggersText ?? null;
    s.form.toolWhitelist = [...(skill.toolWhitelist ?? [])];
    s.form.planTemplate = { ...(skill.planTemplate ?? {}) };
    s.form.inputsSchema = { ...(skill.inputsSchema ?? {}) };
    s.form.outputsSchema = { ...(skill.outputsSchema ?? {}) };
    s.editorOpen.value = true;
  };

  const closeEditor = (): void => {
    s.editorOpen.value = false;
    s.editorLoading.value = false;
  };

  const createSkill = async (payload: SkillForm): Promise<AgentSkillItem> => {
    s.editorLoading.value = true;
    try {
      const created = await createCustomSkill(payload);
      await loadMySkills();
      return created;
    } finally {
      s.editorLoading.value = false;
    }
  };

  const updateSkill = async (skillKey: string, payload: SkillForm): Promise<AgentSkillItem> => {
    s.editorLoading.value = true;
    try {
      const updated = await updateCustomSkill(skillKey, payload);
      await loadMySkills();
      return updated;
    } finally {
      s.editorLoading.value = false;
    }
  };

  const saveSkill = async (payload: SkillForm): Promise<void> => {
    if (s.editingKey.value) await updateSkill(s.editingKey.value, payload);
    else await createSkill(payload);
    closeEditor();
  };

  const removeSkill = async (skillKey: string): Promise<void> => {
    await deleteCustomSkill(skillKey);
    await loadMySkills();
  };

  const submitImport = async (args: {
    mode: ImportAgentSkillMode;
    jsonText: string;
  }): Promise<void> => {
    s.importResults.value = [];
    if (!args.jsonText.trim()) return;
    s.importLoading.value = true;
    try {
      const parsed = JSON.parse(args.jsonText);
      let items: ImportAgentSkillItem[];
      if (Array.isArray(parsed)) items = parsed as ImportAgentSkillItem[];
      else if (parsed && typeof parsed === 'object' && Array.isArray(parsed.items))
        items = parsed.items as ImportAgentSkillItem[];
      else throw new Error('Import JSON must be an array or { items: [...] }.');

      const response = await importGlobalSkills({ mode: args.mode, items });
      s.importResults.value = response.results || [];
      await loadMarketplace();
    } finally {
      s.importLoading.value = false;
    }
  };

  return {
    marketplace: s.marketplace,
    mySkills: s.mySkills,
    marketplacePage: s.marketplacePage,
    mySkillsPage: s.mySkillsPage,
    isMarketplaceLoading: s.isMarketplaceLoading,
    isMySkillsLoading: s.isMySkillsLoading,
    queryText: s.queryText,
    editingKey: s.editingKey,
    editorOpen: s.editorOpen,
    editorLoading: s.editorLoading,
    form: s.form,
    importResults: s.importResults,
    importLoading: s.importLoading,
    loadMarketplace,
    loadMySkills,
    openNewSkill,
    openEditSkill,
    closeEditor,
    createSkill,
    updateSkill,
    saveSkill,
    removeSkill,
    submitImport,
  };
}
