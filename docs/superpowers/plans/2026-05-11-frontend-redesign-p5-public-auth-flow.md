# P5 Public Auth Flow Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rewrite the 4 public auth pages (`/login`, `/register`, `/forgot-password`, `/verify-email`) against the new Industrial Dashboard system. Build a shared `AuthForm` organism that drives Login / Register / ForgotPassword via a `mode` prop. Each page file must be ≤ 100 lines and contain only API + nav orchestration. VerifyEmail uses BareLayout with inline atoms/molecules (no AuthForm — no fields). Functional parity required: no behavior is dropped.

**Architecture:**
- `components/organisms/auth/AuthForm.vue` — single organism owning the visual shell + per-mode field set. Discriminated `submit` payload keeps page logic typed.
- `components/organisms/auth/index.ts` — public barrel.
- `pages/login/Login.vue`, `pages/register/Register.vue`, `pages/forgot-password/ForgotPassword.vue` — rewritten ≤ 100 lines each, mount `AuthForm` and react to its `submit` event.
- `pages/verify-email/VerifyEmail.vue` — rewritten ≤ 100 lines, uses atoms (`Text`, `Spinner`, `Dot`) + `Button` molecule directly. No form fields.
- `pages/__dev/Library.vue` — adds an `Organisms · Auth` section demoing all 3 AuthForm modes + the VerifyEmail status block.
- **Not deleted in P5:** the existing `AuthLayout.vue` still imports `useThemeStore` from `store/theme.ts`. Don't touch that — P6 replaces themeStore with preferencesStore.

**Tech Stack:** Vue 3 `<script setup>`, TypeScript strict, Pinia (`useUserStore`), Vitest + happy-dom + `web/src/test/mount.ts` helper, design tokens from `web/src/styles/tokens/*`. Run commands: `bun run test` / `bun run check` / `bun run build`. CWD for scripts: `web/`. **Never use `npm`/`npx`** — bun only.

**Spec reference:** `docs/superpowers/specs/2026-05-11-frontend-quality-redesign-design.md` §3.1 (`organisms/auth/AuthForm.vue` Login/Register/ForgotPassword 共用), §3.2 (pages ≤ 100 lines), §4 (P5 row: "Public Auth Flow — Login / Register / ForgotPassword / VerifyEmail (共享 AuthForm)"), §5.3 (route layout — already wired in router/routes.ts), §9 (acceptance — 3 accent × 2 theme × 2 motion = 12 combos render correctly, no console errors, reduced-motion compliance).

**Predecessor:** P4 Other File Surfaces (commit `6f3a997`). All 6 sharing/trash/share organisms + 3 page rewrites are live; baseline `bun run test` = 50 files / 263 tests green; `bun run check` clean.

---

## Pre-flight

- [ ] **Step 0a: Confirm P4 commit is on develop**

```bash
git log --oneline | head -5
```

Expected: `6f3a997 feat(p4): migrate Shared / Trash / ShareAccess to industrial dashboard` is the most recent or near-top commit.

- [ ] **Step 0b: Verify test + check + build still clean**

```bash
cd web && bun run test && bun run check && bun run build
```

Expected: all green. If `bun run test` reports failures unrelated to this plan, stop and surface them before continuing.

- [ ] **Step 0c: Skim current auth pages so you know what behavior must be preserved**

Read these files (baseline line counts at top of each — these MUST shrink to ≤ 100):

1. `web/src/pages/login/Login.vue` (267 lines). Behaviors to keep:
   - Username + password form, submit calls `userStore.login({ username, password })`.
   - On success: if `user.emailVerified` push `/files`, else push `/verify-email`.
   - On error: show `error.message` or fallback "Login failed. Please check your credentials.".
   - Remember-me checkbox: if checked, write `localStorage['rememberMe'] = 'true'` + `localStorage['savedUsername'] = username`; if unchecked, remove both.
   - On mount: read those keys, prefill username + checkbox if `rememberMe === 'true'`.
   - Password show/hide toggle (text "Show" / "Hide").
   - Test-account hint block (admin/admin123, demo/demo123) — keep (product not live; useful for QA per spec §1).
   - Footer link "Create one" → `/register`.
   - Side link "Forgot password" → `/forgot-password`.

2. `web/src/pages/register/Register.vue` (225 lines). Behaviors:
   - Username + email + password + confirmPassword fields. Calls `register({ username, email, password })` from `api/user.ts`.
   - Client-side check: if `password !== confirmPassword`, show "两次输入的密码不一致。" and abort.
   - On success: if `response.emailVerificationRequired` push `/verify-email`, else push `/login`.
   - On error: show error message or "注册失败，请稍后再试。".
   - Two password fields each have show/hide toggle.
   - Footer link "前往登录" → `/login`. Strings are Chinese — preserve language exactly.

3. `web/src/pages/forgot-password/ForgotPassword.vue` (151 lines). Behaviors:
   - Email field only. Calls `forgotPassword(email)` from `api/user.ts`.
   - On success: show "重置邮件已发送，请检查邮箱。".
   - On error: show error.message or "发送失败，请稍后再试。".
   - Footer "返回登录" → `/login`. Strings are Chinese — preserve.

4. `web/src/pages/verify-email/VerifyEmail.vue` (195 lines). Behaviors:
   - Status state machine: `idle` → `pending` → `success` | `error`.
   - On mount: if `route.query.token` is a string, call `verifyEmail(token)`; on success call `userStore.fetchUserProfile()`; set status accordingly.
   - If no token but `userStore.user?.emailVerified`, show "Your email has already been verified." with status `success`.
   - Otherwise show initial message: "A verification link has been sent to your email. Please verify your account.".
   - Resend button visible when `userStore.isAuthenticated && !user?.emailVerified`. Click calls `resendVerification()`.
   - Footer: "Back to login" button → `/login`; "Enter files" button (only when authenticated) → `/files`. Strings are English — preserve.

Write a one-line scratch note confirming each of the four pages and its behaviors above is understood before proceeding.

---

## File Structure (locked before any task starts)

```
web/src/components/organisms/auth/
├── index.ts                  # public barrel
├── AuthForm.vue              # ~220 lines (template + style + script)
└── AuthForm.spec.ts          # ~180 lines

web/src/pages/login/Login.vue               # ≤ 100 lines (was 267)
web/src/pages/register/Register.vue         # ≤ 100 lines (was 225)
web/src/pages/forgot-password/ForgotPassword.vue  # ≤ 100 lines (was 151)
web/src/pages/verify-email/VerifyEmail.vue  # ≤ 100 lines (was 195)
web/src/pages/__dev/Library.vue             # +1 section "Organisms · Auth"
```

**Import policy:** AuthForm imports only from `../../atoms`, `../../molecules`. Pages import only from `components/organisms/auth` + composables/stores/api. No `common/*` imports from new auth code. No hex literals — token vars only. No `border-radius` other than `0` / `var(--radius-sm)` / `var(--radius-md)`. No `cubic-bezier(0.4, 0, 0.2, 1)` (legacy Material). No `Manrope`, no `translateY(-1px)` hover, no `backdrop-filter: blur`, no `linear-gradient` on buttons.

---

## Phase A — Build the shared organism

### Task 1: AuthForm organism (TDD, mode-aware)

**Files:**
- Create: `web/src/components/organisms/auth/AuthForm.vue`
- Create: `web/src/components/organisms/auth/AuthForm.spec.ts`
- Create: `web/src/components/organisms/auth/index.ts`

**Design notes:**
- Discriminated submit payload — TypeScript enforces correct destructure in pages:

  ```ts
  type LoginValues = { identifier: string; password: string; rememberMe: boolean };
  type RegisterValues = { username: string; email: string; password: string; confirmPassword: string };
  type ForgotValues = { email: string };
  type AuthSubmitPayload =
    | { mode: 'login'; values: LoginValues }
    | { mode: 'register'; values: RegisterValues }
    | { mode: 'forgot'; values: ForgotValues };
  ```

- Props:

  ```ts
  defineProps<{
    mode: 'login' | 'register' | 'forgot';
    title: string;
    subtitle?: string;
    submitLabel: string;
    isSubmitting?: boolean;
    errorMessage?: string;
    successMessage?: string;
    labels: {
      identifier?: string; identifierPlaceholder?: string;
      username?: string;   usernamePlaceholder?: string;
      email?: string;      emailPlaceholder?: string;
      password?: string;   passwordPlaceholder?: string;
      confirmPassword?: string; confirmPasswordPlaceholder?: string;
      rememberMe?: string;
    };
    initial?: { identifier?: string; username?: string; email?: string; rememberMe?: boolean };
  }>();
  ```

- Emits:

  ```ts
  defineEmits<{ submit: [AuthSubmitPayload] }>();
  ```

- Layout (single `<form @submit.prevent="onSubmit">`):
  1. Header: `<Text variant="h1">{{ title }}</Text>` + optional `<Text variant="small">{{ subtitle }}</Text>` + `#hint` slot for the test-account block (used only by Login page).
  2. Fields by mode:
     - `login`: identifier (text), password (password + eye toggle), `<Checkbox>` for rememberMe inline with a `<router-link to="/forgot-password">{{ labels.forgotLink }}</router-link>`. **Wait** — the forgot link is page-routed; instead, expose a `#secondary` slot for the page to render it. AuthForm stays route-agnostic.
     - `register`: username, email, password (+eye), confirmPassword (+eye).
     - `forgot`: email only.
  3. Error/success block: a single `[role="status"]` div that renders `errorMessage` (red tinted) or `successMessage` (green tinted) — both styled via tokens.
  4. Submit button: `<Button variant="primary" type="submit" :loading="isSubmitting">{{ submitLabel }}</Button>` — full-width via `width: 100%`.
  5. Footer slot: `#footer` (used for the cross-links — "Create one" / "前往登录" / "返回登录").

- Internal state: 3 `ref()` for each possible field (`identifier`, `username`, `email`, `password`, `confirmPassword`, `rememberMe`) — only the ones for the current mode are exposed in the template, but defining all keeps types simple. `showPassword` / `showConfirmPassword` refs for the eye toggles.

- `onSubmit()` switches on `props.mode` and emits the right discriminated payload. Page handles validation that AuthForm doesn't (e.g. password mismatch for register).

- Watch `props.initial`. When `mode === 'login'` and `initial?.identifier` is non-empty, prefill `identifier.value` and `rememberMe.value`. Use `watchEffect` or a single `watch` with `immediate: true`.

- Password input is `<div class="ff-auth__password">` containing `<Input :type="showPassword ? 'text' : 'password'">` followed by `<button type="button" class="ff-auth__eye" aria-label="Toggle password visibility" @click="showPassword = !showPassword"><Icon :name="showPassword ? 'eyeOff' : 'eye'" :size="14" /></button>`. Same shape for confirmPassword.

- **No `border-radius` other than `var(--radius-sm)` on the eye button**. Submit button comes from Button molecule which already uses `var(--radius-sm)`.

- [ ] **Step 1: Create the public barrel**

```ts
// web/src/components/organisms/auth/index.ts
export { default as AuthForm } from './AuthForm.vue';
export type { AuthSubmitPayload, LoginValues, RegisterValues, ForgotValues } from './AuthForm.vue';
```

- [ ] **Step 2: Write the failing test**

```ts
// web/src/components/organisms/auth/AuthForm.spec.ts
import { describe, it, expect } from 'vitest';
import { nextTick } from 'vue';
import { mount } from '../../../test/mount';
import AuthForm from './AuthForm.vue';

const loginLabels = {
  identifier: 'Username or Email', identifierPlaceholder: 'Enter username or email',
  password: 'Password', passwordPlaceholder: 'Enter password',
  rememberMe: 'Remember me',
};
const registerLabels = {
  username: 'Username', usernamePlaceholder: 'Enter username',
  email: 'Email', emailPlaceholder: 'Enter email',
  password: 'Password', passwordPlaceholder: 'Enter password',
  confirmPassword: 'Confirm', confirmPasswordPlaceholder: 'Re-enter password',
};
const forgotLabels = {
  email: 'Email', emailPlaceholder: 'Enter email',
};

describe('AuthForm', () => {
  it('renders title and subtitle', () => {
    const wrapper = mount(AuthForm, {
      props: {
        mode: 'login', title: 'Sign in', subtitle: 'Manage files',
        submitLabel: 'SIGN IN', labels: loginLabels,
      },
    });
    expect(wrapper.text()).toContain('Sign in');
    expect(wrapper.text()).toContain('Manage files');
  });

  it('emits submit with login payload', async () => {
    const wrapper = mount(AuthForm, {
      props: {
        mode: 'login', title: 'Sign in', submitLabel: 'SIGN IN', labels: loginLabels,
      },
    });
    const inputs = wrapper.findAll('input');
    // Two text/password inputs + one checkbox => 3
    expect(inputs.length).toBe(3);
    await inputs[0].setValue('alice');
    await inputs[1].setValue('hunter2');
    await inputs[2].setValue(true); // checkbox
    await wrapper.find('form').trigger('submit.prevent');
    const evt = wrapper.emitted('submit');
    expect(evt).toBeTruthy();
    expect(evt?.[0]?.[0]).toEqual({
      mode: 'login',
      values: { identifier: 'alice', password: 'hunter2', rememberMe: true },
    });
  });

  it('emits submit with register payload', async () => {
    const wrapper = mount(AuthForm, {
      props: {
        mode: 'register', title: 'Sign up', submitLabel: 'REGISTER', labels: registerLabels,
      },
    });
    const inputs = wrapper.findAll('input[type="text"], input[type="email"], input[type="password"]');
    expect(inputs.length).toBe(4);
    await inputs[0].setValue('bob');
    await inputs[1].setValue('bob@example.com');
    await inputs[2].setValue('pw1');
    await inputs[3].setValue('pw2');
    await wrapper.find('form').trigger('submit.prevent');
    const evt = wrapper.emitted('submit');
    expect(evt?.[0]?.[0]).toEqual({
      mode: 'register',
      values: { username: 'bob', email: 'bob@example.com', password: 'pw1', confirmPassword: 'pw2' },
    });
  });

  it('emits submit with forgot payload', async () => {
    const wrapper = mount(AuthForm, {
      props: {
        mode: 'forgot', title: 'Forgot', submitLabel: 'SEND', labels: forgotLabels,
      },
    });
    const inputs = wrapper.findAll('input');
    expect(inputs.length).toBe(1);
    await inputs[0].setValue('carol@example.com');
    await wrapper.find('form').trigger('submit.prevent');
    expect(wrapper.emitted('submit')?.[0]?.[0]).toEqual({
      mode: 'forgot', values: { email: 'carol@example.com' },
    });
  });

  it('renders errorMessage in role=status', () => {
    const wrapper = mount(AuthForm, {
      props: {
        mode: 'forgot', title: 't', submitLabel: 'go', labels: forgotLabels,
        errorMessage: 'Email not found',
      },
    });
    const status = wrapper.find('[role="status"]');
    expect(status.exists()).toBe(true);
    expect(status.text()).toContain('Email not found');
    expect(status.classes()).toContain('ff-auth__msg--error');
  });

  it('renders successMessage in role=status', () => {
    const wrapper = mount(AuthForm, {
      props: {
        mode: 'forgot', title: 't', submitLabel: 'go', labels: forgotLabels,
        successMessage: 'Email sent',
      },
    });
    const status = wrapper.find('[role="status"]');
    expect(status.exists()).toBe(true);
    expect(status.text()).toContain('Email sent');
    expect(status.classes()).toContain('ff-auth__msg--success');
  });

  it('disables submit button when isSubmitting is true', async () => {
    const wrapper = mount(AuthForm, {
      props: {
        mode: 'forgot', title: 't', submitLabel: 'go', labels: forgotLabels,
        isSubmitting: true,
      },
    });
    const btn = wrapper.find('button[type="submit"]');
    expect((btn.element as HTMLButtonElement).disabled).toBe(true);
  });

  it('prefills login fields from initial prop', async () => {
    const wrapper = mount(AuthForm, {
      props: {
        mode: 'login', title: 't', submitLabel: 'go', labels: loginLabels,
        initial: { identifier: 'alice', rememberMe: true },
      },
    });
    await nextTick();
    const inputs = wrapper.findAll('input');
    expect((inputs[0].element as HTMLInputElement).value).toBe('alice');
    expect((inputs[2].element as HTMLInputElement).checked).toBe(true);
  });

  it('toggles password visibility via eye button', async () => {
    const wrapper = mount(AuthForm, {
      props: {
        mode: 'login', title: 't', submitLabel: 'go', labels: loginLabels,
      },
    });
    const pwInput = wrapper.findAll('input')[1];
    expect((pwInput.element as HTMLInputElement).type).toBe('password');
    await wrapper.find('[data-test="toggle-password"]').trigger('click');
    expect((pwInput.element as HTMLInputElement).type).toBe('text');
  });
});
```

- [ ] **Step 3: Run test to verify it fails**

```bash
cd web && bun x vitest run src/components/organisms/auth/AuthForm.spec.ts
```

Expected: FAIL with "Cannot find module './AuthForm.vue'".

- [ ] **Step 4: Implement AuthForm.vue**

```vue
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
      <!-- LOGIN -->
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

      <!-- REGISTER -->
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

      <!-- FORGOT -->
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
  background: rgb(var(--ac-rgb) / 0);
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
.ff-auth__footer :deep(a),
.ff-auth__footer :deep(button.ff-auth-link) {
  color: var(--ac);
  text-decoration: none;
  background: transparent;
  border: none;
  cursor: pointer;
  font: inherit;
  padding: 0;
}
.ff-auth__footer :deep(a:hover),
.ff-auth__footer :deep(button.ff-auth-link:hover) {
  text-decoration: underline;
}
</style>
```

- [ ] **Step 5: Run tests to verify pass**

```bash
cd web && bun x vitest run src/components/organisms/auth/AuthForm.spec.ts && bun run check
```

Expected: 9 passing, type-check clean. If a spec assertion fails because input order in `findAll('input')` differs from expectation (Checkbox is rendered as `<input type="checkbox">` inside the molecule), tighten the selectors: use `input[type="text"]`, `input[type="password"]`, `input[type="checkbox"]` rather than positional indexing. Do NOT change the production code to match a flaky test.

- [ ] **Step 6: Commit**

```bash
git add web/src/components/organisms/auth/AuthForm.vue \
        web/src/components/organisms/auth/AuthForm.spec.ts \
        web/src/components/organisms/auth/index.ts
git commit -m "feat(organisms/auth): add AuthForm (login/register/forgot modes)"
```

---

## Phase B — Dev library coverage

### Task 2: Add `Organisms · Auth` section to Library

**Files:**
- Modify: `web/src/pages/__dev/Library.vue`

**Design notes:**
- Extend the `sections` tuple with `'Organisms · Auth'`.
- Add demo state refs: `authMode: 'login' | 'register' | 'forgot'`, `authSubmitting`, `authError`, `authSuccess`, `lastSubmit`.
- A small SegmentedControl (already used elsewhere) lets the reader switch between the 3 modes live.
- Three label bundles (English, ASCII only) so the reader can see what each mode renders.
- A `<pre>` panel shows the most recent submit payload for sanity.

- [ ] **Step 1: Edit `pages/__dev/Library.vue`**

In the existing `<script setup>`, after the existing imports, add:

```ts
import { AuthForm } from '../../components/organisms/auth';
import type { AuthSubmitPayload } from '../../components/organisms/auth';
```

Extend the `sections` tuple:

```ts
const sections = [
  'Tokens', 'Atoms · Text', 'Atoms · Numbers', 'Atoms · Visual', 'Atoms · Form',
  'Molecules · Action', 'Molecules · Input', 'Molecules · Display', 'Molecules · Nav',
  'Organisms · Files', 'Organisms · Sharing', 'Organisms · Trash', 'Organisms · Share',
  'Organisms · Auth',
] as const;
```

Add auth demo state somewhere near the existing demo state block:

```ts
const authMode = ref<'login' | 'register' | 'forgot'>('login');
const authSubmitting = ref(false);
const authError = ref('');
const authSuccess = ref('');
const lastAuthSubmit = ref('');
const authLabelsByMode = {
  login: {
    identifier: 'Username or Email', identifierPlaceholder: 'Enter username or email',
    password: 'Password', passwordPlaceholder: 'Enter password',
    rememberMe: 'Remember me',
  },
  register: {
    username: 'Username', usernamePlaceholder: 'Enter username',
    email: 'Email', emailPlaceholder: 'Enter email',
    password: 'Password', passwordPlaceholder: 'Enter password',
    confirmPassword: 'Confirm', confirmPasswordPlaceholder: 'Re-enter password',
  },
  forgot: {
    email: 'Email', emailPlaceholder: 'Enter email',
  },
};
const authTitleByMode = { login: 'Sign in to FileFlash', register: 'Create account', forgot: 'Reset password' };
const authSubmitLabelByMode = { login: 'SIGN IN', register: 'REGISTER', forgot: 'SEND LINK' };
function onAuthSubmit(payload: AuthSubmitPayload) {
  lastAuthSubmit.value = JSON.stringify(payload, null, 2);
  authSuccess.value = 'Demo: payload captured';
  authError.value = '';
}
```

In the template, after the existing `Organisms · Share` block, add:

```vue
<section v-else-if="activeSection === 'Organisms · Auth'" class="library__section">
  <h3 class="library__title">Organisms · Auth</h3>

  <div class="library__row">
    <label class="library__cell">
      <span class="library__label">Mode</span>
      <M.SegmentedControl
        :model-value="authMode"
        :options="[{ value: 'login', label: 'LOGIN' }, { value: 'register', label: 'REGISTER' }, { value: 'forgot', label: 'FORGOT' }]"
        @update:model-value="(v) => (authMode = v as 'login' | 'register' | 'forgot')"
      />
    </label>
  </div>

  <div class="library__demo-card library__demo-card--auth">
    <AuthForm
      :mode="authMode"
      :title="authTitleByMode[authMode]"
      :submit-label="authSubmitLabelByMode[authMode]"
      :is-submitting="authSubmitting"
      :error-message="authError"
      :success-message="authSuccess"
      :labels="authLabelsByMode[authMode]"
      @submit="onAuthSubmit"
    >
      <template #hint>
        <div v-if="authMode === 'login'" class="library__hint">
          <strong>Mock</strong>
          <small>admin / admin123</small>
        </div>
      </template>
      <template #secondary>
        <span class="library__hint-link">Forgot password</span>
      </template>
      <template #footer>
        <span>Demo footer</span>
      </template>
    </AuthForm>
  </div>

  <pre v-if="lastAuthSubmit" class="library__pre">{{ lastAuthSubmit }}</pre>
</section>
```

If `library__section` / `library__title` / `library__row` / `library__demo-card` / `library__cell` / `library__label` / `library__pre` are already used in the existing template, reuse them. If `library__demo-card--auth` / `library__hint` / `library__hint-link` are new, append minimal scoped styles at the bottom of the file:

```css
.library__demo-card--auth {
  max-width: 420px;
  padding: var(--sp-xl);
  background: var(--surface-raised);
  border: 1px solid var(--border-default);
}
.library__hint {
  display: flex; flex-direction: column; gap: 2px;
  padding: var(--sp-sm) var(--sp-md);
  background: var(--surface-inset);
  border: 1px solid var(--border-subtle);
  font-family: var(--font-mono);
  font-size: var(--text-small);
  color: var(--text-secondary);
}
.library__hint strong { color: var(--text-primary); font-weight: var(--weight-semibold); font-size: var(--text-label); letter-spacing: var(--tracking-wider); text-transform: uppercase; }
.library__hint-link { color: var(--ac); font-size: var(--text-small); cursor: pointer; }
```

If the existing Library file uses a different naming convention (e.g. unprefixed classes), match the existing style. The aim is one new card + one new hint block — do not refactor the whole library.

- [ ] **Step 2: Run dev server and confirm**

```bash
cd web && bun run dev
```

Open `http://localhost:5173/__dev/library` → `Organisms · Auth`. Confirm:
- All 3 modes render their proper fields.
- Submit captures the payload into the `<pre>` block.
- Switching `data-accent` between lime/amber/oxide tints the submit button + checkbox.
- Switching `data-theme` between light/dark keeps text readable, surfaces flip correctly.
- Reduced motion (force via DevTools `prefers-reduced-motion`) collapses animation.

Stop dev server when done.

- [ ] **Step 3: Commit**

```bash
git add web/src/pages/__dev/Library.vue
git commit -m "feat(dev/library): add Organisms · Auth section"
```

---

## Phase C — Migrate pages

> **Order matters.** Do Login first because its prefill behavior is the trickiest. Register / ForgotPassword are mechanical. VerifyEmail is shape-different (no AuthForm) and goes last.

### Task 3: Rewrite Login.vue (≤ 100 lines)

**Files:**
- Modify: `web/src/pages/login/Login.vue` (was 267 lines → target ≤ 100)

- [ ] **Step 1: Replace the whole file with the rewrite**

```vue
<script setup lang="ts">
import { computed, ref } from 'vue';
import { useRouter } from 'vue-router';
import { AuthForm } from '../../components/organisms/auth';
import type { AuthSubmitPayload } from '../../components/organisms/auth';
import { useUserStore } from '../../store/user';

const router = useRouter();
const userStore = useUserStore();

const isSubmitting = ref(false);
const errorMessage = ref('');

const saved = (() => {
  const flag = localStorage.getItem('rememberMe');
  const name = localStorage.getItem('savedUsername');
  return flag === 'true' && name ? { identifier: name, rememberMe: true } : { identifier: 'admin', rememberMe: false };
})();
const initial = computed(() => saved);

const labels = {
  identifier: 'Username or Email', identifierPlaceholder: 'Enter username or email',
  password: 'Password', passwordPlaceholder: 'Enter password',
  rememberMe: 'Remember me',
};

async function onSubmit(payload: AuthSubmitPayload) {
  if (payload.mode !== 'login') return;
  if (isSubmitting.value) return;
  isSubmitting.value = true;
  errorMessage.value = '';
  try {
    const { identifier, password, rememberMe } = payload.values;
    const response = await userStore.login({ username: identifier, password });
    if (rememberMe) {
      localStorage.setItem('rememberMe', 'true');
      localStorage.setItem('savedUsername', identifier);
    } else {
      localStorage.removeItem('rememberMe');
      localStorage.removeItem('savedUsername');
    }
    router.push(response.user.emailVerified ? '/files' : '/verify-email');
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : 'Login failed. Please check your credentials.';
  } finally {
    isSubmitting.value = false;
  }
}
</script>

<template>
  <AuthForm
    mode="login"
    title="Sign in to FileFlash"
    subtitle="Manage cloud files, team sharing, recycle restore, and admin operations."
    submit-label="SIGN IN"
    :is-submitting="isSubmitting"
    :error-message="errorMessage"
    :labels="labels"
    :initial="initial"
    @submit="onSubmit"
  >
    <template #hint>
      <div class="login__hint">
        <strong>Mock Test Accounts</strong>
        <small>admin / admin123 (administrator)</small>
        <small>demo / demo123 (regular user)</small>
      </div>
    </template>
    <template #secondary>
      <router-link to="/forgot-password" class="login__sec">Forgot password</router-link>
    </template>
    <template #footer>
      <span>Need an account?</span>
      <router-link to="/register">Create one</router-link>
    </template>
  </AuthForm>
</template>

<style scoped>
.login__hint {
  display: flex; flex-direction: column; gap: 2px;
  padding: var(--sp-sm) var(--sp-md);
  background: var(--surface-inset);
  border: 1px solid var(--border-subtle);
  font-family: var(--font-mono);
  font-size: var(--text-small);
  color: var(--text-secondary);
  margin-top: var(--sp-sm);
}
.login__hint strong {
  color: var(--text-primary);
  font-weight: var(--weight-semibold);
  font-size: var(--text-label);
  letter-spacing: var(--tracking-wider);
  text-transform: uppercase;
}
.login__sec {
  color: var(--ac);
  font-size: var(--text-small);
  text-decoration: none;
}
.login__sec:hover { text-decoration: underline; }
</style>
```

- [ ] **Step 2: Verify line count**

```bash
wc -l web/src/pages/login/Login.vue
```

Expected: ≤ 100. If over, condense `saved` derivation inline and remove the `initial` computed (pass `:initial="saved"` directly).

- [ ] **Step 3: Run check + tests**

```bash
cd web && bun run check && bun run test
```

Expected: type-check clean. Tests untouched (none specifically target Login). If `vue-tsc` complains about the `var(--weight-semibold)` / `var(--tracking-wide)` references being unknown — they're CSS variables defined in `web/src/styles/tokens/type.css`, so tsc won't flag them. If you misnamed a token (e.g. `--font-weight-semibold` legacy), grep tokens:

```bash
grep -nE "^\s*--weight-|--tracking-" src/styles/tokens/type.css
```

and align.

- [ ] **Step 4: Commit**

```bash
git add web/src/pages/login/Login.vue
git commit -m "refactor(pages/login): rewrite Login against AuthForm (≤100 lines)"
```

---

### Task 4: Rewrite Register.vue (≤ 100 lines, Chinese strings preserved)

**Files:**
- Modify: `web/src/pages/register/Register.vue` (was 225 lines → target ≤ 100)

- [ ] **Step 1: Replace the whole file**

```vue
<script setup lang="ts">
import { ref } from 'vue';
import { useRouter } from 'vue-router';
import { AuthForm } from '../../components/organisms/auth';
import type { AuthSubmitPayload } from '../../components/organisms/auth';
import { register } from '../../api/user';

const router = useRouter();
const isSubmitting = ref(false);
const errorMessage = ref('');

const labels = {
  username: '用户名', usernamePlaceholder: '请输入用户名',
  email: '邮箱', emailPlaceholder: '请输入邮箱地址',
  password: '密码', passwordPlaceholder: '请输入密码',
  confirmPassword: '确认密码', confirmPasswordPlaceholder: '请再次输入密码',
};

async function onSubmit(payload: AuthSubmitPayload) {
  if (payload.mode !== 'register') return;
  const { username, email, password, confirmPassword } = payload.values;
  if (password !== confirmPassword) {
    errorMessage.value = '两次输入的密码不一致。';
    return;
  }
  if (isSubmitting.value) return;
  isSubmitting.value = true;
  errorMessage.value = '';
  try {
    const response = await register({ username, email, password });
    router.push(response.emailVerificationRequired ? '/verify-email' : '/login');
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '注册失败，请稍后再试。';
  } finally {
    isSubmitting.value = false;
  }
}
</script>

<template>
  <AuthForm
    mode="register"
    title="创建 FileFlash 账号"
    subtitle="注册后即可上传、共享、恢复与管理你的文件"
    submit-label="注册"
    :is-submitting="isSubmitting"
    :error-message="errorMessage"
    :labels="labels"
    @submit="onSubmit"
  >
    <template #footer>
      <span>已有账号？</span>
      <router-link to="/login">前往登录</router-link>
    </template>
  </AuthForm>
</template>
```

- [ ] **Step 2: Verify line count**

```bash
wc -l web/src/pages/register/Register.vue
```

Expected: ≤ 100.

- [ ] **Step 3: Run check + tests**

```bash
cd web && bun run check && bun run test
```

Expected: green.

- [ ] **Step 4: Commit**

```bash
git add web/src/pages/register/Register.vue
git commit -m "refactor(pages/register): rewrite Register against AuthForm (≤100 lines)"
```

---

### Task 5: Rewrite ForgotPassword.vue (≤ 100 lines, Chinese strings preserved)

**Files:**
- Modify: `web/src/pages/forgot-password/ForgotPassword.vue` (was 151 lines → target ≤ 100)

- [ ] **Step 1: Replace the whole file**

```vue
<script setup lang="ts">
import { ref } from 'vue';
import { AuthForm } from '../../components/organisms/auth';
import type { AuthSubmitPayload } from '../../components/organisms/auth';
import { forgotPassword } from '../../api/user';

const isSubmitting = ref(false);
const errorMessage = ref('');
const successMessage = ref('');

const labels = {
  email: '邮箱地址', emailPlaceholder: '请输入邮箱地址',
};

async function onSubmit(payload: AuthSubmitPayload) {
  if (payload.mode !== 'forgot') return;
  if (isSubmitting.value) return;
  isSubmitting.value = true;
  errorMessage.value = '';
  successMessage.value = '';
  try {
    await forgotPassword(payload.values.email);
    successMessage.value = '重置邮件已发送，请检查邮箱。';
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '发送失败，请稍后再试。';
  } finally {
    isSubmitting.value = false;
  }
}
</script>

<template>
  <AuthForm
    mode="forgot"
    title="找回密码"
    subtitle="输入注册邮箱，我们将发送密码重置链接。"
    submit-label="发送重置邮件"
    :is-submitting="isSubmitting"
    :error-message="errorMessage"
    :success-message="successMessage"
    :labels="labels"
    @submit="onSubmit"
  >
    <template #footer>
      <router-link to="/login">返回登录</router-link>
    </template>
  </AuthForm>
</template>
```

- [ ] **Step 2: Verify line count + tests**

```bash
wc -l web/src/pages/forgot-password/ForgotPassword.vue && cd web && bun run check && bun run test
```

Expected: ≤ 100, green.

- [ ] **Step 3: Commit**

```bash
git add web/src/pages/forgot-password/ForgotPassword.vue
git commit -m "refactor(pages/forgot-password): rewrite against AuthForm (≤100 lines)"
```

---

### Task 6: Rewrite VerifyEmail.vue (≤ 100 lines, inline atoms — no AuthForm)

**Files:**
- Modify: `web/src/pages/verify-email/VerifyEmail.vue` (was 195 lines → target ≤ 100)

**Design notes:**
- No form fields → AuthForm isn't a fit. Use atoms (`Text`, `Spinner`, `Dot`) + `Button` molecule directly.
- 4 visual states: `pending` (token-driven verifying), `idle` (waiting for user to check email), `success` (verified), `error` (token invalid / failed).
- Dot color encodes state via the existing `Dot` atom tones (`accent` | `success` | `warning` | `error` | `info` — confirmed). Use `success` / `error` / `accent` (pending) / `info` (idle).
- The page lives inside `BareLayout` — already provides centering and background. The page just renders one centered `<section class="verify">` ≤ 420px wide.

- [ ] **Step 1: Replace the whole file**

```vue
<script setup lang="ts">
import { computed, onMounted, ref } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { Dot, Spinner, Text } from '../../components/atoms';
import { Button } from '../../components/molecules';
import { resendVerification, verifyEmail } from '../../api/user';
import { useUserStore } from '../../store/user';

const route = useRoute();
const router = useRouter();
const userStore = useUserStore();

const status = ref<'idle' | 'pending' | 'success' | 'error'>('idle');
const message = ref('A verification link has been sent to your email. Please verify your account.');
const resendLoading = ref(false);
const resendMessage = ref('');
const resendError = ref('');

const token = computed(() => (typeof route.query.token === 'string' ? route.query.token : ''));
const canResend = computed(() => userStore.isAuthenticated && !userStore.user?.emailVerified);
const dotTone = computed<'success' | 'error' | 'accent' | 'info'>(() => status.value === 'success' ? 'success' : status.value === 'error' ? 'error' : status.value === 'pending' ? 'accent' : 'info');

async function runVerify(t: string) {
  status.value = 'pending';
  resendError.value = '';
  resendMessage.value = '';
  try {
    await verifyEmail(t);
    await userStore.fetchUserProfile();
    status.value = 'success';
    message.value = 'Email verification completed successfully.';
  } catch (e) {
    status.value = 'error';
    message.value = e instanceof Error ? e.message : 'Failed to verify email.';
  }
}

async function onResend() {
  if (resendLoading.value) return;
  resendLoading.value = true;
  resendError.value = '';
  resendMessage.value = '';
  try {
    await resendVerification();
    resendMessage.value = 'Verification email has been resent.';
  } catch (e) {
    resendError.value = e instanceof Error ? e.message : 'Failed to resend verification email.';
  } finally {
    resendLoading.value = false;
  }
}

onMounted(async () => {
  if (token.value) { await runVerify(token.value); return; }
  if (userStore.user?.emailVerified) { status.value = 'success'; message.value = 'Your email has already been verified.'; }
});
</script>

<template>
  <section class="verify">
    <header class="verify__head">
      <Text variant="h1" as="h1">Verify your email</Text>
      <div class="verify__row">
        <Dot :tone="dotTone" />
        <Text variant="small" as="p">{{ message }}</Text>
      </div>
    </header>

    <div v-if="status === 'pending'" class="verify__pending"><Spinner /><Text variant="label">VERIFYING TOKEN</Text></div>
    <div v-if="resendMessage" role="status" class="verify__msg verify__msg--ok">{{ resendMessage }}</div>
    <div v-if="resendError" role="status" class="verify__msg verify__msg--err">{{ resendError }}</div>

    <Button v-if="canResend" variant="primary" :loading="resendLoading" :disabled="resendLoading" class="verify__resend" @click="onResend">
      {{ resendLoading ? 'RESENDING' : 'RESEND VERIFICATION EMAIL' }}
    </Button>

    <footer class="verify__footer">
      <button class="verify__link" type="button" @click="router.push('/login')">Back to login</button>
      <button v-if="userStore.isAuthenticated" class="verify__link" type="button" @click="router.push('/files')">Enter files</button>
    </footer>
  </section>
</template>

<style scoped>
.verify { display: flex; flex-direction: column; gap: var(--sp-lg); width: min(420px, 92vw); padding: var(--sp-2xl); background: var(--surface-raised); border: 1px solid var(--border-default); }
.verify__head { display: flex; flex-direction: column; gap: var(--sp-sm); }
.verify__row { display: flex; align-items: center; gap: var(--sp-sm); }
.verify__pending { display: flex; align-items: center; gap: var(--sp-sm); color: var(--text-dim); }
.verify__msg { padding: var(--sp-sm) var(--sp-md); border: 1px solid var(--border-default); font-family: var(--font-mono); font-size: var(--text-small); }
.verify__msg--ok { color: var(--status-success); border-color: var(--status-success); }
.verify__msg--err { color: var(--status-error); border-color: var(--status-error); }
.verify__resend { width: 100%; justify-content: center; height: 40px; }
.verify__footer { display: flex; justify-content: center; gap: var(--sp-md); }
.verify__link { background: transparent; border: none; color: var(--ac); cursor: pointer; font: inherit; padding: 0; font-size: var(--text-small); }
.verify__link:hover { text-decoration: underline; }
</style>
```

- [ ] **Step 2: Sanity-check the Dot atom signature (already verified in plan but re-check after pull)**

```bash
grep -nE "tone\??:|'success'|'error'|'accent'|'info'" src/components/atoms/Dot.vue
```

Expected: shows tones `'accent' | 'success' | 'warning' | 'error' | 'info'`. The page already targets only `success` / `error` / `accent` / `info`. If the atom signature has drifted since this plan was written, adapt `dotTone` to use only available tones — **do not modify the Dot atom in this task**.

- [ ] **Step 3: Verify line count + tests**

```bash
wc -l web/src/pages/verify-email/VerifyEmail.vue && cd web && bun run check && bun run test
```

Expected: ≤ 100, green.

- [ ] **Step 4: Commit**

```bash
git add web/src/pages/verify-email/VerifyEmail.vue
git commit -m "refactor(pages/verify-email): rewrite against atoms/molecules (≤100 lines)"
```

---

## Phase D — Verification

### Task 7: Full pipeline + token discipline grep

- [ ] **Step 1: Full pipeline**

```bash
cd web && bun run test && bun run check && bun run build
```

Expected: all green, build artifact produced.

- [ ] **Step 2: Token discipline — grep new auth code for legacy color/font references**

```bash
cd web && grep -nE "#[0-9a-fA-F]{3,8}|--color-[a-z]|cubic-bezier\(0.4|translateY\(-1px\)|Manrope|backdrop-filter|linear-gradient" \
  src/components/organisms/auth/*.vue \
  src/pages/login/Login.vue \
  src/pages/register/Register.vue \
  src/pages/forgot-password/ForgotPassword.vue \
  src/pages/verify-email/VerifyEmail.vue
```

Expected: 0 hits. If any sneak in, replace with token references. The acceptable exceptions are documented hex values inside `web/src/styles/tokens/*.css` only.

- [ ] **Step 3: Border-radius audit on new auth files**

```bash
cd web && grep -nE "border-radius" \
  src/components/organisms/auth/*.vue \
  src/pages/login/Login.vue \
  src/pages/register/Register.vue \
  src/pages/forgot-password/ForgotPassword.vue \
  src/pages/verify-email/VerifyEmail.vue
```

Expected: only `var(--radius-sm)` / `var(--radius-md)` / `0`. No literal pixel values like `10px` / `18px` / `42px` for radius.

- [ ] **Step 4: Line-count audit**

```bash
wc -l src/pages/login/Login.vue \
      src/pages/register/Register.vue \
      src/pages/forgot-password/ForgotPassword.vue \
      src/pages/verify-email/VerifyEmail.vue
```

Expected: each file ≤ 100. Total ≤ 400.

- [ ] **Step 5: Manual smoke test — 12-combo coverage**

Run `cd web && bun run dev`. For each route below, cycle `data-accent` (lime/amber/oxide), `data-theme` (dark/light), and `data-motion` (spring/tight/reduced) via DevTools (`document.documentElement.dataset.accent = 'amber'` etc.). Confirm no visual breakage.

**Per-route checklist:**

`/login`:
- a. Page renders inside AuthLayout (brand block + card).
- b. Username + password + Remember me visible; mock-account hint visible.
- c. Submit with `admin/admin123` → land on `/files` (assuming backend supports the mock — fall back to checking a 401 error renders cleanly in the error row).
- d. Submit with wrong password → red error block under fields.
- e. Toggle Remember me + valid login → reload → username pre-filled, checkbox pre-checked.
- f. Untick Remember me + valid login → reload → fields reset, no localStorage leak.
- g. Click "Create one" → navigates to `/register`, no full-page fade.
- h. Click "Forgot password" → navigates to `/forgot-password`.
- i. Click eye → password text becomes visible.
- j. While submitting, button shows spinner and is disabled.

`/register`:
- a. 4 fields visible, Chinese labels.
- b. Submit with mismatched passwords → "两次输入的密码不一致。" appears, no API call.
- c. Submit valid → land on `/verify-email` or `/login` based on backend response.
- d. Click "前往登录" → navigates to `/login`.

`/forgot-password`:
- a. Single email field, Chinese subtitle.
- b. Submit valid email → success block "重置邮件已发送，请检查邮箱。".
- c. Simulate failure (offline) → red error block.
- d. Click "返回登录" → `/login`.

`/verify-email`:
- a. Hit `/verify-email` without query → idle dot + initial English copy + (if authed) resend button.
- b. Hit `/verify-email?token=BAD` → pending dot, then error message.
- c. Authed + already verified → success dot + "Your email has already been verified.".
- d. Click "Back to login" → `/login`. Click "Enter files" (when authed) → `/files`.
- e. Click resend → button enters loading, success/error block updates accordingly.

**Cross-route invariants:**
- Switching `data-accent` retints submit button, checkbox, secondary links, dot, and status borders.
- Switching `data-theme` flips surfaces; text remains WCAG AA readable.
- Switching `data-motion="reduced"` removes spring/fade animation.
- No `console.warn` / `console.error` in DevTools across any of the above.

- [ ] **Step 6: If anything fails**

Fix in a follow-up commit on the same task. Do not declare P5 done with broken parity.

- [ ] **Step 7: No commit if all green**

Otherwise add a `fix(p5): <issue>` commit per fix.

---

### Task 8: Update progress memory

**Files:**
- Modify: `C:\Users\xc150\.claude\projects\D--pyprj-fileflash\memory\frontend_redesign_progress.md`

- [ ] **Step 1: Move P5 from "进行中 / 待开始" into "已完成"**

Read the file, then add an entry after the P4 row in the same format:

```
- **P5 Public Auth Flow**（2026-05-12）— 新组件 `organisms/auth/AuthForm.vue`（login/register/forgot 三模式 + 9 个 spec 通过）+ 4 个页面全部重写：Login X 行（旧 267）/ Register Y 行（旧 225）/ ForgotPassword Z 行（旧 151）/ VerifyEmail W 行（旧 195）。VerifyEmail 走 BareLayout，不用 AuthForm（无表单字段，直接拼 atoms/molecules）。dev library 加 `Organisms · Auth` 段含 mode picker。AuthLayout 仍用旧 themeStore（P6 替换）。
```

Replace `X/Y/Z/W` with the actual `wc -l` outputs from Task 7 Step 4.

Then remove `**P5**` from "进行中 / 待开始" section.

- [ ] **Step 2: Commit a chore entry to the repo**

```bash
git commit --allow-empty -m "chore(progress): mark P5 Public Auth Flow complete"
```

(The memory file lives outside the repo, so its update is not staged; an empty commit records the milestone for git history.)

---

## Self-Review checklist

After all tasks land, run this once.

1. **Spec coverage** — spec §3.1 calls for `organisms/auth/AuthForm.vue` for Login/Register/ForgotPassword. ✅ Created in Task 1. Spec §4 P5 row lists all 4 pages — ✅ all 4 rewritten in Tasks 3–6. Spec §3.3 dev library coverage — ✅ Task 2.

2. **Pages ≤ 100 lines** — Task 7 Step 4 grep confirms.

3. **Token discipline** — Task 7 Step 2 grep returns empty.

4. **No new `common/*` imports from new auth files** — grep:

```bash
cd web && grep -nE "from '\.\./\.\./common/" \
  src/components/organisms/auth/*.vue \
  src/pages/login/Login.vue \
  src/pages/register/Register.vue \
  src/pages/forgot-password/ForgotPassword.vue \
  src/pages/verify-email/VerifyEmail.vue
```

Expected: empty.

5. **Sharp edges** — Task 7 Step 3 grep confirms.

6. **Build + test green** — Task 7 Step 1.

7. **Manual smoke covers all 12 token combos × all 4 routes** — Task 7 Step 5.

If any check fails, add a fix commit before marking P5 done.

---

## Execution Handoff

**Plan complete and saved to `docs/superpowers/plans/2026-05-11-frontend-redesign-p5-public-auth-flow.md`. Two execution options:**

**1. Subagent-Driven (recommended)** — dispatch a fresh subagent per task, review between tasks, fast iteration.

**2. Inline Execution** — execute tasks in this session using `superpowers:executing-plans`, batch execution with checkpoints.

**Which approach?**
