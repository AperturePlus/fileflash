<script setup lang="ts">
import { computed, onMounted, ref } from 'vue';
import { useRoute, useRouter } from 'vue-router';
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

const token = computed(() => {
  const value = route.query.token;
  return typeof value === 'string' ? value : '';
});

const canResend = computed(() => userStore.isAuthenticated && !userStore.user?.emailVerified);

async function executeVerify(tokenValue: string) {
  status.value = 'pending';
  resendError.value = '';
  resendMessage.value = '';
  try {
    await verifyEmail(tokenValue);
    await userStore.fetchUserProfile();
    status.value = 'success';
    message.value = 'Email verification completed successfully.';
  } catch (error) {
    status.value = 'error';
    message.value = error instanceof Error ? error.message : 'Failed to verify email.';
  }
}

async function handleResend() {
  if (resendLoading.value) {
    return;
  }
  resendLoading.value = true;
  resendError.value = '';
  resendMessage.value = '';
  try {
    await resendVerification();
    resendMessage.value = 'Verification email has been resent.';
  } catch (error) {
    resendError.value = error instanceof Error ? error.message : 'Failed to resend verification email.';
  } finally {
    resendLoading.value = false;
  }
}

onMounted(async () => {
  if (token.value) {
    await executeVerify(token.value);
    return;
  }

  if (userStore.user?.emailVerified) {
    status.value = 'success';
    message.value = 'Your email has already been verified.';
  }
});
</script>

<template>
  <div class="auth-card">
    <header class="auth-header">
      <h1>Verify your email</h1>
      <p>{{ message }}</p>
    </header>

    <div class="content">
      <p v-if="status === 'pending'" class="info-message">Verifying token...</p>
      <p v-if="status === 'success'" class="success-message">Verification completed.</p>
      <p v-if="status === 'error'" class="error-message">{{ message }}</p>

      <button
        v-if="canResend"
        class="submit-btn"
        type="button"
        :disabled="resendLoading"
        @click="handleResend"
      >
        {{ resendLoading ? 'Resending...' : 'Resend verification email' }}
      </button>

      <p v-if="resendMessage" class="success-message">{{ resendMessage }}</p>
      <p v-if="resendError" class="error-message">{{ resendError }}</p>
    </div>

    <footer class="auth-footer">
      <button class="link-btn" type="button" @click="router.push('/login')">Back to login</button>
      <button
        v-if="userStore.isAuthenticated"
        class="link-btn"
        type="button"
        @click="router.push('/files')"
      >
        Enter files
      </button>
    </footer>
  </div>
</template>

<style scoped>
.auth-card {
  width: 100%;
  padding: 28px;
  border-radius: 18px;
  border: 1px solid rgba(255, 255, 255, 0.42);
  background: rgba(255, 255, 255, 0.9);
  backdrop-filter: blur(20px);
  box-shadow: 0 24px 44px rgba(15, 23, 42, 0.2);
}

.auth-header {
  margin-bottom: 18px;
}

.auth-header h1 {
  font-size: 28px;
  margin-bottom: 6px;
}

.auth-header p {
  margin: 0;
  color: #52667f;
}

.content {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.submit-btn {
  margin-top: 4px;
  height: 44px;
  border-radius: 10px;
  border: none;
  background: linear-gradient(135deg, var(--color-primary), #3b82f6);
  color: var(--color-text-on-primary);
  font-weight: var(--font-weight-semibold);
  cursor: pointer;
}

.submit-btn:disabled {
  opacity: 0.7;
  cursor: not-allowed;
}

.error-message,
.success-message,
.info-message {
  margin: 0;
  border-radius: 10px;
  padding: 8px 10px;
}

.error-message {
  color: var(--color-danger-dark);
  background-color: var(--color-danger-light);
  border: 1px solid #fca5a5;
}

.success-message {
  color: #166534;
  background-color: #dcfce7;
  border: 1px solid #86efac;
}

.info-message {
  color: #1e3a8a;
  background-color: #dbeafe;
  border: 1px solid #93c5fd;
}

.auth-footer {
  margin-top: 16px;
  display: flex;
  justify-content: center;
  gap: 12px;
}

.link-btn {
  border: none;
  background: transparent;
  color: var(--color-primary);
  cursor: pointer;
}
</style>
