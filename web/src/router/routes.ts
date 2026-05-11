import type { RouteRecordRaw } from 'vue-router';
import MainLayout from '../components/layout/MainLayout.vue';

// Dev-only library route: spreads into the routes array only when running under
// `vite dev` (or `vite build` with mode=development). In production builds the
// array is empty, so the chunk is dead-code-eliminated and the path won't match.
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
    path: '/verify-email',
    name: 'VerifyEmail',
    component: () => import('../pages/verify-email/index.ts'),
  },

  {
    path: '/share/:shareLink',
    name: 'ShareAccess',
    component: () => import('../pages/share/index.ts'),
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
   // 兜底路由，匹配所有未定义的路径
   {
    path: '/:pathMatch(.*)*',
    name: 'NotFound',
    redirect: '/',
  }
];
