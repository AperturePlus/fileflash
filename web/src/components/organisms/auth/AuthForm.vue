<script setup lang="ts">
import { ref, watch } from 'vue';
import { Icon, Input, Checkbox, Text } from '../../atoms';
import { Button } from '../../molecules';

export type LoginValues = { identifier: string; password: string; rememberMe: boolean };
export type RegisterValues = { username: string; email: string; password: string; confirmPassword: string };
export type ForgotValues = { email: string };
export type AuthSubmitPayload =
  | { mode: 'login'; values: LoginValues }
  | { mode: 'register'; values: RegisterValues }
  | { mode: 'forgot'; values: ForgotValues };

export interface AuthFormLabels {
  identifier?: string; identifierPlaceholder?: string;
  username?: string;   usernamePlaceholder?: string;
  email?: string;      emailPlaceholder?: string;
  password?: string;   passwordPlaceholder?: string;
  confirmPassword?: string; confirmPasswordPlaceholder?: string;
  rememberMe?: string;
}

const props = defineProps<{
  mode: 'login' | 'register' | 'forgot';
  title: string;
  subtitle?: string;
  submitLabel: string;
  isSubmitting?: boolean;
  errorMessage?: string;
  successMessage?: string;
  labels: AuthFormLabels;
  initial?: { identifier?: string; username?: string; email?: string; rememberMe?: boolean };
}>();

const emit = defineEmits<{ submit: [AuthSubmitPayload] }>();

const identifier = ref('');
const username = ref('');
const email = ref('');
const password = ref('');
const confirmPassword = ref('');
const rememberMe = ref(false);
const showPassword = ref(false);
const showConfirmPassword = ref(false);

watch(
  () => props.initial,
  (next) => {
    if (!next) return;
    if (typeof next.identifier === 'string') identifier.value = next.identifier;
    if (typeof next.username === 'string') username.value = next.username;
    if (typeof next.email === 'string') email.value = next.email;
    if (typeof next.rememberMe === 'boolean') rememberMe.value = next.rememberMe;
  },
  { immediate: true, deep: true },
);

function onSubmit() {
  if (props.mode === 'login') {
    emit('submit', { mode: 'login', values: { identifier: identifier.value, password: password.value, rememberMe: rememberMe.value } });
  } else if (props.mode === 'register') {
    emit('submit', { mode: 'register', values: { username: username.value, email: email.value, password: password.value, confirmPassword: confirmPassword.value } });
  } else {
    emit('submit', { mode: 'forgot', values: { email: email.value } });
  }
}
</script>

<template>
  <form class="ff-auth" @submit.prevent="onSubmit">
    <header class="ff-auth__head">
      <Text variant="h1" as="h1">{{ title }}</Text>
      <Text v-if="subtitle" variant="small" as="p" class="ff-auth__subtitle">{{ subtitle }}</Text>
      <slot name="hint" />
    </header>

    <div class="ff-auth__fields">
      <template v-if="mode === 'login'">
        <label class="ff-auth__field">
          <Text variant="label" as="span">{{ labels.identifier }}</Text>
          <Input
            v-model="identifier"
            type="text"
            :placeholder="labels.identifierPlaceholder"
          />
        </label>
        <label class="ff-auth__field">
          <Text variant="label" as="span">{{ labels.password }}</Text>
          <div class="ff-auth__password">
            <Input
              v-model="password"
              :type="showPassword ? 'text' : 'password'"
              :placeholder="labels.passwordPlaceholder"
            />
            <button
              type="button"
              data-test="toggle-password"
              class="ff-auth__eye"
              aria-label="Toggle password visibility"
              @click="showPassword = !showPassword"
            >
              <Icon :name="showPassword ? 'eyeOff' : 'eye'" :size="14" />
            </button>
          </div>
        </label>
        <div class="ff-auth__row">
          <Checkbox v-model="rememberMe" :label="labels.rememberMe" />
          <slot name="secondary" />
        </div>
      </template>

      <template v-else-if="mode === 'register'">
        <label class="ff-auth__field">
          <Text variant="label" as="span">{{ labels.username }}</Text>
          <Input v-model="username" type="text" :placeholder="labels.usernamePlaceholder" />
        </label>
        <label class="ff-auth__field">
          <Text variant="label" as="span">{{ labels.email }}</Text>
          <Input v-model="email" type="email" :placeholder="labels.emailPlaceholder" />
        </label>
        <label class="ff-auth__field">
          <Text variant="label" as="span">{{ labels.password }}</Text>
          <div class="ff-auth__password">
            <Input
              v-model="password"
              :type="showPassword ? 'text' : 'password'"
              :placeholder="labels.passwordPlaceholder"
            />
            <button
              type="button"
              data-test="toggle-password"
              class="ff-auth__eye"
              aria-label="Toggle password visibility"
              @click="showPassword = !showPassword"
            >
              <Icon :name="showPassword ? 'eyeOff' : 'eye'" :size="14" />
            </button>
          </div>
        </label>
        <label class="ff-auth__field">
          <Text variant="label" as="span">{{ labels.confirmPassword }}</Text>
          <div class="ff-auth__password">
            <Input
              v-model="confirmPassword"
              :type="showConfirmPassword ? 'text' : 'password'"
              :placeholder="labels.confirmPasswordPlaceholder"
            />
            <button
              type="button"
              data-test="toggle-confirm-password"
              class="ff-auth__eye"
              aria-label="Toggle confirm password visibility"
              @click="showConfirmPassword = !showConfirmPassword"
            >
              <Icon :name="showConfirmPassword ? 'eyeOff' : 'eye'" :size="14" />
            </button>
          </div>
        </label>
      </template>

      <template v-else>
        <label class="ff-auth__field">
          <Text variant="label" as="span">{{ labels.email }}</Text>
          <Input v-model="email" type="email" :placeholder="labels.emailPlaceholder" />
        </label>
      </template>
    </div>

    <div
      v-if="errorMessage || successMessage"
      role="status"
      :class="['ff-auth__msg', errorMessage ? 'ff-auth__msg--error' : 'ff-auth__msg--success']"
    >
      {{ errorMessage || successMessage }}
    </div>

    <Button
      type="submit"
      variant="primary"
      :loading="isSubmitting"
      :disabled="isSubmitting"
      class="ff-auth__submit"
    >
      {{ submitLabel }}
    </Button>

    <footer class="ff-auth__footer">
      <slot name="footer" />
    </footer>
  </form>
</template>

<style scoped>
.ff-auth {
  display: flex;
  flex-direction: column;
  gap: var(--sp-lg);
}
.ff-auth__head {
  display: flex;
  flex-direction: column;
  gap: var(--sp-xs);
}
.ff-auth__subtitle {
  color: var(--text-secondary);
}
.ff-auth__fields {
  display: flex;
  flex-direction: column;
  gap: var(--sp-md);
}
.ff-auth__field {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.ff-auth__password {
  position: relative;
}
.ff-auth__password :deep(.ff-input) {
  padding-right: 36px;
}
.ff-auth__eye {
  position: absolute;
  top: 50%;
  right: 4px;
  transform: translateY(-50%);
  width: 26px;
  height: 26px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  background: transparent;
  border: none;
  color: var(--text-dim);
  cursor: pointer;
  border-radius: var(--radius-sm);
}
.ff-auth__eye:hover {
  color: var(--text-primary);
  background: var(--surface-inset);
}
.ff-auth__row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: var(--sp-sm);
}
.ff-auth__msg {
  padding: var(--sp-sm) var(--sp-md);
  border: 1px solid var(--border-default);
  font-size: var(--text-small);
  font-family: var(--font-mono);
}
.ff-auth__msg--error {
  color: var(--status-error);
  border-color: var(--status-error);
}
.ff-auth__msg--success {
  color: var(--status-success);
  border-color: var(--status-success);
}
.ff-auth__submit {
  width: 100%;
  justify-content: center;
  height: 40px;
}
.ff-auth__footer {
  display: flex;
  justify-content: center;
  gap: var(--sp-sm);
  font-size: var(--text-small);
  color: var(--text-secondary);
}
.ff-auth__footer :deep(a) {
  color: var(--ac);
  text-decoration: none;
}
.ff-auth__footer :deep(a:hover) {
  text-decoration: underline;
}
</style>
