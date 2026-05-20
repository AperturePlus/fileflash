<script setup lang="ts">
import Button from '../../molecules/Button.vue';
import Tag from '../../molecules/Tag.vue';
import type { AgentSkillItem } from '../../../types/skill';

defineProps<{ skill: AgentSkillItem; editable?: boolean }>();
defineEmits<{ edit: []; delete: [] }>();
</script>

<template>
  <article class="ff-sc">
    <header class="ff-sc__head">
      <h3 class="ff-sc__name">{{ skill.name }}</h3>
      <Tag class="ff-sc__vis" :class="`ff-sc__vis--${skill.visibility}`">{{
        skill.visibility
      }}</Tag>
    </header>
    <code class="ff-sc__key">{{ skill.skillKey }}</code>
    <p class="ff-sc__desc">{{ skill.description }}</p>
    <p v-if="skill.triggersText" class="ff-sc__triggers">{{ skill.triggersText }}</p>
    <footer v-if="editable" class="ff-sc__row">
      <Button variant="ghost" size="sm" @click="$emit('edit')">Edit</Button>
      <Button variant="ghost" size="sm" @click="$emit('delete')">Delete</Button>
    </footer>
  </article>
</template>

<style scoped>
.ff-sc {
  display: flex; flex-direction: column; gap: var(--sp-sm);
  padding: var(--sp-md);
  background: var(--surface-raised);
  border: 1px solid var(--border-default);
  border-radius: 0;
  transition: border-color var(--mo-duration-fast) var(--mo-easing);
}
.ff-sc:hover { border-color: var(--ac); }
.ff-sc__head { display: flex; align-items: center; justify-content: space-between; gap: var(--sp-sm); }
.ff-sc__name {
  margin: 0;
  font-family: var(--font-sans);
  font-size: var(--text-body);
  font-weight: var(--weight-bold);
  color: var(--text-primary);
}
.ff-sc__vis { font-size: 9px; letter-spacing: var(--tracking-wide); text-transform: uppercase; }
.ff-sc__vis--global { color: var(--ac); border-color: var(--ac); }
.ff-sc__vis--private { color: var(--status-warning); border-color: var(--status-warning); }
.ff-sc__key {
  font-family: var(--font-mono); font-size: var(--text-small);
  color: var(--text-tertiary);
  word-break: break-all;
}
.ff-sc__desc {
  margin: 0;
  color: var(--text-secondary);
  font-size: var(--text-body);
}
.ff-sc__triggers {
  margin: 0;
  font-family: var(--font-mono); font-size: var(--text-small);
  color: var(--text-tertiary);
}
.ff-sc__row { display: flex; gap: var(--sp-sm); justify-content: flex-end; }
</style>
