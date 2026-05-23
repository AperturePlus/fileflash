<script setup lang="ts">
import { reactive, ref, watch } from 'vue';
import Modal from '../../molecules/Modal.vue';
import Button from '../../molecules/Button.vue';
import TextField from '../../molecules/TextField.vue';
import { useLocaleStore } from '../../../store/locale';
import type { SkillForm } from '../../../composables/useAgentSkills';

const props = defineProps<{
  open: boolean;
  editingKey: string | null;
  initial?: Partial<SkillForm>;
  loading?: boolean;
}>();

const emit = defineEmits<{
  close: [];
  submit: [form: SkillForm];
}>();

const localeStore = useLocaleStore();
const t = localeStore.t;

const local = reactive({
  name: '',
  description: '',
  triggersText: '',
  toolsText: '',
  planTemplate: '{}',
  inputsSchema: '{}',
  outputsSchema: '{}',
});

const error = ref<string | null>(null);
const advancedOpen = ref(false);

const hydrate = () => {
  const i = props.initial ?? {};
  local.name = i.name ?? '';
  local.description = i.description ?? '';
  local.triggersText = i.triggersText ?? '';
  local.toolsText = (i.toolWhitelist ?? []).join(', ');
  local.planTemplate = JSON.stringify(i.planTemplate ?? {}, null, 2);
  local.inputsSchema = JSON.stringify(i.inputsSchema ?? {}, null, 2);
  local.outputsSchema = JSON.stringify(i.outputsSchema ?? {}, null, 2);
  error.value = null;
};

watch(() => props.open, (v) => { if (v) hydrate(); });

const parseJsonOrError = (raw: string, label: string): Record<string, any> => {
  try {
    return raw.trim() ? JSON.parse(raw) : {};
  } catch {
    throw new Error(t('agent.v2.skills.editor.error.invalidJson').replace('{field}', label));
  }
};

const onSubmit = () => {
  error.value = null;
  if (!local.name.trim() || !local.description.trim()) {
    error.value = t('agent.v2.skills.editor.error.required');
    return;
  }
  let plan: Record<string, any>, inputs: Record<string, any>, outputs: Record<string, any>;
  try {
    plan = parseJsonOrError(local.planTemplate, 'planTemplate');
    inputs = parseJsonOrError(local.inputsSchema, 'inputsSchema');
    outputs = parseJsonOrError(local.outputsSchema, 'outputsSchema');
  } catch (e) {
    error.value = (e as Error).message;
    return;
  }
  const tools = local.toolsText.split(',').map((s) => s.trim()).filter(Boolean);
  emit('submit', {
    name: local.name.trim(),
    description: local.description.trim(),
    triggersText: local.triggersText.trim() || null,
    toolWhitelist: tools,
    planTemplate: plan,
    inputsSchema: inputs,
    outputsSchema: outputs,
  });
};
</script>

<template>
  <Modal :open="open" size="lg" @close="emit('close')">
    <template #header>{{ editingKey ? t('agent.v2.skills.editor.titleEdit') : t('agent.v2.skills.editor.titleNew') }}</template>
    <form class="ff-sep" @submit.prevent="onSubmit">
      <div class="ff-sep__grid">
        <TextField v-model="local.name" :label="t('agent.v2.skills.editor.field.name')" />
        <TextField v-model="local.triggersText" :label="t('agent.v2.skills.editor.field.triggers')" :placeholder="t('agent.v2.skills.editor.field.triggersPlaceholder')" />
      </div>
      <label class="ff-sep__field">
        <span class="ff-sep__lbl">{{ t('agent.v2.skills.editor.field.description') }}</span>
        <textarea v-model="local.description" class="ff-sep__ta" rows="3" />
      </label>
      <TextField v-model="local.toolsText" :label="t('agent.v2.skills.editor.field.tools')" :placeholder="t('agent.v2.skills.editor.field.toolsPlaceholder')" />

      <details :open="advancedOpen" class="ff-sep__adv" @toggle="advancedOpen = ($event.target as HTMLDetailsElement).open">
        <summary class="ff-sep__sum">{{ t('agent.v2.skills.editor.advanced') }}</summary>
        <label class="ff-sep__field">
          <span class="ff-sep__lbl">{{ t('agent.v2.skills.editor.field.planTemplate') }}</span>
          <textarea v-model="local.planTemplate" class="ff-sep__ta ff-sep__ta--mono" rows="6" />
        </label>
        <label class="ff-sep__field">
          <span class="ff-sep__lbl">{{ t('agent.v2.skills.editor.field.inputsSchema') }}</span>
          <textarea v-model="local.inputsSchema" class="ff-sep__ta ff-sep__ta--mono" rows="6" />
        </label>
        <label class="ff-sep__field">
          <span class="ff-sep__lbl">{{ t('agent.v2.skills.editor.field.outputsSchema') }}</span>
          <textarea v-model="local.outputsSchema" class="ff-sep__ta ff-sep__ta--mono" rows="6" />
        </label>
      </details>

      <div v-if="error" class="ff-sep__err">{{ error }}</div>
    </form>
    <template #footer>
      <Button variant="ghost" @click="emit('close')">{{ t('agent.v2.skills.editor.cancel') }}</Button>
      <Button variant="primary" :loading="loading" @click="onSubmit">{{ t('agent.v2.skills.editor.save') }}</Button>
    </template>
  </Modal>
</template>

<style scoped>
.ff-sep { display: flex; flex-direction: column; gap: var(--sp-md); }
.ff-sep__grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--sp-md);
}
.ff-sep__field { display: flex; flex-direction: column; gap: 6px; }
.ff-sep__lbl {
  font-family: var(--font-mono); font-size: var(--text-label);
  letter-spacing: var(--tracking-wide); text-transform: uppercase;
  color: var(--text-secondary);
}
.ff-sep__ta {
  width: 100%;
  background: var(--surface-inset);
  color: var(--text-primary);
  border: 1px solid var(--border-default);
  border-radius: 0;
  padding: var(--sp-sm);
  font-family: var(--font-sans); font-size: var(--text-body);
  outline: none;
  resize: vertical;
}
.ff-sep__ta:focus { border-color: var(--ac); }
.ff-sep__ta--mono { font-family: var(--font-mono); font-size: var(--text-small); }

.ff-sep__adv {
  border: 1px solid var(--border-subtle);
  padding: var(--sp-sm);
  display: flex; flex-direction: column; gap: var(--sp-sm);
}
.ff-sep__sum {
  cursor: pointer;
  font-family: var(--font-mono); font-size: var(--text-label);
  letter-spacing: var(--tracking-wide); text-transform: uppercase;
  color: var(--text-tertiary);
  padding: var(--sp-xs) 0;
}
.ff-sep__err {
  color: var(--status-error);
  font-family: var(--font-mono); font-size: var(--text-small);
  border: 1px solid var(--status-error);
  padding: var(--sp-xs) var(--sp-sm);
}

@media (max-width: 720px) {
  .ff-sep__grid { grid-template-columns: 1fr; }
}
</style>
