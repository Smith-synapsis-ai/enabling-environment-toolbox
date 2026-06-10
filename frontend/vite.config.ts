import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    allowedHosts: ['.synapsis-analytics.com'],
    proxy: {
      '/api': {
        target: 'http://localhost:8099',
        changeOrigin: true,
      },
      '/ws': {
        target: 'http://localhost:8099',
        changeOrigin: true,
        ws: true,
      },
    },
  },
})
