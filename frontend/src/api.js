const TOKEN_KEY = 'kaoyan_token'

// 部署子路径（vite base 注入），所有请求统一加前缀
const BASE = (import.meta.env.BASE_URL || '/').replace(/\/$/, '')
function prefixed(path) {
  return path.startsWith('/') ? BASE + path : BASE + '/' + path
}

// 全局错误提示（5xx / 网络错误在这里兜底提示；4xx 由页面自行处理业务含义）
let globalMessage = null
export function bindGlobalToast(messageApi) {
  globalMessage = messageApi
}
function toastError(msg) {
  if (globalMessage) globalMessage.error(msg)
}

export function getToken() {
  return localStorage.getItem(TOKEN_KEY) || ''
}
export function setToken(t) {
  localStorage.setItem(TOKEN_KEY, t)
}
export function clearToken() {
  localStorage.removeItem(TOKEN_KEY)
}

export class ApiError extends Error {
  constructor(status, message) {
    super(message)
    this.status = status
  }
}

export async function api(path, { method = 'GET', body } = {}) {
  let res
  try {
    res = await fetch(prefixed(path), {
      method,
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${getToken()}`,
      },
      body: body === undefined ? undefined : JSON.stringify(body),
    })
  } catch (e) {
    toastError('网络异常：无法连接服务器')
    throw new ApiError(0, '网络异常：无法连接服务器')
  }
  if (res.status === 401) {
    clearToken()
    if (!location.hash.includes('/login')) location.hash = '#/login'
    const err = new ApiError(401, '未登录或登录失效')
    err.silent = true  // 静默跳登录页，页面不再弹错误框
    throw err
  }
  if (!res.ok) {
    let msg = `请求失败 ${res.status}`
    try {
      const data = await res.json()
      if (data.detail) msg = data.detail
    } catch { /* ignore */ }
    if (res.status >= 500) toastError(`服务异常（${res.status}）：` + msg)
    throw new ApiError(res.status, msg)
  }
  return res.json()
}

/** SSE 消费：onEvent 收到每个 data JSON 对象 */
export async function sse(path, { onEvent } = {}) {
  const res = await fetch(prefixed(path), { headers: { Authorization: `Bearer ${getToken()}` } })
  if (res.status === 401) {
    clearToken()
    location.hash = '#/login'
    const err = new ApiError(401, '未登录或登录失效')
    err.silent = true
    throw err
  }
  if (!res.ok || !res.body) throw new ApiError(res.status, '连接失败')
  const reader = res.body.getReader()
  const decoder = new TextDecoder()
  let buf = ''
  for (;;) {
    const { done, value } = await reader.read()
    if (done) break
    buf += decoder.decode(value, { stream: true })
    let idx
    while ((idx = buf.indexOf('\n\n')) >= 0) {
      const frame = buf.slice(0, idx)
      buf = buf.slice(idx + 2)
      const line = frame.split('\n').find((l) => l.startsWith('data: '))
      if (line) {
        try {
          onEvent(JSON.parse(line.slice(6)))
        } catch { /* 忽略坏帧 */ }
      }
    }
  }
}
