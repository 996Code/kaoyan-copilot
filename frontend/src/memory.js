/** 轻量本地记忆：筛选条件 / 滚动位置 / 做题进度，跨刷新与重进恢复。 */

const PREFIX = 'ky_mem_'

export function remember(key, value) {
  try {
    localStorage.setItem(PREFIX + key, JSON.stringify(value))
  } catch { /* 忽略容量/隐私模式异常 */ }
}

export function recall(key, defaultValue = null) {
  try {
    const raw = localStorage.getItem(PREFIX + key)
    return raw === null ? defaultValue : JSON.parse(raw)
  } catch {
    return defaultValue
  }
}
