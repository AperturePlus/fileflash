import { defineConfig, loadEnv } from 'vite'
import vue from '@vitejs/plugin-vue'

// https://vite.dev/config/
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '');
  const isElectronRuntime = env.VITE_APP_RUNTIME === 'electron';

  return {
    plugins: [vue()],
    // Electron file:// mode requires relative asset paths.
    base: isElectronRuntime ? './' : '/',
  };
})
