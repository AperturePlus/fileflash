<script setup lang="ts">
defineProps<{ visible: boolean }>();
</script>

<template>
  <aside :class="['right-sidebar', { visible }]">
    <p class="right-sidebar__placeholder">Reserved for future use.</p>
  </aside>
</template>

<style scoped>
.right-sidebar {
  width: var(--sidebar-right-width);
  margin-right: calc(-1 * var(--sidebar-right-width));
  border-left: 1px solid var(--border-default);
  background: var(--surface-raised);
  display: flex;
  flex-direction: column;
  transition: margin-right var(--mo-duration-mid) var(--mo-easing);
}
.right-sidebar.visible {
  margin-right: 0;
}
.right-sidebar__placeholder {
  padding: var(--sp-md);
  color: var(--text-dim);
  font-size: var(--text-small);
}
</style>
