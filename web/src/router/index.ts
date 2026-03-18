import { createRouter, createWebHistory } from 'vue-router';
import { routes } from './routes';
import { createRouterGuard } from './gurad';

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes,
});

createRouterGuard(router);

export default router; 