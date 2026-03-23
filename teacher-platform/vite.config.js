import { fileURLToPath, URL } from 'node:url'
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
  plugins: [vue()],
  server: {
    proxy: {
      // 将前端开发环境的 /api 请求转发到后端 FastAPI
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      // 下载/预览静态文件（如有）
      '/media': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
})
