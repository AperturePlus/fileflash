import { createRouter, createWebHashHistory, createWebHistory } from 'vue-router';
import { routes } from './routes';
import { createRouterGuard } from './gurad';

const history = import.meta.env.VITE_APP_RUNTIME === 'electron'
  ? createWebHashHistory(import.meta.env.BASE_URL)
  : createWebHistory(import.meta.env.BASE_URL);

const router = createRouter({
  history,
  routes,
});

createRouterGuard(router);

export default router; 
