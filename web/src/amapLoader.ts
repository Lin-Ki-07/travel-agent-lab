// 按需加载高德 JS API 2.0。只使用浏览器端 JS Key；不接触 Web 服务 Key。

// 仅声明本项目用到的最小类型，避免引入额外依赖。
export interface AMapMap {
  add(overlays: unknown[]): void
  remove(overlays: unknown[]): void
  clearMap(): void
  setFitView(overlays?: unknown[], immediately?: boolean, margins?: number[]): void
  resize(): void
  destroy(): void
}

export interface AMapNamespace {
  Map: new (container: HTMLElement, options: Record<string, unknown>) => AMapMap
  Marker: new (options: Record<string, unknown>) => unknown
  Polyline: new (options: Record<string, unknown>) => unknown
}

declare global {
  interface Window {
    AMap?: AMapNamespace
    _AMapSecurityConfig?: { securityJsCode: string }
  }
}

export interface AmapConfig {
  key: string
  securityCode?: string
}

export function readAmapConfig(): AmapConfig | null {
  const key = import.meta.env.VITE_AMAP_JS_KEY?.trim()
  if (!key || key.startsWith('填写')) return null
  const securityCode = import.meta.env.VITE_AMAP_SECURITY_CODE?.trim()
  return securityCode ? { key, securityCode } : { key }
}

let loading: Promise<AMapNamespace> | null = null

export function loadAmap(config: AmapConfig): Promise<AMapNamespace> {
  if (window.AMap) return Promise.resolve(window.AMap)
  if (loading) return loading

  if (config.securityCode) {
    window._AMapSecurityConfig = { securityJsCode: config.securityCode }
  }

  loading = new Promise<AMapNamespace>((resolve, reject) => {
    const script = document.createElement('script')
    script.src = `https://webapi.amap.com/maps?v=2.0&key=${encodeURIComponent(config.key)}`
    script.async = true
    script.onload = () => {
      if (window.AMap) {
        resolve(window.AMap)
      } else {
        loading = null
        reject(new Error('高德地图脚本已加载，但未找到 AMap 对象。'))
      }
    }
    script.onerror = () => {
      loading = null
      reject(new Error('高德地图脚本加载失败，请检查网络或 JS Key 配置。'))
    }
    document.head.appendChild(script)
  })
  return loading
}
