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
  resendError.value = ''; resendMessage.value = '';
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
  resendError.value = ''; resendMessage.value = '';
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
  if (!userStore.isAuthenticated) {
    status.value = 'error';
    message.value = 'Please log in first, then verify your email.';
    return;
  }
  if (userStore.user?.emailVerified) {
    status.value = 'success';
    message.value = 'Your email has already been verified.';
    return;
  }
  status.value = 'idle';
  message.value = 'You are logged in but email is not verified yet. You can resend verification email.';
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
