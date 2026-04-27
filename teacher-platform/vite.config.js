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
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: ['./src/test/setup.js'],
  },
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
      // 讯飞数字人 Web SDK 相关请求代理（官方要求）
      '/vmss': {
        target: 'http://vms.cn-huadong-1.xf-yun.com',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/vmss/, ''),
      },
      // 可选：个性化资源上传代理（背景/模板）
      '/individuation': {
        target: 'http://evo-hu.xf-yun.com',
        changeOrigin: true,
      },
    },
  },
})
