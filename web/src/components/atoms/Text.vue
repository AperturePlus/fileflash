<script setup lang="ts">
export type TextVariant = 'display' | 'h1' | 'h2' | 'body' | 'small' | 'label' | 'data';

withDefaults(defineProps<{
  variant?: TextVariant;
  as?: string;
}>(), {
  variant: 'body',
  as: 'span',
});
</script>

<template>
  <component :is="as" class="ff-text" :class="`ff-text--${variant}`">
    <slot />
  </component>
</template>

<style scoped>
.ff-text {
  font-family: var(--font-sans);
  color: var(--text-primary);
  line-height: var(--leading-normal);
  margin: 0;
}

.ff-text--display { font-size: var(--text-display); font-weight: var(--weight-semibold); letter-spacing: var(--tracking-tight); line-height: var(--leading-tight); }
.ff-text--h1      { font-size: var(--text-h1); font-weight: var(--weight-semibold); letter-spacing: var(--tracking-snug); line-height: var(--leading-snug); }
.ff-text--h2      { font-size: var(--text-h2); font-weight: var(--weight-semibold); letter-spacing: var(--tracking-snug); line-height: var(--leading-snug); }
.ff-text--body    { font-size: var(--text-body); font-weight: var(--weight-regular); }
.ff-text--small   { font-size: var(--text-small); color: var(--text-secondary); }
.ff-text--label   { font-size: var(--text-label); font-family: var(--font-mono); color: var(--text-dim); text-transform: uppercase; letter-spacing: var(--tracking-wider); font-weight: var(--weight-medium); }
.ff-text--data    { font-size: var(--text-data); font-family: var(--font-mono); font-feature-settings: "tnum"; }
</style>
