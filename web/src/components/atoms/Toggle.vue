<script setup lang="ts">
const props = defineProps<{ modelValue: boolean; disabled?: boolean; label?: string }>();
const emit = defineEmits<{ 'update:modelValue': [value: boolean] }>();

function onClick() {
  if (!props.disabled) emit('update:modelValue', !props.modelValue);
}
</script>

<template>
  <button
    type="button"
    role="switch"
    class="ff-toggle"
    :class="{ 'ff-toggle--on': modelValue, 'ff-toggle--disabled': disabled }"
    :aria-checked="modelValue ? 'true' : 'false'"
    :disabled="disabled"
    @click="onClick"
  >
    <span class="ff-toggle-track" aria-hidden="true">
      <span class="ff-toggle-thumb" />
    </span>
    <span v-if="label" class="ff-toggle-label">{{ label }}</span>
  </button>
</template>

<style scoped>
.ff-toggle {
  display: inline-flex; align-items: center; gap: 8px;
  background: transparent; border: 0; padding: 0;
  cursor: pointer; color: inherit;
}
.ff-toggle-track {
  position: relative; display: inline-block;
  width: 32px; height: 18px;
  background: var(--surface-inset);
  border: 1px solid var(--border-default);
  border-radius: 999px;
  transition: background-color var(--mo-duration-fast) var(--mo-easing),
              border-color var(--mo-duration-fast) var(--mo-easing);
}
.ff-toggle-thumb {
  position: absolute; top: 50%; left: 3px;
  width: 12px; height: 12px;
  background: var(--text-dim);
  border-radius: 50%;
  transform: translateY(-50%);
  transition: left var(--mo-duration-fast) var(--mo-easing),
              background-color var(--mo-duration-fast) var(--mo-easing);
}
.ff-toggle--on .ff-toggle-track { background: var(--ac); border-color: var(--ac); }
.ff-toggle--on .ff-toggle-thumb { left: 17px; background: var(--ac-fg); }
.ff-toggle--disabled { opacity: 0.5; cursor: not-allowed; }
.ff-toggle-label { font-size: var(--text-body); color: var(--text-secondary); }
</style>
