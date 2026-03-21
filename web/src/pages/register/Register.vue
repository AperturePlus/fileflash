<script setup lang="ts">
import { ref } from 'vue';
import { useRouter } from 'vue-router';
import { register } from '../../api/user';
import AuthLayout from '../../components/layout/AuthLayout.vue';

const router = useRouter();

const username = ref('');
const email = ref('');
const password = ref('');
const confirmPassword = ref('');
const showPassword = ref(false);
const showConfirmPassword = ref(false);
const isLoading = ref(false);
const errorMessage = ref('');

const handleRegister = async () => {
  if (password.value !== confirmPassword.value) {
    errorMessage.value = '两次输入的密码不一致。';
    return;
  }

  if (isLoading.value) return;

  isLoading.value = true;
  errorMessage.value = '';

  try {
    await register({
      username: username.value,
      email: email.value,
      password: password.value,
    });

    router.push('/login');
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '注册失败，请稍后再试。';
  } finally {
    isLoading.value = false;
  }
};
</script>

<template>
  <AuthLayout>
    <div class="auth-card">
      <header class="auth-header">
        <h1>创建 FileFlash 账号</h1>
        <p>注册后即可上传、共享、恢复与管理你的文件</p>
      </header>

      <form class="auth-form" @submit.prevent="handleRegister">
        <label class="field">
          <span>用户名</span>
          <input v-model="username" type="text" placeholder="请输入用户名" required />
        </label>

        <label class="field">
          <span>邮箱</span>
          <input v-model="email" type="email" placeholder="请输入邮箱地址" required />
        </label>

        <label class="field">
          <span>密码</span>
          <div class="password-wrap">
            <input v-model="password" :type="showPassword ? 'text' : 'password'" placeholder="请输入密码" required />
            <button type="button" class="password-toggle" @click="showPassword = !showPassword">
              {{ showPassword ? '隐藏' : '显示' }}
            </button>
          </div>
        </label>

        <label class="field">
          <span>确认密码</span>
          <div class="password-wrap">
            <input
              v-model="confirmPassword"
              :type="showConfirmPassword ? 'text' : 'password'"
              placeholder="请再次输入密码"
              required
            />
            <button type="button" class="password-toggle" @click="showConfirmPassword = !showConfirmPassword">
              {{ showConfirmPassword ? '隐藏' : '显示' }}
            </button>
          </div>
        </label>

        <p v-if="errorMessage" class="error-message">{{ errorMessage }}</p>

        <button class="submit-btn" type="submit" :disabled="isLoading">
          {{ isLoading ? '注册中...' : '注册' }}
        </button>
      </form>

      <footer class="auth-footer">
        <span>已有账号？</span>
        <router-link to="/login">前往登录</router-link>
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

.password-wrap {
  position: relative;
}

.password-wrap input {
  width: 100%;
  padding-right: 64px;
}

.password-toggle {
  position: absolute;
  right: 8px;
  top: 50%;
  transform: translateY(-50%);
  border: none;
  background: transparent;
  color: var(--color-primary);
  cursor: pointer;
}

.error-message {
  margin: 0;
  color: var(--color-danger-dark);
  background-color: var(--color-danger-light);
  border: 1px solid #fca5a5;
  border-radius: 10px;
  padding: 8px 10px;
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
  margin-top: 18px;
  font-size: 13px;
  color: #475569;
  display: flex;
  gap: 6px;
  justify-content: center;
}

@media (max-width: 480px) {
  .auth-card {
    padding: 22px 18px;
  }

  .auth-header h1 {
    font-size: 23px;
  }
}
</style>
