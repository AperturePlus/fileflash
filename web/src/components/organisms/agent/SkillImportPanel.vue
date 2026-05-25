<script setup lang="ts">
import { computed, ref } from 'vue';
import Button from '../../molecules/Button.vue';
import SegmentedControl from '../../molecules/SegmentedControl.vue';
import FileDrop from '../../molecules/FileDrop.vue';
import Tag from '../../molecules/Tag.vue';
import { useLocaleStore } from '../../../store/locale';
import type { ImportAgentSkillMode, ImportAgentSkillResult } from '../../../types/skill';

defineProps<{
  loading?: boolean;
  results?: ImportAgentSkillResult[];
}>();

const emit = defineEmits<{
  submit: [args: { mode: ImportAgentSkillMode; jsonText: string }];
}>();

const localeStore = useLocaleStore();
const t = localeStore.t;

const mode = ref<ImportAgentSkillMode>('upsert');
const jsonText = ref('');
const error = ref<string | null>(null);

const MODE_OPTIONS = computed(() => [
  { value: 'upsert', label: t('agent.v2.skills.import.mode.upsert') },
  { value: 'insertOnly', label: t('agent.v2.skills.import.mode.insertOnly') },
]);

const onFiles = async (files: File[]) => {
  const f = files[0];
  if (!f) return;
  try {
    jsonText.value = await f.text();
  } catch {
    error.value = t('agent.v2.skills.import.error.readFailed');
  }
};

const onSubmit = () => {
  if (!jsonText.value.trim()) {
    error.value = t('agent.v2.skills.import.error.emptyJson');
    return;
  }
  error.value = null;
  emit('submit', { mode: mode.value, jsonText: jsonText.value });
};
</script>

<template>
  <section class="ff-sip">
    <header class="ff-sip__head">
      <span class="ff-sip__label">{{ t('agent.v2.skills.import.label') }}</span>
      <SegmentedControl
        v-model="mode"
        :options="MODE_OPTIONS as any"
      />
    </header>

    <FileDrop accept=".json,application/json" @files="onFiles">
      {{ t('agent.v2.skills.import.dropHint') }}
    </FileDrop>

    <label class="ff-sip__field">
      <span class="ff-sip__lbl">{{ t('agent.v2.skills.import.jsonLabel') }}</span>
      <textarea
        v-model="jsonText"
        class="ff-sip__ta"
        rows="10"
        :placeholder="t('agent.v2.skills.import.jsonPlaceholder')"
      />
    </label>

    <div v-if="error" class="ff-sip__err">{{ error }}</div>

    <div class="ff-sip__row">
      <Button variant="primary" :loading="loading" @click="onSubmit">{{ t('agent.v2.skills.import.submit') }}</Button>
    </div>

    <section v-if="results && results.length" class="ff-sip__results">
      <span class="ff-sip__lbl">{{ t('agent.v2.skills.import.resultsLabel') }}</span>
      <ul>
        <li v-for="r in results" :key="r.skillKey">
          <code>{{ r.skillKey }}</code>
          <Tag>{{ r.action }}</Tag>
        </li>
      </ul>
    </section>
  </section>
</template>

<style scoped>
.ff-sip {
  display: flex; flex-direction: column; gap: var(--sp-md);
  padding: var(--sp-lg);
  border: 1px solid var(--border-default);
  background: var(--surface-raised);
}
.ff-sip__head {
  display: flex; align-items: center; justify-content: space-between; gap: var(--sp-sm);
}
.ff-sip__label, .ff-sip__lbl {
  font-family: var(--font-mono); font-size: var(--text-small);
  letter-spacing: var(--tracking-wide); text-transform: uppercase;
  color: var(--text-tertiary);
}
.ff-sip__field { display: flex; flex-direction: column; gap: 6px; }
.ff-sip__ta {
  width: 100%;
  background: var(--surface-inset);
  color: var(--text-primary);
  border: 1px solid var(--border-default);
  border-radius: 0;
  padding: var(--sp-sm);
  font-family: var(--font-mono); font-size: var(--text-small);
  outline: none;
  resize: vertical;
}
.ff-sip__ta:focus { border-color: var(--ac); }
.ff-sip__err {
  color: var(--status-error);
  font-family: var(--font-mono); font-size: var(--text-small);
}
.ff-sip__row { display: flex; justify-content: flex-end; }
.ff-sip__results ul {
  list-style: none;
  padding: 0; margin: var(--sp-xs) 0 0;
  display: flex; flex-direction: column; gap: 4px;
}
.ff-sip__results li {
  display: flex; align-items: center; gap: var(--sp-sm);
  font-family: var(--font-mono); font-size: var(--text-small);
  color: var(--text-secondary);
}
</style>
