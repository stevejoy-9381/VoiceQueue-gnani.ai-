import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

export default defineConfig({
  plugins: [react()],
  server: {
    host: '0.0.0.0',
    port: 5173,
    proxy: {
      '/voice': 'http://127.0.0.1:8000',
      '/text': 'http://127.0.0.1:8000',
      '/tokens': 'http://127.0.0.1:8000',
      '/queue': 'http://127.0.0.1:8000',
      '/health': 'http://127.0.0.1:8000',
      '/demo': 'http://127.0.0.1:8000',
      '/voice-logs': 'http://127.0.0.1:8000',
      '/voice-tests': 'http://127.0.0.1:8000',
      '/usage': 'http://127.0.0.1:8000',
      '/debug-audio': 'http://127.0.0.1:8000',
      '/audio-lab/turns': 'http://127.0.0.1:8000',
      '/audio-compare': 'http://127.0.0.1:8000',
      '/ws': {
        target: 'ws://127.0.0.1:8000',
        ws: true,
      },
    },
  },
})
