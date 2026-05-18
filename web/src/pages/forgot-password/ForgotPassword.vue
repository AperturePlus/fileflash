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
  if (payload.mode !== 'forgot' || isSubmitting.value) return;
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
