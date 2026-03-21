<script setup lang="ts">
import { ref } from 'vue';
import { useRouter } from 'vue-router';
import { useUserStore } from '../../store/user';
import { login } from '../../api/user';
import AuthLayout from '../../components/layout/AuthLayout.vue';

const router = useRouter();
const userStore = useUserStore();

const username = ref('admin');
const password = ref('password');
const rememberMe = ref(false);
const isLoading = ref(false);
const errorMessage = ref('');
const showPassword = ref(false);

const handleLogin = async () => {
  if (isLoading.value) return;

  isLoading.value = true;
  errorMessage.value = '';

  try {
    const response = await login({
      username: username.value,
      password: password.value,
    });

    userStore.setToken(response.token, response.refreshToken);
    userStore.user = response.user;

    if (rememberMe.value) {
      localStorage.setItem('rememberMe', 'true');
      localStorage.setItem('savedUsername', username.value);
    } else {
      localStorage.removeItem('rememberMe');
      localStorage.removeItem('savedUsername');
    }

    router.push('/files');
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '登录失败，请检查账号信息。';
  } finally {
    isLoading.value = false;
  }
};

const loadSavedCredentials = () => {
  const savedRememberMe = localStorage.getItem('rememberMe');
  const savedUsername = localStorage.getItem('savedUsername');

  if (savedRememberMe === 'true' && savedUsername) {
    rememberMe.value = true;
    username.value = savedUsername;
  }
};

loadSavedCredentials();
</script>

<template>
  <AuthLayout>
    <div class="auth-card">
      <header class="auth-header">
        <h1>欢迎登录 FileFlash</h1>
        <p>高效管理你的云端文件与共享协作</p>
      </header>

      <form class="auth-form" @submit.prevent="handleLogin">
        <label class="field">
          <span>用户名 / 邮箱</span>
          <input v-model="username" type="text" placeholder="请输入用户名或邮箱" required />
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

        <div class="extra-row">
          <label class="remember">
            <input v-model="rememberMe" type="checkbox" />
            <span>记住我</span>
          </label>
          <router-link to="/forgot-password">忘记密码</router-link>
        </div>

        <p v-if="errorMessage" class="error-message">{{ errorMessage }}</p>

        <button class="submit-btn" type="submit" :disabled="isLoading">
          {{ isLoading ? '登录中...' : '登录' }}
        </button>
      </form>

      <footer class="auth-footer">
        <span>还没有账号？</span>
        <router-link to="/register">立即注册</router-link>
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

.extra-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 13px;
}

.remember {
  display: inline-flex;
  align-items: center;
  gap: 6px;
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
