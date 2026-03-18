import { createApp } from 'vue'
import { createPinia } from 'pinia';
import './style.css'
import App from './App.vue'
import router from './router';

// --- Mock Service ---
// Note: In a real application, this would be conditional,
// e.g., only in development mode.
 import './mock'; // 禁用Mock服务，连接真实后端

const app = createApp(App);
const pinia = createPinia();

app.use(pinia);
app.use(router);

app.mount('#app');
    
