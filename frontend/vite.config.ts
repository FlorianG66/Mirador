import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vitest/config'

// Configuration Vite du frontend.
// En dev, les appels /api/* sont proxifiés vers le backend FastAPI (uvicorn
// lancé sur 127.0.0.1:8000) : le navigateur reste en same-origin, inutile de
// toucher à la règle CORS pour le développement.
export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
    },
  },
  test: {
    environment: 'jsdom',
    setupFiles: ['./src/test/setup.ts'],
  },
})
