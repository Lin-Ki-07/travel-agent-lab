/// <reference types="vite/client" />

interface ImportMetaEnv {
  // 高德 JS API Key（浏览器端，不是 Web 服务 Key）。本地配置于 web/.env.local。
  readonly VITE_AMAP_JS_KEY?: string
  // 若高德控制台启用了安全密钥，填写对应的 securityJsCode。
  readonly VITE_AMAP_SECURITY_CODE?: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}
