import axios from 'axios';
import type { AxiosInstance, AxiosRequestConfig, AxiosResponse } from 'axios';
import qs from 'qs';
import { useUserStore } from '../store/user';

// 通过模块扩展为 AxiosRequestConfig 添加自定义属性
declare module 'axios' {
  export interface AxiosRequestConfig {
    useUrlencoded?: boolean;
    skipAuth?: boolean;
    _retry?: boolean;
  }
}

let refreshPromise: Promise<any> | null = null;

function isAuthEndpoint(url: string) {
  return url.includes('/auth/login') || url.includes('/auth/register') || url.includes('/auth/refresh');
}

const instance: AxiosInstance = axios.create({
  baseURL: import.meta.env.VITE_BASE_URL || '/api/v1',
  timeout: 10000,
  withCredentials: true,
  // 配置参数序列化，避免嵌套对象格式
  paramsSerializer: (params) => {
    return qs.stringify(params, { arrayFormat: 'brackets', encode: false });
  },
  // headers: { 'Content-Type': 'application/json' }, // This was causing issues with FormData uploads
});

// --- 请求拦截器 ---
instance.interceptors.request.use(
  (config) => {
    // 在请求发送前，自动附加认证Token
    const userStore = useUserStore();
    const token = userStore.token;

    if (!config.skipAuth && token) {
      config.headers = config.headers || {};
      if (!config.headers.Authorization) {
        config.headers.Authorization = `Bearer ${token}`;
      }
    }

    // 根据配置，处理 application/x-www-form-urlencoded 格式的数据
    if (config.useUrlencoded && config.data) {
      config.data = qs.stringify(config.data);
      if (config.headers) {
        config.headers['Content-Type'] = 'application/x-www-form-urlencoded';
      }
    }

    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// --- 响应拦截器 ---
instance.interceptors.response.use(
  /**
   * 成功的响应会先进入这里。
   * 我们对响应数据进行解包，直接返回 API 响应中的 `data` 部分。
   */
  (response: AxiosResponse<any>) => {
    // 检查是否是文件流响应
    if (response.request?.responseType === 'blob' && response.data instanceof Blob) {
      // 如果响应是一个 Blob，并且HTTP状态码是200，直接返回它
      if (response.status === 200) {
        return response.data;
      }
      // 如果HTTP状态码不是200, Blob中可能包含错误信息
      return new Promise((_resolve, reject) => {
        const reader = new FileReader();
        reader.onload = () => {
          try {
            const errorData = JSON.parse(reader.result as string);
            console.error('API Error (from blob):', errorData.message || 'Unknown error');
            reject(new Error(errorData.message || 'An error occurred during file download.'));
          } catch (e) {
            reject(new Error('An error occurred during file download.'));
          }
        };
        reader.onerror = () => {
          reject(new Error('Failed to read error response from blob.'));
        };
        reader.readAsText(response.data);
      });
    }

    const res = response.data;

    // 检查是否是项目定义的标准API响应结构
    if (typeof res === 'object' && res !== null && 'success' in res && 'code' in res) {
      if (res.success) {
        // 如果业务成功，直接返回核心数据
        return res.data;
      } else {
        // 如果业务失败，统一处理错误信息，并中断Promise链
        console.error('API Error:', res.message || `Error Code: ${res.code}`);
        // 可在此处添加全局错误提示，例如使用UI库的Message组件
        return Promise.reject(new Error(res.message || 'API Error'));
      }
    }
    
    // 对于非标准响应（如文件流），直接返回响应数据
    return res;
  },
  /**
   * 失败的响应（HTTP状态码非2xx）会进入这里。
   */
  async (error) => {
    if (error.response) {
      const { status, data } = error.response;
      const errorMessage = data?.message || error.message;

      switch (status) {
        case 401:
          {
            const userStore = useUserStore();
            const originalRequest = error.config as AxiosRequestConfig;
            const requestUrl = String(originalRequest?.url || '');

            const canAttemptRefresh =
              !!userStore.token &&
              !!originalRequest &&
              !originalRequest.skipAuth &&
              !originalRequest._retry &&
              !isAuthEndpoint(requestUrl);

            if (canAttemptRefresh) {
              originalRequest._retry = true;
              try {
                refreshPromise =
                  refreshPromise || instance.post('/auth/refresh', undefined, { skipAuth: true });
                const refreshed = await refreshPromise;
                refreshPromise = null;

                userStore.setToken(refreshed.token);
                userStore.setUser(refreshed.user);

                originalRequest.headers = originalRequest.headers || {};
                if (!originalRequest.headers.Authorization) {
                  originalRequest.headers.Authorization = `Bearer ${refreshed.token}`;
                } else {
                  originalRequest.headers.Authorization = `Bearer ${refreshed.token}`;
                }

                return instance(originalRequest);
              } catch (refreshError) {
                refreshPromise = null;
                console.error(`[401] 刷新 Token 失败: ${errorMessage}`);
                userStore.logout();
                return Promise.reject(refreshError);
              }
            }

            console.error(`[401] 认证失败: ${errorMessage}`);
            if (userStore.token) {
              userStore.logout();
            }
            break;
          }
        case 403:
          console.error(`[403] 禁止访问: ${errorMessage}`);
          break;
        case 404:
          console.error(`[404] 资源未找到: ${errorMessage}`);
          break;
        case 500:
            console.error(`[500] 服务器错误: ${errorMessage}`);
            break;
        case 502:
            console.error(`[502] 网关错误: ${errorMessage}`);
            break;
        case 503:
            console.error(`[503] 服务不可用: ${errorMessage}`);
            break;
        case 504:
            console.error(`[504] 网关超时: ${errorMessage}`);
            break;
        default:
          console.error(`[${status}] 请求错误: ${errorMessage}`);
          break;
      }
    } else if (error.request) {
      console.error('网络错误，无法连接到服务器');
    } else {
      console.error('请求设置错误:', error.message);
    }
    return Promise.reject(error);
  }
);

/**
 * 导出的HTTP客户端，提供类型化的请求方法。
 * @template T - 成功响应时期望的数据类型。
 * 
 * @example
 * import http from '@/utils/http';
 * import { User } from '@/types/user';
 * 
 * async function fetchUser() {
 *   try {
 *     const user = await http.get<User>('/user/profile');
 *     console.log(user); // user 是 User 类型的对象
 *   } catch (error) {
 *     console.error('Failed to fetch user:', error);
 *   }
 * }
 */
const http = {
  get: <T>(url: string, params?: object, config?: AxiosRequestConfig): Promise<T> =>
    instance.get(url, { params, ...config }),

  post: <T>(url: string, data?: any, config?: AxiosRequestConfig): Promise<T> =>
    instance.post(url, data, config),

  put: <T>(url: string, data?: any, config?: AxiosRequestConfig): Promise<T> =>
    instance.put(url, data, config),

  patch: <T>(url: string, data?: any, config?: AxiosRequestConfig): Promise<T> =>
    instance.patch(url, data, config),

  delete: <T>(url: string, config?: AxiosRequestConfig): Promise<T> =>
    instance.delete(url, config),
};

export default http;  
