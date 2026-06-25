import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig(({ mode }) => ({
  plugins: [react()],
  base: mode === 'production' ? '/ui/' : '/',
  server: {
    port: 3000,
    proxy: {
      '/apps': { target: 'http://localhost:8080', changeOrigin: true },
      '/list-apps': { target: 'http://localhost:8080', changeOrigin: true },
      '/run_sse': { target: 'http://localhost:8080', changeOrigin: true },
      '/run': { target: 'http://localhost:8080', changeOrigin: true },
    },
  },
  build: {
    outDir: 'dist',
    assetsDir: 'assets',
  },
}))
