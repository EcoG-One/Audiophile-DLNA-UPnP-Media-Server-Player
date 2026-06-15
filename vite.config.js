import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    host: true, // Listen on all network interfaces
    proxy: {
      // Forward all API requests to the Python DLNA server
      '/api': {
        target: 'http://localhost:8080',
        changeOrigin: true,
        secure: false,
      },
      // Forward audio streaming requests
      '/media': {
        target: 'http://localhost:8080',
        changeOrigin: true,
        secure: false,
      },
      // Forward album art image requests
      '/art': {
        target: 'http://localhost:8080',
        changeOrigin: true,
        secure: false,
      }
    }
  }
})