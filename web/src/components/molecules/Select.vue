<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from 'vue';
import Icon from '../atoms/Icon.vue';

interface SelectOption {
  value: string | number;
  label: string;
}

const props = withDefaults(
  defineProps<{
    modelValue: string | number;
    options: SelectOption[];
    size?: 'sm' | 'md';
    placeholder?: string;
    disabled?: boolean;
  }>(),
  { size: 'md', placeholder: 'Select…' },
);

const emit = defineEmits<{ 'update:modelValue': [value: string | number] }>();

const rootEl = ref<HTMLElement | null>(null);
const open = ref(false);
const activeIndex = ref(-1);
const placement = ref<'down' | 'up'>('down');
const menuMaxHeight = ref<number>(240);

const selectedLabel = computed(() => {
  const m = props.options.find((o) => o.value === props.modelValue);
  return m?.label ?? '';
});

const MENU_HARD_CAP = 240;
const MENU_MIN_HEIGHT = 80;
const ROW_HEIGHT = 24;
const MENU_GAP = 8;

const updatePlacement = () => {
  if (!rootEl.value || typeof window === 'undefined') return;
  const rect = rootEl.value.getBoundingClientRect();
  const vh = window.innerHeight || document.documentElement.clientHeight;
  const spaceBelow = Math.max(0, vh - rect.bottom - MENU_GAP);
  const spaceAbove = Math.max(0, rect.top - MENU_GAP);
  const naturalHeight = Math.min(MENU_HARD_CAP, props.options.length * ROW_HEIGHT + 8);

  if (spaceBelow >= naturalHeight || spaceBelow >= spaceAbove) {
    placement.value = 'down';
    menuMaxHeight.value = Math.max(MENU_MIN_HEIGHT, Math.min(MENU_HARD_CAP, spaceBelow));
  } else {
    placement.value = 'up';
    menuMaxHeight.value = Math.max(MENU_MIN_HEIGHT, Math.min(MENU_HARD_CAP, spaceAbove));
  }
};

const toggle = () => {
  if (props.disabled) return;
  const next = !open.value;
  if (next) {
    updatePlacement();
    const i = props.options.findIndex((o) => o.value === props.modelValue);
    activeIndex.value = i >= 0 ? i : 0;
  }
  open.value = next;
};

const pick = (value: string | number) => {
  emit('update:modelValue', value);
  open.value = false;
};

const onKey = (e: KeyboardEvent) => {
  if (props.disabled) return;
  if (!open.value) {
    if (e.key === 'Enter' || e.key === ' ' || e.key === 'ArrowDown') {
      e.preventDefault();
      toggle();
    }
    return;
  }
  if (e.key === 'Escape') { open.value = false; return; }
  if (e.key === 'ArrowDown') {
    e.preventDefault();
    activeIndex.value = (activeIndex.value + 1) % props.options.length;
  } else if (e.key === 'ArrowUp') {
    e.preventDefault();
    activeIndex.value = (activeIndex.value - 1 + props.options.length) % props.options.length;
  } else if (e.key === 'Enter') {
    e.preventDefault();
    const opt = props.options[activeIndex.value];
    if (opt) pick(opt.value);
  }
};

const onDocClick = (e: MouseEvent) => {
  if (!open.value || !rootEl.value) return;
  if (!rootEl.value.contains(e.target as Node)) open.value = false;
};

const onViewportChange = () => {
  if (!open.value) return;
  // Defer to next frame to let layout settle before remeasure.
  nextTick(updatePlacement);
};

onMounted(() => {
  document.addEventListener('mousedown', onDocClick);
  window.addEventListener('resize', onViewportChange);
  window.addEventListener('scroll', onViewportChange, true);
});
onBeforeUnmount(() => {
  document.removeEventListener('mousedown', onDocClick);
  window.removeEventListener('resize', onViewportChange);
  window.removeEventListener('scroll', onViewportChange, true);
});
</script>

<template>
  <div
    ref="rootEl"
    class="ff-select"
    :class="[`ff-select--${size}`, { 'is-open': open, 'is-disabled': disabled }]"
    tabindex="0"
    @keydown="onKey"
  >
    <button
      type="button"
      class="ff-select__trigger"
      :disabled="disabled"
      @click="toggle"
    >
      <span class="ff-select__value" :class="{ 'is-placeholder': !selectedLabel }">
        {{ selectedLabel || placeholder }}
      </span>
      <Icon :name="open ? 'chevronUp' : 'chevronDown'" :size="size === 'sm' ? 12 : 14" />
    </button>
    <ul
      v-if="open"
      class="ff-select__menu"
      :class="`ff-select__menu--${placement}`"
      :style="{ maxHeight: `${menuMaxHeight}px` }"
      role="listbox"
    >
      <li
        v-for="(opt, i) in options"
        :key="opt.value"
        class="ff-select__option"
        :class="{
          'is-active': i === activeIndex,
          'is-selected': opt.value === modelValue,
        }"
        role="option"
        :aria-selected="opt.value === modelValue ? 'true' : 'false'"
        @click="pick(opt.value)"
        @mouseenter="activeIndex = i"
      >
        {{ opt.label }}
      </li>
    </ul>
  </div>
</template>

<style scoped>
.ff-select {
  position: relative;
  display: inline-block;
  font-family: var(--font-mono);
  font-size: var(--text-label);
  letter-spacing: var(--tracking-wide);
  text-transform: uppercase;
  outline: none;
  min-width: 120px;
}
.ff-select__trigger {
  display: inline-flex; align-items: center; gap: var(--sp-xs);
  width: 100%;
  background: var(--surface-raised);
  color: var(--text-primary);
  border: 1px solid var(--border-default);
  border-radius: 0;
  padding: 0 var(--sp-sm);
  font: inherit;
  letter-spacing: inherit;
  text-transform: inherit;
  cursor: pointer;
  transition: border-color var(--mo-duration-fast) var(--mo-easing);
}
.ff-select--sm .ff-select__trigger { height: 24px; font-size: 9px; }
.ff-select--md .ff-select__trigger { height: 32px; }
.ff-select__trigger:hover:not(:disabled),
.ff-select.is-open .ff-select__trigger { border-color: var(--ac); }
.ff-select__trigger:disabled { opacity: 0.5; cursor: not-allowed; }
.ff-select__value { flex: 1; text-align: left; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.ff-select__value.is-placeholder { color: var(--text-tertiary); }

.ff-select__menu {
  position: absolute; left: 0; right: 0;
  background: var(--surface-raised);
  border: 1px solid var(--border-default);
  border-radius: 0;
  padding: 0;
  margin: 0;
  list-style: none;
  z-index: 50;
  max-height: 240px;
  overflow: auto;
}
.ff-select__menu--down { top: calc(100% + 2px); }
.ff-select__menu--up { bottom: calc(100% + 2px); }
.ff-select__option {
  padding: var(--sp-xs) var(--sp-sm);
  color: var(--text-secondary);
  cursor: pointer;
}
.ff-select__option.is-active { background: var(--surface-inset); color: var(--text-primary); }
.ff-select__option.is-selected { color: var(--ac); }
</style>
