const TOKEN_KEY = 'kaoyan_token'

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
  const res = await fetch(path, {
    method,
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${getToken()}`,
    },
    body: body === undefined ? undefined : JSON.stringify(body),
  })
  if (res.status === 401) {
    clearToken()
    if (!location.hash.includes('/login')) location.hash = '#/login'
    throw new ApiError(401, '未登录或登录失效')
  }
  if (!res.ok) {
    let msg = `请求失败 ${res.status}`
    try {
      const data = await res.json()
      if (data.detail) msg = data.detail
    } catch { /* ignore */ }
    throw new ApiError(res.status, msg)
  }
  return res.json()
}

/** SSE 消费：onEvent 收到每个 data JSON 对象 */
export async function sse(path, { onEvent } = {}) {
  const res = await fetch(path, { headers: { Authorization: `Bearer ${getToken()}` } })
  if (res.status === 401) {
    clearToken()
    location.hash = '#/login'
    throw new ApiError(401, '未登录或登录失效')
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
