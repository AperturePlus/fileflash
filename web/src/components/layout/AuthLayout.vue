<template>
  <div class="auth-layout">
    <!-- 全屏背景图片 -->
    <div class="background-container">
      <img :src="randomBanner" alt="Background" class="background-image" />
      <div class="background-overlay"></div>
    </div>
    
    <!-- 登录框容器 -->
    <div class="content-container">
      <div class="content-wrapper">
        <slot></slot>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue';

import banner1 from '../../assets/banner/banner_1.png';
import banner2 from '../../assets/banner/banner_2.png';
import banner3 from '../../assets/banner/banner_3.png';
import banner4 from '../../assets/banner/banner_4.png';

const banners = [banner1, banner2, banner3, banner4];
const randomBanner = ref('');

onMounted(() => {
  const randomIndex = Math.floor(Math.random() * banners.length);
  randomBanner.value = banners[randomIndex];
});
</script>

<style scoped>
.auth-layout {
  position: relative;
  width: 100vw;
  height: 100vh;
  overflow: hidden;
  display: flex;
  align-items: center;
  justify-content: center;
}

/* 全屏背景图片 */
.background-container {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  z-index: 0;
}

.background-image {
  width: 100%;
  height: 100%;
  object-fit: cover;
  object-position: center;
}

.background-overlay {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background: rgba(0, 0, 0, 0.3);
  backdrop-filter: blur(2px);
}

/* 登录框容器 */
.content-container {
  position: relative;
  z-index: 10;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 100%;
  height: 100%;
  padding: 2rem;
}

.content-wrapper {
  width: 100%;
  max-width: 420px;
  position: relative;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .content-container {
    padding: 1.5rem;
  }
  
  .content-wrapper {
    max-width: 100%;
  }
}

@media (max-width: 480px) {
  .content-container {
    padding: 1rem;
  }
  
  .background-overlay {
    background: rgba(0, 0, 0, 0.4);
  }
}
</style> 