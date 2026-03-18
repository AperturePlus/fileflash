import { defineStore } from 'pinia';
import { ref, computed } from 'vue';
import { login as apiLogin, getProfile, getStorageStats, refreshToken as apiRefreshToken } from '../api/user';
import type { LoginRequest, User, UserProfile, StorageStats } from '../types/user';


export const useUserStore = defineStore('user', () => {
  const token = ref<string | null>(localStorage.getItem('authToken'));
  const refreshToken = ref<string | null>(localStorage.getItem('refreshToken'));
  const user = ref<UserProfile | User | null>(null);
  const storageStats = ref<StorageStats | null>(null);

  const isAuthenticated = computed(() => !!token.value);

  /**
   * Set the token
   * @param newToken - The new token
   * @param newRefreshToken - The new refresh token
   */
  function setToken(newToken: string | null, newRefreshToken?: string | null) {
    token.value = newToken;
    if (newRefreshToken !== undefined) {
      refreshToken.value = newRefreshToken;
    }
    
    if (newToken) {
      localStorage.setItem('authToken', newToken);
    } else {
      localStorage.removeItem('authToken');
    }
    
    if (newRefreshToken) {
      localStorage.setItem('refreshToken', newRefreshToken);
    } else if (newRefreshToken === null) {
      localStorage.removeItem('refreshToken');
    }
  }

  /**
   * Login the user
   * @param credentials - The login credentials
   * @returns The login response
   */
  async function login(credentials: LoginRequest) {
    const response = await apiLogin(credentials);
    setToken(response.token, response.refreshToken);
    user.value = response.user as UserProfile; // Assuming login returns full profile for now
    await fetchUserProfile();
  }

  /**
   * Fetch the user profile
   * @returns The user profile
   */
  async function fetchUserProfile() {
    if (!isAuthenticated.value) return;
    try {
      const profile = await getProfile();
      user.value = profile;
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
    try {
      const stats = await getStorageStats();
      storageStats.value = stats;
    } catch (error) {
      console.error('Failed to fetch storage stats:', error);
    }
  }

  /**
   * Refresh the access token
   * @returns The refresh token response
   */
  async function refreshAccessToken() {
    if (!refreshToken.value) {
      throw new Error('No refresh token available');
    }
    
    try {
      const response = await apiRefreshToken();
      setToken(response.token, response.refreshToken);
      user.value = response.user as UserProfile;
      return response;
    } catch (error) {
      // If refresh fails, logout the user
      logout();
      throw error;
    }
  }

  function logout() {
    setToken(null, null);
    user.value = null;
    storageStats.value = null;
    // In a real app, you'd probably want to redirect to the login page
    // router.push('/login');
  }

  // Fetch initial data if authenticated
  if (isAuthenticated.value) {
    fetchUserProfile();
    fetchStorageStats();
  }

  return { 
    token, 
    refreshToken,
    user, 
    storageStats,
    isAuthenticated,
    setToken, 
    login,
    logout,
    refreshAccessToken,
    fetchUserProfile,
    fetchStorageStats,
  };
});
