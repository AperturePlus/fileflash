<script setup lang="ts">
import { onMounted, ref } from 'vue';
import {
  createRegistrationEmailDomainRule,
  deleteRegistrationEmailDomainRule,
  getRegistrationEmailDomainRules,
  updateRegistrationEmailDomainRule,
} from '../../../api/registration-email-domain-rule';
import { AdminTable, FilterBar, StatusBadge } from '../../../components/console';
import { ui } from '../../../utils/ui';
import type { RegistrationEmailDomainRuleItem } from '../../../types/registration-email-domain-rule';

const items = ref<RegistrationEmailDomainRuleItem[]>([]);
const queryText = ref('');
const enabledFilter = ref<'all' | 'enabled' | 'disabled'>('all');
const newName = ref('');
const newPattern = ref('');
const newEnabled = ref(true);

async function load() {
  const enabled = enabledFilter.value === 'all' ? undefined : enabledFilter.value === 'enabled';
  const resp = await getRegistrationEmailDomainRules({
    page: 1,
    perPage: 50,
    queryText: queryText.value.trim() || undefined,
    enabled,
  });
  items.value = resp.items;
}

async function create() {
  const name = newName.value.trim();
  const pattern = newPattern.value.trim();
  if (!name || !pattern) {
    ui.toast({ type: 'warning', message: 'Name and pattern required' });
    return;
  }
  await createRegistrationEmailDomainRule({ name, pattern, enabled: newEnabled.value });
  newName.value = '';
  newPattern.value = '';
  await load();
}

async function toggle(row: RegistrationEmailDomainRuleItem) {
  await updateRegistrationEmailDomainRule(row.ruleId, { enabled: !row.enabled });
  row.enabled = !row.enabled;
}

async function remove(row: RegistrationEmailDomainRuleItem) {
  await deleteRegistrationEmailDomainRule(row.ruleId);
  items.value = items.value.filter((it) => it.ruleId !== row.ruleId);
}

onMounted(load);
</script>

<template>
  <section class="page">
    <header class="page__header"><h1>Registration Rules</h1></header>

    <FilterBar @change="load">
      <input v-model="queryText" type="text" placeholder="Search name/pattern" />
      <select v-model="enabledFilter">
        <option value="all">All</option>
        <option value="enabled">Enabled</option>
        <option value="disabled">Disabled</option>
      </select>
    </FilterBar>

    <div class="rule-create">
      <input v-model="newName" type="text" placeholder="Rule name" />
      <input v-model="newPattern" type="text" placeholder="Regex e.g. .*\.example\.com" />
      <label class="rule-create__toggle">
        <input v-model="newEnabled" type="checkbox" /> Enabled
      </label>
      <button class="rule-create__btn" @click="create">Add</button>
    </div>

    <AdminTable :items="items">
      <template #row="{ row }">
        <div class="rule-row">
          <div class="rule-row__main">
            <strong>{{ (row as RegistrationEmailDomainRuleItem).name }}</strong>
            <small>{{ (row as RegistrationEmailDomainRuleItem).pattern }}</small>
          </div>
          <div class="rule-row__actions">
            <StatusBadge
              :value="(row as RegistrationEmailDomainRuleItem).enabled ? 'enabled' : 'disabled'"
              :tone="(row as RegistrationEmailDomainRuleItem).enabled ? 'positive' : 'neutral'"
            />
            <button class="rule-row__btn" @click="toggle(row as RegistrationEmailDomainRuleItem)">
              {{ (row as RegistrationEmailDomainRuleItem).enabled ? 'Disable' : 'Enable' }}
            </button>
            <button
              class="rule-row__btn is-danger"
              @click="remove(row as RegistrationEmailDomainRuleItem)"
            >
              Delete
            </button>
          </div>
        </div>
      </template>
    </AdminTable>
  </section>
</template>

<style scoped>
.page {
  display: flex;
  flex-direction: column;
  gap: var(--sp-lg);
}
.page__header h1 {
  margin: 0;
  font-family: var(--font-sans);
  font-size: var(--text-h1);
  color: var(--text-primary);
  font-weight: var(--weight-medium);
  letter-spacing: var(--tracking-snug);
}
.rule-create {
  display: flex;
  gap: var(--sp-sm);
  align-items: center;
  flex-wrap: wrap;
  padding: var(--sp-md);
  background: var(--surface-raised);
  border: 1px solid var(--border-default);
}
.rule-create input[type='text'] {
  flex: 1;
  min-width: 180px;
  height: 32px;
  padding: 0 var(--sp-sm);
  background: var(--surface-base);
  border: 1px solid var(--border-default);
  color: var(--text-primary);
  font-family: var(--font-mono);
  font-size: var(--text-body);
}
.rule-create input[type='text']:focus { outline: none; border-color: var(--ac); }
.rule-create__toggle {
  display: inline-flex;
  align-items: center;
  gap: var(--sp-xs);
  font-family: var(--font-mono);
  font-size: var(--text-small);
  color: var(--text-secondary);
}
.rule-create__btn {
  height: 32px;
  padding: 0 var(--sp-lg);
  background: var(--ac);
  border: none;
  color: var(--ac-fg);
  font-family: var(--font-mono);
  font-size: var(--text-label);
  text-transform: uppercase;
  letter-spacing: var(--tracking-wide);
  cursor: pointer;
}
.rule-row {
  display: flex;
  justify-content: space-between;
  gap: var(--sp-md);
  padding: 10px 14px;
  background: var(--surface-raised);
  border: 1px solid var(--border-default);
}
.rule-row__main { display: flex; flex-direction: column; min-width: 0; }
.rule-row__main strong {
  font-family: var(--font-sans);
  font-size: var(--text-body);
  color: var(--text-primary);
}
.rule-row__main small {
  color: var(--text-tertiary);
  font-family: var(--font-mono);
  font-size: var(--text-small);
}
.rule-row__actions { display: flex; gap: var(--sp-sm); align-items: center; }
.rule-row__btn {
  height: 28px;
  padding: 0 var(--sp-md);
  background: var(--surface-base);
  border: 1px solid var(--border-default);
  color: var(--text-primary);
  font-family: var(--font-mono);
  font-size: var(--text-small);
  cursor: pointer;
}
.rule-row__btn:hover {
  border-color: var(--ac);
  color: var(--ac);
}
.rule-row__btn.is-danger { color: var(--status-error); border-color: var(--status-error); }
.rule-row__btn.is-danger:hover {
  background: rgba(var(--status-error-rgb), 0.1);
  color: var(--status-error);
}
</style>
