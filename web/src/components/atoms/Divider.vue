<script setup lang="ts">
withDefaults(defineProps<{ orientation?: 'horizontal' | 'vertical' }>(), {
  orientation: 'horizontal',
});
</script>

<template>
  <hr v-if="orientation === 'horizontal'" class="ff-divider ff-divider--h" />
  <span v-else class="ff-divider ff-divider--v" aria-hidden="true" />
</template>

<style scoped>
.ff-divider { border: 0; margin: 0; padding: 0; }
.ff-divider--h { border-top: 1px solid var(--border-subtle); width: 100%; }
.ff-divider--v {
  display: inline-block;
  border-left: 1px solid var(--border-subtle);
  width: 0;
  height: 1em;
  vertical-align: middle;
}
</style>
