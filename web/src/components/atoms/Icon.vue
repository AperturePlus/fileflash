<script setup lang="ts">
import { computed } from 'vue';
import { ICONS, type IconName } from './icons';

const props = withDefaults(defineProps<{
  name: IconName;
  size?: number;
  label?: string;
}>(), { size: 18 });

const path = computed(() => ICONS[props.name]);
// Use boolean true for aria-hidden so the SVGAttributes type accepts the spread.
// Vue serialises true to the string "true" in the DOM.
const a11y = computed(() =>
  props.label
    ? { role: 'img', 'aria-label': props.label }
    : { 'aria-hidden': true },
);
</script>

<template>
  <svg
    xmlns="http://www.w3.org/2000/svg"
    :width="size"
    :height="size"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    stroke-width="2"
    stroke-linecap="round"
    stroke-linejoin="round"
    v-bind="a11y"
  >
    <path :d="path" />
  </svg>
</template>
