<script setup lang="ts">
import Icon from '../atoms/Icon.vue';
import IconButton from './IconButton.vue';

defineProps<{ modelValue: string; placeholder?: string; disabled?: boolean }>();

defineEmits<{ 'update:modelValue': [value: string] }>();
</script>

<template>
  <div class="ff-searchfield">
    <Icon name="search" :size="16" class="ff-searchfield-icon" />
    <input
      class="ff-searchfield-input"
      type="text"
      :value="modelValue"
      :placeholder="placeholder ?? 'Search…'"
      :disabled="disabled"
      @input="$emit('update:modelValue', ($event.target as HTMLInputElement).value)"
    />
    <IconButton
      v-if="modelValue"
      icon="close"
      label="Clear"
      size="sm"
      class="ff-searchfield-clear"
      @click="$emit('update:modelValue', '')"
    />
  </div>
</template>

<style scoped>
.ff-searchfield {
  display: inline-flex; align-items: center; gap: 8px;
  height: 32px; padding: 0 12px;
  background: var(--surface-inset);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-sm);
  transition: border-color var(--mo-duration-fast) var(--mo-easing);
}
.ff-searchfield:focus-within { border-color: var(--ac); }
.ff-searchfield-icon { color: var(--text-dim); flex-shrink: 0; }
.ff-searchfield-input {
  flex: 1;
  background: transparent; border: 0; outline: none;
  font-family: var(--font-sans); font-size: var(--text-body);
  color: var(--text-primary);
}
.ff-searchfield-input::placeholder { color: var(--text-dim); }
</style>
