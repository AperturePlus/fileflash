<script setup lang="ts">
import { ref } from 'vue';
import Icon from '../../atoms/Icon.vue';
import Tag from '../../molecules/Tag.vue';
import type { AgentProposedAction } from '../../../types/agent';

defineProps<{ action: AgentProposedAction }>();

const expanded = ref(false);
</script>

<template>
  <div class="ff-par">
    <button type="button" class="ff-par__head" @click="expanded = !expanded">
      <span class="ff-par__num">{{ action.step.toString().padStart(2, '0') }}</span>
      <code class="ff-par__tool">{{ action.tool }}</code>
      <Tag class="ff-par__se" :class="`ff-par__se--${action.sideEffect}`">{{ action.sideEffect }}</Tag>
      <Icon :name="expanded ? 'chevronUp' : 'chevronDown'" :size="12" />
    </button>
    <pre v-if="expanded" class="ff-par__input">{{ JSON.stringify(action.input, null, 2) }}</pre>
  </div>
</template>

<style scoped>
.ff-par {
  border-bottom: 1px solid var(--border-subtle);
}
.ff-par__head {
  display: flex; align-items: center; gap: var(--sp-sm);
  width: 100%;
  height: 28px;
  padding: 0 var(--sp-sm);
  background: transparent;
  border: 0;
  cursor: pointer;
  color: var(--text-secondary);
  font-family: var(--font-mono);
  font-size: var(--text-label);
  letter-spacing: var(--tracking-wide);
  text-align: left;
}
.ff-par__head:hover { background: var(--surface-inset); color: var(--text-primary); }
.ff-par__num {
  color: var(--text-tertiary);
  min-width: 20px;
}
.ff-par__tool { flex: 1; color: var(--text-primary); }
.ff-par__se { font-size: 9px; padding: 1px 6px; }
.ff-par__se--write { color: var(--status-warning); border-color: var(--status-warning); }
.ff-par__input {
  margin: 0;
  padding: var(--sp-sm);
  background: var(--surface-inset);
  color: var(--text-secondary);
  font-family: var(--font-mono);
  font-size: var(--text-small);
  overflow: auto;
  border-top: 1px solid var(--border-subtle);
}
</style>
