<template>
  <footer class="app-footer">
    <p>&copy; {{ new Date().getFullYear() }} fileflash. All rights reserved.</p>
    <div class="footer-links">
      <router-link to="/terms">Terms of Use</router-link>
      <router-link to="/privacy">Privacy Policy</router-link>
    </div>
  </footer>
</template>

<style scoped>
.app-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: var(--layout-footer-height);
  padding: 0 var(--spacing-lg);
  background-color: var(--color-bg-secondary);
  border-top: 1px solid var(--color-border);
  color: var(--color-text-tertiary);
  font-size: 0.875rem;
  flex-shrink: 0;
  transition: background-color var(--transition-base), border-color var(--transition-base);
}

.footer-links {
  display: flex;
  gap: var(--spacing-md);
}

.footer-links a {
  color: var(--color-text-tertiary);
  text-decoration: none;
}

.footer-links a:hover {
  color: var(--color-text-primary);
}
</style> 