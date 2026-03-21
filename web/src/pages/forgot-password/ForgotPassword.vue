<script setup lang="ts">
import { ref } from 'vue';
import { forgotPassword } from '../../api/user';
import AuthLayout from '../../components/layout/AuthLayout.vue';

const email = ref('');
const isSubmitting = ref(false);
const errorMessage = ref('');
const successMessage = ref('');

const handleSubmit = async () => {
  if (isSubmitting.value) return;

  isSubmitting.value = true;
  errorMessage.value = '';
  successMessage.value = '';

  try {
    await forgotPassword(email.value);
    successMessage.value = '重置邮件已发送，请检查邮箱。';
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '发送失败，请稍后再试。';
  } finally {
    isSubmitting.value = false;
  }
};
</script>

<template>
  <AuthLayout>
    <div class="auth-card">
      <header class="auth-header">
        <h1>找回密码</h1>
        <p>输入注册邮箱，我们将发送密码重置链接。</p>
      </header>

      <form class="auth-form" @submit.prevent="handleSubmit">
        <label class="field">
          <span>邮箱地址</span>
          <input v-model="email" type="email" placeholder="请输入邮箱地址" required />
        </label>

        <p v-if="errorMessage" class="error-message">{{ errorMessage }}</p>
        <p v-if="successMessage" class="success-message">{{ successMessage }}</p>

        <button class="submit-btn" type="submit" :disabled="isSubmitting">
          {{ isSubmitting ? '发送中...' : '发送重置邮件' }}
        </button>
      </form>

      <footer class="auth-footer">
        <router-link to="/login">返回登录</router-link>
      </footer>
    </div>
  </AuthLayout>
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
  margin-bottom: 20px;
}

.auth-header h1 {
  font-size: 28px;
  margin-bottom: 6px;
}

.auth-header p {
  margin: 0;
  color: #52667f;
}

.auth-form {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.field {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.field span {
  font-size: 13px;
  color: #334155;
}

.field input {
  height: 42px;
  border-radius: 10px;
  border: 1px solid #cbd5e1;
  background-color: #fff;
  padding: 0 12px;
}

.field input:focus {
  outline: none;
  border-color: var(--color-primary);
  box-shadow: 0 0 0 3px rgba(var(--color-primary-rgb), 0.14);
}

.error-message,
.success-message {
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

.auth-footer {
  margin-top: 16px;
  text-align: center;
}
</style>
