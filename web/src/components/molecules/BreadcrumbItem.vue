<script setup lang="ts">
import Icon from '../atoms/Icon.vue';

defineProps<{ href?: string }>();
</script>

<template>
  <span class="ff-breadcrumb-item">
    <a v-if="href" :href="href" class="ff-breadcrumb-link"><slot /></a>
    <span v-else class="ff-breadcrumb-current"><slot /></span>
    <Icon v-if="href" name="chevronRight" :size="12" class="ff-breadcrumb-sep" />
  </span>
</template>

<style scoped>
.ff-breadcrumb-item { display: inline-flex; align-items: center; gap: 6px; }
.ff-breadcrumb-link { color: var(--text-secondary); text-decoration: none; font-size: var(--text-body); transition: color var(--mo-duration-fast) var(--mo-easing); }
.ff-breadcrumb-link:hover { color: var(--text-primary); }
.ff-breadcrumb-current { color: var(--text-primary); font-size: var(--text-body); font-weight: var(--weight-medium); }
.ff-breadcrumb-sep { color: var(--text-dim); }
</style>
