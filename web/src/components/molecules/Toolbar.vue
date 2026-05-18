<script setup lang="ts">
import { computed, useSlots } from 'vue';
import Divider from '../atoms/Divider.vue';

const slots = useSlots();
const hasSplit = computed(() => !!slots.split);
</script>

<template>
  <div class="ff-toolbar" role="toolbar">
    <div class="ff-toolbar-group">
      <slot />
    </div>
    <Divider v-if="hasSplit" orientation="vertical" class="ff-toolbar-divider" />
    <div v-if="hasSplit" class="ff-toolbar-group">
      <slot name="split" />
    </div>
  </div>
</template>

<style scoped>
.ff-toolbar { display: inline-flex; align-items: center; gap: 4px; }
.ff-toolbar-group { display: inline-flex; align-items: center; gap: 4px; }
.ff-toolbar-divider { height: 20px; margin: 0 6px; }
</style>
