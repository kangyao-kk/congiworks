const BASE_URL = 'http://localhost:8080/api';

/**
 * 核心请求函数 — 根据 body 类型自动选择 JSON / FormData / SSE
 *
 * @param {string} method   - GET | POST | PATCH | DELETE
 * @param {string} path     - 接口路径
 * @param {object|FormData} [body] - 请求体
 * @param {{ raw?: boolean }} [opts]
 * @returns {Promise<Response|any>}  raw=true 时返回 Response，否则返回解析后的 JSON
 */
export async function request(method, path, body, opts = {}) {
  const url = `${BASE_URL}${path}`;
  const fetchOpts = { method };

  if (body instanceof FormData) {
    fetchOpts.body = body;
  } else if (body) {
    fetchOpts.headers = { 'Content-Type': 'application/json' };
    fetchOpts.body = JSON.stringify(body);
  }

  const res = await fetch(url, fetchOpts);

  if (opts.raw) return res;

  if (!res.ok) {
    const errBody = await res.json().catch(() => ({}));
    throw new Error(errBody.error || `HTTP ${res.status}`);
  }
  return res.json();
}

export const api = {
  get: (path) => request('GET', path),
  post: (path, body, opts) => request('POST', path, body, opts),
  patch: (path, body) => request('PATCH', path, body),
  delete: (path) => request('DELETE', path),
};
