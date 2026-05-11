<template>
  <footer class="app-footer">
    <p>&copy; {{ new Date().getFullYear() }} FileFlash. All rights reserved.</p>
    <div class="footer-links">
      <a href="#">Terms of Service</a>
      <a href="#">Privacy Policy</a>
    </div>
  </footer>
</template>

<style scoped>
.app-footer {
  display: flex; align-items: center; justify-content: space-between;
  height: var(--layout-footer-height);
  padding: 0 var(--sp-lg);
  background: var(--surface-raised);
  border-top: 1px solid var(--border-default);
  color: var(--text-dim);
  font-size: var(--text-small);
  flex-shrink: 0;
}
.footer-links { display: flex; gap: var(--sp-md); }
.footer-links a { color: var(--text-dim); text-decoration: none; transition: color var(--mo-duration-fast) var(--mo-easing); }
.footer-links a:hover { color: var(--text-primary); }
</style>
