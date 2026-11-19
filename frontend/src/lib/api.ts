export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? ''

export const resourceUrl = (path: string) => `${API_BASE_URL}${path}`

export async function api<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response
  try {
    response = await fetch(resourceUrl(path), init)
  } catch {
    throw new Error('无法连接服务，请检查后端是否已启动。')
  }
  if (!response.ok) {
    const body = await response.json().catch(() => ({}))
    throw new Error(
      typeof body.detail === 'string'
        ? body.detail
        : body.detail
          ? '输入格式不正确，请检查后重试。'
          : `请求失败（${response.status}）`,
    )
  }
  return response.json()
}

export const post = <T>(path: string, body?: unknown) =>
  api<T>(path, {
    method: 'POST',
    ...(body === undefined
      ? {}
      : { headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) }),
  })
