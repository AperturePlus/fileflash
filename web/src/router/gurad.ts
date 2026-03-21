import type { Router } from 'vue-router';
import { useUserStore } from '../store/user';

const LOGIN_ROUTE_NAME = 'Login';
const HOME_ROUTE_NAME = 'Home';
const FILES_ROUTE_PATH = '/files';

export function createRouterGuard(router: Router) {
  router.beforeEach((to, _from, next) => {
    const userStore = useUserStore();
    const isLoggedIn = !!userStore.token;
    const requiresAdmin = Boolean(to.meta.requiresAdmin);
    const hasAdminAccess = userStore.user?.role === 'admin';

    if (to.meta.requiresAuth && !isLoggedIn) {
      // This route requires auth, check if logged in
      // if not, redirect to login page.
      next({
        name: LOGIN_ROUTE_NAME,
        query: { redirect: to.fullPath }, // Pass the original destination to the login page
      });
    } else if (to.name === LOGIN_ROUTE_NAME && isLoggedIn) {
      // If logged in, redirect to home page from login page
      next({ name: HOME_ROUTE_NAME });
    } else if (requiresAdmin && !hasAdminAccess) {
      next({ path: FILES_ROUTE_PATH });
    } else {
      // Make sure to always call next()!
      next();
    }
  });
}
