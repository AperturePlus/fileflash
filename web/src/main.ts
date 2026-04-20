import { createApp } from 'vue';
import { createPinia } from 'pinia';
import './style.css';
import App from './App.vue';
import router from './router';

async function bootstrap() {
  const enableMocks = import.meta.env.VITE_ENABLE_MOCKS !== 'false';
  if (enableMocks) {
    await import('./mock');
  }

  const app = createApp(App);
  const pinia = createPinia();

  app.use(pinia);
  app.use(router);

  app.mount('#app');
}

bootstrap();

