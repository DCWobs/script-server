<template>
  <button 
    class="btn-icon-flat waves-effect waves-circle theme-toggle" 
    :title="isDark ? 'Switch to light mode' : 'Switch to dark mode'"
    @click="toggleTheme">
    <i class="material-icons primary-color-text">{{ isDark ? 'light_mode' : 'dark_mode' }}</i>
  </button>
</template>

<script>
const THEME_KEY = 'wobbler-theme';

export default {
  name: 'ThemeToggle',
  
  data() {
    return {
      isDark: false
    }
  },

  created() {
    this.initTheme();
  },

  methods: {
    initTheme() {
      const savedTheme = localStorage.getItem(THEME_KEY);
      
      if (savedTheme) {
        this.isDark = savedTheme === 'dark';
      } else {
        // Check system preference
        this.isDark = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
      }
      
      this.applyTheme();
    },

    toggleTheme() {
      this.isDark = !this.isDark;
      localStorage.setItem(THEME_KEY, this.isDark ? 'dark' : 'light');
      this.applyTheme();
    },

    applyTheme() {
      document.documentElement.setAttribute('data-theme', this.isDark ? 'dark' : 'light');
    }
  }
}
</script>

<style scoped>
.theme-toggle {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background: transparent;
  border: none;
  cursor: pointer;
  transition: background-color 0.2s ease;
}

.theme-toggle:hover {
  background-color: var(--hover-color);
}

.theme-toggle i {
  font-size: 24px;
}
</style>

