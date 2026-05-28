<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue';
import useAgentSkills from '../../../composables/useAgentSkills';
import SkillCard from '../../../components/organisms/agent/SkillCard.vue';
import SkillEditorPanel from '../../../components/organisms/agent/SkillEditorPanel.vue';
import SkillImportPanel from '../../../components/organisms/agent/SkillImportPanel.vue';
import SegmentedControl from '../../../components/molecules/SegmentedControl.vue';
import Pagination from '../../../components/molecules/Pagination.vue';
import TextField from '../../../components/molecules/TextField.vue';
import Button from '../../../components/molecules/Button.vue';
import { useUserStore } from '../../../store/user';
import { useLocaleStore } from '../../../store/locale';

const s = useAgentSkills();
const userStore = useUserStore();
const localeStore = useLocaleStore();
const t = localeStore.t;
const isAdmin = computed(() => userStore.user?.role === 'admin');

type TabId = 'marketplace' | 'my';
const activeTab = ref<TabId>('marketplace');
const TAB_OPTIONS = computed(() => [
  { value: 'marketplace', label: t('agent.v2.skills.tab.marketplace') },
  { value: 'my', label: t('agent.v2.skills.tab.mySkills') },
]);

const activeData = computed(() =>
  activeTab.value === 'marketplace' ? s.marketplace.value : s.mySkills.value,
);
const activeTotal = computed(() => activeData.value?.pagination?.totalItems ?? 0);
const activePage = computed({
  get: () => (activeTab.value === 'marketplace' ? s.marketplacePage.value : s.mySkillsPage.value),
  set: (v) => { (activeTab.value === 'marketplace' ? s.marketplacePage : s.mySkillsPage).value = v; },
});

watch(s.marketplacePage, () => s.loadMarketplace());
watch(s.mySkillsPage, () => s.loadMySkills());
onMounted(() => { s.loadMarketplace(); s.loadMySkills(); });
</script>

<template>
  <div class="as">
    <header class="as__head">
      <TextField v-model="s.queryText.value" :label="t('agent.v2.skills.search.label')" :placeholder="t('agent.v2.skills.search.placeholder')" />
      <div class="as__tabs">
        <SegmentedControl v-model="activeTab" :options="TAB_OPTIONS" />
        <Button v-if="activeTab === 'my'" variant="primary" size="sm" @click="s.openNewSkill">{{ t('agent.v2.skills.newSkill') }}</Button>
      </div>
    </header>

    <section class="as__grid">
      <SkillCard
        v-for="sk in activeData?.items || []"
        :key="sk.skillKey"
        :skill="sk"
        :editable="activeTab === 'my'"
        @edit="s.openEditSkill(sk)"
        @delete="s.removeSkill(sk.skillKey)"
      />
      <p v-if="!activeData?.items?.length" class="as__empty">{{ t('agent.v2.skills.empty') }}</p>
    </section>

    <Pagination v-model:page="activePage" :page-size="20" :total="activeTotal" />

    <SkillImportPanel
      v-if="isAdmin && activeTab === 'marketplace'"
      :loading="s.importLoading.value"
      :results="s.importResults.value"
      @submit="s.submitImport"
    />

    <SkillEditorPanel
      :open="s.editorOpen.value"
      :editing-key="s.editingKey.value"
      :initial="s.form"
      :loading="s.editorLoading.value"
      @close="s.closeEditor"
      @submit="s.saveSkill"
    />
  </div>
</template>

<style scoped>
.as { display: flex; flex-direction: column; gap: var(--sp-lg); padding: var(--sp-xl); }
.as__head { display: flex; gap: var(--sp-md); align-items: end; }
.as__head > :first-child { flex: 1; max-width: 360px; }
.as__tabs { display: flex; gap: var(--sp-sm); align-items: center; }
.as__grid { display: grid; gap: var(--sp-md); grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); }
.as__empty {
  grid-column: 1 / -1; padding: var(--sp-xl); text-align: center;
  font-family: var(--font-mono); font-size: var(--text-small);
  letter-spacing: var(--tracking-wide); text-transform: uppercase;
  color: var(--text-tertiary);
}
</style>
