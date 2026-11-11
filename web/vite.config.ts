import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// 开发时把 /api 转发到本地 FastAPI（uvicorn 默认 8000 端口），无需修改后端 CORS。
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/api': 'http://127.0.0.1:8000',
    },
  },
})
