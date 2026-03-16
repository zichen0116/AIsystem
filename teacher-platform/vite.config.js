import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
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
