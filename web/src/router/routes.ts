import type { RouteRecordRaw } from 'vue-router';
import MainLayout from '../components/layout/MainLayout.vue';

export const routes: Array<RouteRecordRaw> = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('../pages/login/index.ts'),
  },
  {
    path: '/register',
    name: 'Register',
    component: () => import('../pages/register/index.ts'),
  },
  {
    path: '/forgot-password',
    name: 'ForgotPassword',
    component: () => import('../pages/forgot-password/index.ts'),
  },
  
  {
    path: '/',
    name: 'Home',
    component: MainLayout,
    redirect: '/files',
    meta: { requiresAuth: true },
    children: [
      {
        path: 'files',
        name: 'MyFiles',
        component: () => import('../pages/files/index.ts'),
        meta: { navId: 'my-files' }
      },
      {
        path: 'shared',
        name: 'Shared',
        component: () => import('../pages/shared/index.ts'),
        meta: { navId: 'shared' }
      },
      {
        path: 'trash',
        name: 'Trash',
        component: () => import('../pages/trash/index.ts'),
        meta: { navId: 'trash' }
      },
      {
        path: 'profile',
        name: 'Profile',
        component: () => import('../pages/profile/index.ts'),
        meta: { navId: 'profile' }
      },
      {
        path: 'settings',
        name: 'Settings',
        component: () => import('../pages/settings/index.ts'),
        meta: { navId: 'settings' }
      },
      {
        path: 'dashboard',
        name: 'Dashboard',
        component: () => import('../pages/dashboard/index.ts'),
        meta: { navId: 'dashboard', requiresAdmin: true }
      }
    ],
  },
   // 兜底路由，匹配所有未定义的路径
   {
    path: '/:pathMatch(.*)*',
    name: 'NotFound',
    redirect: '/',
  }
];
