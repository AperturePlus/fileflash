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
