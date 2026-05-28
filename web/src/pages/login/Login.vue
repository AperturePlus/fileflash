<script setup lang="ts">
import { ref } from 'vue';
import { useRouter } from 'vue-router';
import { AuthForm } from '../../components/organisms/auth';
import type { AuthSubmitPayload } from '../../components/organisms/auth';
import { useUserStore } from '../../store/user';

const router = useRouter();
const userStore = useUserStore();
const isSubmitting = ref(false);
const errorMessage = ref('');

const savedFlag = localStorage.getItem('rememberMe'); const savedName = localStorage.getItem('savedUsername');
const initial = savedFlag === 'true' && savedName
  ? { identifier: savedName, rememberMe: true }
  : { identifier: 'admin', rememberMe: false };

const labels = {
  identifier: 'Username or Email', identifierPlaceholder: 'Enter username or email',
  password: 'Password', passwordPlaceholder: 'Enter password',
  rememberMe: 'Remember me',
};

async function onSubmit(payload: AuthSubmitPayload) {
  if (payload.mode !== 'login' || isSubmitting.value) return;
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
.login__sec {
  color: var(--ac);
  font-size: var(--text-small);
  text-decoration: none;
}
.login__sec:hover { text-decoration: underline; }
</style>
