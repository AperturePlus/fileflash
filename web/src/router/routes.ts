import type { RouteRecordRaw } from 'vue-router';
import MainLayout from '../components/templates/MainLayout.vue';

const devRoutes: Array<RouteRecordRaw> = import.meta.env.DEV
  ? [{
      path: '/__dev/library',
      name: 'DevLibrary',
      component: () => import('../pages/__dev/index.ts'),
      meta: { requiresAuth: false },
    }]
  : [];

export const routes: Array<RouteRecordRaw> = [
  ...devRoutes,
  {
    path: '/login',
    name: 'Login',
    component: () => import('../pages/login/index.ts'),
    meta: { requiresAuth: false },
  },
  {
    path: '/register',
    name: 'Register',
    component: () => import('../pages/register/index.ts'),
    meta: { requiresAuth: false },
  },
  {
    path: '/forgot-password',
    name: 'ForgotPassword',
    component: () => import('../pages/forgot-password/index.ts'),
    meta: { requiresAuth: false },
  },
  {
    path: '/verify-email',
    name: 'VerifyEmail',
    component: () => import('../pages/verify-email/index.ts'),
    meta: { requiresAuth: false },
  },
  {
    path: '/share/:shareLink',
    name: 'ShareAccess',
    component: () => import('../pages/share/index.ts'),
    meta: { requiresAuth: false },
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
        path: 'agent',
        component: () => import('../pages/agent/index.ts'),
        meta: { navId: 'agent' },
        children: [
          {
            path: '',
            name: 'AgentWorkspace',
            component: () => import('../pages/agent/workspace/index.ts'),
            meta: { navId: 'agent' }
          },
          {
            path: 'skills',
            name: 'AgentSkills',
            component: () => import('../pages/agent/skills/index.ts'),
            meta: { navId: 'agent' }
          }
        ]
      },
      {
        path: 'skills',
        name: 'SkillsLegacy',
        redirect: '/agent/skills',
        meta: { navId: 'agent' }
      },
      {
        path: 'dashboard',
        name: 'Dashboard',
        component: () => import('../pages/dashboard/index.ts'),
        meta: { navId: 'dashboard', requiresAdmin: true }
      }
    ],
  },
   {
    path: '/:pathMatch(.*)*',
    name: 'NotFound',
    redirect: '/',
  }
];
