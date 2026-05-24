import { defineStore } from 'pinia';
import { ref, computed } from 'vue';
import {
  login as apiLogin,
  getProfile,
  getStorageStats,
  refreshToken as apiRefreshToken,
  logout as apiLogout,
  updatePreference as apiUpdatePreference,
} from '../api/user';
import type {
  LoginRequest,
  User,
  UserProfile,
  StorageStats,
  UpdateUserPreferenceRequest,
} from '../types/user';
import { useLocaleStore } from './locale';

const STORED_USER_KEY = 'authUser';

function loadStoredUser(): UserProfile | User | null {
  const raw = localStorage.getItem(STORED_USER_KEY);
  if (!raw) {
    return null;
  }

  try {
    return JSON.parse(raw) as UserProfile | User;
  } catch {
    localStorage.removeItem(STORED_USER_KEY);
    return null;
  }
}

export const useUserStore = defineStore('user', () => {
  const token = ref<string | null>(localStorage.getItem('authToken'));
  const user = ref<UserProfile | User | null>(loadStoredUser());
  const storageStats = ref<StorageStats | null>(null);
  let storageRefreshTimer: ReturnType<typeof setTimeout> | null = null;

  const isAuthenticated = computed(() => !!token.value);
  const isAdmin = computed(() => user.value?.role === 'admin');

  function applyUserLocale(nextUser: UserProfile | User | null) {
    const preferredLanguage = nextUser?.preference?.language;
    if (preferredLanguage) {
      const localeStore = useLocaleStore();
      localeStore.setLocale(preferredLanguage);
    }
  }

  function setUser(nextUser: UserProfile | User | null) {
    user.value = nextUser;
    applyUserLocale(nextUser);

    if (nextUser) {
      localStorage.setItem(STORED_USER_KEY, JSON.stringify(nextUser));
    } else {
      localStorage.removeItem(STORED_USER_KEY);
    }
  }

  /**
   * Set the token
   * @param newToken - The new token
   */
  function setToken(newToken: string | null) {
    token.value = newToken;
    
    if (newToken) {
      localStorage.setItem('authToken', newToken);
    } else {
      localStorage.removeItem('authToken');
    }
  }

  /**
   * Login the user
   * @param credentials - The login credentials
   * @returns The login response
   */
  async function login(credentials: LoginRequest) {
    const response = await apiLogin(credentials);
    setToken(response.token);
    setUser(response.user as UserProfile);
    await fetchUserProfile();
    return response;
  }

  /**
   * Fetch the user profile
   * @returns The user profile
   */
  async function fetchUserProfile() {
    if (!isAuthenticated.value) return;
    try {
      const profile = await getProfile();
      setUser(profile);
    } catch (error) {
      console.error('Failed to fetch user profile:', error);
      // Maybe handle token expiration
    }
  }

  /**
   * Fetch the storage stats
   * @returns The storage stats
   */
  async function fetchStorageStats() {
    if (!isAuthenticated.value) return;
    if (user.value?.emailVerified === false) {
      storageStats.value = null;
      return;
    }
    try {
      const stats = await getStorageStats();
      storageStats.value = stats;
    } catch (error) {
      console.error('Failed to fetch storage stats:', error);
    }
  }

  function scheduleStorageStatsRefresh(delayMs = 250) {
    if (!isAuthenticated.value || user.value?.emailVerified === false) {
      return;
    }
    if (storageRefreshTimer !== null) {
      clearTimeout(storageRefreshTimer);
    }
    storageRefreshTimer = setTimeout(() => {
      storageRefreshTimer = null;
      void fetchStorageStats();
    }, delayMs);
  }

  /**
   * Refresh the access token
   * @returns The refresh token response
   */
  async function refreshAccessToken() {
    try {
      const response = await apiRefreshToken();
      setToken(response.token);
      setUser(response.user as UserProfile);
      return response;
    } catch (error) {
      // If refresh fails, logout the user
      logout();
      throw error;
    }
  }

  async function updatePreference(changes: UpdateUserPreferenceRequest) {
    if (!isAuthenticated.value) {
      throw new Error('User is not authenticated');
    }

    const nextPreference = await apiUpdatePreference(changes);
    const currentUser = user.value;
    if (currentUser) {
      setUser({
        ...currentUser,
        preference: nextPreference,
      });
    }
    return nextPreference;
  }

  function logout() {
    apiLogout().catch(() => undefined);
    if (storageRefreshTimer !== null) {
      clearTimeout(storageRefreshTimer);
      storageRefreshTimer = null;
    }
    setToken(null);
    setUser(null);
    storageStats.value = null;
    // In a real app, you'd probably want to redirect to the login page
    // router.push('/login');
  }

  // Fetch initial data if authenticated
  applyUserLocale(user.value);
  if (isAuthenticated.value) {
    fetchUserProfile();
    if (user.value?.emailVerified !== false) {
      fetchStorageStats();
    }
  }

  return { 
    token, 
    user, 
    storageStats,
    isAuthenticated,
    isAdmin,
    setToken, 
    setUser,
    login,
    logout,
    refreshAccessToken,
    updatePreference,
    fetchUserProfile,
    fetchStorageStats,
    scheduleStorageStatsRefresh,
  };
});
