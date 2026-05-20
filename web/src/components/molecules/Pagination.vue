<script setup lang="ts">
import { computed } from 'vue';

const props = withDefaults(
  defineProps<{
    page: number;
    pageSize: number;
    total: number;
    siblingCount?: number;
  }>(),
  { siblingCount: 1 },
);

defineEmits<{ 'update:page': [page: number] }>();

const pageCount = computed(() => Math.max(1, Math.ceil(props.total / props.pageSize)));

const visiblePages = computed<(number | string)[]>(() => {
  const count = pageCount.value;
  const current = props.page;
  const siblings = props.siblingCount;
  const totalNumbers = siblings * 2 + 5;

  if (count <= totalNumbers) {
    return Array.from({ length: count }, (_, i) => i + 1);
  }

  const left = Math.max(current - siblings, 2);
  const right = Math.min(current + siblings, count - 1);
  const showLeftDots = left > 2;
  const showRightDots = right < count - 1;

  const result: (number | string)[] = [1];
  if (showLeftDots) result.push('…');
  else for (let i = 2; i < left; i++) result.push(i);
  for (let i = left; i <= right; i++) result.push(i);
  if (showRightDots) result.push('…');
  else for (let i = right + 1; i < count; i++) result.push(i);
  result.push(count);
  return result;
});
</script>

<template>
  <nav v-if="pageCount > 1" class="ff-pg" aria-label="Pagination">
    <button
      type="button"
      class="ff-pg__btn ff-pg__btn--nav"
      :disabled="page <= 1"
      aria-label="Previous page"
      @click="$emit('update:page', page - 1)"
    >‹</button>
    <button
      v-for="(p, i) in visiblePages"
      :key="i"
      type="button"
      class="ff-pg__btn"
      :class="{ 'is-active': p === page, 'is-dots': typeof p !== 'number' }"
      :disabled="typeof p !== 'number'"
      :aria-current="p === page ? 'page' : undefined"
      @click="typeof p === 'number' && $emit('update:page', p)"
    >{{ p }}</button>
    <button
      type="button"
      class="ff-pg__btn ff-pg__btn--nav"
      :disabled="page >= pageCount"
      aria-label="Next page"
      @click="$emit('update:page', page + 1)"
    >›</button>
  </nav>
</template>

<style scoped>
.ff-pg {
  display: inline-flex; gap: 2px;
  font-family: var(--font-mono);
  font-feature-settings: 'tnum';
  font-size: var(--text-label);
}
.ff-pg__btn {
  min-width: 28px; height: 28px;
  padding: 0 6px;
  border: 1px solid var(--border-default);
  background: var(--surface-raised);
  color: var(--text-secondary);
  font-family: var(--font-mono);
  font-size: var(--text-label);
  cursor: pointer;
  display: inline-flex; align-items: center; justify-content: center;
  border-radius: 0;
  transition: background var(--mo-duration-fast) var(--mo-easing),
              color var(--mo-duration-fast) var(--mo-easing);
}
.ff-pg__btn:hover:not(:disabled):not(.is-dots) {
  background: var(--surface-inset);
  color: var(--text-primary);
}
.ff-pg__btn.is-active {
  background: var(--ac);
  color: var(--ac-fg);
  border-color: var(--ac);
}
.ff-pg__btn:disabled:not(.is-dots) { opacity: 0.4; cursor: not-allowed; }
.ff-pg__btn.is-dots { background: transparent; border-color: transparent; cursor: default; }
</style>
